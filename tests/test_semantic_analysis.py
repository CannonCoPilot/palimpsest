# palimpsest/tests/test_semantic_analysis.py
import unittest
import sys
import os
import numpy as np
from typing import List, Dict, Any

# Add the parent directory to the path so we can import the modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.core.semantic_analysis_module import SemanticAnalyzer # Correct class name

class TestSemanticAnalyzer(unittest.TestCase): # Rename test class
    def setUp(self):
        """Set up test fixtures."""
        # Update instantiation based on the actual class
        # The original class takes model_name and cache_size
        self.analyzer = SemanticAnalyzer(
            model_name='all-MiniLM-L6-v2', # Use a real model name or mock appropriately
            cache_size=128 # Use a smaller cache for testing
        )
        # Note: The original test setup used dummy parameters (embedding_dim, use_pretrained)
        # which don't match the actual SemanticAnalyzer.__init__.
        # The tests themselves might need further adjustment if they relied on those dummy params.
        
        # Sample texts for testing
        self.text1 = "The quick brown fox jumps over the lazy dog."
        self.text2 = "A rapid auburn fox leaps over the idle canine."  # Semantically similar to text1
        self.text3 = "Neural networks have revolutionized machine learning and artificial intelligence."

    def test_initialization(self):
        """Test proper initialization of SemanticAnalyzer."""
        # Check that the model attribute is loaded (it's loaded in __init__)
        self.assertIsNotNone(self.analyzer.model)
        # Add other relevant checks if needed, e.g., device setting
        self.assertTrue(hasattr(self.analyzer, 'device'))

    # def test_load_models(self):
    #     """Test model loading."""
    #     # This test might be invalid as the actual class loads the model in __init__
    #     # result = self.analyzer.load_models()
    #     # self.assertTrue(result)
    #     # self.assertIn("embedding", self.analyzer.models) # analyzer doesn't have 'models' attribute
    #     # self.assertIn("topic", self.analyzer.models)
    #     pass

    def test_get_embedding(self):
        """Test text embedding computation using _get_embedding."""
        # Test that embeddings are numpy arrays
        embedding = self.analyzer._get_embedding(self.text1)
        self.assertIsInstance(embedding, np.ndarray)
        # Dimension depends on the loaded model ('all-MiniLM-L6-v2' is 384)
        self.assertEqual(embedding.shape, (384,))

        # Test caching: same text should return identical embedding object
        embedding2 = self.analyzer._get_embedding(self.text1)
        self.assertIs(embedding, embedding2) # Check object identity due to cache

        # Different text should give different embedding
        embedding3 = self.analyzer._get_embedding(self.text2)
        self.assertFalse(np.array_equal(embedding, embedding3))


    def test_compute_similarity(self):
        """Test computation of semantic similarity between texts."""
        # Compute similarities using the actual method
        sim_1_2 = self.analyzer.compute_similarity(self.text1, self.text2)
        sim_1_3 = self.analyzer.compute_similarity(self.text1, self.text3)
        sim_1_1 = self.analyzer.compute_similarity(self.text1, self.text1)

        # Check basic properties of similarity measures
        self.assertGreaterEqual(sim_1_2, 0.0)
        self.assertLessEqual(sim_1_2, 1.0)

        # Identical texts should have maximum similarity
        self.assertAlmostEqual(sim_1_1, 1.0, places=5) # Use almostEqual for float comparison

        # Semantically similar texts (text1, text2) should have higher similarity than different ones (text1, text3)
        self.assertGreater(sim_1_2, sim_1_3)


    # def test_extract_topics(self):
    #     """Test topic extraction from texts."""
    #     # This method doesn't exist on SemanticAnalyzer
    #     # texts = [self.text1, self.text2, self.text3]
    #     # num_topics = 3
    #     # topics = self.analyzer.extract_topics(texts, num_topics)
    #     # self.assertEqual(len(topics), num_topics)
    #     # for topic_id, keywords in topics.items():
    #     #     self.assertIsInstance(keywords, list)
    #     #     self.assertTrue(all(isinstance(kw, str) for kw in keywords))
    #     #     self.assertEqual(len(keywords), 5)
    #     pass

    def test_find_similar_segments(self):
        """Test finding semantic connections using find_similar_segments."""
        corpus = [self.text2, self.text3, self.text1] # Include text1 in corpus
        connections = self.analyzer.find_similar_segments(
            target_text=self.text1, corpus=corpus, threshold=0.5 # Use a reasonable threshold
        )

        # Should find at least text1 itself and potentially text2
        self.assertGreaterEqual(len(connections), 1)

        # Check connection structure
        found_self = False
        for conn in connections:
            self.assertIn("text", conn)
            self.assertIn("similarity", conn)
            self.assertIn("index", conn)
            self.assertIsInstance(conn["similarity"], float)
            self.assertGreaterEqual(conn["similarity"], 0.5) # Should meet threshold
            if conn["text"] == self.text1:
                found_self = True
                self.assertAlmostEqual(conn["similarity"], 1.0, places=5)

        self.assertTrue(found_self, "Did not find the target text itself in similar segments")

        # Test with high threshold
        high_threshold_connections = self.analyzer.find_similar_segments(
            target_text=self.text1, corpus=corpus, threshold=0.99
        )
        # Should only find text1 itself
        self.assertEqual(len(high_threshold_connections), 1)
        self.assertEqual(high_threshold_connections[0]['text'], self.text1)


    # def test_analyze_conceptual_overlap(self):
    #     """Test conceptual overlap analysis."""
    #     # This method doesn't exist on SemanticAnalyzer
    #     # overlap = self.analyzer.analyze_conceptual_overlap(self.text1, self.text2)
    #     # self.assertIn("overall_similarity", overlap)
    #     # self.assertIn("shared_concepts", overlap)
    #     # self.assertIn("conceptual_overlap_score", overlap)
    #     # self.assertGreaterEqual(overlap["overall_similarity"], 0.0)
    #     # self.assertLessEqual(overlap["overall_similarity"], 1.0)
    #     # self.assertGreaterEqual(overlap["conceptual_overlap_score"], 0.0)
    #     # self.assertLessEqual(overlap["conceptual_overlap_score"], 1.0)
    #     # self.assertIsInstance(overlap["shared_concepts"], list)
    #     # if overlap["overall_similarity"] > 0.5:
    #     #     self.assertGreater(len(overlap["shared_concepts"]), 0)
    #     pass

if __name__ == '__main__':
    unittest.main()