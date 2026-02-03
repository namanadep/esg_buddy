# ESGBuddy Quick Start Guide

Get ESGBuddy up and running in 5 minutes!

## Step 1: Backend Setup (2 minutes)

```bash
# Navigate to backend
cd backend

# Install dependencies (first time only)
pip install -r requirements.txt

# Configure your OpenAI API key
# Option 1: Copy and edit .env file
cp .env.example .env
# Then open .env and add: OPENAI_API_KEY=your_key_here

# Option 2: Set environment variable directly (Windows PowerShell)
$env:OPENAI_API_KEY="your_key_here"

# Option 2: Set environment variable directly (macOS/Linux)
export OPENAI_API_KEY="your_key_here"

# Start the backend server
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

✅ Backend running at `http://localhost:8000`

📚 API docs at `http://localhost:8000/docs`

## Step 2: Frontend Setup (2 minutes)

Open a NEW terminal window:

```bash
# Navigate to frontend
cd frontend

# Install dependencies (first time only)
npm install

# Start the development server
npm run dev
```

✅ Frontend running at `http://localhost:3000`

## Step 3: Start Using ESGBuddy (1 minute)

1. **Open your browser** → `http://localhost:3000`

2. **Upload a document**:

   - Click "Upload" in the navigation
   - Drag & drop or select a PDF file (e.g., annual report, ESG policy)
   - Wait for processing to complete

3. **Run compliance evaluation**:

   - Go to "Documents"
   - Select an ESG framework (GRI, BRSR, SASB, or TCFD)
   - Click the play button (▶) on your document
   - Wait for evaluation to complete

4. **View your report**:
   - Go to "Reports"
   - Click on your report to see detailed clause-by-clause analysis
   - Explore AI explanations, evidence, and validation results

## Troubleshooting

### "OpenAI API Error"

- Check that your API key is set correctly
- Verify you have API credits available
- Check your internet connection

### "No clauses found"

- The backend automatically parses ESG standards on first startup
- Check backend logs for parsing errors
- ESG standard PDFs should be in the `Standards/` folder

### "Module not found"

- Make sure you ran `pip install -r requirements.txt` (backend)
- Make sure you ran `npm install` (frontend)

### Backend won't start

- Ensure Python 3.9+ is installed: `python --version`
- Check port 8000 is not already in use
- Check backend logs for detailed error messages

### Frontend won't start

- Ensure Node.js 18+ is installed: `node --version`
- Check port 3000 is not already in use
- Delete `node_modules/` and run `npm install` again

## Next Steps

- **Browse Clauses**: Explore the ESG clauses that ESGBuddy evaluates against
- **Multiple Documents**: Upload multiple documents and compare compliance
- **Different Frameworks**: Try different ESG frameworks (GRI, BRSR, SASB, TCFD)
- **Accuracy Tracking**: Add ground truth labels to measure system accuracy

## Getting Help

- Backend docs: `backend/README.md`
- Frontend docs: `frontend/README.md`
- API documentation: `http://localhost:8000/docs` (when backend is running)

---

Happy analyzing! 🌱
