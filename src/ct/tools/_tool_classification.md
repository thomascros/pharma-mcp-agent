Tool Categorization — Local Data vs. API-Based
## Category 1: Require Local Data
Tools that need datasets pre-downloaded (ct data pull) or user-provided files. Grouped by dependency:

### DepMap / PRISM (cell viability, CRISPR essentiality, drug sensitivity)

data_api.depmap_search, target.coessentiality
viability.dose_response, viability.compare_compounds, viability.tissue_selectivity
combination.synthetic_lethality, combination.metabolic_vulnerability
clinical.indication_map

### L1000 / CLUE (transcriptomic compound signatures)

expression.l1000_similarity, combination.synergy_predict
clue.compound_signature, clue.connectivity_query
repurposing.cmap_query

### Proteomics / Imaging (requires user datasets)

omics.proteomics_diff, omics.proteomics_enrich
imaging.cellpainting_lookup, imaging.morphology_similarity

### Expression matrices (require count/expression input)

expression.diff_expression, expression.deconvolution
expression.immune_score, expression.tf_activity
omics.deseq2, omics.multiomics_integrate

### Single-cell / Epigenomics (user-uploaded data)

singlecell.cluster, singlecell.cell_type_annotate, singlecell.trajectory
omics.atac_peak_annotate, omics.chipseq_enrich, omics.hic_compartments
omics.methylation_cluster, omics.methylation_diff, omics.methylation_profile
omics.spatial_cluster, omics.spatial_autocorrelation
omics.cytof_cluster

### Download-then-analyze (fetches from internet, then works locally)

omics.geo_fetch, omics.tcga_fetch, omics.cellxgene_fetch
User-provided clinical/PK files

pk.nca_basic, statistics.dose_response_fit, statistics.survival_analysis
regulatory.cdisc_lint, regulatory.define_xml_lint, regulatory.submission_package_check

### Workspace utilities

code.execute / run_python, shell.run
remote_data.list_datasets, remote_data.query, omics.dataset_info
files.* (create, read, edit, copy, delete, etc.)

## Category 2: API-Based Tools — Ranked by Drug Discovery Utility
No local data required. Ranked by breadth of impact across the drug discovery pipeline.

### Tier 1 — Essential: Use on Every Target or Compound
Rank	Tool	Why it's critical
1	target.disease_association	Single richest output per query — genetic, drug, and literature evidence scores across all diseases for a target. First tool to run on any new target
2	data_api.opentargets_search	Complements above; retrieves top targets for a disease, top indications for a drug, full competitive target landscape
3	literature.pubmed_search	Ground truth — catches any mechanistic nuance, clinical readout, or safety signal not yet in structured databases
4	genomics.gwas_lookup	Human genetic validation — the non-negotiable first filter for target confidence; identifies GWAS credible sets and causal signals
5	target.expression_profile	Defines tissue-selectivity and therapeutic window before any further investment; GTEx + HPA in one call

### Tier 2 — High Value: Run on Shortlisted Targets/Compounds
Rank	Tool	Why it's valuable
6	genomics.mendelian_randomization_lookup	Upgrades genetic association to causal inference — the strongest human evidence short of a clinical trial
7	genomics.eqtl_lookup	Connects GWAS variants to gene expression in specific tissues; critical for interpreting non-coding GWAS signals
8	genomics.coloc	Confirms shared causal variant between GWAS and eQTL — closes the causal evidence chain
9	data_api.uniprot_lookup	Protein function, post-translational modifications, subcellular localization, domain architecture, known disease links — often the fastest mechanistic primer
10	clinical.competitive_landscape	Multi-source competitive intelligence (OT + ChEMBL + ClinicalTrials.gov) in one call; essential before committing program resources
11	clinical.trial_search	Identifies active/recruiting trials, competitor programs, benchmark endpoints, patient populations
12	literature.chembl_query	Known bioactivity data, IC₅₀ landscape, known ligands — critical before starting a chemistry program
13	safety.classify	Go/no-go safety verdict early; aggregates ADMET, antitarget, and FAERS signals

### Tier 3 — Situational: Deploy for Specific Pipeline Stage Questions
Rank	Tool	Stage / Use case
14	structure.alphafold_fetch	Early structure-based drug design; enables virtual screening and binding site prediction when no experimental structure exists
15	chemistry.descriptors	Hit-to-lead — drug-likeness, Lipinski, TPSA, LogP for any compound before chemistry investment
16	safety.admet_predict	Lead optimization — ADMET profiling of compound series
17	safety.antitarget_profile	Safety check for degrader/PROTAC programs — screens for tumor suppressor off-target degradation
18	clinical.tcga_stratify	Target expression in patient tumors across cancer subtypes; oncology positioning
19	clinical.population_size	Business case — addressable patient population per indication
20	clinical.endpoint_benchmark	Trial design — benchmark ORR/PFS/OS endpoints against historical trials in the indication
21	network.ppi_analysis	Target biology — protein interaction network, functional partners, pathway context
22	data_api.pdb_search	Structural biology — known experimental structures, binding site precedent
23	chemistry.sar_analyze	Lead optimization — SAR landscape from ChEMBL for a chemical series
24	chemistry.mmp_analysis	Lead optimization — matched molecular pairs that improve potency or ADMET
25	design.suggest_modifications	Medicinal chemistry ideation — AI-suggested structural modifications
26	literature.openalex_search	Broader academic coverage than PubMed; useful for preprints, conference abstracts, non-English literature

