import spacy
from typing import List, Dict, Optional
from dataclasses import dataclass
from functools import lru_cache

@dataclass
class SyntacticPattern:
    pattern_type: str
    elements: List[str]
    frequency: int

@dataclass
class ComplexityMetrics:
    clause_depth: int
    branching_factor: float
    pattern_density: Dict[str, float]

@dataclass
class SyntacticAnalysis:
    patterns: List[SyntacticPattern]
    metrics: ComplexityMetrics
    features: Dict[str, any]

class SyntacticAnalysisModule:
    def __init__(self):
        self.nlp = spacy.load('en_core_web_sm')
        self.cache_size = 1024

    @lru_cache(maxsize=1024)
    async def analyze_syntax(self, text: str) -> SyntacticAnalysis:
        """Analyze syntactic structure of text."""
        doc = self.nlp(text)
        patterns = await self._extract_patterns(doc)
        metrics = await self._calculate_metrics(doc)
        features = await self._extract_features(doc)
        
        return SyntacticAnalysis(
            patterns=patterns,
            metrics=metrics,
            features=features
        )

    async def _extract_grammatical_constructions(self, doc) -> Dict[str, int]:
        """Extract counts of specific grammatical constructions."""
        constructions = {
            'passive_voice': 0,
            'subjunctive_mood': 0,
            'conditional_clauses': 0 # Example, needs specific logic
        }
        for token in doc:
            # Basic passive voice check (auxpass + verb)
            if token.dep_ == 'auxpass' and token.head.pos_ == 'VERB':
                constructions['passive_voice'] += 1
            # Basic subjunctive check (e.g., 'if I were') - needs refinement
            if token.tag_ == 'VBD' and token.lemma_ == 'be' and token.text == 'were':
                 # Check context for subjunctive indicators like 'if'
                 if token.head.dep_ == 'ROOT' and any(c.lemma_ == 'if' for c in token.head.children if c.dep_ == 'mark'):
                     constructions['subjunctive_mood'] += 1

        # Add logic for conditional clauses if needed

        return constructions


    async def _extract_patterns(self, doc) -> List[SyntacticPattern]:
        """Extract syntactic patterns from doc."""
        patterns = []
        # Extract dependency patterns
        dep_patterns = {}
        for token in doc:
            # More specific pattern key: DependentPOS_Relation_HeadPOS
            pattern = f"{token.pos_}_{token.dep_}_{token.head.pos_}"
            if pattern in dep_patterns:
                dep_patterns[pattern]['frequency'] += 1
                dep_patterns[pattern]['elements'].append(token.text)
            else:
                dep_patterns[pattern] = {
                    'frequency': 1,
                    'elements': [token.text]
                }
        
        # Convert to SyntacticPattern objects
        for pattern_type, data in dep_patterns.items():
            patterns.append(SyntacticPattern(
                pattern_type=pattern_type,
                elements=data['elements'],
                frequency=data['frequency']
            ))
        
        return patterns

    async def _calculate_metrics(self, doc) -> ComplexityMetrics:
        """Calculate complexity metrics."""
        # Calculate clause depth
        clause_depths = [len(list(token.ancestors)) 
                      for token in doc 
                      if token.dep_ == 'ROOT']
        avg_clause_depth = sum(clause_depths) / len(clause_depths) if clause_depths else 0
        
        # Calculate branching factor
        branch_counts = [len(list(token.children)) for token in doc]
        avg_branching = sum(branch_counts) / len(branch_counts) if branch_counts else 0
        
        # Calculate pattern density
        total_tokens = len(doc)
        pattern_counts = {}
        for token in doc:
            if token.dep_ in pattern_counts:
                pattern_counts[token.dep_] += 1
            else:
                pattern_counts[token.dep_] = 1
        
        pattern_density = {pattern: count/total_tokens 
                          for pattern, count in pattern_counts.items()}
        
        return ComplexityMetrics(
            clause_depth=int(avg_clause_depth),
            branching_factor=float(avg_branching),
            pattern_density=pattern_density
        )

    async def _extract_features(self, doc) -> Dict:
        """Extract syntactic features."""
        return {
            'sentence_count': len(list(doc.sents)),
            'noun_phrases': [chunk.text for chunk in doc.noun_chunks],
            'verb_phrases': [token.text for token in doc if token.pos_ == 'VERB'],
            'dependency_types': list(set(token.dep_ for token in doc))
,
            'grammatical_constructions': await self._extract_grammatical_constructions(doc)
        }

    async def extract_patterns(self, text: str) -> List[SyntacticPattern]:
        """Extract syntactic patterns from text."""
        doc = self.nlp(text)
        return await self._extract_patterns(doc)

    async def get_complexity_metrics(self, text: str) -> ComplexityMetrics:
        """Get complexity metrics for text."""
        doc = self.nlp(text)
        return await self._calculate_metrics(doc)


    async def compare_syntax(self, analysis1: SyntacticAnalysis, analysis2: SyntacticAnalysis) -> Dict[str, float]:
        """Compare the syntactic analyses of two texts."""
        similarity_scores = {}

        # 1. Compare Syntactic Patterns (e.g., Jaccard similarity on pattern types)
        patterns1 = {p.pattern_type for p in analysis1.patterns}
        patterns2 = {p.pattern_type for p in analysis2.patterns}
        intersection = patterns1.intersection(patterns2)
        union = patterns1.union(patterns2)
        similarity_scores['pattern_jaccard'] = len(intersection) / len(union) if union else 1.0

        # 2. Compare Complexity Metrics (e.g., normalized difference)
        metrics1 = analysis1.metrics
        metrics2 = analysis2.metrics
        # Avoid division by zero; add epsilon or handle cases where max is 0
        epsilon = 1e-6
        max_depth = max(metrics1.clause_depth, metrics2.clause_depth, epsilon)
        similarity_scores['depth_similarity'] = 1.0 - abs(metrics1.clause_depth - metrics2.clause_depth) / max_depth

        max_branching = max(metrics1.branching_factor, metrics2.branching_factor, epsilon)
        similarity_scores['branching_similarity'] = 1.0 - abs(metrics1.branching_factor - metrics2.branching_factor) / max_branching

        # Compare pattern density (more complex - requires aligning dictionaries)
        # For simplicity, calculate cosine similarity of density vectors
        all_pattern_keys = set(metrics1.pattern_density.keys()) | set(metrics2.pattern_density.keys())
        vec1 = [metrics1.pattern_density.get(k, 0) for k in all_pattern_keys]
        vec2 = [metrics2.pattern_density.get(k, 0) for k in all_pattern_keys]
        if sum(v*v for v in vec1) > 0 and sum(v*v for v in vec2) > 0:
             dot_product = sum(v1 * v2 for v1, v2 in zip(vec1, vec2))
             norm1 = sum(v*v for v in vec1) ** 0.5
             norm2 = sum(v*v for v in vec2) ** 0.5
             similarity_scores['density_cosine_similarity'] = dot_product / (norm1 * norm2)
        else:
             similarity_scores['density_cosine_similarity'] = 1.0 if vec1 == vec2 else 0.0 # Handle zero vectors

        # 3. Compare Extracted Features (e.g., Jaccard on noun phrases, verb phrases)
        features1 = analysis1.features
        features2 = analysis2.features

        np1 = set(features1.get('noun_phrases', []))
        np2 = set(features2.get('noun_phrases', []))
        np_union = np1.union(np2)
        similarity_scores['noun_phrase_jaccard'] = len(np1.intersection(np2)) / len(np_union) if np_union else 1.0

        vp1 = set(features1.get('verb_phrases', []))
        vp2 = set(features2.get('verb_phrases', []))
        vp_union = vp1.union(vp2)
        similarity_scores['verb_phrase_jaccard'] = len(vp1.intersection(vp2)) / len(vp_union) if vp_union else 1.0

        # 4. Calculate Overall Score (simple average for now)
        valid_scores = [s for s in similarity_scores.values() if isinstance(s, (int, float))]
        similarity_scores['overall_syntactic_similarity'] = sum(valid_scores) / len(valid_scores) if valid_scores else 0.0

        return similarity_scores

        """Compare the syntactic analyses of two texts."""
        similarity_scores = {}

        # 1. Compare Syntactic Patterns (e.g., Jaccard similarity on pattern types)
        patterns1 = {p.pattern_type for p in analysis1.patterns}
        patterns2 = {p.pattern_type for p in analysis2.patterns}
        intersection = patterns1.intersection(patterns2)
        union = patterns1.union(patterns2)
        similarity_scores['pattern_jaccard'] = len(intersection) / len(union) if union else 1.0

        # 2. Compare Complexity Metrics (e.g., normalized difference)
        metrics1 = analysis1.metrics
        metrics2 = analysis2.metrics
        # Avoid division by zero; add epsilon or handle cases where max is 0
        epsilon = 1e-6
        max_depth = max(metrics1.clause_depth, metrics2.clause_depth, epsilon)
        similarity_scores['depth_similarity'] = 1.0 - abs(metrics1.clause_depth - metrics2.clause_depth) / max_depth

        max_branching = max(metrics1.branching_factor, metrics2.branching_factor, epsilon)
        similarity_scores['branching_similarity'] = 1.0 - abs(metrics1.branching_factor - metrics2.branching_factor) / max_branching

        # Compare pattern density (more complex - requires aligning dictionaries)
        # For simplicity, calculate cosine similarity of density vectors
        all_pattern_keys = set(metrics1.pattern_density.keys()) | set(metrics2.pattern_density.keys())
        vec1 = [metrics1.pattern_density.get(k, 0) for k in all_pattern_keys]
        vec2 = [metrics2.pattern_density.get(k, 0) for k in all_pattern_keys]
        if sum(v*v for v in vec1) > 0 and sum(v*v for v in vec2) > 0:
             dot_product = sum(v1 * v2 for v1, v2 in zip(vec1, vec2))
             norm1 = sum(v*v for v in vec1) ** 0.5
             norm2 = sum(v*v for v in vec2) ** 0.5
             similarity_scores['density_cosine_similarity'] = dot_product / (norm1 * norm2)
        else:
             similarity_scores['density_cosine_similarity'] = 1.0 if vec1 == vec2 else 0.0 # Handle zero vectors

        # 3. Compare Extracted Features (e.g., Jaccard on noun phrases, verb phrases)
        features1 = analysis1.features
        features2 = analysis2.features

        np1 = set(features1.get('noun_phrases', []))
        np2 = set(features2.get('noun_phrases', []))
        np_union = np1.union(np2)
        similarity_scores['noun_phrase_jaccard'] = len(np1.intersection(np2)) / len(np_union) if np_union else 1.0

        vp1 = set(features1.get('verb_phrases', []))
        vp2 = set(features2.get('verb_phrases', []))
        vp_union = vp1.union(vp2)
        similarity_scores['verb_phrase_jaccard'] = len(vp1.intersection(vp2)) / len(vp_union) if vp_union else 1.0

        # 4. Calculate Overall Score (simple average for now)
        valid_scores = [s for s in similarity_scores.values() if isinstance(s, (int, float))]
        similarity_scores['overall_syntactic_similarity'] = sum(valid_scores) / len(valid_scores) if valid_scores else 0.0

        return similarity_scores

        """Get complexity metrics for text."""
        doc = self.nlp(text)
        return await self._calculate_metrics(doc)
