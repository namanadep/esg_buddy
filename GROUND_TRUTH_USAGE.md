# Ground Truth System - Usage Guide

## Overview

The ground truth system allows you to verify ESGBuddy's compliance predictions against manually reviewed "correct" labels for TCS, RIL, and TATA Motors BRSR reports.

---

## Ground Truth Files

**Location:** `Company Reports/BRSR Ground Truth/`

| File | Company | Clauses |
|------|---------|---------|
| `TCS Ground Truth.json` | TCS | ~1407 labels |
| `RIL Ground Truth.json` | RIL (Reliance) | ~1407 labels |
| `TATA Motors Ground Truth.json` | TATA Motors | ~1407 labels |

**Format:**
```json
[
  {
    "clause_id": "BRSR-Core-Cust-Supplier-DataBreachPct",
    "compliance_status": "Compliant",
    "comments": "Disclosed 0 data breaches and 0% involving customer data."
  },
  {
    "clause_id": "BRSR-Core-Energy-Intensity",
    "compliance_status": "Partial",
    "comments": "Energy intensity per rupee provided, but not PPP-adjusted."
  },
  {
    "clause_id": "BRSR-Core-GHG-Intensity-ProductOutput",
    "compliance_status": "Non-Compliant",
    "comments": "No GHG intensity per product/service output disclosed."
  }
]
```

**Status Mapping:**
- `"Compliant"` → `supported`
- `"Partial"` → `partial`
- `"Non-Compliant"` → `not_supported`
- `"Inferred"` → `inferred` (if present in ground truth)

---

## How It Works

### 1. **Automatic Loading**

When you view a report detail page, the system:
1. Detects the company name from the filename (e.g., "TCS BRSR.pdf" → TCS)
2. Loads the corresponding ground truth file (`TCS Ground Truth.json`)
3. Links ground truth labels to the report's `document_id`
4. Calculates accuracy metrics automatically

### 2. **Company Matching**

The system matches filenames to ground truth files:

| Filename Pattern | Ground Truth File |
|-----------------|-------------------|
| Contains "TCS" | `TCS Ground Truth.json` |
| Contains "RIL" or "RELIANCE" | `RIL Ground Truth.json` |
| Contains "TATA" | `TATA Motors Ground Truth.json` |

**Examples:**
- `TCS BRSR.pdf` → TCS ground truth
- `RIL BRSR.pdf` → RIL ground truth
- `TATA Motors BRSR.pdf` → TATA Motors ground truth

### 3. **Accuracy Metrics Displayed**

On the report detail page, when ground truth is available, you'll see a **"Ground Truth Accuracy"** section showing:

- **Precision**: % of system's "compliant" predictions that are actually correct
- **Recall**: % of truly compliant clauses that the system identified
- **F1 Score**: Harmonic mean of precision and recall
- **Clauses Verified**: Number of clauses with ground truth labels

---

## API Endpoints

### Load Ground Truth from Files
```bash
POST /accuracy/load-ground-truth
```

Loads all three ground truth files and links them to existing reports by matching company names.

**Response:**
```json
{
  "message": "Loaded ground truth from 3 companies",
  "companies": ["TCS", "RIL", "TATA Motors"],
  "total_labels": 4221,
  "matched_reports": 3,
  "labels_by_company": {
    "TCS": 1407,
    "RIL": 1407,
    "TATA Motors": 1407
  }
}
```

### Get Accuracy Metrics for a Report
```bash
GET /accuracy/metrics/{report_id}
```

Returns accuracy metrics for a specific report (automatically loads ground truth if available).

**Response:**
```json
{
  "report_id": "report_abc123...",
  "document_filename": "TCS BRSR.pdf",
  "ground_truth_loaded": 1407,
  "metrics": {
    "retrieval_recall_at_k": 0.0,
    "llm_precision": 0.92,
    "llm_recall": 0.88,
    "llm_f1_score": 0.90,
    "rule_validation_precision": 1.0,
    "confidence_calibration_error": 0.15,
    "total_clauses_evaluated": 265
  }
}
```

**Note:** `retrieval_recall_at_k` will be 0.0 because the ground truth files don't include page numbers (`expected_evidence_pages` is empty).

---

## Understanding the Metrics

### LLM Precision
**What it measures:** Of all clauses the system marked as "compliant" (supported/inferred), what % are actually compliant according to ground truth?

**Formula:** `true_positives / (true_positives + false_positives)`

**Example:** System says 230 clauses are compliant; ground truth says 215 of those are actually compliant → Precision = 215/230 = 93.5%

### LLM Recall
**What it measures:** Of all truly compliant clauses (per ground truth), what % did the system identify?

**Formula:** `true_positives / (true_positives + false_negatives)`

**Example:** Ground truth says 220 clauses are compliant; system found 215 of them → Recall = 215/220 = 97.7%

### F1 Score
**What it measures:** Balanced measure of precision and recall.

**Formula:** `2 × (precision × recall) / (precision + recall)`

**Good score:** > 0.85 (85%)

### Confidence Calibration Error
**What it measures:** How well the system's confidence scores match actual accuracy.

**Example:** When system says 90% confident, is it actually correct 90% of the time?

**Good score:** < 0.15 (lower is better)

---

## Usage Workflow

### For TCS, RIL, or TATA Motors BRSR Reports:

1. **Upload document** via Documents page
2. **Run compliance evaluation** (select BRSR framework)
3. **View report** - Navigate to report detail page
4. **Accuracy metrics auto-load** - Ground truth is automatically loaded and accuracy is calculated
5. **Review metrics** - See precision, recall, F1 in the blue "Ground Truth Accuracy" section

### For Other Documents:

- If no ground truth file exists for the company, accuracy metrics won't be shown
- You can still use Human Verification to review and approve/reject clauses
- Self-benchmark metrics are available (system's internal consistency checks)

---

## Adding New Ground Truth

To add ground truth for a new company:

1. **Create JSON file** in `Company Reports/BRSR Ground Truth/`
2. **Name it:** `{CompanyName} Ground Truth.json`
3. **Format:** Same as existing files (array of objects with `clause_id`, `compliance_status`, `comments`)
4. **Update mapping** in `backend/app/ground_truth_loader.py`:
   ```python
   self.company_mappings = {
       "TCS": "TCS Ground Truth.json",
       "RIL": "RIL Ground Truth.json",
       "TATA Motors": "TATA Motors Ground Truth.json",
       "NewCompany": "NewCompany Ground Truth.json"  # Add this
   }
   ```

---

## Notes

- Ground truth is loaded **per-report** when you view the report detail page
- Ground truth is stored **in-memory** (lost on backend restart)
- Each company's ground truth is only used for that company's reports (no mixing)
- The system matches clause IDs exactly (e.g., `BRSR-Core-Energy-Intensity`)
- If clause IDs in ground truth don't match the system's clause IDs, those labels are skipped

---

*Generated for ESGBuddy - BRSR Ground Truth Accuracy Verification*
