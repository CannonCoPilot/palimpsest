# OriginalDR OCR Masterplan — Executive Summary

**Read this first. Three pages. It states what changed, what it costs, and the six things I need from you.**

Companion documents: `OCR-OVERVIEW.md` (the architecture) · `OCR-WALKTHROUGH.md` (how it works, page by
page) · `OCR-MASTERPLAN-V3.md` (the plan itself, revision 3) · critique records R1 and R2.

---

## 1. The one sentence

**The plan was paying for two different products, and this revision picks one:** a faithful documentary
transcript of the 1582 New Testament and the 1609/1610 Old Testament, in archaic typeset and archaic
spelling — **not** six publication-quality OCR transcripts feeding a six-witness collated critical edition.

## 2. How that conclusion was reached

You asked for a deep rethink, then antagonistic specialists, then revision, then a **second** round of
subject-matter experts, then revision again. That is what happened, with one accident that turned out to be
the most useful thing in the process.

- **Round 1** — five critics against revision 1. Seven findings, all epistemic: the plan could not be
  falsified. Rebuilt into revision 2.
- **Round 2** — four critics against revision 2. **A context refresh mid-round caused me to re-launch them,
  believing the results lost. They were not lost. Both panels returned.**

**So every remit was critiqued twice, blind.** That gives a within-remit control I did not design and could
not have justified paying for: where two specialists on the same remit converge, the finding is
*replicated*; where they diverge, the uncertainty is *real* and belongs to you, not to me.

**Twenty-three findings replicated across both panels.** Four questions came back split. I decided all four
and flagged each — see §5.

## 3. What the two panels found, in the order that matters

**The structural finding — reached independently by a program lead costing the plan and a scholarly editor
reading its constitution.** Revision 2 adopted copy-text discipline, under which **five of the six sources
may never alter a spelling or a glyph**. It then required all six to reach publication quality and sized
everything accordingly. Those two commitments belong to different projects. The second one — the critical
edition — is legitimate and is *not what you asked for*.

**Cutting to one product deletes**: six-way collation and the variant graph · calibrated ensembles ·
witness weighting · the entire write-back drift guard · five-sixths of the diplomatic ground truth · the
model hierarchy below fount level.

**The three findings that would have cost the most had they survived:**

1. **The ground-truth stage was unbudgeted and unstartable.** Independently costed at **155–275 h** and
   **210–280 h** — call it ~200–280 operator-hours, stated nowhere in the plan, gating ten of twelve build
   steps. At a realistic 12 productive hrs/week that is **17–23 weeks before any product work begins.**
   Both red teams named the failure precisely: *this is not over-ambition, it is unstartability — the
   original status-quo failure mode reached by a longer route.* And the plan claimed to honour your
   instruction about human-review bottlenecks "at the production path" while **making the whole build order
   depend on the review path, which is the same bottleneck one level up.**

2. **Several gates could not fail.** Nine or ten of twelve lacked a threshold, an n, or both. **δ — used in
   three places as *the* convergence criterion — was never given a value anywhere in the document.** One
   gate required **≥200 instances of glyph classes the same plan says occur "tens of times corpus-wide"** —
   unmeetable, with an escape clause that quietly converted it into automatic satisfaction at n=30. That is
   exactly the below-threshold-accepted-as-terminal pattern the project forbids, and I had written it in
   while removing the same pattern elsewhere.

3. **The ligature and long-ſ machinery would not have worked.** Both HTR engineers dismantled it
   independently: connected components fail because **at 650 ppi a printed line is largely one connected
   component**; advance width is **the true discriminant and unmeasurable** (you can measure ink extent, not
   body width, and the difference is swamped by ink spread); and forced-aligning to `ﬁ` **requires `ﬁ`
   already in the codec — the same circularity I had just removed, relocated.** They also showed my
   Unicode-decomposition fix was backwards: **the macron sits above the bowl, not after it, so under CTC's
   monotonic alignment a decomposed `õ` is strictly *harder* than an atomic one.**

**What replaces it is better and cheaper**, and one idea is genuinely strong: **letterpress repeats the same
physical sort**, so instead of classifying `ſ` instance by instance, cluster the candidate crops per fount,
key ~50 cluster exemplars, and propagate. And the pair classifiers now emit **`A` / `B` / *indeterminate***,
abstaining into `<unclear>` — *an 8% abstention rate on `ſ`/`f` is an honest edition; a 0% one is a
fabricated one.*

## 4. What this now costs, and when you see something

**The honest total: 400–1,000 hours of human correction** (~3,000–4,500 pages at 6–15 min/page). That is the
price of this product **under any architecture**. The simplification does not remove those hours — it means
**they produce the deliverable directly instead of producing the instrument that produces it.**

