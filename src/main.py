# palimpsest/src/main.py
"""
Main entry point for the Palimpsest application.

This module integrates the various analysis components and provides
interfaces for text analysis and comparison workflows.
"""

import os
import sys
import logging
import http.server
import socketserver
from typing import List, Dict, Any, Optional
import argparse
from flask import Flask, request, jsonify, send_from_directory
import tempfile
import os
import time
import shutil
from threading import Timer
from core.string_matching_analysis import StringMatchingAnalysis
from core.string_matching_visualization import StringMatchingVisualization

# Add the project root directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import Palimpsest modules
# from src.core.string_matching_module import StringMatchingModule # Old import
from src.core.string_matching_analysis import StringMatchingAnalysis # New import
from src.core.semantic_analysis_module import SemanticAnalyzer # Correct class name

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('palimpsest.log')
    ]
)
logger = logging.getLogger(__name__)

# Application configuration
APP_CONFIG = {
    'ANALYSIS_DIR': os.path.join(tempfile.gettempdir(), 'palimpsest_analysis'),
    'VISUALIZATION_DIR': os.path.join(tempfile.gettempdir(), 'palimpsest_visualizations'),
    'MAX_CONTENT_LENGTH': 16 * 1024 * 1024,  # 16MB max file size
    'ALLOWED_EXTENSIONS': {'txt'},
    'DEFAULT_FUZZY_ALGORITHM': 'levenshtein'
}

# Ensure analysis directories exist
os.makedirs(APP_CONFIG['ANALYSIS_DIR'], exist_ok=True)
os.makedirs(APP_CONFIG['VISUALIZATION_DIR'], exist_ok=True)

in_memory_docs: Dict[str, Dict[str, str]] = {}
"""
Example structure:
{
  "doc_id": {
      "name": "Document Name",
      "content": "Document text..."
  }
}
"""

