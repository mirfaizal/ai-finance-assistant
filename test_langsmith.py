import os
from dotenv import load_dotenv
from langsmith import Client

load_dotenv()  # loads keys from .env — never hardcode secrets

api_key = os.environ.get("LANGCHAIN_API_KEY")
if not api_key:
    raise EnvironmentError("LANGCHAIN_API_KEY is not set. Add it to .env or export it.")

client = Client()
try:
    projects = list(client.list_projects())
    print(f"SUCCESS: Connected to LangSmith. Found {len(projects)} project(s).")
    for p in projects:
        print(f"  - {p.name}")
except Exception as e:
    print(f"FAILED: {e}")