### Tier 4 — Specialized: High Value in Specific Contexts
Rank	Tool	Context
27	chemistry.retrosynthesis	Route scouting for novel scaffolds; CRO engagement
28	chemistry.scaffold_hop	IP diversification; scaffold diversification to escape existing patents
29	chemistry.pharmacophore	Virtual screening setup; pharmacophore-guided library design
30	structure.binding_site	Cryptic pocket identification; allosteric site discovery
31	structure.ternary_predict	PROTAC/molecular glue programs specifically
32	target.druggability	Early go/no-go on structural druggability before chemistry program
33	target.neosubstrate_score	Molecular glue programs — neosubstrate likelihood scoring
34	target.degron_predict	PROTAC design — identifies degron motifs in target protein
35	safety.ddi_predict	Clinical-stage — drug-drug interaction risk assessment
36	safety.faers_signal_scan	Post-market safety signal detection; useful before entering competitive indication
37	safety.sall4_risk	IMiD/CRBN-based programs exclusively — teratogenicity screen
38	safety.label_risk_extract	Competitive benchmarking — extract safety liabilities from approved drug labels
39	biomarker.mutation_sensitivity	Patient stratification — identifies mutations predicting drug response
40	biomarker.panel_select	CDx development — optimal biomarker panel for patient selection
41	biomarker.resistance_profile	Late preclinical/early clinical — resistance mechanism anticipation
42	cellxgene.gene_expression	Single-cell resolution target expression across cell types/tissues
43	cellxgene.cell_type_markers	Cell type annotation in scRNA-seq; target cell-type specificity
44	omics.geo_search / omics.tcga_search	Dataset discovery before pulling data
45	network.pathway_crosstalk	Systems-level pathway interactions; combination therapy rationale
46	data_api.reactome_pathway_search	Canonical pathway context for target
47	protein.domain_annotate	Domain function, ligandable motifs (InterPro/Pfam)
48	protein.function_predict	Understudied targets with no literature — AI-based function inference
49	protein.embed	Protein similarity search; homolog-based druggability transfer
50	intel.competitor_snapshot	BD/licensing — rapid competitive landscape for deal assessment
51	intel.pipeline_watch	Ongoing monitoring of competitor clinical programs
52	literature.patent_search	IP freedom-to-operate; compound series prior art
53	literature.preprint_search	Earliest signal on emerging biology (bioRxiv/medRxiv)
54	data_api.drug_info	Known drug profiles — repurposing context, approved indications
55	data_api.chembl_advanced	Complex ChEMBL queries beyond literature.chembl_query
56	data_api.myvariant_lookup / genomics.variant_annotate / genomics.variant_classify	Variant-level annotation for precision medicine
57	chemistry.pairwise_similarity / chemistry.similarity_search	Compound identity check; FTO assessment
58	chemistry.sa_score	Synthetic accessibility scoring in library design
59	expression.pathway_enrichment	DEG list → pathway interpretation (no local data if gene list provided externally)
60	statistics.enrichment_test	Gene set enrichment from any externally provided list
61	omics.kegg_ora	KEGG over-representation analysis for pathway context
62	structure.dock / structure.fep / structure.md_simulate	Late-stage computational chemistry — binding pose, affinity prediction, dynamics
63	structure.compound_3d	3D conformer for docking input
64	data_api.mygene_lookup / data_api.mydisease_lookup / data_api.ensembl_lookup / data_api.ncbi_gene	ID mapping, annotation utilities — supporting tools rather than primary insights
65	dna.* tools (primer design, codon optimize, PCR protocol, etc.)	Molecular biology wet lab support — niche utility for drug discovery vs. biotech
66	notification.send_email / ops.* (notebook, todo, workflow)	Workflow management — infrastructure, not discovery

Key takeaway: Tiers 1–2 (tools 1–13) deliver 80% of the drug discovery value with API-only access. The data-dependent tools in Category 1 unlock the remaining depth — primarily for compound mechanism of action (L1000/CLUE), essentiality context (DepMap), and custom omics analysis (DESeq2, scRNA-seq).