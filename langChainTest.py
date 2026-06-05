import sys
print(f"Using Python interpreter: {sys.executable}")

import os

try:
    from langchain_openai import ChatOpenAI
except ImportError:
    print("Required package not found. Please install it using:")
    print("pip install langchain-openai")
    exit(1)

try:
    from dotenv import load_dotenv
    load_dotenv("langSmithEnv")
except ImportError:
    print("Please install python-dotenv: pip install python-dotenv")
    exit(1)

# Set environment variables
os.environ["LANGSMITH_TRACING"] = "true"
os.environ["LANGSMITH_ENDPOINT"] = "https://api.smith.langchain.com"
os.environ["LANGSMITH_PROJECT"] = "pr-elderly-mangrove-73"

# Prompt for API keys if not set
if not os.environ.get("LANGSMITH_API_KEY"):
    os.environ["LANGSMITH_API_KEY"] = input("Enter LangSmith API Key: ")
if not os.environ.get("OPENAI_API_KEY"):
    os.environ["OPENAI_API_KEY"] = input("Enter OpenAI API Key: ")

llm = ChatOpenAI()

print("\nSending message to ChatGPT...")
response = llm.invoke("Hello, world!")
print("\nResponse from ChatGPT:")
print(response.content)