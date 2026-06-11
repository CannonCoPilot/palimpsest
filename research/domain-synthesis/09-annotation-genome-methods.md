# Research Report: Genome Annotation Methodologies as Analogies for Literary Text Annotation (Palimpsest Platform)

**Date**: 2026-06-06
**Scope**: Systematic analysis of genome annotation tools, formats, and architectures as conceptual and technical models for a computational literary analysis platform called Palimpsest. Each tool is examined for its genomics function, literary analogue, proposed Palimpsest equivalent, and data requirements.

---

## Executive Summary

Genome annotation and literary text annotation are structurally isomorphic problems. Both involve layering heterogeneous, semantically distinct interpretations over a fixed reference sequence — DNA in one case, the character stream of a text in the other. The genomics field has spent thirty years building rigorous infrastructure for exactly this problem: coordinate systems, controlled vocabularies, evidence-weighting pipelines, multi-resolution browsers, and cross-corpus statistical models. Palimpsest can adopt these patterns almost directly, treating character offsets the way genomics treats base-pair coordinates, and treating annotation layers (narrative structure, rhetoric, allusion, discourse) the way genomics treats feature tracks (genes, repeats, regulatory elements, chromatin states).

Three architectural lessons dominate. First, the GFF3/Sequence Ontology pattern — a hierarchical, parent-child coordinate record anchored to a reference with a controlled feature vocabulary — is directly portable to text. Second, MAKER's evidence-integration architecture (weighting ab initio predictions against orthogonal empirical evidence) is the right model for combining ML-generated annotations with human reader signals. Third, JBrowse 2's pluggable adapter/renderer architecture, which separates data retrieval from display logic, is the correct pattern for a multi-layer literary browser where the same passage must simultaneously display phonemic, syntactic, rhetorical, and intertextual annotations at different zoom granularities.

---

**Format note**: Throughout this document, GFF3-format annotations are used to illustrate the structural analogy between genome and literary annotation. The actual Palimpsest output format is W3C Web Annotation JSONL (see doc 14 v3.0). GFF3/PAF is available as a computational export format.

## Part I: Gene Prediction Tools

### 1.1 MAKER — Evidence Integration Pipeline

**Genomics function.** MAKER is a portable genome annotation pipeline that synthesizes three independent evidence streams into a unified gene model set: (a) ab initio predictions from tools like SNAP or Augustus that find gene-like patterns in the raw sequence without prior knowledge; (b) transcript evidence — ESTs, cDNAs, or RNA-seq alignments showing where the organism actually transcribed sequence; and (c) protein homology alignments from related species, anchoring predictions to known functional proteins. MAKER runs iteratively: the first pass generates a training set, which retrains the ab initio predictor, which feeds a second pass with improved parameters. The final output is a GFF3 file where each feature carries an Annotation Edit Distance (AED) score — 0.0 meaning perfect evidence agreement, 1.0 meaning no evidence support. MAKER also wraps RepeatMasker to prevent transposable elements from corrupting gene calls.

**Literary analogue.** This is the core narrative annotation pipeline. In a literary text, a "gene" corresponds to a bounded narrative unit — a scene, an episode, a speech act, a thematic cluster. Just as a genomic gene must be confirmed by multiple orthogonal evidence types, a literary annotation gains credibility when multiple independent signals agree: a reader's segmentation judgment (transcript evidence), a statistical model trained on chapter-level patterns (ab initio), and alignment to similar scenes in other texts of the genre (protein homology). The AED score maps cleanly to annotation confidence.

**Palimpsest equivalent: NarrativeMAKER.** A pipeline that integrates: (a) an unsupervised boundary-detection model trained on prosodic and syntactic signals (the ab initio component); (b) human reader segmentation data collected via annotation interface — where readers actually drew chapter or scene breaks (transcript evidence); (c) alignment of candidate scenes against a corpus of canonical scene-type templates — the "confrontation scene," the "recognition scene," the anagnorisis pattern (protein homology). The pipeline runs in two passes: rough segmentation informs training of the boundary model, which feeds a second pass with tighter parameters.

**Inputs.** Raw text as character-offset FASTA equivalent; reader segmentation logs with timestamps and confidence ratings; a corpus of pre-annotated scene-type templates; a statistical model of clause-level boundary signals (sentence length drop, tense shift, character re-entry).

**Outputs.** A GFF3-analogue annotation file: each scene/episode as a span record with `chrom` = document ID, `start`/`end` = character offsets, `type` = SO-analogue term from a Literary Feature Ontology (LFO), `AED`-equivalent confidence score, and `evidence_support` attribute listing which signals agreed.

