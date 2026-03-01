import os
from langsmith import Client

# Set LANGCHAIN_API_KEY and LANGSMITH_WORKSPACE_ID in your environment or .env file
# export LANGCHAIN_API_KEY=lsv2_pt_...
# export LANGSMITH_WORKSPACE_ID=...

client = Client()
try:
    client.create_project("test_connection", description="Testing API Key")
    print("SUCCESS: Connection worked!")
except Exception as e:
    print(f"FAILED: {e}")
