# ESGBuddy - Intelligent ESG Compliance Copilot

A full-stack AI web application that performs clause-level ESG compliance verification by mapping uploaded company documents to ESG standards (BRSR, GRI, SASB, TCFD) using a hybrid AI pipeline.

![ESGBuddy Banner](https://via.placeholder.com/1200x300/3d8269/ffffff?text=ESGBuddy+ESG+Compliance+Copilot)

## 🌟 Overview

ESGBuddy automates ESG compliance verification through **Agentic AI**:

1. **Semantic Retrieval** - Vector embeddings find relevant evidence in documents
2. **Chain-of-Thought Reasoning** - LLM thinks step-by-step through compliance analysis
3. **Self-Reflection** - AI critically reviews its own reasoning for errors
4. **Adaptive Revision** - System corrects identified issues automatically
5. **Rule Validation** - Deterministic checks validate numeric, temporal, and structural requirements
6. **Accuracy Measurement** - Comprehensive metrics track system performance

## 🎯 Key Features

### Document Processing

- PDF parsing with semantic chunking (512 tokens)
- Automatic metadata extraction
- Vector embedding generation (OpenAI)
- ChromaDB storage for fast retrieval

### ESG Standards Parser

- Automatic extraction of clauses from standard PDFs
- Supports BRSR (SEBI), GRI, SASB, TCFD
- Structured clause representation with validation rules
- Keyword and evidence type inference

### Agentic Compliance Evaluation Pipeline

- **Step 1**: Semantic retrieval (Top-K evidence chunks)
- **Step 2a**: Chain-of-Thought reasoning (explicit step-by-step analysis)
- **Step 2b**: Self-Reflection (critical review of reasoning)
- **Step 2c**: Revision (if issues identified)
- **Step 3**: Rule validation (deterministic checks)
- **Step 4**: Final decision (LLM + rules combined)

**📖 See [AGENTIC_AI.md](AGENTIC_AI.md) for detailed documentation.**

### Accuracy Measurement

- **Retrieval Recall@K** - % of clauses where correct evidence is found
- **LLM Precision/Recall/F1** - Compliance decision accuracy
- **Rule Validation Precision** - Deterministic check accuracy
- **Confidence Calibration** - Correlation between confidence and correctness

### Production-Grade UI

- Distinctive design with Playfair Display + DM Sans typography
- Forest green and clay beige color palette
- Smooth Framer Motion animations
- Fully responsive and accessible

## 📁 Project Structure

```
esg_buddy/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI application
│   │   ├── config.py            # Configuration management
│   │   ├── models.py            # Pydantic data models
│   │   ├── ingestion.py         # PDF processing & chunking
│   │   ├── clause_parser.py     # ESG standard parser
│   │   ├── vector_store.py      # ChromaDB management
│   │   ├── compliance_pipeline.py  # Main evaluation engine
│   │   ├── rule_validator.py    # Rule-based validation
│   │   └── accuracy.py          # Accuracy measurement
│   ├── requirements.txt
│   ├── .env.example
│   └── README.md
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   └── Layout.jsx
│   │   ├── pages/
│   │   │   ├── Home.jsx
│   │   │   ├── Upload.jsx
│   │   │   ├── Documents.jsx
│   │   │   ├── Clauses.jsx
│   │   │   ├── Reports.jsx
│   │   │   └── ReportDetail.jsx
│   │   ├── lib/
│   │   │   └── api.js
│   │   ├── App.jsx
│   │   └── main.jsx
│   ├── package.json
│   ├── vite.config.js
│   └── README.md
├── Standards/
│   ├── BRSR.pdf
│   ├── tcfd.pdf
│   ├── automobiles-standard_en-gb-sasb.pdf
│   └── GRI/
│       └── [GRI standard PDFs]
└── README.md
```

## 🚀 Quick Start

### Prerequisites

- Python 3.9+
- Node.js 18+
- OpenAI API key

### Backend Setup

```bash
# Navigate to backend
cd backend

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY

# Run the server
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Backend will be available at `http://localhost:8000`

API documentation: `http://localhost:8000/docs`

### Frontend Setup

```bash
# Navigate to frontend
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

Frontend will be available at `http://localhost:3000`

## 📊 Workflow

```
User Document (PDF)
    ↓
1. INGESTION
   - Extract text with PyMuPDF
   - Chunk into 512-token segments
   - Generate OpenAI embeddings
    ↓
2. VECTOR STORE (ChromaDB)
   - Store document chunks
   - Store ESG clause embeddings
    ↓
3. COMPLIANCE EVALUATION
   ├─ Semantic Retrieval (Top-K chunks)
   ├─ LLM Analysis (GPT-4)
   └─ Rule Validation (Deterministic)
    ↓
4. COMPLIANCE REPORT
   - Status per clause (supported/partial/not_supported/inferred)
   - Confidence scores
   - Evidence mapping
   - LLM explanations
   - Rule validation results
```

## 🎨 UI Design

The frontend follows a distinctive editorial aesthetic:

- **Typography**: Playfair Display (headlines), DM Sans (body), JetBrains Mono (code)
- **Colors**: Forest green (#3d8269), Clay beige (#f0ebe3), Ink dark (#2d2f33)
- **Animations**: Purposeful motion with Framer Motion
- **Layout**: Generous white space, asymmetric accents

The design avoids generic AI aesthetics and creates a memorable, professional experience.

## 🔧 API Endpoints

### Documents

- `POST /documents/upload` - Upload PDF document
- `GET /documents` - List all documents
- `DELETE /documents/{id}` - Delete document

### Clauses

- `GET /clauses` - Get all clauses (filterable by framework)
- `GET /clauses/{id}` - Get clause details

### Compliance

- `POST /compliance/evaluate` - Run compliance evaluation
- `GET /compliance/reports/{id}` - Get report
- `GET /compliance/reports/{report_id}/clause/{clause_id}` - Get clause evaluation detail
- `POST /compliance/override` - Override clause decision

### Accuracy

- `POST /accuracy/ground-truth` - Add ground truth labels
- `GET /accuracy/metrics/{report_id}` - Get accuracy metrics
- `GET /accuracy/benchmark` - Get benchmark statistics

### System

- `GET /health` - Health check
- `GET /system/stats` - System statistics
- `POST /system/reparse-standards` - Reparse ESG standards

## 📈 Accuracy Measurement

ESGBuddy tracks accuracy across multiple dimensions:

1. **Retrieval Accuracy** (Recall@K)

   - Measures: % of clauses where correct evidence is retrieved in top-K chunks
   - Goal: High recall ensures relevant evidence is found

2. **LLM Reasoning** (Precision/Recall/F1)

   - Measures: Accuracy of compliance status decisions
   - Compares: System predictions vs. ground truth labels

3. **Rule Validation Precision**

   - Measures: When rules override LLM, how often are they correct?
   - Tracks: False positives from rule-based logic

4. **Confidence Calibration**
   - Measures: Correlation between confidence score and actual accuracy
   - Goal: Lower calibration error (0 = perfect calibration)

## 🎓 ESG Frameworks Supported

- **BRSR** (Business Responsibility & Sustainability Report) - SEBI India
- **GRI** (Global Reporting Initiative) - 40+ standards
- **SASB** (Sustainability Accounting Standards Board) - Sector-specific
- **TCFD** (Task Force on Climate-related Financial Disclosures)

## 🛠️ Technology Stack

### Backend

- **FastAPI** - Modern Python web framework
- **PyMuPDF** - PDF text extraction
- **ChromaDB** - Vector database
- **OpenAI** - GPT-4 and embeddings
- **Pydantic** - Data validation
- **SQLAlchemy** - Database ORM (optional)

### Frontend

- **React 18** - UI library
- **React Router** - Navigation
- **Framer Motion** - Animations
- **Tailwind CSS** - Styling
- **Axios** - HTTP client
- **Vite** - Build tool

## 🔒 Security Considerations

- API keys stored in environment variables
- CORS configured for production
- Input validation with Pydantic
- File type validation (PDF only)
- Rate limiting recommended for production

## 🚦 Production Deployment

### Backend

1. Set environment to `production` in `.env`
2. Use production ASGI server (Gunicorn + Uvicorn workers)
3. Configure CORS for your domain
4. Set up database (PostgreSQL recommended)
5. Enable logging and monitoring
6. Secure API keys with secret management

### Frontend

1. Build production bundle: `npm run build`
2. Serve with Nginx or similar
3. Configure environment variables
4. Enable CDN for static assets
5. Set up analytics

## 📝 License

All rights reserved.

## 👥 Contributors

Built for advanced ESG compliance automation.

## 📞 Support

For questions or issues, please refer to the documentation in `backend/README.md` and `frontend/README.md`.

---

**ESGBuddy** - Bringing AI intelligence to ESG compliance verification.