**Source**: [MAKER: An easy-to-use annotation pipeline](https://pmc.ncbi.nlm.nih.gov/articles/PMC2134774/), [NIH HPC MAKER docs](https://hpc.nih.gov/apps/maker.html)

---

### 1.2 BRAKER — Unsupervised Ab Initio Training from Native Signal

**Genomics function.** BRAKER automates the hardest step in genome annotation: training a species-specific gene-finder without a pre-curated training set. In BRAKER1, RNA-seq reads are aligned to the genome; spliced alignments are extracted into GFF; GeneMark-ET trains unsupervised gene models from these intron footprints; genes with full intron support are selected to auto-train AUGUSTUS; AUGUSTUS then predicts the full gene complement using those trained parameters plus the RNA-seq signal as extrinsic evidence. BRAKER2 added protein homology; BRAKER3 (2023) fully combines RNA-seq and protein in GeneMark-ETP + AUGUSTUS + TSEBRA (a gene model combiner).

The key insight is unsupervised domain adaptation: BRAKER learns the statistical signature of coding sequence in a novel genome from that genome's own transcriptional output, without any expert-curated training genes.

**Literary analogue.** BRAKER maps to style-trained annotation: training a structural or rhetorical annotator on the target text's own internal patterns rather than on external labeled corpora. A text has its own "transcriptome" — the pattern of reader attention signals (dwell time, re-reading, highlighting), the frequency distribution of syntactic constructions, the rhythm of speech-act transitions. A BRAKER-analogue mines these native signals to learn what counts as a structurally significant unit in this particular author's idiolect.

**Palimpsest equivalent: StyleBRAKER.** An unsupervised self-training pipeline: (1) Collect reader engagement signals (dwell time per sentence, highlighting, re-reading events) as the "RNA-seq BAM" equivalent. (2) Extract high-confidence structural boundaries where signals spike, analogous to fully-supported introns. (3) Train a text-specific boundary model on those high-confidence boundaries. (4) Retrain the annotation model using the trained parameters plus the engagement signal as extrinsic evidence. (5) Apply to full text. This approach means Palimpsest can develop author-specific or genre-specific annotation models without pre-labeled training data for each new text.

**Inputs.** Reader engagement logs (character-offset × dwell-time matrix, the text equivalent of a BAM file); raw text; seed examples of boundary types (optional, analogous to a small curated gene set).

**Outputs.** Trained model parameters (AUGUSTUS HMM analogue) serializable per author/genre; GFF3-analogue feature file with confidence scores reflecting degree of reader-signal support.

**Source**: [BRAKER1 paper, Bioinformatics 2016](https://academic.oup.com/bioinformatics/article/32/5/767/1744611), [BRAKER3 preprint](https://www.biorxiv.org/content/10.1101/2023.06.10.544449.full.pdf), [BRAKER GitHub](https://github.com/Gaius-Augustus/BRAKER)

---

### 1.3 Prokka — Rapid Batch Annotation via Hierarchical Database Lookup

**Genomics function.** Prokka annotates a bacterial genome in approximately 10 minutes on a desktop machine. Its architecture is hierarchical: Prodigal identifies CDS coordinates (the structural step); Prokka then assigns functional identity by BLAST-searching predicted proteins against a tiered database hierarchy — species-specific trusted proteins first, then genus-level, then a broad Swiss-Prot database as fallback. Non-CDS features (rRNA, tRNA, ncRNA, signal peptides) are handled by dedicated sub-tools (RNAmmer, tRNAscan-SE, SignalP). The result is a standards-compliant GenBank/GFF3 file suitable for immediate submission to NCBI.

The design principle is speed via pre-ranked database specificity: prefer the closest known relative's annotations before falling back to generic function labels.

**Literary analogue.** Prokka maps to rapid baseline annotation — fast first-pass labeling of well-understood features in a text using a pre-built knowledge base. Just as Prokka assigns EC numbers and gene names by similarity to known proteins, a literary Prokka would label known rhetorical figures, genre conventions, and narrative tropes by similarity to a pre-curated pattern library. The hierarchical database lookup corresponds to preferring period-specific or author-specific pattern libraries before falling back to universal rhetorical taxonomies.

**Palimpsest equivalent: RhetoriKa.** A rapid baseline annotator: (1) A "Prodigal" module that identifies candidate rhetorical/structural spans using heuristic signal patterns (anaphora: parallel sentence openings; chiasmus: mirror syntactic structures; climax: ascending enumeration). (2) A tiered lookup against: (a) author-specific pattern library if available; (b) period/genre library; (c) universal rhetorical figure ontology (Rhetorica ad Herennium–derived). (3) Sub-annotators for specialized features: meter scanner, dialogue tagger, free indirect discourse detector. Output should be generated within seconds per novel, enabling batch processing of large corpora.

**Inputs.** Tokenized, POS-tagged text; tiered pattern libraries in a standardized format; optionally, author-specific training data.

**Outputs.** Annotation file with feature type, confidence, and the database tier from which the match was drawn (analogous to Prokka's `/inference` tag distinguishing "similar to protein" from "hypothetical protein").

**Source**: [Prokka: rapid prokaryotic genome annotation](https://academic.oup.com/bioinformatics/article/30/14/2068/2390517), [Prokka GitHub](https://github.com/tseemann/prokka)

---

### 1.4 Liftoff — Annotation Transfer Between Assemblies

**Genomics function.** Liftoff transfers a reference genome's GFF3/GTF annotation to a new assembly of the same or related species. It uses Minimap2 to align each gene's sequence from the reference to the target assembly, then uses the alignments to optimally remap each exon's coordinates. Crucially, it enforces inter-exon constraints (all exons of a transcript must map to a coherent locus) and prevents paralog collapse (distinct genes must map to distinct loci). It also detects duplicated gene copies not in the reference with the `-copies` flag.

**Literary analogue.** Liftoff maps to annotation transfer across text versions or translations — taking annotations from a canonical edition and projecting them onto a new edition, a manuscript variant, a translation, or an adaptation. The challenge is exactly analogous: the "genome" has been shuffled (editorial revision, omitted passages, translated phrasing), and feature boundaries must be intelligently remapped rather than naively offset-shifted.

**Palimpsest equivalent: TextLiftoff.** A version-aware annotation transfer tool: (1) Align source and target text at the passage level using a literary alignment algorithm (analogous to Minimap2 for long reads — tolerating gaps, insertions, and substitutions). (2) Remap annotation spans from source coordinates to target coordinates using alignment chain math. (3) Flag spans where alignment coverage drops below threshold (heavily revised passages). (4) Detect passages in the target that have no source counterpart — new material added in revision (analogous to Liftoff's `-copies` novel gene detection). (5) Produce a transfer confidence score per annotation based on alignment identity over the span.

This tool is critical for Palimpsest's handling of manuscript traditions, editorial variants (e.g., Wordsworth's two-part vs. thirteen-book Prelude), and translated corpora where annotations derived from an authoritative source text must be projected onto variant witnesses.

**Inputs.** Source text with GFF3-analogue annotations; target text (variant/translation/edition); minimum alignment identity threshold; gap penalty parameters.

**Outputs.** GFF3-analogue annotation file for the target text; transfer confidence per feature; list of unmapped features; list of novel spans in the target.

**Source**: [Liftoff: accurate mapping of gene annotations, Bioinformatics 2021](https://academic.oup.com/bioinformatics/article/37/12/1639/6035128), [Liftoff GitHub](https://github.com/agshumate/Liftoff)

---

### 1.5 Apollo — Collaborative Manual Curation

**Genomics function.** Apollo is a web-based collaborative genome annotation editor described as "Google Docs for genome annotation." It embeds JBrowse as its underlying browser, displaying automatically generated evidence tracks (RNA-seq coverage, protein alignments, ab initio predictions) and allowing curators to create and edit gene models in a "User Annotations" track that sits above the evidence. Multiple curators work simultaneously with real-time conflict management. Edits propagate to a central server; export produces standards-compliant GFF3. Apollo explicitly distinguishes between machine-generated evidence tracks (read-only) and the curated annotation layer (writable).

**Literary analogue.** Apollo maps directly to collaborative scholarly annotation — the digital equivalent of the annotated critical edition. Evidence tracks correspond to computational analyses (NER output, syntactic parse, ML-generated boundary predictions); the User Annotations track corresponds to the scholarly gloss, the critical commentary, the editorial note. The separation between evidence (computational, read-only) and annotation (scholarly, writable) is architecturally essential and has no clean equivalent in most humanities platforms.

**Palimpsest equivalent: ScholiaApollo.** A web-based collaborative literary annotation environment: (1) JBrowse-analogue text browser (see Section IV) displaying all computational analysis tracks as evidence. (2) A writable "Scholarly Annotation" track above the evidence, where curators add, edit, merge, and split annotation spans with free-text notes and structured attribute fields. (3) Real-time collaborative editing with user authentication and edit history. (4) Feature-type dropdown constrained to the Literary Feature Ontology (analogous to Apollo's Sequence Ontology constraint on feature types). (5) BLAT-analogue full-text search to quickly navigate to specific passages or patterns. (6) Export to Palimpsest's canonical annotation format. The critical design constraint: computational evidence tracks must be read-only; only the Scholarly Annotation track is writable, so that human curation clearly supersedes machine output but does not corrupt it.

**Inputs.** Pre-loaded text with all computational analysis tracks; user accounts with role-based permissions (viewer, annotator, curator, admin).

**Outputs.** Export of the curated annotation layer in Palimpsest canonical format; edit audit log; per-annotation provenance record (who annotated, when, from what evidence).

**Source**: [Apollo: Democratizing genome annotation, PLOS Computational Biology 2019](https://journals.plos.org/ploscompbiol/article?id=10.1371/journal.pcbi.1006790), [Web Apollo, Genome Biology 2013](https://genomebiology.biomedcentral.com/articles/10.1186/gb-2013-14-8-r93)

---

## Part II: Feature-Specific Annotation Tools

### 2.1 MAPLE/KAAS — Metabolic Pathway Completeness

**Genomics function.** KAAS (KEGG Automatic Annotation Server) assigns KEGG Orthology (KO) identifiers to predicted proteins via bidirectional best-hit BLAST against the curated KEGG GENES database. Once KO assignments are made, organism-specific metabolic pathway maps are automatically reconstructed: genes are colored on KEGG pathway diagrams, showing which reactions are present and which are absent. MAPLE extends this by calculating a Module Completion Ratio (MCR) per functional module — the fraction of required enzymatic steps present in the genome — which characterizes whether a complete metabolic pathway is encoded.

The key abstraction: genes are not just labeled individually; they are evaluated as components of larger functional circuits, and the circuit's completeness is itself a first-class annotation.

**Literary analogue.** The direct analogue is thematic completeness analysis: characterizing whether a text contains the full set of "reactions" required to instantiate a recognized narrative or rhetorical pattern. A sonnet needs an octave, a volta, and a sestet; a tragedy needs hamartia, peripeteia, anagnorisis, and catastrophe; an argument needs claim, grounds, warrant, and rebuttal. MAPLE/KAAS maps to a tool that (a) identifies which thematic/structural "enzymes" (motifs, speech acts, plot functions) are present, (b) maps them onto known narrative "pathway" schemas, and (c) calculates a structural completeness score for each schema.

**Palimpsest equivalent: NarrativeKEGG.** A structural completeness annotator: (1) A "KO assignment" step: map identified narrative units (scenes, speech acts, rhetorical figures) to entries in a Narrative Function Library (NFL) — analogous to KEGG's KO table, but populated with Propp's narrative functions, Frye's mythoi, Aristotle's dramatic elements, Toulmin's argument schema components. (2) A "pathway reconstruction" step: given the NFL assignments, reconstruct which narrative schemas are instantiated and to what degree. (3) An MCR-equivalent: Narrative Completeness Ratio (NCR) per schema — "this text instantiates 7 of 8 Propppian functions of the hero tale; the missing function is 'hero returns'." (4) Visualization: schema diagrams with present elements colored, absent elements grayed.

**Inputs.** GFF3-analogue annotation file with feature types drawn from the NFL ontology; a library of narrative schema definitions expressed as Boolean combinations of NFL terms (analogous to KEGG module Boolean expressions); text character offsets.

**Outputs.** Per-schema NCR scores; colored schema maps; list of "missing" narrative functions; cross-text comparative MCR matrix (analogous to MAPLE's comparative functionome analysis across 1,488 prokaryotes).

**Source**: [KAAS original paper, PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC1933193/), [MAPLE 2.1.0, DNA Research 2016](https://academic.oup.com/dnaresearch/article/23/5/467/2236168), [MAPLE web portal](https://www.genome.jp/tools/maple/)

---

### 2.2 Infernal — Covariance Model Search for Structurally-Defined ncRNA

**Genomics function.** Infernal implements covariance models (CMs) — stochastic context-free grammars (SCFGs) that jointly model a sequence family's primary sequence consensus and its consensus RNA secondary structure (base-pair pattern). The key insight: many non-coding RNAs are poorly conserved at the nucleotide level but highly conserved at the structural level — their function depends on folding into specific shapes, and covariation (when one side of a base pair mutates, the other tends to compensate) is the signature of structural conservation. CMs detect this covariation signal. CMs are built from curated seed alignments in the Rfam database via `cmbuild`; `cmsearch` scans genomes using these models at much higher sensitivity than sequence-only methods.

**Literary analogue.** The analogue is pattern-conserved form detection: identifying literary features that are recognizable by their structural configuration rather than their lexical content. A chiasmus (ABBA structure) is recognizable by the mirror-symmetry of its constituents even when the words themselves vary completely. A sonnet is recognizable by its 14-line iambic pentameter structure even across centuries and languages. The covariance principle maps to: when the second hemistich of a line changes, the first tends to compensate to maintain the overall stress pattern — structural compensation that is the literary equivalent of base-pair covariation.

**Palimpsest equivalent: FormInfernal.** A structural grammar-based formal pattern scanner: (1) Build "literary covariance models" from curated seed alignments of known instances of formal patterns — sonnets, villanelles, terza rima, chiastic structures, anaphoric series, Petrarchan conceit patterns. These models encode the structural consensus (metrical template, syntactic frame, semantic opposition pattern) as a stochastic context-free grammar over text spans. (2) The SCFG for a chiasmus would encode: span A spans B spans B' spans A', where B and B' must be semantically or syntactically related and A and A' must be in a mirror relation, but the specific content can vary. (3) `litcmbuild` trains models from seed examples; `litcmsearch` scans a text using these models, reporting scored matches. (4) Integration with a Palimpsest-equivalent of Rfam: a curated database of literary form models built from scholarly consensus.

**Inputs.** Seed alignments of known formal pattern instances, annotated with structural positions (the literary equivalent of structural alignment with base-pair annotations); raw text for search.

**Outputs.** Hit table with span coordinates, match score, E-value, and the structural alignment diagram showing how the text matches the model; calibrated statistical significance estimates.

**Source**: [Infernal official site](http://eddylab.org/infernal/), [Rfam and ncRNA analysis, PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC6754622/), [Studying RNA homology with Infernal, PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC5010141/)

---

### 2.3 tRNAscan-SE — Structural Covariance Model for a Universal Functional RNA

**Genomics function.** tRNAscan-SE is specialized for one RNA type: transfer RNAs. It uses a suite of covariance models — nearly one hundred in tRNAscan-SE 2.0 — differentiated by isotype (the amino acid the tRNA charges) and phylogenetic clade (eukaryote, prokaryote, mitochondria). Predicted tRNAs are scored against all isotype-specific models to classify amino acid identity based on both anticodon sequence and full structural score. The tool achieves near-perfect sensitivity and specificity (false positive rate under 1 in 15 gigabases) by combining a fast filter stage (tRNAscan, MERNAC) with a computationally expensive CM scoring stage. It also identifies tRNA pseudogenes and tRNA-derived SINEs.

**Literary analogue.** tRNAscan-SE maps to a specialized detector for a single, precisely defined functional unit with a known universal structure: in literary terms, a verse-form scanner. A sonnet has as precise a structural specification as a tRNA: a fixed metrical template, a canonical fold pattern (octave/sestet or ABAB CDCD EFEF GG), known functional variants (Petrarchan, Shakespearean, Spenserian). The isotype classification maps to sonnet-type classification; the pseudogene detection maps to detection of "broken" or parodic sonnets that use sonnet structure without fulfilling its function.

**Palimpsest equivalent: VerseFormScan.** A dedicated verse-form detector using specialized models per form: (1) Individual CMs for sonnet, villanelle, sestina, ode, terza rima, ballade, rondeau, haiku, ghazal — each encoding the metrical, stanzaic, and rhyme-scheme constraints as an SCFG over phonemic and syntactic features. (2) Fast filter stage using simple rule-based line counting and syllable estimation. (3) Expensive CM scoring stage for candidate spans. (4) Isotype-analogue classification: Petrarchan vs. Shakespearean vs. Spenserian vs. variant sonnet. (5) Pseudogene-analogue detection: poems that begin like a known form but deviate or truncate — parodic sonnets, deliberately broken villanelles. (6) A database of form models analogous to the Genomic tRNA Database (GtRNAdb), updated as new literary forms are curated.

**Inputs.** Phonemically-annotated text (stress patterns, rhyme identities); line-boundary annotations; stanza-boundary annotations.

**Outputs.** Form hit table with coordinates, form type, subtype, confidence score, and deviation report for non-canonical instances.

**Source**: [tRNAscan-SE 2.0, Nucleic Acids Research 2021](https://academic.oup.com/nar/article/49/16/9077/6355886), [tRNAscan-SE methods, PMC](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC6768409/)

---

### 2.4 RepeatMasker — Transposon/Repeat Detection and Masking

**Genomics function.** RepeatMasker screens a DNA sequence against the Dfam database (a collection of transposable element family HMMs and consensus sequences) using HMMER or RMBlast. It produces three outputs: a soft-masked genome (repeat regions in lowercase), an annotation file listing every repeat hit (coordinates, family, class, divergence from consensus), and an overview statistics table. Critically, repeat masking is a prerequisite for gene annotation: unmasked transposons generate millions of spurious BLAST alignments and cause gene predictors to incorporate TE ORFs as false exons. The Dfam database classifies TEs hierarchically: Class I (retrotransposons: LTR, LINE, SINE) vs. Class II (DNA transposons); family-level; subfamily-level.

**Literary analogue.** Transposable elements — mobile DNA sequences that insert copies of themselves throughout the genome — map to borrowed language: quotations, allusions, clichés, formulas, set phrases, stock characters, and conventional metaphors that recur across texts and can be traced to recognizable source families. Like TEs, they are often "silenced" in sophisticated literary analysis (the critic "masks" them to find the original creative expression), yet they also carry crucial information about intertextual networks and generic conventions. A cliché is a SINE; a sustained allusion to Homer is a retrotransposon LTR; a stock phrase like "the sun was setting" is a simple repeat.

**Palimpsest equivalent: AllusionMasker.** A borrowed-language detector and masker: (1) An AllusioDB (Allusionome Database) equivalent of Dfam: a hierarchical library of stock phrases, Biblical phrases, classical allusions, formulaic expressions, genre conventions, and known quotation families, each represented as a probabilistic sequence model. (2) A scanner that identifies spans matching AllusioDB entries above a threshold, recording family, class (conscious allusion vs. unconscious cliché vs. formula), and divergence from the canonical form. (3) Soft-masking output: the text with intertextual material flagged for downstream annotators, preventing spurious evidence from confounding original-expression analyses. (4) Hard-masking for specific analyses where borrowed language should be excluded. (5) Statistics: percent of text covered by different borrowed-language classes, analogous to RepeatMasker's genome repeat percentage statistics.

A critical additional function: just as active cellular genes can be derived from transposable elements (and must not be masked), some allusions are structurally load-bearing — the entire argument of a poem may depend on an allusion. AllusionMasker must distinguish functional from incidental borrowing.

**Inputs.** Tokenized text; AllusioDB (curated allusion library); threshold parameters (divergence tolerance, minimum match length).

**Outputs.** Soft-masked text; allusion annotation file with span, family, class, divergence score, and AllusioDB entry ID; overview statistics.

**Source**: [RepeatMasker documentation](https://www.repeatmasker.org/webrepeatmaskerhelp.html), [TE annotation best practices, PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC10149145/)

---

### 2.5 Pseudofinder — Pseudogene Decay Detection

**Genomics function.** Pseudofinder identifies genes that have lost function through molecular decay. It operates via two branches: (1) The "Annotate" branch compares predicted ORFs to a protein reference database (e.g., RefSeq), identifying truncated ORFs (premature stop codons), fragmented genes (split across multiple non-overlapping ORFs), run-on ORFs (frameshifts creating fused products), and remnants with no identifiable ORF. (2) The "Sleuth" branch uses a closely related reference genome to detect inactivating mutations at finer resolution: frameshift-inducing indels, nonsense substitutions, loss of start/stop codons, and elevated dN/dS (relaxed purifying selection). The "Break" module can simulate pseudogenization at specified decay levels (1–10) for testing.

**Literary analogue.** Pseudogenes map to literary decay features: narrative threads that begin but are abandoned, arguments that lose their warrant mid-sentence, characters who are introduced but forgotten, motifs that appear without fulfilling their traditional function, ironic or parodic uses of a convention that signal its emptiness. In manuscripts, scribal corruptions produce the exact literary analogue of frameshifts (a missing word that makes the rest of the line nonsense) and premature stops (lacunae). At the stylistic level, a cliché is a pseudogene: a sequence that still resembles a functional metaphor but has lost its cognitive force through over-use.

**Palimpsest equivalent: NarrativePseudofinder.** A literary decay and dysfunction detector: (1) An "Annotate" branch: compare narrative units against a literary reference library to identify truncated patterns (scenes that begin a conventional structure but abandon it before completion), fragmented arguments (claims without warrants, evidence without claims), and "run-on" narrative passages (two distinct episodes merged without transition, the literary frameshift). (2) A "Sleuth" branch: using a closely related text (a precursor, a source, an earlier draft), identify specific decay mutations — an allusion present in the source but corrupted in the target; a metaphor whose vehicle is retained but whose tenor is dropped; a speech act that uses the form of a promise but lacks sincerity conditions. (3) A simulation module: generate test texts at specified "literary decay" levels to validate the detector. (4) dN/dS analogue: ratio of structural-content changes (synonymous) to functional-impact changes (non-synonymous) across draft versions.

**Inputs.** Annotated text; literary reference library; optional closely-related reference text (source text, earlier draft, precursor).

**Outputs.** Decay annotation file with type (truncated, fragmented, run-on, remnant), location, severity, inactivating mutation type; per-text decay statistics.

**Source**: [Pseudofinder, Molecular Biology and Evolution 2022](https://academic.oup.com/mbe/article/39/7/msac153/6633826), [PMC9336565](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC9336565/)

---

## Part III: Epigenomic/Structural Layers

### 3.1 ChromHMM/Segway — Chromatin State Discovery

**Genomics function.** ChromHMM trains a multivariate Hidden Markov Model on the combinatorial presence/absence patterns of histone modifications across the genome, learning a discrete state vocabulary (15–25 states in the Roadmap Epigenomics models) that partitions the genome into functional regions — active promoters, strong enhancers, bivalent chromatin, polycomb-repressed regions, heterochromatin, transcribed gene bodies, etc. Each 200 bp bin receives one state assignment. Crucially, the Roadmap Epigenomics consortium trained a single model by virtually concatenating 60 reference epigenomes, so the state vocabulary is consistent across all 127 cell types — the same "State 7 = Active Enhancer" in every cell type, enabling cross-cell-type comparison.

Segway uses a dynamic Bayesian network (rather than an HMM) operating at base-pair resolution with continuous signal values (rather than binarized marks), providing higher spatial resolution at greater computational cost.

**Literary analogue.** Chromatin states map to functional mode annotations: the operational register or rhetorical mode that a passage is in at any given point. Just as a genomic region can be in "active transcription mode," "silenced/repressed mode," or "poised/bivalent mode," a literary passage can be in "expository mode," "lyric mode," "argumentative mode," "ironic mode," "free indirect discourse mode," or "repressed/elliptical mode." The HMM learns these modes from the combinatorial presence/absence of surface signals (sentence-length patterns, POS distributions, punctuation density, pronoun shifts) in the same way ChromHMM learns states from histone mark combinations.

The cross-corpus joint training is the most powerful aspect: training a single mode model across many texts means the same "Mode 4 = Free Indirect Discourse" is consistently defined across all texts in the corpus, enabling genuine cross-text comparison.

**Palimpsest equivalent: ModeHMM.** A multivariate HMM over combinatorial textual signals: (1) Feature binarization: for each 100-word window (the text equivalent of a 200 bp bin), compute presence/absence of signals — elevated first-person pronoun rate, elevated syntactic complexity, elevated figurative language density, elevated deictic marker frequency, elevated reported speech markers, etc. (This binarization step is directly analogous to ChromHMM's Poisson threshold binarization of ChIP-seq reads.) (2) Train a 15–25 state HMM on a concatenation of 60+ texts from a representative corpus, learning a universal mode vocabulary. (3) Apply the trained model to any new text, segmenting it into mode states. (4) Biological enrichment analogue: ModeHMM should automatically compute enrichment of each learned state for known literary features (high incidence of State 4 at known FID passages → State 4 = FID mode). (5) Segway-analogue: a DBN variant operating at the sentence level with continuous signal values for higher resolution.

**Inputs.** Feature matrix (windows × binarized signals) for the training corpus; number of states K (hyperparameter); list of known feature annotations for enrichment validation.

**Outputs.** State assignments for every window of every text; transition probability matrix; emission probability matrix; enrichment table of states vs. known literary features; BED-analogue files for each state.

**Source**: [ChromHMM Nature Protocols 2017](https://www.nature.com/articles/nprot.2017.124), [Roadmap Epigenomics chromatin state learning](https://egg2.wustl.edu/roadmap/web_portal/chr_state_learning.html), [ChromHMM/Segway ENCODE integration, NAR 2013](https://academic.oup.com/nar/article/41/2/827/1071531), [Segway official site](https://segway.hoffmanlab.org/)

---

### 3.2 Akita/HiCExplorer — 3D Folding and Topologically Associating Domains

**Genomics function.** Chromosomes fold in 3D into topologically associating domains (TADs) — regions of elevated self-interaction that serve as regulatory units, insulating genes from enhancers outside the domain. HiCExplorer calls TADs from experimental Hi-C contact maps by computing insulation scores (how much contact crosses each boundary) and identifying local minima. Akita is a deep learning model (CNN with a "trunk" architecture derived from Basenji, plus a 2D "head") that predicts Hi-C contact maps directly from DNA sequence at 1 Mb resolution, enabling in silico prediction of how sequence variants affect TAD structure.

**Literary analogue.** TADs map to structural modules at the organizational level above individual scenes or paragraphs: chapters, books, acts, or larger thematic arcs that function as coherent interpretive units. The TAD concept specifically implies insulation — what happens inside the domain is more tightly coupled than what happens across domain boundaries. The literary analogue is the "interpretive module": a span within which characters, motifs, and themes interact tightly, with a distinct boundary across which the interaction pattern shifts. Akita's ability to predict 3D structure from sequence translates to predicting chapter/act boundaries from the linear sequence of textual features — a deep learning equivalent of structural boundary prediction.

**Palimpsest equivalent: StructureFold.** A hierarchical structural segmentation tool operating at multiple scales: (1) A HiCExplorer-analogue that computes "narrative contact maps" — a 2D matrix where cell (i,j) records the strength of thematic/character/motif co-occurrence between passage i and passage j (analogous to Hi-C contact frequency). Computing this requires a co-occurrence model across the full text. (2) An insulation score calculation on the resulting 1D diagonal: where the co-occurrence pattern shifts sharply, a structural boundary is inferred. (3) TAD-calling algorithm: a local minimum finder on the insulation score profile, producing nested domain boundaries at multiple scales (scene → episode → act → book). (4) An Akita-analogue deep CNN trained to predict the contact map from the linear feature sequence — enabling structural prediction on texts without prior annotation, and enabling "in silico mutagenesis" (what if this scene were deleted? what happens to the contact map?).

**Inputs.** Full-text feature matrix (sentence-level features across the whole text); or co-occurrence counts derived from NER + coreference resolution; text length.

**Outputs.** Narrative contact map (stored as sparse matrix); insulation score vector; TAD-equivalent boundary list with hierarchical nesting; domain identity assignments per passage.

**Source**: [Akita, Nature Methods 2020](https://www.nature.com/articles/s41592-020-0958-x), [AkitaV2, PLOS Computational Biology 2025](https://journals.plos.org/ploscompbiol/article?id=10.1371/journal.pcbi.1012824), [Topologically associating domains review, PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC12086760/)

---

### 3.3 TargetFinder/EPIVAN — Enhancer-Promoter Interaction Prediction

**Genomics function.** Enhancers are regulatory elements that can activate gene promoters over distances of hundreds of kilobases, and identifying which enhancer activates which promoter is a central problem in regulatory genomics. TargetFinder addresses this by training an ensemble classifier (gradient boosted trees + random forests) on chromatin annotation features (DNase-seq, histone marks, TF ChIP-seq, DNA methylation, CAGE, gene expression) for pairs of enhancers and promoters known to interact (positive class) vs. known not to interact (negative class), with a critical finding: features from the chromatin between the enhancer and promoter are more predictive than features at the elements themselves. EPIVAN takes a sequence-only approach using pre-trained DNA vectors, 1D convolution, gated recurrent units, and attention mechanisms to predict EPIs without requiring chromatin data.

**Literary analogue.** Long-range regulatory interactions map to long-range intertextual and narrative links: the connection between a passage that establishes a symbolic motif (the "enhancer") and a later passage that deploys or fulfills that motif (the "promoter"). In narrative terms: foreshadowing-fulfillment pairs, echo patterns, thematic rhymes across structural distance, and Chekhovian gun resolutions. The "enhancer" passage introduces charged language, a recurring motif, an unresolved tension; the "promoter" passage is where that charge is discharged. Like TargetFinder's finding about intervening chromatin, the passages between the foreshadowing and its fulfillment often carry the most diagnostic information about whether the link is active.

**Palimpsest equivalent: EchoFinder.** A long-range intertextual link predictor: (1) Identify candidate "signal" spans (passages with elevated lexical density, motif introduction, charged language) and candidate "resolution" spans (passages with resolution markers, return of lexis, closure signals). (2) Extract features for each candidate pair: (a) lexical similarity between signal and resolution spans; (b) character co-occurrence in the intervening passages; (c) motif frequency in the intervening passages; (d) temporal/spatial distance. (3) Train an ensemble classifier on known foreshadowing-fulfillment pairs (positive) and non-linked span pairs (negative). (4) Provide probability estimates for each candidate link. (5) EPIVAN-analogue: a sequence-only version using only local textual features (character n-grams, POS patterns, semantic vectors), enabling transfer to texts without rich annotation.

**Inputs.** Annotated span pairs with known link status (training); full feature matrix for the target text.

**Outputs.** Ranked list of candidate long-range links with probability scores; visualization of the "contact map" of predicted links across the text.

**Source**: [TargetFinder, Nature Genetics 2016](https://pubmed.ncbi.nlm.nih.gov/27064255/), [EPIVAN, Bioinformatics 2020](https://academic.oup.com/bioinformatics/article/36/4/1037/5564117), [Quantitative EPI prediction, Genome Research 2020](https://genome.cshlp.org/content/30/1/72.full)

---

### 3.4 G4Hunter — G-Quadruplex Scoring

**Genomics function.** G4Hunter predicts G-quadruplex (G4) forming sequences: non-canonical DNA structures where runs of guanine form Hoogsteen hydrogen bonds in a planar quartet, with biological roles in telomere stability, transcription regulation, replication, and genome instability. The algorithm assigns each nucleotide a score based on the length of its G-run context: isolated G = +1; GG = +2; GGG = +3; GGGG = +4; C runs receive symmetrical negative scores. A sliding window of 25 nt computes a local mean score; windows above a threshold (typically |2|) are flagged. Validated on 392 published sequences; the window size and threshold are tunable parameters.

**Literary analogue.** G-quadruplexes are locally stable non-canonical structures that form from specific sequence properties independent of the double-helix context. The literary analogue is a locally distinctive stylistic signal — a passage that stands structurally apart from its context by virtue of concentrated local properties. Specifically: passages with unusually high anaphoric density (GGG-runs ≡ aaaa-runs of the same word at sentence-openings), passages with extreme syntactic parallelism, passages where metaphors "stack" into a dense figurative cluster, or passages with concentrated sound-patterning (alliteration, assonance). These are the textual equivalent of G-quadruplex structures: locally stable special configurations that have functional roles in the text's operation.

**Palimpsest equivalent: StyleG4Hunter.** A local stylistic intensity scorer: (1) Replace G/C with presence/absence scores for specific stylistic signals per token: anaphoric position score, alliterative score, metaphoric density score, parallelism depth score. (2) Apply sliding window of N tokens (tunable, default 25). (3) Score each window as mean of token-level signal scores. (4) Flag windows above threshold as "stylistic G4" regions — passages of unusually concentrated stylistic intensity. (5) Report window coordinates, peak score, signal type. (6) Biological function analogue: correlate G4-equivalent regions with known rhetorical high-points, oration climaxes, lyric intensity peaks to validate that the structural signal predicts functional significance.

**Inputs.** Token-level feature scores; window size; threshold parameter.

**Outputs.** G4-equivalent span table; heat map score vector; per-text statistics on high-intensity region distribution.

**Source**: [G4Hunter original, Nucleic Acids Research 2016](https://academic.oup.com/nar/article/44/4/1746/1854457), [G4Hunter web application, Bioinformatics 2019](https://academic.oup.com/bioinformatics/article/35/18/3493/5306941)

---

### 3.5 LADetector — Heterochromatic Domain Boundary Detection

**Genomics function.** Lamina-Associated Domains (LADs) are large (0.1–10 Mb) regions of heterochromatin anchored at the nuclear periphery, characterized by gene repression, low transcriptional activity, and enrichment for H3K9me3 (constitutive heterochromatin). LAD boundaries are sharp transitions between repressed interior and active flanking regions, marked by CTCF binding and H3K27me3 enrichment. LADetector applies a circular binary segmentation algorithm to DamID signal data (a method for mapping genome-nuclear lamina contacts) to call LAD boundaries. Two-state HMM variants and sliding window approaches are also used. LADs define which genomic regions are "silenced by default" and require active derepression to be expressed.

**Literary analogue.** LADs map to topically suppressed or marginalized regions in a text: the passages that are structurally present but functionally peripheral — extended digressions, proleptic asides, subordinate clauses embedded within main narrative action, passages consistently skipped in reader engagement data, sections that critics rarely cite or discuss. Like LADs at the nuclear periphery, these are the textual "periphery" — segments anchored to the structural scaffold (they must be there for the text to cohere) but heterochromatically silent in terms of active readerly attention. The sharp LAD boundary maps to the transition point between main narrative action and embedded digression.

**Palimpsest equivalent: MarginDetector.** A textual periphery and digression detector: (1) Compute an "attention DamID signal" — a continuous engagement score per passage derived from reader dwell time, highlighting, and skip rates (analogous to DamID's lamina proximity signal). (2) Apply binary segmentation (circular binary segmentation or two-state HMM) to identify sustained low-engagement domains vs. high-engagement active regions. (3) Identify boundary regions: the sharp transitions between sustained low-engagement and high-engagement. (4) Characterize boundary properties: are boundaries marked by transition signals (chapter headings, paragraph breaks, syntactic frames like "Meanwhile..." or "In a digression...")?  (5) Classify domain types: constitutive periphery (always low attention across all readers) vs. facultative periphery (low attention in some reader populations, high in others — analogous to H3K27me3 vs. H3K9me3 heterochromatin).

**Inputs.** Reader engagement signal vector (continuous, per passage); text structure annotations (paragraph/chapter boundaries); optional: multiple reader populations for cell-type-analogue comparison.

**Outputs.** Domain boundary calls with confidence; domain type classification; boundary coordinate list; statistics on domain size distribution; cross-reader-population comparison.

**Source**: [LADs: peripheral matters and internal affairs, Genome Biology 2020](https://genomebiology.biomedcentral.com/articles/10.1186/s13059-020-02003-5), [LADs: links with chromosome architecture, PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC5532494/)

---

## Part IV: Infrastructure Architecture

### 4.1 GFF3 and BED: The Coordinate and Format Standards

**GFF3 architecture.** GFF3 (Generic Feature Format version 3) is a nine-column tab-delimited format where each row describes one genomic feature:

```
seqname  source  type  start  end  score  strand  phase  attributes
chr1     MAKER   gene  1000   5000  .      +       .      ID=gene1;Name=BRCA1
chr1     MAKER   mRNA  1000   5000  .      +       .      ID=mRNA1;Parent=gene1
chr1     MAKER   exon  1000   1200  .      +       .      Parent=mRNA1
```

The `Parent` attribute creates a directed acyclic graph of feature containment: gene → mRNA → exon/CDS. The `ID` attribute must be unique within the file. Feature types are drawn from the Sequence Ontology (2,278 terms). Attributes are free key-value pairs, enabling arbitrary metadata attachment. Multi-genome features are expressed using the `Target` attribute with alignment coordinates.

The critical design principle: **annotation and reference sequence are separated**. The GFF3 file contains only coordinates and metadata; the reference FASTA is a separate file. This standoff design enables multiple independent annotation layers to coexist over the same reference without any file modification.

**BED format.** BED (Browser Extensible Data) uses a 0-based, half-open coordinate system (`[start, end)`) against a `chrom` field. The minimal three fields are chrom, chromStart, chromEnd. Optional fields add name, score, strand, thickStart, thickEnd (for CDS vs. UTR visualization), itemRgb (display color), and blockCount/blockStarts/blockSizes (for exon structures within a gene). BED's simplicity makes it the preferred format for track data in genome browsers; GFF3's hierarchy makes it the preferred format for annotation exchange.

**For Palimpsest.** The Palimpsest Annotation Format (PAF) should directly mirror GFF3:

```
docname    tool       type         start  end   score  strand  phase  attributes
moby_dick  RhetoriKa  scene        0      4821  0.92   +       .      ID=scene1;chapter=1;AED=0.08
moby_dick  ModeHMM    mode_region  0      4821  .      +       .      ID=mode1;state=expository;Parent=scene1
moby_dick  FormInfernal chiasmus   245    312   8.7    +       .      ID=form1;model=chiasmus_classical;evalue=3e-4
```

- `docname` replaces `seqname` (the reference sequence identifier)
- `start`/`end` are Unicode character offsets, 0-based half-open (following BED convention for arithmetic simplicity)
- `type` is drawn from a Literary Feature Ontology (LFO), the SO analogue for Palimpsest
- `Parent` enables hierarchical containment: a book contains chapters contains scenes contains speech acts
- `score` is the annotation confidence (AED analogue, inverted if desired)
- `attributes` carries tool-specific metadata as free key-value pairs

Multi-layer annotations are multiple GFF3 files, one per tool/layer, sharing the same reference coordinates — the standoff principle. A query layer can be overlaid on any combination of other layers without modification.

**Coordinate system choice.** Use character offsets over a Unicode-normalized text. The normalization step (Unicode normalization form NFC, collapsing variant whitespace, standardizing quote characters) is the genome assembly step — it must be done once, producing a canonical reference to which all annotations are anchored.

**Source**: [GFF3 specification, Sequence Ontology GitHub](https://github.com/The-Sequence-Ontology/Specifications/blob/master/gff3.md), [NCBI GFF3 documentation](https://www.ncbi.nlm.nih.gov/datasets/docs/v2/reference-docs/file-formats/annotation-files/about-ncbi-gff3/), [BED format specification, SAMtools](https://samtools.github.io/hts-specs/BEDv1.pdf), [The Sequence Ontology, Genome Biology 2005](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC1175956/)

---

### 4.2 Evidence-Based Annotation: The MAKER Architecture Applied to Text

MAKER's core contribution is formalized evidence integration: rather than trusting any single annotation source, it weights and reconciles multiple independent evidence types to produce a consensus annotation with a calibrated confidence score (AED). The three evidence tiers are:

1. **Ab initio prediction** (breadth): finds everything that looks gene-like from sequence statistics alone; high sensitivity, lower precision; provides coverage.
2. **Transcript evidence** (locality): shows where this organism actually expressed sequence under sampled conditions; high precision for expressed genes, incomplete coverage.
3. **Protein homology** (constraint): anchors predictions to known biological functions in related species; provides functional plausibility and evolutionary validation.

EvidenceModeler (EVM) formalizes this as a weighted consensus: each evidence type gets an assigned weight; for each candidate feature structure, the weighted sum of supporting evidence is computed; the structure with highest weighted evidence score is selected. IPred extends this with more sophisticated integration at the transcript level.

**Translation to Palimpsest.** The Palimpsest evidence architecture for any annotation type (say, "scene boundaries") should follow the same three-tier structure:

| MAKER Tier | Text Equivalent | Tool |
|---|---|---|
| Ab initio prediction | Statistical boundary model trained on syntactic/prosodic signals; no prior knowledge of this text | StyleBRAKER |
| Transcript evidence | Reader segmentation data: where actual readers drew boundaries in this text | ScholiaApollo (collected readings) |
| Protein homology | Alignment to canonical scene-type templates from known texts of the same genre | NarrativeMAKER genre library |

The AED score translates directly: an annotation where all three sources agree gets AED near 0.0 (high confidence); an annotation where only the ab initio model fires gets AED near 1.0 (low confidence, requires manual curation).

**The iterative retraining loop** is essential: Palimpsest should, like MAKER, use first-pass annotations to retrain its ab initio models. Specifically, high-confidence annotations (AED < 0.2) from a first pass should be used as training data to refine the boundary models, which then produce a second pass with higher precision. This is the Palimpsest equivalent of MAKER's "autotraining" feature.

**Source**: [MAKER evidence integration, PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC2134774/), [EvidenceModeler, Genome Biology 2008](https://link.springer.com/article/10.1186/gb-2008-9-1-r7), [IPred, BMC Genomics 2015](https://bmcgenomics.biomedcentral.com/articles/10.1186/s12864-015-1315-9)

---

### 4.3 JBrowse/IGV Architecture: The Multi-Layer Multi-Resolution Text Browser

**JBrowse 1 architectural innovation.** The original JBrowse's key contribution was moving genome rendering to the client. All feature retrieval and rendering happen in the browser, not the server. The critical data structure enabling this is the **NCList (Nested Containment List)**: a hierarchical interval data structure that efficiently retrieves all features overlapping a query region in O(log n + k) time, where k is the number of hits. This structure handles overlapping features naturally (parent-child containment, overlapping features on the same track) without requiring a database query to the server for every pan or zoom operation.

**JBrowse 2 modular architecture.** JBrowse 2 separates concerns into: **adapters** (data retrieval, format-specific, e.g. BAMAdapter, VcfTabixAdapter), **renderers** (visual output generation, e.g. PileupRenderer), **displays** (a method for rendering a track in a specific view), and **views** (the top-level container, e.g. LinearGenomeView, CircularView, DotplotView). Plugins add new pluggable elements in any category; tracks can wrap other tracks; adapters can chain (an adapter computing from another adapter's output). This makes the system genuinely extensible without modifying core code.

**Zoom-level rendering strategy.** At maximum zoom, sequence tracks show individual bases. At intermediate zoom, feature tracks show individual features. At low zoom (megabase scale), density/coverage tracks show summary statistics rather than individual features (analogous to BigWig summarization). The transition between representations is handled by track configuration specifying zoom-level cutoffs. Overlapping features are collapsed into a compact display by default, with options to expand on separate rows.

**IGV complementary approach.** IGV handles annotation track overplotting by default "compact" mode (collapsing overlapping transcripts to a single line) with expansion options showing individual features on separate rows. IGV-web and JBrowse 2 now share a circular view component for structural variants.

**For Palimpsest.** The Palimpsest Text Browser (PTB) should follow JBrowse 2's adapter/renderer/display/view architecture precisely:

- **Adapters**: PAFAdapter (reads PAF annotation files), ReaderSignalAdapter (reads engagement logs), AllusioDB Adapter, etc.
- **Renderers**: SpanRenderer (draws annotation spans as colored bars), DensityRenderer (draws signal coverage as continuous curve), ContactMapRenderer (draws 2D co-occurrence heat map).
- **Views**: LinearTextView (the primary sequential text view, analogous to LinearGenomeView); ChapterMapView (zoomed-out structural overview, analogous to CircularView for whole-chromosome structure); ContactMapView (2D narrative contact map, analogous to Hi-C contact map view in JBrowse 2).
- **Zoom levels**: At maximum zoom (word level), phonemic annotations (stress, rhyme) are visible; at sentence level, syntactic and rhetorical annotations; at paragraph/scene level, narrative structure annotations; at chapter level, thematic arc annotations; at whole-text level, ModeHMM state coverage only.

The NCList data structure should be used for efficient retrieval of overlapping annotation spans at any zoom level. The key insight from JBrowse's design: the browser should never contact the server during pan and zoom operations — all necessary feature data for the current viewport should already be on the client, loaded lazily as new regions come into view.

**Source**: [JBrowse: A next-generation genome browser, Genome Research 2009](https://genome.cshlp.org/content/19/9/1630), [JBrowse 2, Genome Biology 2023](https://genomebiology.biomedcentral.com/articles/10.1186/s13059-023-02914-z), [JBrowse 2 developer guide](https://jbrowse.org/jb2/docs/developer_guide/)

---

### 4.4 ChromHMM Joint Training Across Cell Types: The Cross-Corpus Model

**The ENCODE/Roadmap approach.** The Roadmap Epigenomics consortium's key methodological contribution was training a single ChromHMM model by virtually concatenating data from 60 high-quality reference epigenomes. The training protocol:

1. Select 5 histone marks assayed in all 127 epigenomes (H3K4me3, H3K4me1, H3K36me3, H3K27me3, H3K9me3).
2. For each epigenome, binarize the signal in 200 bp bins using a Poisson threshold (p < 10⁻⁴).
3. Virtually concatenate all 60 training epigenomes' binarized matrices.
4. Train a single HMM on this concatenated matrix.
5. Apply the trained model to all 127 epigenomes to produce consistent state assignments.

The result: an 18-state model where State 7 = Active Enhancer means the same thing in embryonic stem cells as in T-cells as in hepatocytes — because the model learned the definition of "Active Enhancer" from signal patterns consistent across all 60 training cell types. This cross-cell-type consistency is what enables comparative epigenomics.

**For Palimpsest.** The critical translation: train ModeHMM jointly across a representative corpus of texts, so that Mode 4 = Free Indirect Discourse means the same thing in Woolf as in Flaubert as in James. The training protocol for Palimpsest:

1. Select 5–8 textual signals assayed uniformly across all texts in the training corpus (sentence length, POS distribution entropy, pronoun shift rate, punctuation density, named entity density, reported speech markers, figurative language density, tense shift rate).
2. For each text, binarize or discretize signals in 100-word windows.
3. Virtually concatenate all training texts.
4. Train a single HMM on the concatenated matrix (number of states K = 15–25; validated by enrichment analysis against a held-out set of hand-annotated passages).
5. Apply to any new text to produce consistent mode state assignments.

The hiHMM generalization — joint non-parametric Bayesian inference across multiple datasets — translates to training a Bayesian non-parametric mode model that learns the number of states from data rather than pre-specifying it, which is valuable since the appropriate number of literary modes is not known a priori.

**Source**: [Roadmap Epigenomics chromatin state model](https://egg2.wustl.edu/roadmap/web_portal/chr_state_learning.html), [hiHMM: Bayesian non-parametric joint inference, PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC4481846/), [Multi-scale chromatin state annotation, Nature Communications 2017](https://www.nature.com/articles/ncomms15011)

---

## Comparison Table: Genomics Tools → Palimpsest Equivalents

| Genomics Tool | Genomics Function | Literary Analogue | Palimpsest Tool | Key Algorithm |
|---|---|---|---|---|
| MAKER | Multi-evidence gene model synthesis | Scene/episode annotation with AED confidence | NarrativeMAKER | Weighted evidence consensus + iterative training |
| BRAKER | Unsupervised self-training from native signal | Style-adaptive boundary learning from reader data | StyleBRAKER | GeneMark-ET analogue + DBN |
| Prokka | Rapid batch annotation via tiered database lookup | Fast rhetorical figure labeling | RhetoriKa | BLAST-analogue tiered lookup |
| Liftoff | Annotation transfer between genome assemblies | Annotation transfer across text versions/translations | TextLiftoff | Minimap2-analogue + exon-constraint remapping |
| Apollo | Collaborative manual curation over evidence tracks | Scholarly edition with computational evidence | ScholiaApollo | Web-based concurrent editing + JBrowse |
| MAPLE/KAAS | Metabolic pathway completeness scoring | Narrative schema completeness scoring | NarrativeKEGG | KO assignment + Boolean MCR |
| Infernal | Structure-based ncRNA search via CMs | Structural pattern search via literary CMs | FormInfernal | SCFG covariance model |
| tRNAscan-SE | Precise universal structural RNA detection | Verse form detection with isotype classification | VerseFormScan | Multi-model CM scoring |
| RepeatMasker | Transposon/repeat detection and masking | Allusion/cliché detection and masking | AllusionMasker | HMM-based homology to AllusioDB |
| Pseudofinder | Pseudogene decay detection | Narrative dysfunction and decay detection | NarrativePseudofinder | Comparative decay analysis |
| ChromHMM | HMM chromatin state discovery | Rhetorical mode segmentation | ModeHMM | Multivariate HMM on binarized signals |
| Segway | DBN continuous signal genome segmentation | High-resolution mode segmentation | ModeDBN | Dynamic Bayesian network |
| Akita | CNN prediction of 3D genome folding | CNN prediction of chapter/act structure | StructureFold-CNN | Basenji-derived CNN + 2D head |
| HiCExplorer | TAD calling from Hi-C contact maps | Narrative domain calling from contact maps | StructureFold-HiC | Insulation score + local minima |
| TargetFinder | Enhancer-promoter interaction prediction | Foreshadowing-fulfillment link prediction | EchoFinder | Gradient boosted trees + chromatin features |
| EPIVAN | Sequence-only EPI prediction | Sequence-only long-range link prediction | EchoFinder-Seq | CNN + GRU + attention |
| G4Hunter | Local G-quadruplex propensity scoring | Local stylistic intensity scoring | StyleG4Hunter | Sliding window G-score |
| LADetector | Heterochromatic peripheral domain detection | Structural periphery and digression detection | MarginDetector | CBS algorithm + 2-state HMM |
| GFF3 | Multi-layer hierarchical annotation format | Palimpsest Annotation Format (PAF) | PAF spec | Parent/ID hierarchy + SO-analogue LFO |
| ChromHMM joint training | Cross-cell-type consistent state vocabulary | Cross-text consistent mode vocabulary | ModeHMM training protocol | Virtual concatenation + single HMM |
| JBrowse 2 | Modular multi-track genome browser | Modular multi-layer text browser | Palimpsest Text Browser | NCList + adapter/renderer/view |

---

## Recommendations

1. **Primary Recommendation: Adopt GFF3/standoff architecture as the canonical annotation format.** Palimpsest's Annotation Format (PAF) should be a near-direct translation of GFF3 with character offsets replacing base-pair coordinates and a Literary Feature Ontology replacing the Sequence Ontology. This is a solved problem in genomics — use it exactly as designed. Build tooling to render multiple PAF files as simultaneous tracks over the same text reference.

   - Rationale: Standoff annotation is the correct architecture for multi-layer text annotation. It separates annotation from text, allows independent layers to coexist without mutual interference, and enables cross-layer queries.
   - Caveats: Requires a normalization step to produce a canonical reference text — this is non-trivial for historical texts with encoding variants.

2. **Build ModeHMM first, joint-trained across a corpus.** This is the most technically powerful and theoretically novel component. The Roadmap-style joint training protocol is straightforward to implement with ChromHMM or its Python equivalents (pomegranate, hmmlearn). Train on 60+ texts with 5–8 binarized features. The resulting universal mode vocabulary enables genuine cross-text comparison, which is the core scientific value proposition of Palimpsest.

   - Rationale: Without consistent cross-text annotation, comparative literary analysis remains informal. A jointly trained mode model is the foundation for all quantitative comparison.

3. **Implement StyleBRAKER's reader-signal pipeline early.** The unsupervised self-training approach eliminates the need for large annotated corpora for each new text or author. If Palimpsest collects reader engagement signals (dwell time, re-reading events, highlighting) via its interface, these become a perpetual training signal that improves annotation models with every reader session.

4. **Build the PTB (Palimpsest Text Browser) on JBrowse 2's adapter/renderer/view architecture** rather than a custom visualization stack. JBrowse 2 is MIT-licensed, has an active plugin ecosystem, and has already solved the hard problems of overlapping annotation rendering, zoom-level transitions, and parallel track loading. The NCList data structure for overlapping spans is particularly valuable.

   - Caveat: JBrowse 2 is oriented to genomic coordinates; significant adapter work is required to make it operate over character-offset text. A dedicated PAFAdapter and text-sequence track must be implemented.

5. **Implement NarrativePseudofinder for manuscript studies.** The comparison of text versions using a decay-mutation model is directly applicable to stemmatic analysis and editorial scholarship. A "sleuth" branch comparing manuscript variants to an archetype can systematically catalog scribal error types, which is of direct interest to digital humanities projects.

---

## Action Items

- [ ] Define the Literary Feature Ontology (LFO): a controlled vocabulary of literary feature types organized in a hierarchy analogous to the Sequence Ontology, starting with ~50 terms covering the most common narrative, rhetorical, and formal feature types
- [ ] Specify the Palimpsest Annotation Format (PAF): adapt the GFF3 nine-column structure with character-offset coordinates and LFO types; define required vs. optional attributes; define the AED-equivalent confidence metric
- [ ] Prototype ModeHMM: implement a ChromHMM-analogue using Python hmmlearn or pomegranate; collect a training corpus of 60 texts; select 5–8 binarized feature signals; validate against hand-annotated passages
- [ ] Evaluate JBrowse 2 as PTB foundation: build a proof-of-concept PAFAdapter and text-sequence track for JBrowse 2; assess performance for literary text scales (character-offset arithmetic is simpler than genomic math)
- [ ] Build AllusioDB: begin curating a hierarchical allusion database as a Dfam analogue, starting with Biblical, classical, and Shakespearean allusion families in HMM/profile form
- [ ] Design the StructureFold narrative contact map: implement co-occurrence counting across chapter/passage pairs; generate a contact matrix for a test novel; apply insulation score algorithm to detect narrative domain boundaries

---

## Sources

1. [MAKER: An easy-to-use annotation pipeline, PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC2134774/)
2. [MAKER HPC documentation, NIH](https://hpc.nih.gov/apps/maker.html)
3. [BRAKER1: Unsupervised RNA-Seq-Based Genome Annotation, Bioinformatics 2016](https://academic.oup.com/bioinformatics/article/32/5/767/1744611)
4. [BRAKER2, NAR Genomics and Bioinformatics 2021](https://academic.oup.com/nargab/article/3/1/lqaa108/6066535)
5. [BRAKER3 preprint, bioRxiv 2023](https://www.biorxiv.org/content/10.1101/2023.06.10.544449.full.pdf)
6. [BRAKER GitHub](https://github.com/Gaius-Augustus/BRAKER)
7. [Prokka: rapid prokaryotic genome annotation, Bioinformatics 2014](https://academic.oup.com/bioinformatics/article/30/14/2068/2390517)
8. [Prokka GitHub](https://github.com/tseemann/prokka)
9. [Liftoff: accurate mapping of gene annotations, Bioinformatics 2021](https://academic.oup.com/bioinformatics/article/37/12/1639/6035128)
10. [Liftoff GitHub](https://github.com/agshumate/Liftoff)
11. [LiftoffTools, PMC](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC11137477/)
12. [Apollo: Democratizing genome annotation, PLOS Computational Biology 2019](https://journals.plos.org/ploscompbiol/article?id=10.1371/journal.pcbi.1006790)
13. [Web Apollo, Genome Biology 2013](https://genomebiology.biomedcentral.com/articles/10.1186/gb-2013-14-8-r93)
14. [KAAS: automatic genome annotation and pathway reconstruction, PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC1933193/)
15. [MAPLE 2.1.0, DNA Research 2016](https://academic.oup.com/dnaresearch/article/23/5/467/2236168)
16. [MAPLE web portal](https://www.genome.jp/tools/maple/)
17. [Infernal official site](http://eddylab.org/infernal/)
18. [Non-coding RNA analysis with Rfam, PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC6754622/)
19. [Studying RNA homology with Infernal, PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC5010141/)
20. [tRNAscan-SE 2.0, Nucleic Acids Research 2021](https://academic.oup.com/nar/article/49/16/9077/6355886)
21. [tRNAscan-SE methods, PMC](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC6768409/)
22. [RepeatMasker documentation](https://www.repeatmasker.org/webrepeatmaskerhelp.html)
23. [TE annotation best practices, PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC10149145/)
24. [Pseudofinder, Molecular Biology and Evolution 2022](https://academic.oup.com/mbe/article/39/7/msac153/6633826)
25. [ChromHMM Nature Protocols 2017](https://www.nature.com/articles/nprot.2017.124)
26. [ChromHMM official site, MIT/ENCODE](https://compbio.mit.edu/ChromHMM/)
27. [Roadmap Epigenomics chromatin state models](https://egg2.wustl.edu/roadmap/web_portal/chr_state_learning.html)
28. [ChromHMM + Segway ENCODE integration, NAR 2013](https://academic.oup.com/nar/article/41/2/827/1071531)
29. [Segway official site](https://segway.hoffmanlab.org/)
30. [Segway 2.0 preprint, bioRxiv](https://www.biorxiv.org/content/10.1101/147470.full.pdf)
31. [Akita, Nature Methods 2020](https://www.nature.com/articles/s41592-020-0958-x)
32. [AkitaV2, PLOS Computational Biology 2025](https://journals.plos.org/ploscompbiol/article?id=10.1371/journal.pcbi.1012824)
33. [TargetFinder, Nature Genetics 2016](https://pubmed.ncbi.nlm.nih.gov/27064255/)
34. [Quantitative EPI prediction, Genome Research 2020](https://genome.cshlp.org/content/30/1/72.full)
35. [EPIVAN, Bioinformatics 2020](https://academic.oup.com/bioinformatics/article/36/4/1037/5564117)
36. [G4Hunter original, Nucleic Acids Research 2016](https://academic.oup.com/nar/article/44/4/1746/1854457)
37. [G4Hunter web application, Bioinformatics 2019](https://academic.oup.com/bioinformatics/article/35/18/3493/5306941)
38. [LADs: peripheral matters and internal affairs, Genome Biology 2020](https://genomebiology.biomedcentral.com/articles/10.1186/s13059-020-02003-5)
39. [GFF3 specification, Sequence Ontology GitHub](https://github.com/The-Sequence-Ontology/Specifications/blob/master/gff3.md)
40. [NCBI GFF3 documentation](https://www.ncbi.nlm.nih.gov/datasets/docs/v2/reference-docs/file-formats/annotation-files/about-ncbi-gff3/)
41. [BED format specification, SAMtools](https://samtools.github.io/hts-specs/BEDv1.pdf)
42. [Sequence Ontology, Genome Biology 2005](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC1175956/)
43. [EvidenceModeler, Genome Biology 2008](https://link.springer.com/article/10.1186/gb-2008-9-1-r7)
44. [IPred integration tool, BMC Genomics 2015](https://bmcgenomics.biomedcentral.com/articles/10.1186/s12864-015-1315-9)
45. [JBrowse: A next-generation genome browser, Genome Research 2009](https://genome.cshlp.org/content/19/9/1630)
46. [JBrowse 2, Genome Biology 2023](https://genomebiology.biomedcentral.com/articles/10.1186/s13059-023-02914-z)
47. [JBrowse 2 developer guide](https://jbrowse.org/jb2/docs/developer_guide/)
48. [JBrowse 2 pluggable elements](https://jbrowse.org/jb2/docs/developer_guides/pluggable_elements/)
49. [hiHMM: Bayesian non-parametric joint inference, PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC4481846/)
50. [STAM: Stand-off Text Annotation Model](https://annotation.github.io/stam/)

---

## Uncertainties

- **EPIVAN specifics**: The paper from Hong et al. 2020 describes using pre-trained DNA vectors; the exact transferability of this architecture to text (where "sequence" means token sequence rather than nucleotide sequence) requires empirical validation. Sentence-level GRU models with attention are well-established in NLP, but the specific architectural choices need testing on literary data.
- **Optimal window size for ModeHMM**: ChromHMM uses 200 bp bins because that is the nucleosome resolution. The equivalent for text — the size of the "functional unit" — is not determined a priori. 100-word windows are a reasonable starting hypothesis but require empirical validation against hand-annotated mode transitions.
- **LADetector specifics**: The LADetector tool itself is described in genomics literature primarily as a refinement of the circular binary segmentation (CBS) algorithm for DamID data; it is less widely cited than ChromHMM or RepeatMasker. Its implementation details (beyond CBS + HMM) are less thoroughly documented in the public literature. The literary MarginDetector should be built from the CBS algorithm directly, using the LADetector design principle.
- **AllusioDB curation**: Building an AllusioDB equivalent is a significant humanities labor effort. The Dfam database was built over decades by a large community. The literary equivalent will require sustained scholarly curation infrastructure before it reaches useful coverage for most literary traditions.

---

## Related Topics for Future Research

- **ENCODE Data Coordination Center pipeline automation** as a model for large-scale batch annotation pipelines across corpora
- **Variant Call Format (VCF)** as a model for representing textual variants across manuscript witnesses (substitution, insertion, deletion at character-offset coordinates)
- **JASPAR/TRANSFAC transcription factor binding motif databases** as models for curated pattern libraries (the binding site motif as the precise analogue of a rhetorical figure's syntactic template)
- **Comparative epigenomics (cross-species ChromHMM)** as a model for cross-linguistic literary comparison — can mode annotations trained on English texts transfer to French texts of the same period?
- **Oxford Nanopore direct RNA sequencing and epitranscriptomics** as a model for annotation of the reading experience in real time (the "base modifications" map to cognitive load, emotional response, interpretive uncertainty)
- **STAM (Stand-off Text Annotation Model)** — a recent humanities infrastructure project that has already begun implementing GFF3-like standoff annotation for text; Palimpsest should evaluate STAM as a potential foundation before building a custom PAF from scratch