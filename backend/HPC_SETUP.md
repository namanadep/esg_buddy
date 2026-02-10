# Parsing TCFD on HPC Node

Your laptop doesn't have enough memory to parse TCFD documents. Use your HPC node instead.

## Step 1: Setup on HPC Node

1. **Copy project files to HPC:**
   ```bash
   # Copy the entire backend directory and Standards directory
   scp -r backend/ user@hpc-node:/path/to/esgbuddy/
   scp -r Standards/ user@hpc-node:/path/to/esgbuddy/
   ```

2. **SSH into HPC node:**
   ```bash
   ssh user@hpc-node
   cd /path/to/esgbuddy/backend
   ```

3. **Setup Python environment:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Linux/Mac
   # or: venv\Scripts\activate  # On Windows HPC
   
   pip install -r requirements.txt
   ```

4. **Create .env file on HPC:**
   ```bash
   # Copy your .env or create new one with just:
   echo "OPENAI_API_KEY=your_key_here" > .env
   ```

## Step 2: Run Standalone Parser on HPC

```bash
cd backend
python parse_tcfd_standalone.py
```

**What it does:**
- Parses both TCFD PDFs (or just the 2017 report if you have skip logic)
- Uses chunked LLM parsing with memory optimizations
- Exports to `tcfd_clauses.json` (~200KB file)

**Expected output:**
```
================================================================================
TCFD Standalone Parser for HPC Node
================================================================================

Standards directory: /path/to/esgbuddy/Standards
Output file: /path/to/esgbuddy/backend/tcfd_clauses.json

Initializing parser with LLM enabled...
Parsing TCFD documents...
TCFD directory: /path/to/esgbuddy/Standards/TCFD

Document long (238100 chars), splitting into 6 chunks for LLM parsing
Chunk 1/6: extracted 5 clauses
...
Chunk 6/6: extracted 3 clauses

✓ Successfully parsed 43 TCFD clauses

Saving to tcfd_clauses.json...
✓ Saved 43 clauses to tcfd_clauses.json

================================================================================
SUCCESS!
================================================================================

Next steps:
1. Transfer 'tcfd_clauses.json' to your laptop
2. Place it in the backend/ directory
3. Run: python import_clauses.py tcfd_clauses.json
```

**Runtime:** ~5–10 minutes depending on HPC specs and network latency to OpenAI API.

## Step 3: Transfer JSON to Laptop

```bash
# From your laptop, download the JSON file
scp user@hpc-node:/path/to/esgbuddy/backend/tcfd_clauses.json D:\NAMAN\College\Semester_8\esg_buddy\backend\
```

Or use SFTP, WinSCP, or any file transfer method.

## Step 4: Import Clauses on Laptop

```powershell
cd "D:\NAMAN\College\Semester 8\esg_buddy\backend"
.\venv\Scripts\activate
python import_clauses.py tcfd_clauses.json
```

**What it does:**
- Loads clauses from JSON
- Clears existing TCFD clauses from vector store
- Generates embeddings (lighter operation, ~1–2 min)
- Indexes into ChromaDB

**Expected output:**
```
================================================================================
ESGBuddy Clause Importer
================================================================================

Loading clauses from tcfd_clauses.json...
Framework: TCFD
Total clauses in file: 43

✓ Converted 43 clauses
Initializing vector store...
Clearing existing TCFD clauses from vector store...
Adding 43 clauses to vector store...

================================================================================
SUCCESS!
================================================================================
Imported 43 TCFD clauses into vector store

Restart the backend to load these clauses into memory for the API.
```

## Step 5: Restart Backend on Laptop

```powershell
# Stop backend
.\stop_esgbuddy.bat

# Start backend
.\start_esgbuddy.bat
```

The backend will load TCFD clauses from the vector store (no re-parsing needed).

---

## Alternative: API-based Import

Instead of `import_clauses.py`, you can use the API endpoint (after adding it):

```powershell
# Copy JSON content
$json = Get-Content tcfd_clauses.json | ConvertFrom-Json | ConvertTo-Json -Depth 10

# Import via API
Invoke-RestMethod -Method Post -Uri "http://localhost:8000/system/import-clauses" -Body $json -ContentType "application/json"
```

---

## Troubleshooting

**HPC doesn't have internet for OpenAI API?**
- Use regex parsing instead: Set `USE_LLM_PARSING=false` in HPC .env
- Or run on a cloud VM with internet access

**Transfer fails?**
- The JSON file is small (~200KB), use email/USB if needed

**Import fails?**
- Check the JSON format matches expected structure
- Verify OpenAI API key is valid in laptop .env (for embeddings)
