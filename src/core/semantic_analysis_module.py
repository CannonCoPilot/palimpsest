"""
Semantic Analysis Module for Palimpsest
Implements batch processing for semantic similarity using sentence transformers
"""

import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from typing import List, Tuple, Dict, Optional
from functools import lru_cache
import torch

class SemanticAnalyzer:
    def __init__(self, model_name: str = 'all-MiniLM-L6-v2', cache_size: int = 1024):
        """
        Initialize the semantic analyzer with a specific model and cache size.
        
        Args:
            model_name: Name of the sentence transformer model to use
            cache_size: Size of the LRU cache for embeddings
        """
        self.model = SentenceTransformer(model_name)
        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        self.model.to(self.device)

    @lru_cache(maxsize=1024)
    def _get_embedding(self, text: str) -> np.ndarray:
        """
        Get embedding for a single text with caching.
        
        Args:
            text: Input text to embed
            
        Returns:
            numpy.ndarray: Text embedding
        """
        return self.model.encode([text])[0]

    def compute_similarity(self, text1: str, text2: str) -> float:
        """
        Compute semantic similarity between two texts.
        
        Args:
            text1: First text
            text2: Second text
            
        Returns:
            float: Similarity score between 0 and 1
        """
        embedding1 = self._get_embedding(text1)
        embedding2 = self._get_embedding(text2)
        return float(np.dot(embedding1, embedding2) / 
                    (np.linalg.norm(embedding1) * np.linalg.norm(embedding2)))

    def batch_compute_similarity(self, text_pairs: List[Tuple[str, str]]) -> List[float]:
        """
        Compute similarities for multiple text pairs in batch.
        
        Args:
            text_pairs: List of (text1, text2) tuples
            
        Returns:
            List[float]: List of similarity scores
        """
        # Extract unique texts to avoid redundant encoding
        unique_texts = list(set([t for pair in text_pairs for t in pair]))
        
        # Create embedding dictionary
        embeddings = {}
        batch_size = 32
        for i in range(0, len(unique_texts), batch_size):
            batch = unique_texts[i:i + batch_size]
            batch_embeddings = self.model.encode(batch)
            embeddings.update(dict(zip(batch, batch_embeddings)))

        # Compute similarities
        similarities = []
        for text1, text2 in text_pairs:
            emb1, emb2 = embeddings[text1], embeddings[text2]
            similarity = float(np.dot(emb1, emb2) / 
                            (np.linalg.norm(emb1) * np.linalg.norm(emb2)))
            similarities.append(similarity)

        return similarities

    def find_similar_segments(self, 
                            target_text: str, 
                            corpus: List[str], 
                            threshold: float = 0.7) -> List[Dict[str, any]]:
        """
        Find semantically similar segments in a corpus.
        
        Args:
            target_text: Text to compare against
            corpus: List of texts to search through
            threshold: Minimum similarity score to consider
            
        Returns:
            List[Dict]: List of matches with similarity scores
        """
        target_embedding = self._get_embedding(target_text)
        
        # Process corpus in batches
        batch_size = 32
        matches = []
        
        for i in range(0, len(corpus), batch_size):
            batch = corpus[i:i + batch_size]
            batch_embeddings = self.model.encode(batch)
            
            # Compute similarities for the batch
            similarities = cosine_similarity([target_embedding], batch_embeddings)[0]
            
            # Filter and store matches
            for j, similarity in enumerate(similarities):
                if similarity >= threshold:
                    matches.append({
                        'text': batch[j],
                        'similarity': float(similarity),
                        'index': i + j
                    })
        
        return sorted(matches, key=lambda x: x['similarity'], reverse=True)