"""
Simple script to verify your OpenAI API key works.
Run from backend folder: python check_openai_key.py
"""

import os
from pathlib import Path

# Load .env if present
env_path = Path(__file__).parent / ".env"
if env_path.exists():
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                os.environ.setdefault(key.strip(), value.strip())

try:
    from openai import OpenAI
except ImportError:
    print("ERROR: openai package not installed. Run: pip install openai")
    exit(1)

api_key = os.environ.get("OPENAI_API_KEY")
if not api_key:
    print("ERROR: OPENAI_API_KEY not set. Add it to backend/.env")
    exit(1)

if api_key.startswith("sk-") and len(api_key) > 20:
    print("API key found (starts with sk-...)")
else:
    print("WARNING: Key format looks unusual. Proceeding anyway...")

print("Calling OpenAI API (models/list)...")
try:
    client = OpenAI(api_key=api_key)
    models = client.models.list()
    names = [m.id for m in models.data[:5]]
    print("OK - API key is valid.")
    print("Sample models:", ", ".join(names))
except Exception as e:
    print("FAILED:", type(e).__name__, str(e))
    exit(1)
