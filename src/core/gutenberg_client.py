import os
import re
import requests
from typing import Optional
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class TextCache:
    """Handles caching of downloaded texts."""
    def __init__(self, base_dir: str = "cache/gutenberg"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"TextCache initialized with base directory: {self.base_dir.resolve()}")

    def _get_cache_path(self, book_id: int) -> Path:
        """Get the file path for a cached book."""
        return self.base_dir / f"{book_id}.txt"

    def save_text(self, book_id: int, text: str):
        """Save text to the cache."""
        cache_path = self._get_cache_path(book_id)
        try:
            with open(cache_path, 'w', encoding='utf-8') as f:
                f.write(text)
            logger.info(f"Saved text for book ID {book_id} to cache: {cache_path}")
        except IOError as e:
            logger.error(f"Error saving text for book ID {book_id} to cache: {e}")

    def load_text(self, book_id: int) -> Optional[str]:
        """Load text from the cache if it exists."""
        cache_path = self._get_cache_path(book_id)
        if cache_path.exists():
            try:
                with open(cache_path, 'r', encoding='utf-8') as f:
                    text = f.read()
                logger.info(f"Loaded text for book ID {book_id} from cache: {cache_path}")
                return text
            except IOError as e:
                logger.error(f"Error loading text for book ID {book_id} from cache: {e}")
                return None
        else:
            logger.info(f"No cache found for book ID {book_id} at {cache_path}")
            return None

    def clear_cache(self):
        """Remove all cached files."""
        try:
            for item in self.base_dir.iterdir():
                if item.is_file():
                    item.unlink()
            logger.info(f"Cleared all files from cache directory: {self.base_dir}")
        except Exception as e:
            logger.error(f"Error clearing cache directory {self.base_dir}: {e}")


class GutenbergClient:
    """
    Client for fetching, cleaning, and caching texts from Project Gutenberg.
    """
    def __init__(self, cache_dir: str = "cache/gutenberg"):
        # Updated URL template based on common Gutenberg plain text format
        self.download_url_template = "https://www.gutenberg.org/ebooks/{book_id}.txt.utf-8"
        self.cache = TextCache(cache_dir)
        logger.info("GutenbergClient initialized.")

    def _download_text(self, book_id: int) -> Optional[str]:
        """Downloads the raw text for a given book ID."""
        url = self.download_url_template.format(book_id=book_id)
        logger.info(f"Attempting to download text for book ID {book_id} from {url}")
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
            # Project Gutenberg files are often encoded in UTF-8, but sometimes specify others.
            # We'll try UTF-8 first, then let requests guess if that fails.
            try:
                text = response.content.decode('utf-8')
            except UnicodeDecodeError:
                logger.warning(f"UTF-8 decoding failed for book ID {book_id}. Using requests' detected encoding: {response.encoding}")
                text = response.text # Use requests' fallback decoding

            logger.info(f"Successfully downloaded text for book ID {book_id}. Length: {len(text)} chars.")
            return text
        except requests.exceptions.RequestException as e:
            logger.error(f"Error downloading text for book ID {book_id} from {url}: {e}")
            return None

    def _remove_headers_footers(self, text: str) -> str:
        """Removes standard Project Gutenberg headers and footers."""
        logger.debug("Attempting to remove Project Gutenberg headers and footers.")

        # Define start and end markers using regex
        # These are common patterns but might need refinement for specific texts
        start_markers = [
            r"\*\*\* START OF (THIS|THE) PROJECT GUTENBERG EBOOK .* \*\*\*",
            r"\*\*\*START OF THE PROJECT GUTENBERG EBOOK.*\*\*\*", # Variation
        ]
        end_markers = [
            r"\*\*\* END OF (THIS|THE) PROJECT GUTENBERG EBOOK .* \*\*\*",
            r"End of (the )?Project Gutenberg's .* Etext",
            r"End of Project Gutenberg's .*",
            r"\*\*\*END OF THE PROJECT GUTENBERG EBOOK.*\*\*\*", # Variation
        ]

        start_pos = -1
        # Find the latest possible start marker
        for marker in start_markers:
            match = re.search(marker, text, re.IGNORECASE)
            if match:
                start_pos = max(start_pos, match.end())

        end_pos = len(text)
        # Find the earliest possible end marker
        for marker in end_markers:
            match = re.search(marker, text, re.IGNORECASE)
            if match:
                end_pos = min(end_pos, match.start())

        if start_pos != -1:
            cleaned_text = text[start_pos:end_pos].strip()
            logger.debug(f"Removed header/footer. Original length: {len(text)}, Cleaned length: {len(cleaned_text)}")
            return cleaned_text
        else:
            # If no start marker found, maybe it's not a standard PG text or format changed.
            # Try removing potential footer only.
            cleaned_text = text[:end_pos].strip()
            if len(cleaned_text) < len(text):
                 logger.warning(f"Could not find standard Project Gutenberg start marker. Removed potential footer only. Original length: {len(text)}, Cleaned length: {len(cleaned_text)}")
            else:
                 logger.warning("Could not find standard Project Gutenberg start/end markers. Returning original text.")
            return cleaned_text


    def clean_text(self, raw_text: str) -> str:
        """Cleans the raw text by removing headers/footers."""
        return self._remove_headers_footers(raw_text)

    def fetch_text(self, book_id: int) -> Optional[str]:
        """
        Fetches cleaned text for a book ID, using cache if available.

        Args:
            book_id: The Project Gutenberg book ID.

        Returns:
            The cleaned text as a string, or None if fetching failed.
        """
        logger.info(f"Fetching text for book ID: {book_id}")
        # 1. Check cache
        cached_text = self.cache.load_text(book_id)
        if cached_text:
            return cached_text

        # 2. Download if not in cache
        raw_text = self._download_text(book_id)
        if raw_text is None:
            return None # Download failed

        # 3. Clean the text
        cleaned_text = self.clean_text(raw_text)

        # 4. Save to cache
        self.cache.save_text(book_id, cleaned_text)

        return cleaned_text

# Example Usage (optional, can be removed or placed under if __name__ == "__main__":)
# if __name__ == "__main__":
#     client = GutenbergClient()
#     # Example: The Adventures of Sherlock Holmes
#     sherlock_holmes_id = 1661
#     text = client.fetch_text(sherlock_holmes_id)
#     if text:
#         print(f"Successfully fetched and cleaned text for book ID {sherlock_holmes_id}.")
#         print(f"First 500 characters:\n{text[:500]}")
#         print(f"\nLast 500 characters:\n{text[-500:]}")
#     else:
#         print(f"Failed to fetch text for book ID {sherlock_holmes_id}.")

#     # Example: Pride and Prejudice
#     pride_prejudice_id = 1342
#     text_pp = client.fetch_text(pride_prejudice_id)
#     if text_pp:
#         print(f"\nSuccessfully fetched and cleaned text for book ID {pride_prejudice_id}.")
#     else:
#         print(f"\nFailed to fetch text for book ID {pride_prejudice_id}.")

#     # Test caching - fetch again
#     print("\nFetching Sherlock Holmes again (should use cache)...")
#     text_cached = client.fetch_text(sherlock_holmes_id)
#     if text_cached:
#         print("Successfully fetched from cache.")