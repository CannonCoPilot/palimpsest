"""
String Matching Module for Palimpsest
Implements dependency parsing and subject-verb-object extraction using spaCy
"""

import spacy
from typing import List, Dict, Any, Optional, Set
from collections import defaultdict
import networkx as nx
from functools import lru_cache

class SyntacticAnalyzer:
    def __init__(self, model_name: str = 'en_core_web_sm', cache_size: int = 1024):
        """
        Initialize the syntactic analyzer with a specific spaCy model.
        
        Args:
            model_name: Name of the spaCy model to use
            cache_size: Size of the LRU cache for parsed documents
        """
        self.nlp = spacy.load(model_name)
        self._cache_size = cache_size

    @lru_cache(maxsize=1024)
    def _parse_text(self, text: str) -> spacy.tokens.Doc:
        """
        Parse text using spaCy with caching.
        
        Args:
            text: Text to parse
            
        Returns:
            spacy.tokens.Doc: Parsed document
        """
        return self.nlp(text)

    def extract_dependency_relations(self, text: str) -> List[Dict[str, Any]]:
        """
        Extract dependency relations from text.
        
        Args:
            text: Input text
            
        Returns:
            List[Dict]: List of dependency relations
        """
        doc = self._parse_text(text)
        
        dependencies = []
        for token in doc:
            dependencies.append({
                'token': token.text,
                'dep': token.dep_,
                'head': token.head.text,
                'children': [child.text for child in token.children],
                'pos': token.pos_,
                'tag': token.tag_
            })
        
        return dependencies

    def extract_svo_triplets(self, text: str) -> List[Dict[str, str]]:
        """
        Extract subject-verb-object triplets from text.
        
        Args:
            text: Input text
            
        Returns:
            List[Dict]: List of SVO triplets
        """
        doc = self._parse_text(text)
        triplets = []
        
        for token in doc:
            if token.pos_ == "VERB":
                # Find subject
                subjects = [w for w in token.children 
                          if w.dep_ in ["nsubj", "nsubjpass"]]
                
                # Find objects
                objects = [w for w in token.children 
                         if w.dep_ in ["dobj", "pobj"]]
                
                # Find prepositions
                preps = [w for w in token.children if w.dep_ == "prep"]
                for prep in preps:
                    objects.extend([w for w in prep.children if w.dep_ == "pobj"])
                
                # Create triplets
                for subj in subjects:
                    for obj in objects:
                        triplets.append({
                            'subject': subj.text,
                            'verb': token.text,
                            'object': obj.text,
                            'subject_type': subj.pos_,
                            'object_type': obj.pos_
                        })
        
        return triplets

    def create_dependency_graph(self, text: str) -> nx.DiGraph:
        """
        Create a NetworkX directed graph of dependency relations.
        
        Args:
            text: Input text
            
        Returns:
            nx.DiGraph: Dependency graph
        """
        doc = self._parse_text(text)
        G = nx.DiGraph()
        
        for token in doc:
            G.add_node(token.text, pos=token.pos_, tag=token.tag_)
            G.add_edge(token.head.text, token.text, dep=token.dep_)
        
        return G

    def analyze_plot_structure(self, text: str) -> Dict[str, Any]:
        """
        Perform comprehensive plot structure analysis.
        
        Args:
            text: Input text
            
        Returns:
            Dict: Analysis results including dependencies, SVO triplets,
                 and various structural metrics
        """
        doc = self._parse_text(text)
        
        # Basic structure analysis
        sentence_count = len(list(doc.sents))
        word_count = len(doc)
        
        # Extract main components
        dependencies = self.extract_dependency_relations(text)
        svo_triplets = self.extract_svo_triplets(text)
        
        # Analyze verb chains
        verb_chains = []
        for sent in doc.sents:
            verbs = [token for token in sent if token.pos_ == "VERB"]
            if len(verbs) > 1:
                verb_chains.append([v.text for v in verbs])
        
        # Collect named entities
        entities = [{
            'text': ent.text,
            'label': ent.label_,
            'start': ent.start_char,
            'end': ent.end_char
        } for ent in doc.ents]
        
        return {
            'structure_metrics': {
                'sentence_count': sentence_count,
                'word_count': word_count,
                'avg_sentence_length': word_count / sentence_count if sentence_count > 0 else 0
            },
            'dependencies': dependencies,
            'svo_triplets': svo_triplets,
            'verb_chains': verb_chains,
            'entities': entities
        }