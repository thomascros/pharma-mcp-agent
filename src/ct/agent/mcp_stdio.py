"""Standalone stdio MCP server for Claude Code integration.

Exposes all ct tools via the MCP stdio protocol so Claude Code can connect
to them directly. The existing in-process server (mcp_server.py) is kept
for the ct CLI / AgentRunner — this file is only for Claude Code.

Usage (Claude Code wires this up via .claude/settings.json):
    uv run ct-mcp-server
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from ct.agent.mcp_server import _format_tool_result, _params_to_json_schema
from ct.tools import registry

logger = logging.getLogger("ct.mcp_stdio")

server = Server("ct-tools")

# Sandbox created once on first use, persists for the process lifetime.
# This mirrors the in-process server behaviour: variables carry over between
# run_python calls within the same Claude Code session.
_sandbox = None


def _get_sandbox():
    global _sandbox
    if _sandbox is None:
        from ct.agent.sandbox import Sandbox
        _sandbox = Sandbox()
    return _sandbox


def _coerce(val: Any) -> Any:
    """Coerce a string argument to int/float/bool when appropriate.

    MCP sends all arguments as strings. Tools often expect typed values.
    """
    if not isinstance(val, str):
        return val
    try:
        return int(val)
    except ValueError:
        pass
    try:
        return float(val)
    except ValueError:
        pass
    if val.lower() in ("true", "false"):
        return val.lower() == "true"
    return val


# ---------------------------------------------------------------------------
# Tool listing
# ---------------------------------------------------------------------------

@server.list_tools()
async def list_tools() -> list[Tool]:
    import os
    from ct.tools import EXPERIMENTAL_CATEGORIES

    tools: list[Tool] = []

    # CT_MCP_MAX_TOOLS=N limits the tool list (useful for diagnosing response-size
    # issues with the MCP client; set to 1 to verify connectivity with a minimal
    # payload before enabling the full tool set).
    max_tools = int(os.environ.get("CT_MCP_MAX_TOOLS", "0")) or None

    for tool in registry.list_tools():
        if tool.category in EXPERIMENTAL_CATEGORIES:
            continue
        if max_tools is not None and len(tools) >= max_tools:
            break
        desc = tool.description
        if tool.usage_guide:
            desc += f"\n\nUSE WHEN: {tool.usage_guide}"
        # Claude API requires tool names matching ^[a-zA-Z0-9_-]{1,64}$.
        # Internal names use dots (e.g. "target.coessentiality"); replace with
        # hyphens so the API accepts them.  call_tool() reverses this mapping.
        tools.append(Tool(
            name=tool.name.replace(".", "-"),
            description=desc,
            inputSchema=_params_to_json_schema(tool.parameters),
        ))

    # run_python — persistent Python sandbox
    tools.append(Tool(
        name="run_python",
        description=(
            "Execute Python code in a persistent sandbox. Variables persist between "
            "calls within a session. Pre-imported: pd, np, plt, sns, scipy_stats, sklearn, "
            "json, re, math, os, glob, gzip, csv, zipfile, io, Path. "
            "Save plots: plt.savefig(OUTPUT_DIR / 'name.png', dpi=150, bbox_inches='tight'). "
            "Assign result = {'summary': '...', 'answer': '...'} to surface structured output."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "code": {"type": "string", "description": "Python code to execute"},
            },
            "required": ["code"],
        },
    ))

    # run_r — R execution via rpy2 (optional, only if rpy2 is installed)
    try:
        import rpy2.robjects  # noqa: F401
        tools.append(Tool(
            name="run_r",
            description=(
                "Execute R code via rpy2. Prefer over run_python for: natural splines (ns()), "
                "wilcox.test(), p.adjust(), fisher.test(), lm()/predict(), DESeq2, KEGGREST, "
                "survival analysis, and any analysis where R is the reference implementation. "
                "R and Python give DIFFERENT results for splines, multiple testing correction, "
                "and nonparametric tests — use R when the expected answer was computed in R."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "code": {"type": "string", "description": "R code to execute"},
                },
                "required": ["code"],
            },
        ))
    except ImportError:
        pass

    return tools


# ---------------------------------------------------------------------------
# Tool dispatch
# ---------------------------------------------------------------------------

@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    if name == "run_python":
        return await _handle_run_python(arguments)
    if name == "run_r":
        return await _handle_run_r(arguments)

    # Reverse the dot→hyphen mapping applied in list_tools().
    internal_name = name.replace("-", ".")
    tool = registry.get_tool(internal_name)
    if tool is None:
        return [TextContent(type="text", text=f"Unknown tool: {name}")]

    call_args = {k: _coerce(v) for k, v in arguments.items()}
    try:
        result = await asyncio.to_thread(tool.function, **call_args)
    except Exception as exc:
        logger.exception("Tool %s failed", name)
        result = {"error": str(exc), "summary": f"Tool {name} raised an exception: {exc}"}

    return [TextContent(type="text", text=_format_tool_result(result))]


# ---------------------------------------------------------------------------
# run_python handler
# ---------------------------------------------------------------------------

async def _handle_run_python(arguments: dict) -> list[TextContent]:
    code = arguments.get("code", "").strip()
    if not code:
        return [TextContent(type="text", text="Error: no code provided")]

    sandbox = _get_sandbox()
    exec_result = await asyncio.to_thread(sandbox.execute, code)

    parts: list[str] = []
    if exec_result.get("stdout"):
        parts.append(exec_result["stdout"])
    if exec_result.get("error"):
        parts.append(f"Error:\n{exec_result['error']}")
    if exec_result.get("plots"):
        parts.append(f"Plots saved: {exec_result['plots']}")
    if exec_result.get("exports"):
        parts.append(f"Exports saved: {exec_result['exports']}")

    result_var = sandbox.get_variable("result")
    if result_var and isinstance(result_var, dict):
        if result_var.get("summary"):
            parts.append(f"\nResult summary: {result_var['summary']}")
        if result_var.get("answer"):
            parts.append(f"Result answer: {result_var['answer']}")

    text = "\n".join(parts) if parts else "(no output)"
    return [TextContent(type="text", text=text[:6000])]


# ---------------------------------------------------------------------------
# run_r handler
# ---------------------------------------------------------------------------

async def _handle_run_r(arguments: dict) -> list[TextContent]:
    code = arguments.get("code", "").strip()
    if not code:
        return [TextContent(type="text", text="Error: no R code provided")]

    def _exec_r(code: str) -> str:
        try:
            import rpy2.robjects as ro
            from rpy2.robjects import numpy2ri, pandas2ri

            wrapper = f"paste(capture.output({{ {code} }}), collapse='\\n')"
            try:
                captured = ro.r(wrapper)
                output_text = str(captured[0]) if captured else ""
            except Exception:
                try:
                    result = ro.r(code)
                    output_text = str(result)[:3000]
                except Exception as e2:
                    return f"R Error: {e2}"

            result_text = ""
            try:
                result = ro.r(code)
                if result is not None and result != ro.NULL:
                    numpy2ri.activate()
                    pandas2ri.activate()
                    try:
                        if hasattr(result, "__len__") and len(result) == 1:
                            result_text = f"\nReturn value: {float(result[0])}"
                        elif hasattr(result, "__len__") and len(result) <= 50:
                            result_text = f"\nReturn value: [{', '.join(str(x) for x in result)}]"
                        else:
                            result_text = f"\nReturn value: {str(result)[:2000]}"
                    except Exception:
                        result_text = f"\nReturn value: {str(result)[:2000]}"
                    finally:
                        numpy2ri.deactivate()
                        pandas2ri.deactivate()
            except Exception:
                pass

            return (output_text + result_text).strip() or "(no output)"
        except Exception as e:
            return f"R Error: {e}"

    text = await asyncio.to_thread(_exec_r, code)
    return [TextContent(type="text", text=text[:6000])]


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    logging.basicConfig(level=logging.WARNING)

    # Pre-load all tools before the MCP event loop starts so that the
    # tools/list response is instant.  Without this, ensure_loaded() runs
    # inside the async list_tools() handler and the ~1-2 s blocking import
    # causes the client's pending-request entry to expire before the response
    # arrives, producing "unknown message ID" errors.
    from ct.tools import ensure_loaded
    ensure_loaded()

    async def _run() -> None:
        async with stdio_server() as (r, w):
            await server.run(r, w, server.create_initialization_options())

    asyncio.run(_run())
