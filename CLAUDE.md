# Drug Discovery Agent — Claude Code Configuration

## What you have access to

190+ drug discovery tools exposed via an MCP stdio server (`src/ct/agent/mcp_stdio.py`). The
tools call external databases directly — no Anthropic API key is needed. Most work immediately
via public APIs; a subset require local data downloads (see Known Limitations).

You also have two persistent code execution sandboxes:

- **`run_python`** — stateful Python environment. Pre-imported: `pd`, `np`, `plt`, `sns`,
  `scipy_stats`, `sklearn`, `json`, `re`, `math`, `os`, `glob`, `gzip`, `csv`, `zipfile`, `io`,
  `Path`. Variables survive across calls within a session. Save plots with
  `plt.savefig(OUTPUT_DIR / "name.png", dpi=150, bbox_inches="tight")`.

- **`run_r`** — R via rpy2 (only if rpy2 is installed; omitted from tool list otherwise). Prefer
  this for DESeq2, `wilcox.test()`, `p.adjust()`, natural splines (`ns()`), and any analysis
  where R is the reference implementation.

---

## Tool categories and when to use them

### Target tools
**Databases:** Open Targets, DepMap CRISPR, UniProt, GTEx, Human Protein Atlas

- `target-disease_association` — richest single call for a new target: genetic, drug, and
  literature evidence scores across all diseases. Run this first on any target.
- `target-expression_profile` — tissue selectivity and therapeutic window from GTEx + HPA.
- `target-druggability` — structural druggability assessment.
- `target-coessentiality` — functional gene network from DepMap CRISPR screens. *Requires local data.*
- `target-degron_predict`, `target-neosubstrate_score` — PROTAC and molecular glue programs.

### Chemistry tools
**Databases:** PubChem, ChEMBL, RDKit (requires `pip install -e ".[chemistry]"`)

- `chemistry-descriptors` — drug-likeness, Lipinski, TPSA, LogP for any compound.
- `chemistry-sar_analyze` — SAR landscape from ChEMBL for a chemical series.
- `chemistry-mmp_analysis` — matched molecular pair transformations that improve potency or ADMET.
- `chemistry-scaffold_hop`, `chemistry-retrosynthesis` — IP diversification, route scouting.
- `chemistry-similarity_search`, `chemistry-pairwise_similarity` — compound identity and FTO.

### Clinical tools
**Databases:** ClinicalTrials.gov, TCGA, Open Targets

- `clinical-trial_search` — active/recruiting trials, competitor programs, benchmark endpoints.
- `clinical-competitive_landscape` — multi-source competitive intelligence in one call.
- `clinical-indication_map` — maps compound sensitivity to cancer indications. *Requires local data.*
- `clinical-tcga_stratify` — target expression across cancer subtypes in patient tumors.
- `clinical-population_size` — addressable patient population per indication.

### Safety tools
**Databases:** FAERS, ChEMBL, internal ADMET models

- `safety-classify` — go/no-go safety verdict; aggregates ADMET, antitarget, and FAERS signals.
- `safety-admet_predict` — ADMET profiling of a compound series.
- `safety-antitarget_profile` — screens for tumor-suppressor off-target degradation (PROTAC/degrader programs).
- `safety-sall4_risk` — teratogenicity risk for IMiD/CRBN-based programs.
- `safety-ddi_predict` — drug-drug interaction risk at clinical stage.

### Literature tools
**Databases:** PubMed, OpenAlex, Espacenet, bioRxiv/medRxiv

- `literature-pubmed_search` — ground truth; catches mechanistic nuance and safety signals not
  yet in structured databases.
- `literature-chembl_query` — known bioactivity data, IC₅₀ landscape, known ligands.
- `literature-patent_search` — IP freedom-to-operate, compound prior art.
- `literature-openalex_search` — broader academic coverage including preprints.

### Genomics tools
**Databases:** GWAS Catalog, GTEx, OpenTargets genetics

- `genomics-gwas_lookup` — human genetic validation; GWAS credible sets and causal signals.
  Non-negotiable first filter for target confidence.
- `genomics-eqtl_lookup` — connects GWAS variants to gene expression in specific tissues.
- `genomics-mendelian_randomization_lookup` — upgrades association to causal inference.
- `genomics-coloc` — confirms shared causal variant between GWAS and eQTL.

### Expression / Omics tools
**Databases:** GEO, CELLxGENE, CLUE/L1000 (L1000 requires local data)

- `expression-pathway_enrichment` — DEG list to pathway interpretation.
- `omics-geo_search` / `omics-geo_fetch` — find and download public expression datasets.
- `omics-deseq2` — differential expression from count matrices. *Requires local data.*
- `expression-l1000_similarity` — transcriptomic compound signature matching. *Requires local data.*
- `cellxgene-gene_expression` — single-cell resolution expression across cell types.

