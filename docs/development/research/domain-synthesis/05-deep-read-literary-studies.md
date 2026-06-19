# Deep Reading: Literary Studies Books — Palimpsest Relevance Analysis

**Generated**: 2026-06-06

---

## Structured Analysis: Eight Books on Computational Literary Studies

---

### 1. Andrew Piper — *Enumerations: Data and Literary Study* (2018)

**Core Thesis**
Literary study has suffered from two foundational problems: it cannot account for the pervasive fact of textual repetition (the vast majority of any text is repetition, not singularity), and it lacks a "science of generalization" — a principled way to move from individual observations to categorical claims about genres, periods, and forms. Computational modeling, understood as explicit representational craft rather than objective measurement, addresses both problems by making the critic's process legible, testable, and revisable.

**Chapter-by-Chapter Relevance**
- **Introduction (Reading's Refrain)**: Frames the core concepts — distributional semantics, vector space models, the modeling paradigm. Directly applicable to Palimpsest's analytical engine. Piper's insistence that models are "as if" constructions (Vaihinger) and always situated is critical for UI that communicates uncertainty.
- **Ch. 1 — Punctuation (Opposition)**: Uses grep-level regex to study punctuation in 230,000+ poems. Demonstrates that the most elementary textual features carry structural meaning. For Palimpsest: punctuation as a parseable signal of style and genre.
- **Ch. 2 — Plot (Lack)**: Vector space models + social network graphs approximate plot structure via the concept of "lack" (Greimassian narrative grammar operationalized computationally). Direct blueprint for Palimpsest's narrative arc modeling.
- **Ch. 3 — Topoi (Dispersion)**: Topic models over 15,000 novels to study the distribution of commonplace ideas. Relevant to Palimpsest's theme-tracking and intertextuality features.
- **Ch. 4 — Fictionality (Sense)**: Machine learning classifiers distinguish fiction from nonfiction using features like sensorial language and embodied entities. Tells Palimpsest what linguistic registers define fictional mode — useful for text classification and alignment.
- **Ch. 5 — Characterization (Constraint)**: Dependency parsing + coreference resolution to study character behavior across 650,000 fictional characters. Blueprint for Palimpsest's character analysis layer.
- **Ch. 6 — Corpus (Vulnerability)**: Nested models to measure a poet's "vulnerability" — stylistic exposure over a career. For Palimpsest: career/corpus-level analysis, diachronic evolution.
- **Conclusion (Implications)**: Calls for making the observer's position explicit within models. For Palimpsest: every analysis should surface its assumptions and data sources in the UI.

**Key Methodology**
Progression from simple (regex, frequency counts) through intermediate (vector space models, topic models, logistic regression) to complex (dependency parsing, coreference, nested models). Each chapter's method is scaled to the literary concept being studied. Strong emphasis on reproducibility: all code and derived data made public.

**Conceptual Contribution**
Reframes the close/distant binary as a circular, iterative process: belief → close reading → measurement → distant reading → interpretation → model → remodel. Introduces "modeling" as the central concept replacing both "close reading" and "distant reading." The model is a representation that encodes the critic's situated beliefs, not an objective transcript of the text. Repetition — not singularity — is the primary substance of literature.

**Development Implication for Palimpsest**
Build a layered analysis pipeline mirroring Piper's methodological progression: (1) surface features (punctuation, word frequency), (2) vector/semantic space, (3) topic models, (4) supervised classification, (5) dependency/coreference. Every analysis output must expose its assumptions and corpus parameters in the UI. The model diagram (fig. 0.1 — close reading ↔ measurement ↔ distant reading ↔ interpretation cycling through Model and Remodel) should be Palimpsest's architectural metaphor.

---

### 2. Ted Underwood — *Distant Horizons: Digital Evidence and Literary Change* (2019)

**Core Thesis**
Literary history has been narrated at the wrong scale: we understand individual authors and discrete periods well, but century-spanning patterns have been invisible because they exceed any single reader's memory. Quantitative methods — specifically "perspectival modeling" using supervised machine learning trained on labeled human evidence — make these long arcs visible without sacrificing interpretive nuance or claiming objectivity.

**Chapter-by-Chapter Relevance**
- **Preface (The Curve of the Literary Horizon)**: Articulates the scale problem and the modeling turn. Critical for Palimpsest's theoretical framing: numbers are not more objective than words; they are another way to model situated interpretive communities.
- **Ch. 1 — Do We Understand the Outlines of Literary History?**: Demonstrates fiction/biography divergence over 300 years using logistic regression on word frequencies. Shows how to frame a hypothesis-first inquiry rather than data-dredging. For Palimpsest: the fiction/nonfiction classifier is a concrete first feature.
- **Ch. 2 — The Life Spans of Genres**: Perspectival modeling applied to genre history — detective fiction, science fiction. Different historical observers define genre differently; models can crystallize those perspectives and compare them. For Palimpsest: multi-perspective genre tagging where users can choose which historical frame to apply.
- **Ch. 3 — The Long Arc of Prestige**: Enriches text corpus with social metadata (reviews, bestseller lists) to study how aesthetic judgment shaped literary change. For Palimpsest: attaching reception metadata to texts opens new analytical dimensions.
- **Ch. 4 — Metamorphoses of Gender**: Character-level analysis of gender in characterization over 200 years using BookNLP-style tools. Gender dimorphism in verbs, adjectives, body parts is quantifiable and historically variable. For Palimpsest: character-level attribute extraction and tracking is validated here.
- **Ch. 5 — The Risks of Distant Reading**: Addresses limitations honestly. For Palimpsest: the uncertainty layer in visualizations; what claims the platform can and cannot support.
- **Appendix B — Methods**: Full technical description of logistic regression with regularization, cross-validation, and model evaluation. Directly usable as specification for Palimpsest's classification backend.

**Key Methodology**
Supervised logistic regression (with L2 regularization) on word-frequency feature vectors; cross-validation for accuracy estimation; perspectival modeling where different training sets crystallize different historical viewpoints; collaboration with computer scientists (David Bamman's BookNLP) for character-level NLP. Works at volume level and below-volume level.

**Conceptual Contribution**
"Perspectival modeling": instead of seeking objective classifications, train models on evidence labeled by specific communities (1973 readers of detective fiction; reviewers in prestigious journals) and use the resulting models to measure the parallax between perspectives. Genre, prestige, and gender are not stable categories but historically varying perspectives that can be crystallized in models and compared.

**Development Implication for Palimpsest**
Implement perspectival modeling as a first-class concept. Users should be able to select a "perspective" (a historical period's definition of a genre, or a critic's canon) and apply that lens to other texts. The platform should never present a single authoritative classification — always show the perspective that generated it. The Appendix B methods are a near-complete technical spec for the classification system.

---

### 3. Martin Paul Eve — *Close Reading with Computers: David Mitchell's Cloud Atlas* (2019)

**Core Thesis**
Computational methods can serve close reading — not replace it — by bringing microscopic attention to textual features that are present but too fine-grained for unassisted human perception. Using Cloud Atlas as a case study (a novel whose six sections deliberately mimic different historical genres and styles), Eve demonstrates that genre, historical linguistic mimesis, and textual variation are computationally detectable at the close level, yielding insights that enrich rather than dissolve literary interpretation.

**Chapter-by-Chapter Relevance**
- **Introduction**: Provides the best available critique and defense of the close/distant binary. The microscope vs. telescope metaphor is essential for Palimpsest's self-positioning. "Computational close reading" as going back to the text.
- **Ch. 1 — The Contemporary History of the Book**: Textual scholarship — tracking version variants across UK, US, and Kindle editions of Cloud Atlas, including cross-edition splice detection. For Palimpsest: the text-alignment and edition-comparison layer.
- **Ch. 2 — Reading Genre Computationally**: Parts-of-speech distributions and stylometric features distinguish the six chapters of Cloud Atlas as different genre signals. For Palimpsest: POS tagging as a genre-detection layer; authorship attribution methods applied adversarially.
- **Ch. 3 — Historical Fiction and Linguistic Mimesis**: Compares Cloud Atlas chapters against the Corpus of Contemporary American English to measure how accurately Mitchell mimics the language of each historical period. For Palimpsest: corpus comparison as a historical accuracy or style-distance metric.
- **Ch. 4 — Interpretation**: Connects computational findings back to literary argument. The "redaction" concept — what metadata reveals about texts. For Palimpsest: the interpretation layer where computational outputs are translated into humanistic arguments.
- **Conclusion**: Political aesthetics of metadata; what is revealed by the data surrounding a text. For Palimpsest: metadata as analytical object, not just organizational infrastructure.

**Key Methodology**
Textual collation across editions; POS tagging and frequency analysis for genre detection; corpus comparison against reference corpora (COCA, BNC); stylometry; authorship attribution methods applied to genre divergence. Close reading is used to validate and interpret computational outputs throughout.

**Conceptual Contribution**
The "microscope" framing: computation used at the single-text level to reveal features invisible to unassisted reading — not scale but resolution. "Taxonomographic metafiction": fiction that is about genre/taxonomy, making genre itself a computational object. The "necroreading ratio": the tradeoff between death-avoidance (processing more texts via computation) and reading-avoidance (alienation from the text). Palimpsest must manage this ratio in its design.

**Development Implication for Palimpsest**
Build edition comparison and textual collation as a first-class feature, not an afterthought. POS-based genre fingerprinting is implementable with spaCy right now. The corpus comparison feature (how does this text's language compare to a reference corpus?) is a high-value, tractable feature. Eve's methodology shows that a platform focused on a single text can still be computationally rigorous — Palimpsest does not have to operate only at corpus scale.

---

### 4. Franco Moretti — *Distant Reading* (2013)

**Core Thesis**
Literary history has been imprisoned by the canon — a few hundred texts out of the hundreds of thousands produced. Distant reading (studying literature at the scale of the full literary system, using maps, graphs, trees, and other non-textual representations) reveals formal and structural patterns invisible at the close-reading scale, particularly the systemic organization of world literature as an unequal, center-periphery system shaped by geography, evolution, and market forces.

**Chapter-by-Chapter Relevance**
- **Modern European Literature: A Geographical Sketch**: Literature as an ecological system shaped by geography — "allopatric speciation" of forms across national spaces. For Palimpsest: spatial metadata and geography as an analytical dimension; the "archipelago" model of literary culture.
- **Conjectures on World Literature**: The foundational distant reading manifesto. World literature is not a canon but a system; studying it requires models, not readings. For Palimpsest: justification for corpus-level features.
- **The Slaughterhouse of Literature**: Studies the failure of most detective fiction to achieve canonicity via tree diagrams of narrative devices. The "slaughterhouse" — what never gets studied. For Palimpsest: the platform should make the un-canonical accessible.
- **Network Theory, Plot Analysis**: Network graphs of character interactions in hamlet, applied to study how plot topology structures narrative. Direct blueprint for Palimpsest's character network visualization.
- **Style, Inc.: Reflections on 7,000 Titles**: Semantic analysis of British novel titles 1740–1850 reveals systematic changes in the social imaginary. For Palimpsest: title and paratextual analysis as a feature.

**Key Methodology**
Quantitative history drawing from evolutionary biology (species, selection, speciation), world-systems theory (center-periphery), and network science. Maps, graphs, trees as primary analytical tools rather than prose argument. Willing to work with derived data (not reading the texts directly) to achieve scale.

**Conceptual Contribution**
The literary system as an ecology: forms evolve, compete, and speciate under pressure from geography, market, and adjacent forms. "Distant reading" as a necessary complement to close reading — not a replacement but a different scale of analysis with different objects of knowledge (genres, systems, trends) rather than individual texts. The "great unread" as an epistemological problem, not a moral failing.

**Development Implication for Palimpsest**
Network visualization of character interactions is validated and specified here (the Hamlet analysis gives a concrete graph schema). The ecological/evolutionary framing suggests Palimpsest should support temporal views — how do features change across a corpus over time? The center-periphery model suggests including metadata about a text's cultural position (canonical vs. obscure, reviewed vs. unreviewed).

---

### 5. Matthew Jockers — *Macroanalysis: Digital Methods and Literary History* (2013)

**Core Thesis**
Literary scholars can no longer be content with anecdotal, close-reading evidence when digital libraries have made the full literary record accessible. "Macroanalysis" — systematic computational mining of large corpora — is not opposed to close reading but complements it; both scales are necessary, and only together can they produce sound literary-historical arguments.

**Chapter-by-Chapter Relevance**
- **Chs. 1–4 (Foundation)**: Establishes the methodological rationale with unusual clarity. Ch. 2 (Evidence) is the best single argument for why computational methods are necessary — the geological analogy (panning for gold vs. open-pit mining) should inform Palimpsest's marketing copy. Ch. 4 (Macroanalysis) formally defines the method.
- **Ch. 5 — Metadata**: Metadata as a first-order object of analysis — nationality, gender, date, publisher. For Palimpsest: metadata schema design; metadata-driven filtering and faceting.
- **Ch. 6 — Style**: Stylometric analysis using word frequency, POS, and other surface features across a large corpus of nineteenth-century fiction. For Palimpsest: the style analysis module.
- **Ch. 7 — Nationality**: How stylistic features cluster by national tradition. For Palimpsest: geographic/national faceting as an analytical dimension.
- **Ch. 8 — Theme**: LDA topic modeling applied to 3,000+ novels to map thematic distributions. Direct specification for Palimpsest's topic modeling feature. Jockers also trained topic models with MALLET.
- **Ch. 9 — Influence**: Network graphs of stylistic similarity as a proxy for literary influence. For Palimpsest: influence network visualization; "find similar texts" as a core feature.
- **Ch. 10 — Orphans**: Copyright as a barrier to research. For Palimpsest: data sourcing strategy; pre-1928 public domain vs. contemporary texts.

**Key Methodology**
Stylometry (word frequency, Burrows's Delta), LDA topic modeling (MALLET), network graphs of similarity (Gephi), metadata-driven analysis. Strongly empirical and reproducible; companion website with confusion matrices and color graphs.

**Conceptual Contribution**
Reframes literary research as evidence-driven inquiry analogous to (not identical with) scientific method. "Macroanalysis" as the companion to microanalysis — different grain, same object. The key insight: scale changes what is knowable, not just how much you know. Features invisible at the level of a few texts become detectable trends across thousands.

**Development Implication for Palimpsest**
Chs. 5–9 function as a feature specification for Palimpsest's analytical modules: metadata faceting, style distance, nationality clustering, topic modeling, and influence networks are all validated here with implementation details. The companion website model — supplementary interactive graphics — should be Palimpsest's deployment model for the public-facing layer.

---

### 6. Michael Toolan — *Making Sense of Narrative Text* (2016)

**Core Thesis**
Readers make sense of narrative not through abstract story grammars but through three interlocking processes anchored in language: tracking a changing *situation* (not just a plot), processing *lexical repetition* (cross-sentence bonds that create coherence), and constructing *mental pictures* that are updated as the text advances. The emotional and ethical peaks of a story (HEI passages — Heightened Emotional Involvement) are linguistically distinctive and detectable.

**Chapter-by-Chapter Relevance**
- **Ch. 1 — Introduction (Intersentential Connection to Interpersonal Engagement)**: The fundamental mystery of how readers combine sentences into unified texts. Establishes collocation, lexical priming, and semantic prosody as cross-sentence cohesion mechanisms. For Palimpsest: the sentence-to-passage coherence model; why word co-occurrence matters beyond individual sentences.
- **Ch. 2 — Patterning by Lexical Repetition**: "Links and bonds" analysis — a method for mapping which sentences are cohesively connected via shared lexical items. Applied to "The Princess and the Pea." For Palimpsest: the lexical patterning visualizer; coherence mapping.
- **Ch. 3 — Situation**: The "Situation" as the core narrative unit — a configuration of who/where/what that changes through events. Operationalizes Emmott's "contextual frame" theory. For Palimpsest: situation tracking as a scene-level annotation layer.
- **Ch. 4 — Mental Picturing**: Readers construct mental images from text; these images are updated rather than replaced. Spatiotemporal context-monitoring. For Palimpsest: the theoretical basis for scene/setting visualization features.
- **Ch. 5 — Integrating Lexical Patterning and the Pictured Narrative Situation**: Develops the concept of "prominent lexis" — words with high keyness relative to a reference corpus — and uses it to locate HEI passages. Combines corpus stylistics (Wmatrix/keyword analysis) with cognitive narratology. This is the closest thing in the literature to a specification for automatic emotional arc detection at the passage level.
- **Ch. 6 — Attempting to Bring It All Together**: Story sense + reader emotion + foregrounding. The unified model.

**Key Methodology**
Corpus stylistics (keyword analysis via Wmatrix, British National Corpus as reference); Hoey's links-and-bonds cohesion analysis; cognitive narratology (Emmott's contextual frames, Werth's Text World Theory); reader-response testing of HEI passages. Works at the short-story level with high lexical granularity.

**Conceptual Contribution**
The "HEI passage" (Heightened Ethical/Emotional Involvement) concept: the moments in a text that readers identify as most significant are linguistically distinctive — they show para-repetition, deictic amplification, specific syntactic patterns ("it was as if..."), and elevated semantic prominence. These are computationally detectable. This is the most actionable finding in the book for Palimpsest: a method for automatically locating narrative peaks.

**Development Implication for Palimpsest**
Implement HEI detection: keyword prominence (keyness vs. BNC), para-repetition density, deictic amplification signals, and clause-final constructions as features for a passage-level emotional intensity model. The "prominent lexis" table (Ch. 5, Table 5.1) is a concrete starting point. Toolan's links-and-bonds method could become Palimpsest's coherence graph — a network of cohesive relations among sentences that visualizes text texture. The Situation framework maps directly to scene-level segmentation.

---

### 7. Greg Carlisle — *Elegant Complexity: A Study of David Foster Wallace's Infinite Jest* (2007)

**Core Thesis**
*Infinite Jest* is structurally organized around a fractal Sierpinski Gasket — a recursive self-similar geometry that generates narrative meaning as much through gaps and absences as through explicit content. The novel's "elegant complexity" requires systematic, scene-by-scene annotation and pattern tracking (16 plot/character categories, 16 thematic categories) to be navigable and interpretable.

**Introduction + Chapter 1 Relevance**
- The introduction establishes the Sierpinski Gasket as the generative structural principle — readers "construct narrative interpretations as much out of what's missing as what's there." For Palimpsest: the idea that structured absence is a first-class narrative element.
- The 32-category tracking system (16 plot/character × 16 theme, arranged in four quaternary groups "Between / Around / Under / Away") is Carlisle's operational schema for the novel. This is the most fully developed manual annotation taxonomy in the corpus — directly usable as a test case for Palimpsest's annotation layer.
- Chapter 1 summaries demonstrate scene-level annotation practice: each section gets orientation data (POV, date, location), narrative summary, and thematic commentary (listing relevant categories). This is the annotation format Palimpsest should support.
- The Chronologies, ETA Spatial Orientation, and Character Associations sections at the back demonstrate the kinds of derived reference materials that a platform like Palimpsest should be able to generate or support: timeline reconstruction from a non-linear text, spatial mapping of settings, relationship graphs among characters.

**Key Methodology**
Manual close reading at the scene/section level; systematic thematic coding using a predefined taxonomy; chronological reconstruction; spatial mapping. No computational methods — but provides the ground truth annotations that computational methods should eventually reproduce.

**Conceptual Contribution**
The Sierpinski Gasket as a structural model for *Infinite Jest* implies that Palimpsest needs to handle fractal-patterned texts — texts where large-scale structure mirrors small-scale structure, where gaps are as important as content. The taxonomy of prepositions-as-themes (Between, Around, Under, Away) suggests that relational/spatial metaphors can organize thematic classification.

**Development Implication for Palimpsest**
Use *Infinite Jest* with Carlisle's annotation taxonomy as the primary test case for the annotation pipeline. Build the 32-category system as a demonstrable annotation schema. The scene-level summary + commentary structure should be a Palimpsest output format. Derive the character association network and timeline automatically from annotated text and compare to Carlisle's manual version. The Sierpinski Gasket framing validates building a "narrative structure" view that emphasizes recursive self-similarity and absent/missing sections.

---

### 8. Stephen Burn — *David Foster Wallace's Infinite Jest: A Reader's Guide* (2012, 2nd ed.)

**Core Thesis**
*Infinite Jest* is best understood not as a hermetically sealed postmodern artifact but as a node in a dense literary and cultural network: it both draws upon and reshapes a genealogy extending from DeLillo, Gaddis, and the encyclopedic novel tradition, while simultaneously spawning a "post-Wallace" generation of writers (Franzen, Powers, Saunders, Egan) who process and respond to its influence. Reading Wallace's novel in isolation — even close reading it — fails to capture its significance.

**Preface + Chapters 1–2 Relevance**
- **Ch. 1 (Legacy)**: Traces how *Infinite Jest* infected subsequent American fiction — specific allusions, formal borrowings, and thematic echoes in Franzen, Powers, Saunders, Lethem, Egan. This is network-theory applied manually to literary influence. For Palimpsest: intertextual network modeling validated at high resolution. Burn's essay also demonstrates that "E Unibus Pluram" functions as a program document for a literary generation — texts can have downstream effects on other texts that are traceable.
- **Ch. 2 (Problems in Wallace's Poetics)**: Close reading of "A Radically Condensed History of Postindustrial Life" (79 words) to derive Wallace's poetics: aural rhythm, alliteration/assonance, apostrophed possessives, cascading clause structures. Shows how a poetic/rhythmic analysis can be grounded in specific formal features — directly translatable to computational prosody features in Palimpsest.
- **Ch. 3 (The Novel)**: Structural analysis of *Infinite Jest* itself, focusing on time, identity, and order beneath apparent disorder. Burn argues the novel is best understood in modernist (not postmodernist) terms — the search for order is the latent structure.
- **Appendix (Chronology of Infinite Jest)**: Reconstructed timeline of the novel's events. For Palimpsest: this is a manually constructed ground truth for the timeline reconstruction feature.

**Key Methodology**
Genealogical criticism (mapping literary influence networks), close attention to micro-stylistic features (rhythm, phonemic patterns), structural analysis (time schemes, identity), archival research at the Harry Ransom Center (Wallace's manuscript drafts).

**Conceptual Contribution**
The "post-Wallace novel" as a genre/network concept: texts are not autonomous but nodes in a communicative network, and a novelist's significance lies partly in the influence-network they generate. This validates building intertextual networks as a core Palimpsest feature. Burn also demonstrates that micro-stylistic analysis (the 79-word story) can yield poetic principles that characterize an entire body of work — the close-reading-to-distant-reading feedback loop instantiated at the single-author level.

**Development Implication for Palimpsest**
Build the intertextual influence network as a first-class feature: for any text, show what it draws from (sources, influences, allusions) and what it generates (influenced works, responses). Burn's Wallace case study provides a high-resolution manually-constructed influence graph that can serve as ground truth for algorithmic influence detection. The micro-stylistic poetics chapter suggests implementing a "rhythmic fingerprint" feature — phonemic/prosodic analysis at the sentence level, complementing semantic analysis.

---

## Cross-Cutting Synthesis for Palimpsest

**The Emergent Architecture**
Across all eight books, a consistent layered architecture emerges that should structure Palimpsest:

1. **Text layer** (Eve): Edition collation, textual variants, metadata
2. **Surface features layer** (Piper, Jockers): Punctuation, word frequency, POS, sentence structure, rhythm
3. **Semantic/vector layer** (Piper, Underwood): Vector space models, distributional semantics, topic models
4. **Structural layer** (Moretti, Carlisle): Character networks, plot topology, situation tracking
5. **Temporal/diachronic layer** (Underwood, Jockers): Change over time, genre evolution, career arcs
6. **Reader experience layer** (Toolan): Lexical patterning, HEI passage detection, coherence mapping
7. **Intertextual/network layer** (Moretti, Burn): Influence networks, allusion detection, system-level analysis

**The Critical Design Principle**
Piper's "modeling" concept is the unifying principle. Every analytical output should surface: the corpus used, the method applied, the observer's perspective encoded in the model. Underwood's "perspectival modeling" extends this: users should be able to choose the historical/critical perspective from which a genre or quality is defined. The platform is not an oracle — it is a modeling environment.

**The Primary Test Case**
*Infinite Jest* with Carlisle's annotations + Burn's influence network is the ideal test corpus. It is maximally complex (non-linear chronology, recursive structure, 32 thematic categories, dense intertextuality), has extensive ground-truth manual annotation available (Carlisle), and has a documented influence network (Burn). Every feature Palimpsest builds should be validated against this ground truth.

**The Immediate High-Value Features**
In priority order based on tractability and theoretical grounding:
1. POS-based genre fingerprinting (Eve, Ch. 2)
2. HEI passage detection via keyness + para-repetition (Toolan, Ch. 5)
3. Character network visualization (Moretti's Hamlet analysis, BookNLP)
4. Corpus comparison / style distance (Eve, Jockers)
5. LDA topic modeling with temporal tracking (Jockers, Ch. 8)
6. Perspectival modeling / multi-view classification (Underwood, Ch. 2)
7. Intertextual influence network (Burn, Moretti)
