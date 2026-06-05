import asyncio
import sys
import os
import logging

# Add the project root directory to the Python path
# This allows importing modules from the 'core' directory
script_dir = os.path.dirname(__file__)
project_root = os.path.abspath(os.path.join(script_dir, '..'))
sys.path.insert(0, project_root)

try:
    from core.gutenberg_client import GutenbergClient
except ImportError:
    print("Error: Could not import GutenbergClient. Make sure you are running this script from the 'src' directory or have the project structure set up correctly.")
    sys.exit(1)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Project Gutenberg IDs for the Gospels (King James Version likely)
# Note: These IDs might correspond to the entire Bible or specific versions.
# Verification on the Gutenberg website is recommended if specific versions are needed.
GOSPEL_IDS = {
    "Matthew": 8040,
    "Mark": 8041,
    "Luke": 8042,
}

async def fetch_all_gospels(client: GutenbergClient):
    """Fetches all specified gospels using the GutenbergClient."""
    tasks = []
    for name, book_id in GOSPEL_IDS.items():
        logger.info(f"Creating task to fetch {name} (ID: {book_id})")
        # GutenbergClient methods are not async, so we run them in the default executor
        # If GutenbergClient were async, we would await client.fetch_text(book_id) directly
        loop = asyncio.get_running_loop()
        tasks.append(loop.run_in_executor(None, client.fetch_text, book_id))

    results = await asyncio.gather(*tasks, return_exceptions=True)

    for (name, book_id), result in zip(GOSPEL_IDS.items(), results):
        if isinstance(result, Exception):
            logger.error(f"Failed to fetch {name} (ID: {book_id}): {result}")
        elif result is None:
             logger.error(f"Failed to fetch {name} (ID: {book_id}) - fetch_text returned None.")
        else:
            logger.info(f"Successfully fetched and cached {name} (ID: {book_id}). Text length: {len(result)}")

async def main():
    """Main function to initialize client and fetch gospels."""
    logger.info("Initializing GutenbergClient...")
    # Use a specific cache directory within the project structure
    cache_path = os.path.join(project_root, 'data', 'gutenberg_cache')
    client = GutenbergClient(cache_dir=cache_path)
    logger.info("Fetching Gospels...")
    await fetch_all_gospels(client)
    logger.info("Gospel fetching process complete.")

if __name__ == "__main__":
    # Ensure the script is run from the correct location or paths are adjusted
    print(f"Project Root: {project_root}")
    print(f"Current Directory: {os.getcwd()}")
    print("Starting Gospel fetching script...")
    asyncio.run(main())
    print("Script finished.")