### Structure tools
**Databases:** RCSB PDB, AlphaFold DB (docking requires RDKit)

- `structure-alphafold_fetch` — predicted structure for any protein.
- `structure-binding_site` — binding site and allosteric pocket identification.
- `structure-ternary_predict` — ternary complex prediction for PROTAC/molecular glue programs.
- `structure-dock`, `structure-fep` — late-stage computational chemistry.

### Data API tools
**Databases:** MyGene, UniProt, Reactome, PDBe, NCBI Gene, MyVariant, Ensembl, and 15+ more

These are supporting lookups for annotation, ID mapping, and database cross-referencing.
`data_api-uniprot_lookup` and `data_api-opentargets_search` are the most broadly useful.

---

## Usage patterns that work well

**1. Anchor the biology before asking about compounds.**
Start with `target-disease_association` on your target of interest. It returns a ranked disease
list with genetic, expression, and drug evidence scores. This context makes every follow-up
compound or indication query more accurate.

**2. Use literature search as a reality check.**
Before running computational tools on an unfamiliar compound or target, run
`literature-pubmed_search` first. It confirms the entity is what you think it is and surfaces
any known mechanism, clinical outcome, or safety signal that should frame the subsequent queries.

**3. Chain genomics tools for causal evidence.**
`gwas_lookup` → `eqtl_lookup` → `mendelian_randomization_lookup` → `coloc` is the standard
causal evidence chain. Each step narrows from "associated" to "causal" to "in the right tissue
and direction." Running all four takes under a minute and produces the level of evidence expected
in a target ID memo.

**4. Use `run_python` to aggregate multi-tool results.**
When you need to combine outputs from three or more tool calls into a ranked table or chart, it's
cleaner to collect the results in Python than to ask Claude to synthesize them in prose. Assign
each result to a variable, build a DataFrame, and `plt.savefig()` a summary figure.

**5. Batch lookups where possible.**
`data_api-uniprot_lookup` and `data_api-mygene_lookup` accept gene lists. For a panel of
targets, pass them together rather than calling the tool once per target.

---

## Query examples

**Genetic evidence for a target**
> "Build the causal evidence case for PCSK9 as a cardiovascular drug target."

Sequence: `genomics-gwas_lookup` (LDL cholesterol GWAS hits at PCSK9 locus) →
`genomics-eqtl_lookup` (liver eQTL) → `genomics-mendelian_randomization_lookup` (causal effect
on CAD) → `target-disease_association` (OT scores) → `literature-pubmed_search` (clinical
outcome data from evolocumab/alirocumab trials).

**Compound mechanism of action**
> "What pathway does the kinase inhibitor bosutinib primarily affect, and which resistance
> mutations are known?"

Sequence: `literature-chembl_query` (bioactivity profile) →
`data_api-opentargets_search` (target landscape) → `literature-pubmed_search`
(resistance mutations from clinical literature) → `expression-pathway_enrichment`
(if a transcriptomic signature is available).

**Indication positioning**
> "Which hematological malignancies have the strongest rationale for a CRBN-based
> molecular glue targeting IKZF1?"

Sequence: `target-disease_association` (IKZF1 disease scores) →
`clinical-tcga_stratify` (IKZF1 expression in heme cancers) →
`clinical-trial_search` (existing IMiD/CELMoD trials) →
`clinical-population_size` (addressable patients per indication).

---

## Known limitations

- **Local data required for some tools.** DepMap (cell viability, CRISPR essentiality), PRISM
  (drug sensitivity screening), and L1000 (transcriptomic compound signatures) require datasets
  downloaded to disk. Without them, those tools return empty results. Full list:
  [`src/ct/tools/_tool_classification.md`](src/ct/tools/_tool_classification.md).

- **Chemistry tools need RDKit.** SAR analysis, docking, retrosynthesis, and pharmacophore tools
  will fail with an import error unless you've installed `pip install -e ".[chemistry]"`.

- **Single-cell tools need scanpy.** Clustering, annotation, and trajectory tools require
  `pip install -e ".[singlecell]"`.

- **No retry logic on rate limits.** PubMed, UniProt, and Open Targets may throttle
  high-frequency queries. If a tool call times out or returns an empty result unexpectedly,
  waiting a few seconds and retrying usually works.

- **`run_r` is conditional.** The tool only appears in the tool list if rpy2 is installed.

---

## Setup verification

Run this query to confirm the MCP server is connected and functional:

> "Look up the UniProt entry for TP53 and return its function annotation."

You should see a `ct-tools:data_api-uniprot_lookup` tool call in the tool use panel and a
structured result within 3 seconds. If the tool call doesn't appear, check that `.mcp.json`
is present in the project root and that Claude Code picked it up (Settings → MCP servers).
