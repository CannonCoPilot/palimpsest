# Palimpsest Annotation Model — Specification v0.1

**Date**: 2026-06-09
**Status**: Active

## 1. Overview

Palimpsest annotations follow the [W3C Web Annotation Data Model](https://www.w3.org/TR/annotation-model/) with Palimpsest-specific extensions for literary analysis. All annotations are serialized as JSONL (one JSON-LD object per line) in track files.

## 2. Annotation Structure

```json
{
  "@context": ["http://www.w3.org/ns/anno.jsonld", {"palimpsest": "https://palimpsest.dev/ns/"}],
  "type": "Annotation",
  "id": "urn:palimpsest:{project}:{track}:{hash}",
  "body": {
    "type": "palimpsest:{BodyType}",
    "purpose": "classifying|describing|linking|tagging",
    "value": "human-readable label",
    "palimpsest:lfoType": "signal.sentiment",
    "palimpsest:valence": 0.72
  },
  "target": {
    "source": "urn:palimpsest:{project}",
    "selector": {"type": "TextPositionSelector", "start": 0, "end": 100}
  },
  "creator": {"type": "Software", "name": "palimpsest-sentiment/0.1"},
  "palimpsest:confidence": 0.85,
  "palimpsest:evidenceLevel": "E4"
}
```

## 3. Body Types

| Body Type | Purpose | LFO Type | Track | Extra Properties |
|-----------|---------|----------|-------|-----------------|
| `palimpsest:EntityAnnotation` | classifying | entity.* | entities | entityType, mentionType, canonicalName |
| `palimpsest:SentimentAnnotation` | describing | signal.sentiment | sentiment | valence, arousal, model |
| `palimpsest:LexicalAnnotation` | describing | signal.lexical_density | lexical | ttr, hapaxCount, meanWordLength, yulesK |
| `palimpsest:SyntaxAnnotation` | describing | signal.syntactic_complexity | syntax | meanTreeDepth, subordinationRatio, meanSentenceLength |
| `palimpsest:DialogueAnnotation` | tagging | structural.dialogue.quote | dialogue | quoteType, speaker, verb |
| `palimpsest:TopicAnnotation` | classifying | signal.topic_assignment | topics | topicId, topicWeight, topicTerms |
| `palimpsest:CoreferenceAnnotation` | linking | entity.coreference_link | coreference | chainId, referentId, mentionType |
| `palimpsest:LitHMMAnnotation` | classifying | signal.lithmm_state | lithmm | stateId, statePosterior, stateDescription |
| `palimpsest:CompartmentAnnotation` | classifying | signal.compartment | compartments | compartment (A/B), eigenvalue |
| `palimpsest:SegmentAnnotation` | describing | structural.* | segments | segmentType, segmentIndex |
| `palimpsest:SectionAnnotation` | classifying | structure.section_boundary | sections | headingText, headingLevel, sectionIndex |
| `palimpsest:EndnoteAnnotation` | linking | structure.endnote | endnotes | noteNumber, noteText, callSiteStart, callSiteEnd |

## 4. Evidence Levels

| Level | Description | Example |
|-------|-------------|---------|
| E1 | Explicit in text or document structure | EPUB heading element, sentence boundary |
| E2 | Human annotator judgment | Manual annotation, expert correction |
| E3 | Cross-text alignment evidence | Shared passage detected via Smith-Waterman |
| E4 | ML prediction | spaCy NER, BookNLP coreference |
| E5 | Rule-based or statistical | VADER sentiment, LDA topics, LitHMM states |

## 5. Selectors

### TextPositionSelector
```json
{"type": "TextPositionSelector", "start": 0, "end": 100}
```
Character offsets into `reference.txt` (0-indexed, exclusive end). All annotation tracks use this selector type.

### TextQuoteSelector
```json
{"type": "TextQuoteSelector", "exact": "matched text", "prefix": "before", "suffix": "after"}
```
Used for human-created annotations and cross-text alignment results.

## 6. ID Format

Annotation IDs are deterministic SHA-256 hashes:
```
urn:palimpsest:{project_id}:{track_name}:{sha256(project+track+type+start+end)[:12]}
```
Same input always produces the same ID, ensuring reproducibility.

## 7. Namespacing

All Palimpsest-specific properties use the `palimpsest:` namespace prefix. The W3C context is always included first in the `@context` array. Extra properties in the body are flat key-value pairs prefixed with `palimpsest:`.
