import sys
print(f"Using Python interpreter: {sys.executable}")

import os

try:
    import openai
    from langsmith.wrappers import wrap_openai
    from langsmith import traceable
except ImportError:
    print("Required packages not found. Please install them using:")
    print("pip install openai langsmith")
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

# Auto-trace LLM calls in-context
client = wrap_openai(openai.Client())

@traceable # Auto-trace this function
def pipeline(user_input: str):
    result = client.chat.completions.create(
        messages=[{"role": "user", "content": user_input}],
        model="gpt-3.5-turbo"
    )
    return result.choices[0].message.content

print("\nSending message to ChatGPT...")
response = pipeline("Hello, world!")
print("\nResponse from ChatGPT:")
print(response)