class PalimpsestAnalyzer:
    """
    Main class for the Palimpsest text analysis system.
    
    Integrates string matching and semantic analysis to find connections
    between texts at multiple levels.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the Palimpsest analyzer with configuration.
        
        Args:
            config: Configuration dictionary for analyzer modules
        """
        self.config = config or {}
        logger.info("Initializing Palimpsest Analyzer")
        
        # Initialize analysis modules
        # Instantiate the new analysis class. It expects text_files list.
        # Pass empty list for now, assuming main analysis flow might change.
        self.string_matcher = StringMatchingAnalysis(text_files=[])
        self.semantic_analyzer = SemanticAnalyzer() # Correct class name
        
        logger.info("Palimpsest Analyzer initialized successfully")
    
    def load_text(self, file_path: str) -> str:
        """
        Load text from a file.
        
        Args:
            file_path: Path to the text file
            
        Returns:
            The text content as a string
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                text = file.read()
            logger.info(f"Loaded text from {file_path}, length: {len(text)} characters")
            return text
        except Exception as e:
            logger.error(f"Error loading text from {file_path}: {e}")
            raise
    
    def analyze_texts(self, source_text: str, target_texts: List[str]) -> Dict[str, Any]:
        """
        Analyze relationships between a source text and multiple target texts.
        
        Args:
            source_text: Main text to analyze
            target_texts: List of texts to compare against
            
        Returns:
            Dictionary of analysis results
        """
        results = {
            "string_matches": [],
            "semantic_connections": [],
            "combined_score": 0.0
        }
        
        # Perform string matching analysis
        # TODO: Integrate the new StringMatchingAnalysis workflow.
        # The new class has a run_analysis method which takes file paths
        # and handles the full pipeline internally, saving results to files.
        # This differs from the semantic analyzer's approach here.
        # For now, string matching results are not integrated into this function's output.
        # Example (needs file paths):
        # string_analyzer = StringMatchingAnalysis(text_files=[args.source] + args.targets)
        # string_analyzer.run_analysis(output_dir="analysis_results/string_matching")
        # results["string_matches"] = string_analyzer.load_results_somehow() # Need method to load results
        
        # Perform semantic analysis
        # Call the correct method name: find_similar_segments
        # Note: find_similar_segments compares one target against a list (corpus)
        # The original code structure here might need rethinking if comparing source to multiple targets individually.
        # TODO: Adjust logic if source needs to be compared against each target separately.
        semantic_connections = []
        if target_texts:
            # Ensure target_texts is a list of strings
            if isinstance(target_texts, list) and all(isinstance(t, str) for t in target_texts):
                 semantic_connections = self.semantic_analyzer.find_similar_segments(
                     target_text=source_text, corpus=target_texts, threshold=0.5)
            else:
                 logger.warning("Target texts format is not a list of strings, skipping semantic analysis.")

        
        results["semantic_connections"] = semantic_connections
        
        # Compute a combined relevance score
        if semantic_connections:
            results["combined_score"] = sum(c["similarity"] for c in semantic_connections) / len(semantic_connections)
        
        logger.info(f"Analysis complete. Found {len(semantic_connections)} semantic connections")
        return results
    
    def generate_report(self, analysis_results: Dict[str, Any], output_path: str = "report.txt") -> None:
        """
        Generate a text report from analysis results.
        
        Args:
            analysis_results: Results from analyze_texts
            output_path: Path to save the report
        """
        try:
            with open(output_path, 'w', encoding='utf-8') as file:
                file.write("PALIMPSEST ANALYSIS REPORT\n")
                file.write("========================\n\n")
                
                file.write(f"Combined relevance score: {analysis_results['combined_score']:.4f}\n\n")
                
                file.write("SEMANTIC CONNECTIONS\n")
                file.write("-------------------\n")
                for i, conn in enumerate(analysis_results['semantic_connections']):
                    file.write(f"Connection {i+1}:\n")
                    file.write(f"  Similarity: {conn['similarity']:.4f}\n")
                    # Adjust key based on find_similar_segments output ('text' instead of 'text_preview')
                    file.write(f"  Text: {conn['text']}\n\n")
            
            logger.info(f"Report generated and saved to {output_path}")
        except Exception as e:
            logger.error(f"Error generating report: {e}")
            raise

def main():
    """Main function to run the Palimpsest application."""
    parser = argparse.ArgumentParser(description="Palimpsest Text Analysis Tool")
    parser.add_argument("source", nargs='?', default=None, help="Path to source text file (CLI mode)")
    parser.add_argument("targets", nargs='*', default=None, help="Paths to target text files (CLI mode)")
    parser.add_argument("--output", "-o", default="palimpsest_report.txt",
                        help="Output report file path (CLI mode only)")
    parser.add_argument("--mode", choices=['cli', 'ui'], default='cli',
                        help="Run mode: 'cli' for command-line analysis, 'ui' to launch the web UI")
    parser.add_argument("--port", type=int, default=8000,
                        help="Port for the UI web server (UI mode only)")
    
    args = parser.parse_args()
    
    if args.mode == 'cli':
        try:
            analyzer = PalimpsestAnalyzer()

            # Load texts
            logger.info(f"Loading source text: {args.source}")
            source_text = analyzer.load_text(args.source)
            logger.info(f"Loading {len(args.targets)} target text(s)...")
            target_texts = [analyzer.load_text(target) for target in args.targets]

            # Perform analysis
            logger.info("Starting analysis...")
            results = analyzer.analyze_texts(source_text, target_texts)

            # Generate report
            logger.info("Generating report...")
            analyzer.generate_report(results, args.output)

            print(f"CLI analysis complete. Report saved to {args.output}")
            return 0

        except Exception as e:
            logger.error(f"Error in Palimpsest CLI analysis: {e}", exc_info=True)
            print(f"Error: {e}")
            return 1
    elif args.mode == 'ui':
        app = Flask(__name__)
        PORT = args.port

        # Set up static file serving
        script_dir = os.path.dirname(__file__)
        ui_dir = os.path.abspath(os.path.join(script_dir, '..', 'ui'))
        app.static_folder = ui_dir
        app.static_url_path = ''

        if not os.path.isdir(ui_dir):
            print(f"Error: UI directory not found at {ui_dir}")
            logger.error(f"UI directory not found at {ui_dir}")
            return 1

        # Initialize directories
        os.makedirs(APP_CONFIG['ANALYSIS_DIR'], exist_ok=True)
        os.makedirs(APP_CONFIG['VISUALIZATION_DIR'], exist_ok=True)

        @app.route('/')
        def serve_index():
            return send_from_directory(ui_dir, 'index.html')

        @app.route('/api/upload', methods=['POST'])
        def upload_document():
            """
            Upload a single doc, store in memory.
            Expects JSON: { "doc_id": "someID", "name": "Name", "content": "Raw text" }
            """
            data = request.json
            if not data or 'doc_id' not in data or 'content' not in data:
                return jsonify({"error": "Invalid upload request"}), 400

            doc_id = data['doc_id']
            doc_name = data.get('name', f"Document {doc_id}")
            doc_content = data['content']

            in_memory_docs[doc_id] = {
                "name": doc_name,
                "content": doc_content
            }
            logger.info(f"Uploaded document [{doc_id}] - len={len(doc_content)}")
            return jsonify({"status": "OK", "doc_id": doc_id}), 200

        @app.route('/api/gutenberg', methods=['GET'])
        def fetch_gutenberg():
            """
            Placeholder for final Gutenberg fetch API.
            Accepts ?book_id=NNN
            """
            book_id = request.args.get('book_id', None)
            if not book_id:
                return jsonify({"error": "Missing 'book_id' parameter"}), 400

            # For now, just pretend we loaded from disk or an API
            doc_content = f"Fetched text for Gutenberg ID {book_id}...\nThe End."
            doc_id = f"gutenberg_{book_id}"
            in_memory_docs[doc_id] = {
                "name": f"Gutenberg {book_id}",
                "content": doc_content
            }
            logger.info(f"Gutenberg doc loaded: {doc_id}")
            return jsonify({
                "status": "OK",
                "doc_id": doc_id,
                "name": f"Gutenberg {book_id}",
                "content": doc_content
            }), 200

        @app.route('/api/analyze', methods=['POST'])
        def analyze_api():
            """Run analysis on selected documents."""
            try:
                # Validate request
                data = request.json
                if not data or 'document_ids' not in data or 'modules' not in data:
                    return jsonify({"error": "Invalid request format"}), 400

                doc_ids = data['document_ids']
                modules = data['modules']

                # Load document contents
                docs_loaded = []
                for d_id in doc_ids:
                    doc_obj = in_memory_docs.get(d_id)
                    if not doc_obj:
                        return jsonify({"error": f"Document ID not found: {d_id}"}), 404
                    docs_loaded.append(doc_obj['content'])

                if not docs_loaded:
                    return jsonify({"error": "No documents provided for analysis"}), 400

                results = {"status": "OK", "analysisResults": {}}

                # Handle string matching analysis
                if "string" in modules:
                    try:
                        analysis_id = f"analysis_{int(time.time())}"
                        analysis_dir = os.path.join(APP_CONFIG['ANALYSIS_DIR'], analysis_id)
                        vis_dir = os.path.join(APP_CONFIG['VISUALIZATION_DIR'], analysis_id)
                        os.makedirs(analysis_dir, exist_ok=True)
                        os.makedirs(vis_dir, exist_ok=True)

                        # Write documents to analysis directory
                        temp_files = []
                        for idx, content in enumerate(docs_loaded):
                            temp_path = os.path.join(analysis_dir, f"doc_{idx}.txt")
                            with open(temp_path, 'w', encoding='utf-8') as f:
                                f.write(content)
                            temp_files.append(temp_path)

                        logger.info(f"Running string matching analysis on {len(temp_files)} documents")
                        
                        # Run analysis
                        sm_analysis = StringMatchingAnalysis(text_files=temp_files)
                        sm_analysis.run_analysis(
                            fuzzy_algorithm=APP_CONFIG['DEFAULT_FUZZY_ALGORITHM'],
                            output_dir=analysis_dir
                        )

                        # Generate visualizations
                        sm_visual = StringMatchingVisualization(results_dir=analysis_dir)
                        sm_visual.generate_visualizations(output_dir=vis_dir)

                        # Read preliminary match scores
                        import pandas as pd
                        prelim_path = os.path.join(analysis_dir, "preliminary_match_scores.csv")
                        preliminary_scores = None
                        if os.path.exists(prelim_path):
                            preliminary_scores = pd.read_csv(prelim_path).to_dict('records')

                        # Get visualization paths
                        vis_files = [
                            f"/api/visualizations/{analysis_id}/{f}"
                            for f in os.listdir(vis_dir)
                            if f.endswith(('.png', '.svg', '.html'))
                        ]

                        # Add results
                        results["analysisResults"]["string_matching"] = {
                            "analysis_id": analysis_id,
                            "preliminary_scores": preliminary_scores,
                            "visualizations": vis_files,
                            "status": "complete"
                        }
                        logger.info("String matching analysis complete")

                    except Exception as e:
                        logger.error(f"String matching analysis failed: {str(e)}")
                        results["analysisResults"]["string_matching"] = {
                            "status": "error",
                            "error": str(e)
                        }

                # Semantic analysis
                if "semantic" in modules:
                    try:
                        analyzer = PalimpsestAnalyzer()
                        # Ensure we have at least two documents for semantic comparison
                        source_text = docs_loaded[0] if docs_loaded else ""
                        target_texts = docs_loaded[1:] if len(docs_loaded) > 1 else []
                        
                        semantic_res = analyzer.analyze_texts(source_text, target_texts)
                        results["analysisResults"]["semantic"] = {
                            "status": "complete",
                            "connections": semantic_res.get("semantic_connections", [])
                        }
                        logger.info("Semantic analysis complete")

                    except Exception as e:
                        logger.error(f"Semantic analysis failed: {str(e)}")
                        results["analysisResults"]["semantic"] = {
                            "status": "error",
                            "error": str(e)
                        }

                return jsonify(results)

            except Exception as e:
                logger.error(f"Analysis request failed: {str(e)}")
                return jsonify({"error": str(e)}), 500

        @app.route('/api/visualizations/<analysis_id>/<path:filename>')
        def serve_visualization(analysis_id, filename):
            """
            Serve visualization files (e.g., heatmaps) from the visualization directory.
            Path format: /api/visualizations/<analysis_id>/<filename>
            """
            try:
                # Validate analysis_id format (should be analysis_timestamp)
                if not analysis_id.startswith('analysis_'):
                    raise ValueError("Invalid analysis ID format")

                # Construct path to visualization
                vis_dir = os.path.join(APP_CONFIG['VISUALIZATION_DIR'], analysis_id)
                
                # Basic security check - ensure file exists in visualization directory
                file_path = os.path.join(vis_dir, filename)
                if not os.path.exists(file_path):
                    raise FileNotFoundError(f"Visualization file not found: {filename}")
                
                # Serve the file
                logger.info(f"Serving visualization: {analysis_id}/{filename}")
                return send_from_directory(vis_dir, filename)

            except ValueError as e:
                logger.error(f"Invalid visualization request: {e}")
                return jsonify({"error": "Invalid visualization request"}), 400
            except FileNotFoundError as e:
                logger.error(f"Visualization not found: {e}")
                return jsonify({"error": "Visualization not found"}), 404
            except Exception as e:
                logger.error(f"Error serving visualization: {e}")
                return jsonify({"error": "Internal server error"}), 500

        @app.route('/api/cleanup-old-analysis', methods=['POST'])
        def cleanup_old_analysis():
            """Clean up analysis and visualization files older than 24 hours."""
            try:
                cutoff = time.time() - (24 * 60 * 60)  # 24 hours ago
                cleaned = 0

                # Clean up analysis directory
                for analysis_id in os.listdir(APP_CONFIG['ANALYSIS_DIR']):
                    dir_path = os.path.join(APP_CONFIG['ANALYSIS_DIR'], analysis_id)
                    if os.path.getmtime(dir_path) < cutoff:
                        shutil.rmtree(dir_path)
                        cleaned += 1

                # Clean up visualization directory
                for analysis_id in os.listdir(APP_CONFIG['VISUALIZATION_DIR']):
                    dir_path = os.path.join(APP_CONFIG['VISUALIZATION_DIR'], analysis_id)
                    if os.path.getmtime(dir_path) < cutoff:
                        shutil.rmtree(dir_path)
                        cleaned += 1

                return jsonify({
                    "status": "success",
                    "message": f"Cleaned up {cleaned} old analysis directories"
                })

            except Exception as e:
                logger.error(f"Error during cleanup: {e}")
                return jsonify({"error": str(e)}), 500

        @app.route('/api/analysis-status')
        def get_analysis_status():
            """Get the current status of any running analysis."""
            return jsonify({
                "status": "OK",
                "is_analyzing": False,  # TODO: Implement actual status tracking
                "progress": 100,
                "last_error": None
            })
        
        @app.route('/api/exit', methods=['POST'])
        def exit_palimpsest():
            """Shut down the Flask server and exit Palimpsest."""
            try:
                logger.info(f"Received exit request from {request.remote_addr}")
                
                # Get Werkzeug server
                func = request.environ.get('werkzeug.server.shutdown')
                if func is None:
                    logger.error("Not running with Werkzeug server")
                    return jsonify({"error": "Server shutdown not available"}), 500
                    
                logger.info("Shutting down Werkzeug server...")
                func()  # This will stop the server
                
                # Set a flag to exit after response is sent
                def exit_after_response(response):
                    logger.info("Response sent, terminating process...")
                    os._exit(0)
                    
                response = jsonify({"status": "success", "message": "Server shutting down"})
                response.call_on_close(exit_after_response)
                
                return response
                
            except Exception as e:
                logger.error(f"Error during shutdown: {str(e)}")
                return jsonify({"error": str(e)}), 500

        logger.info(f"Starting Flask-based UI server on port {PORT}, serving from {ui_dir}")
        try:
            app.run(port=PORT, host='0.0.0.0')
        except KeyboardInterrupt:
            print("\\nUI Server stopped.")
            logger.info("UI server stopped by user.")
        except Exception as e:
            logger.error(f"Error running Flask UI server: {e}", exc_info=True)
            print(f"An unexpected error occurred in the UI server: {e}")
        return 0

if __name__ == "__main__":
    sys.exit(main())