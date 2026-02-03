# ESGBuddy Backend

Intelligent ESG Compliance Copilot - Backend API

## Overview

The ESGBuddy backend is a FastAPI-based application that performs clause-level ESG compliance verification by mapping uploaded company documents to ESG standards like BRSR, GRI, SASB, and TCFD using a hybrid AI pipeline (semantic retrieval + LLM + rule validation).

## Architecture

### Core Components

1. **Ingestion Pipeline** (`ingestion.py`)

   - PDF text extraction using PyMuPDF
   - Semantic chunking (512 tokens)
   - Embedding generation (OpenAI)

2. **Clause Parser** (`clause_parser.py`)

   - Parses ESG standard PDFs into structured clauses
   - Extracts requirements, validation rules, keywords
   - Supports BRSR, GRI, SASB, TCFD

3. **Vector Store** (`vector_store.py`)

   - ChromaDB for semantic search
   - Stores document chunks and clause embeddings
   - Efficient similarity-based retrieval

4. **Compliance Pipeline** (`compliance_pipeline.py`)

   - **Step 1**: Semantic retrieval (find relevant evidence)
   - **Step 2**: LLM evaluation (GPT-4 assessment)
   - **Step 3**: Rule validation (deterministic checks)
   - **Step 4**: Final decision (combine LLM + rules)

5. **Rule Validator** (`rule_validator.py`)

   - Numeric validation (amounts, percentages)
   - Temporal validation (dates, periods)
   - Keyword matching
   - Field presence checks

6. **Accuracy Measurement** (`accuracy.py`)
   - Retrieval Recall@K
   - LLM Precision/Recall/F1
   - Rule validation precision
   - Confidence calibration

## Setup

### Prerequisites

- Python 3.9+
- OpenAI API key

### Installation

```bash
cd backend
pip install -r requirements.txt
```

### Configuration

1. Copy `.env.example` to `.env`:

```bash
cp .env.example .env
```

2. Edit `.env` and add your OpenAI API key:

```
OPENAI_API_KEY=your_key_here
```

### Running the Server

```bash
cd backend
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`

API documentation (Swagger UI): `http://localhost:8000/docs`

## API Endpoints

### Document Management

- `POST /documents/upload` - Upload a company document (PDF)
- `GET /documents` - List all uploaded documents
- `DELETE /documents/{document_id}` - Delete a document

### ESG Clauses

- `GET /clauses` - Get all ESG clauses (filterable by framework)
- `GET /clauses/{clause_id}` - Get detailed clause information

### Compliance Evaluation

- `POST /compliance/evaluate` - Evaluate document against ESG clauses
- `GET /compliance/reports/{report_id}` - Get compliance report
- `GET /compliance/reports/{report_id}/clause/{clause_id}` - Get detailed clause evaluation
- `POST /compliance/override` - Override a clause evaluation decision

### Accuracy & Benchmarking

- `POST /accuracy/ground-truth` - Add ground truth labels
- `GET /accuracy/metrics/{report_id}` - Calculate accuracy metrics
- `GET /accuracy/benchmark` - Get overall benchmark statistics

### System Management

- `GET /health` - Health check
- `GET /system/stats` - System statistics
- `POST /system/reparse-standards` - Reparse ESG standards

## Data Flow

```
User Document (PDF)
    ↓
Ingestion → Chunking → Embeddings
    ↓
Vector Store (ChromaDB)
    ↓
Compliance Pipeline
    ├─ Semantic Retrieval (Top-K chunks)
    ├─ LLM Evaluation (GPT-4)
    └─ Rule Validation (Deterministic)
    ↓
Final Compliance Report
```

## Accuracy Measurement

The system measures accuracy across multiple dimensions:

1. **Retrieval Accuracy**: % of clauses where correct evidence is found
2. **LLM Reasoning**: Precision/Recall/F1 of compliance decisions
3. **Rule Validation**: Precision of rule-based overrides
4. **Confidence Calibration**: Correlation between confidence and accuracy

## Project Structure

```
backend/
├── app/
│   ├── main.py                 # FastAPI application
│   ├── config.py               # Configuration management
│   ├── models.py               # Pydantic data models
│   ├── ingestion.py            # PDF processing & chunking
│   ├── clause_parser.py        # ESG standard parser
│   ├── vector_store.py         # ChromaDB management
│   ├── compliance_pipeline.py  # Main evaluation engine
│   ├── rule_validator.py       # Rule-based validation
│   └── accuracy.py             # Accuracy measurement
├── requirements.txt
├── .env.example
└── README.md
```

## Development

### Adding New ESG Standards

1. Place PDF in `../Standards/` directory
2. Update `clause_parser.py` with parsing logic
3. Run `POST /system/reparse-standards` to update

### Adding New Validation Rules

Edit `rule_validator.py` and add new rule types to the `RuleValidator` class.

### Customizing LLM Prompts

Edit the `_build_llm_prompt` method in `compliance_pipeline.py`.

## Troubleshooting

### "No clauses found"

- Ensure ESG standard PDFs are in the `../Standards/` directory
- Check logs for parsing errors
- Run `POST /system/reparse-standards`

### "OpenAI API error"

- Verify API key in `.env`
- Check API rate limits and quotas
- Ensure sufficient credits

### Low retrieval accuracy

- Adjust `TOP_K_CHUNKS` in `.env`
- Tune `CHUNK_SIZE` and `CHUNK_OVERLAP`
- Check document quality (scanned vs text PDFs)

## License

All rights reserved.
