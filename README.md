# Drug Discovery Agent — MCP-powered research assistant

## What this is

190+ drug discovery tools exposed as an MCP server for Claude Code. The tools cover target
prioritization, compound profiling, indication mapping, safety assessment, and clinical trial
analysis. They connect directly to PubMed, ChEMBL, UniProt, Open Targets, ClinicalTrials.gov,
Reactome, PDBe, GEO, and 25+ other databases. No Anthropic API key required — the server runs
on a Claude subscription via Claude Code.

## Why I built this

I came across [celltype-agent](https://github.com/celltype/cli) while exploring the intersection of agentic AI and drug discovery. The original system runs inside the Claude Agent SDK and requires an Anthropic API key with per-token billing. I wanted to use it through Claude Code on a subscription plan, so I reconfigured the tool registry as a standalone MCP server over stdio transport. The result is a Claude Code-native version of the same 190+ tool set. 

## What I changed from the original

The original system wires the tool registry into the Claude Agent SDK via `create_ct_mcp_server()`
in `src/ct/agent/mcp_server.py`. That function creates an in-process MCP server used by the `ct`
CLI agent — it requires an Anthropic API key and bills per token.

I added `src/ct/agent/mcp_stdio.py`, which exposes the same tool registry via `mcp.server.Server`
over stdio transport. Claude Code connects to it as an MCP client. Four implementation details
worth noting:

- **Tool pre-loading.** All tools are imported before the MCP event loop starts. Without this,
  the first `tools/list` call blocks for 1-2 seconds on imports, and the MCP client's
  pending-request entry expires before the response arrives — producing "unknown message ID" errors.

- **Name mapping.** Internal tool names use dots (`target.coessentiality`). The Claude API
  requires names matching `^[a-zA-Z0-9_-]{1,64}$`, so dots are replaced with hyphens in
  `list_tools()` and reversed in `call_tool()`.

- **Type coercion.** MCP sends all tool arguments as strings. The server coerces them to
  `int`, `float`, or `bool` where the value warrants it, since tool functions often expect
  typed parameters.

- **Persistent sandbox.** The `run_python` sandbox is a singleton for the process lifetime.
  Variables declared in one tool call are available in the next, matching how the original
  in-process server behaved.

The entry point is registered in `pyproject.toml` as `ct-mcp-server`, so `.mcp.json` only needs
`uv run ct-mcp-server`.

## Architecture

```
Claude Code
    │  MCP stdio (stdin/stdout)
    ▼
ct-mcp-server  ←  src/ct/agent/mcp_stdio.py
    │
    ├── Tool registry  ←  src/ct/tools/
    │       190+ domain tools
    │
    └── Persistent Python sandbox  (run_python · run_r)
            │
            ▼
    External APIs
        PubMed · ChEMBL · UniProt · Open Targets · ClinicalTrials.gov
        Reactome · PDBe · GEO · GWAS Catalog · GTEx · CELLxGENE
        DepMap · PRISM · L1000 · PubChem · FAERS · ...
```

## Tools available

| Category | What it does | Key databases |
|----------|-------------|---------------|
| **Target** | Druggability, co-essentiality, disease association, expression profiling | Open Targets, DepMap, UniProt |
| **Chemistry** | SAR analysis, scaffold hopping, similarity search, retrosynthesis, ADMET | PubChem, ChEMBL, RDKit |
| **Clinical** | Trial search, indication mapping, population sizing, TCGA stratification | ClinicalTrials.gov, TCGA |
| **Safety** | ADMET prediction, anti-target profiling, SALL4 risk, DDI screening | FAERS, ChEMBL |
| **Literature** | Full-text search, patent search, preprints | PubMed, OpenAlex, Espacenet |
| **Expression / Omics** | Pathway enrichment, L1000 signatures, TF activity, DESeq2, scRNA-seq | GEO, CELLxGENE, CLUE/L1000 |
| **Genomics** | GWAS lookup, eQTL, Mendelian randomization, colocalization | GWAS Catalog, GTEx, OpenTargets genetics |
| **Structure** | AlphaFold fetch, binding site analysis, docking, FEP, ternary complex prediction | RCSB PDB, AlphaFold DB |
| **Data APIs** | Individual gene, protein, variant, pathway, compound, and disease lookups | MyGene, UniProt, Reactome, PDBe, and 20+ more |

Most tools work immediately via public APIs. A subset (DepMap viability, PRISM screening, L1000
transcriptomics) require local data downloads. See
[`src/ct/tools/_tool_classification.md`](src/ct/tools/_tool_classification.md) for the complete
breakdown.

## Setup

**Requirements:** Python 3.10+, [uv](https://docs.astral.sh/uv/) (recommended) or pip, Claude Code.

```bash
git clone <your-fork-url>
cd pharma-mcp-agent
pip install -e .
# or with uv:
uv sync
```

For chemistry tools (SAR, docking, retrosynthesis):
```bash
pip install -e ".[chemistry]"   # requires RDKit
```

For single-cell tools (scRNA-seq clustering, annotation):
```bash
pip install -e ".[singlecell]"  # requires scanpy / anndata
```

**Configure Claude Code.** The `.mcp.json` at the repo root is already set up for project-local
use. For global use, add the same block to `~/.claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "ct-tools": {
      "command": "uv",
      "args": ["run", "ct-mcp-server"]
    }
  }
}
```

**Verify.** Open Claude Code in this directory and ask:

> "Look up the UniProt entry for TP53"

You should see a `ct-tools:data_api-uniprot_lookup` tool call and a result within a few seconds.

## Example queries

**Target validation**
> "What is the genetic evidence for KRAS as a drug target in non-small cell lung cancer?"

Invokes `genomics-gwas_lookup`, `genomics-eqtl_lookup`, `target-disease_association`,
`literature-pubmed_search`. Returns a causal chain from GWAS associations through expression
quantitative trait loci to clinical trial evidence.

**Compound safety profile**
> "Profile the safety and selectivity of vemurafenib — what are the key off-target risks?"

Invokes `safety-classify`, `safety-admet_predict`, `safety-antitarget_profile`,
`literature-chembl_query`. Returns ADMET properties, predicted off-target binding, and a summary
of known clinical adverse events.

**Indication mapping**
> "Which cancer types are most sensitive to BET inhibitors, and what biomarkers predict response?"

Invokes `clinical-indication_map`, `viability-tissue_selectivity`,
`biomarker-mutation_sensitivity`. Returns a ranked indication list with sensitivity data from
PRISM screens and candidate predictive biomarkers.

## Technical notes

- **Most tools need no data download.** They call public APIs and return results immediately.
  [`src/ct/tools/_tool_classification.md`](src/ct/tools/_tool_classification.md) lists which
  tools fall into each category (API-only vs. requires local data).
- **Pre-loading is load-bearing.** Removing the `ensure_loaded()` call before `asyncio.run()`
  in `mcp_stdio.py` will produce intermittent "unknown message ID" errors from the MCP client
  on first connection.
- **API rate limits apply.** PubMed, UniProt, and Open Targets may throttle high-frequency
  queries. The tools have no built-in retry logic — if a call times out, retrying usually works.
- **R execution is optional.** `run_r` is exposed only if rpy2 is installed. It will not appear
  in the tool list otherwise. Useful for DESeq2, survival analysis, and spline fitting where R
  is the reference implementation.

## Credits

All 190+ domain tools, the tool registry, and the original in-process MCP server are the work of
[CellType Inc.](https://github.com/celltype/cli) (MIT license). This fork adds the stdio
transport layer (`src/ct/agent/mcp_stdio.py`) and this documentation to enable Claude Code
integration.
