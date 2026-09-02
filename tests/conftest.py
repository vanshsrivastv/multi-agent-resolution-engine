import os

# Force LangSmith tracing off for the entire test session, regardless of
# what .env sets for real manual runs. This must run before any app module
# is imported (conftest.py loads before test collection), and python-dotenv
# never overrides an already-set variable, so this reliably wins even if
# .env later enables tracing for real use. Without this, running pytest
# would silently send real trace data to LangSmith on every test run.
os.environ["LANGSMITH_TRACING"] = "false"
os.environ["LANGCHAIN_TRACING_V2"] = "false"