The load-bearing insight, from the second program lead: **gold-keying and production transcription are the
same keystrokes.** One correction UI, five outputs — shippable transcript pages, evaluation text, training
ground truth, layout ground truth, and glyph instances. That is the only way ~250 annotation hours becomes
affordable.

| when | what ships |
|---|---|
| **week 1** | drop-cap board fix (**18 cells**); page axis; source concordance; scan inspection |
| **week 2** | **residue detector** — a ranked defect queue for the existing chapter workflow, no gold set, no new model, using the incumbent pipeline *as a detector rather than a generator* so its bias does not propagate |
| **week 3+** | **corrected transcript pages, continuously**, starting in a zero-archaic-witness book |
| later | frozen evaluation sets, G1 geometry and recognition, the census, the edition |

**Nothing in the first quarter waits on the ground-truth stage.** Only metric *claims* do — never
improvements. Conflating those two is what made the previous revision four months of unshipped
infrastructure.

## 5. Six things I need from you

**Four are decisions I already made** because the specialists split and you have told me to decide and
proceed rather than block. Each is reversible in a paragraph, and each is flagged **[SIR'S CALL]** in the
plan at the point of use.

| # | question | my decision | the losing argument |
|---|---|---|---|
| **1** | copy-text framing, or documentary? | **Documentary/diplomatic** (TEI P5 ch. 11). Copy-text survives only as the mechanism for choosing *which physical copy* we transcribe. | Keeping copy-text language preserves continuity with round 1 and a large body of practice. **I judged that the word drags the whole critical-edition apparatus in behind it — which is exactly what happened once already.** |
| **2** | model scope above SOURCE | **FOUNT**, not TOME. Roman text vs italic annotation vs display are where letterforms *actually* differ; tome is just a proxy for scan conditions, which SOURCE already captures. | Simply cutting TOME. Both agreed TOME-as-written was wrong. |
| **3** | what to build first | **Both, composed**: the residue detector *orders the pages*, the correction UI *transcribes them*. | Either alone. |
| **4** | `ꝛ`, and the Latin `ꝑ ꝓ ꝗ` | **Neither in nor out — inspect the scans.** One editor called them anachronistic; the other pointed out that **removing `ꝛ` while admitting blackletter headings is self-contradictory**, and that brevigraphs do appear in the Latin of the Rheims annotations. | — **This became a task rather than a judgement, and it closes a third question at the same time: whether Fogny and Kellam set any blackletter at all.** |

**Two are genuinely yours, and I have not pre-empted them:**

5. **§10.4 — what is actually in the transcript.** Original line breaks, hyphenation, catchwords, running
   heads, chapter arguments, the marginal annotations, the 1582 preface. **The scholarly review found no
   policy on any of this anywhere in the plan and called these the largest unstated scoping decisions in
   the project.** I have proposed defaults for all ten classes. **Every one is cheap to change now and
   expensive to change later.** One note: **in the Douay-Rheims the apparatus is half the book, and a
   transcript that drops the marks keying annotation to text is unusable** — so I have included them.

6. **Where the planning documents live.** This plan and both critique records sit in a **gitignored scratch
   directory**. They are the most valuable output of the last two sessions and are one `rm` from gone.
   Moving them under version control is five minutes. **It is your call where the project keeps its
   planning documents, so I have not moved them unilaterally.**

## 6. Three things I got wrong, recorded so the pattern is visible

You identified the pattern before round 1 did: **each time a measurement came back ambiguous, I converted it
into a reason to keep the status quo.** Native resolution "no free win"; the 120 px input height "a
training-time choice"; the coarse metric "the limit of what can be measured"; the sources "good enough to
vote." **Status-quo preservation dressed as empiricism.** You were right on every count.

Round 2 caught the over-correction: revision 2 answered a critical-edition reviewer by **adopting a critical
edition**, and answered a measurement reviewer by **building a measurement regime that could not be
started**. And the retracted numbers stay retracted — `s_dismas` and `odr_com` are **~0.9879 mean similarity,
median 1.0000, 79% character-identical**; you were right that they are essentially the same text, and my
"94% differ" figures were verse-key artefacts. **That corrected number is itself flawed** (a maximum over 11
candidate alignments, on the easy subset, folding the very glyphs the product exists to preserve), and §2.1
now fixes the reporting standard so the next such number cannot be produced the same way.

**One measurement that stands and blocks work**: **8.0% of verses best-match at a non-zero verse offset.**
`ref_renumber` is incomplete, and **every verse-keyed comparison of the two archaic references is invalid
until it is finished.**

---

**Recommended next action**: confirm or overturn the four decisions in §5, set the scope table in §10.4, and
I start step 0 — the source concordance, the scan inspection, and the drop-cap fix — immediately.
