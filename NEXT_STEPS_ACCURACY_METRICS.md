# Next Steps: Testing Accuracy Metrics

## ✓ What's Been Completed

1. **Regenerated ground truth files** with correct clause IDs for all 3 companies
2. **Updated ground truth loader** to use new file format
3. **AI-analyzed PDFs** to determine compliance status for 9 Core metrics
4. **Validated files** - all 3 companies have 9 valid ground truth entries

## 🚀 How to See Accuracy Metrics

### Step 1: Restart Backend
Your backend needs to reload the new ground truth files.

```bash
# Stop the current backend (Ctrl+C in the terminal running it)
# Then restart:
uvicorn app.main:app --reload
```

### Step 2: Generate a New Report
1. Go to the **Documents** page in your UI
2. Find **TCS BRSR.pdf** (or RIL/TATA Motors)
3. Click **"Evaluate BRSR"**
4. Wait for evaluation to complete

### Step 3: View Accuracy Metrics
1. Click on the newly generated report
2. Scroll to the **"Ground Truth Accuracy"** section
3. You should now see:
   - **Ground truth loaded: 9** (instead of 0)
   - **Precision**: X.XX
   - **Recall**: X.XX
   - **F1 Score**: X.XX
   - **Clauses Verified: 9**

## 📊 What to Expect

### Ground Truth Baseline (from AI analysis)

All 3 companies have the same pattern:

**✓ Compliant (3 metrics)**:
- Core 5: Employment metrics
- Core 6: Gender diversity
- Core 9: Turnover rate

**❌ Non-Compliant (6 metrics)**:
- Core 1: GHG footprint
- Core 2: Water footprint
- Core 3: Waste footprint
- Core 4: Energy footprint
- Core 7: Return to investors
- Core 8: Median remuneration

### Interpreting Accuracy Metrics

**If your system matches the ground truth perfectly**:
- Precision = 1.0 (100%)
- Recall = 1.0 (100%)
- F1 Score = 1.0 (100%)

**If there are mismatches**:
- **Low Precision**: System is marking things as Compliant when they're actually Non-Compliant
- **Low Recall**: System is marking things as Non-Compliant when they're actually Compliant
- **Low F1**: Overall poor agreement with ground truth

## 🔍 Debugging

If you still see `ground_truth_loaded = 0`:

1. **Check backend logs** for errors:
   ```
   Look for: "Loaded X ground truth labels for TCS"
   ```

2. **Verify filename matching**:
   - Your report must have filename: "TCS BRSR.pdf" (exact match)
   - Check in UI: Report title should show "TCS BRSR.pdf"

3. **Check ground truth files exist**:
   ```bash
   ls "Company Reports/BRSR Ground Truth/"
   # Should show: TCS Ground Truth.json, RIL Ground Truth.json, TATA Motors Ground Truth.json
   ```

4. **Validate JSON format**:
   ```bash
   python backend/test_ground_truth.py
   # Should show: "Valid entries: 9" for each company
   ```

## 📈 Expanding Coverage

Current: **9 Core metrics** (3.4% of total clauses)

To get full accuracy metrics:

### Quick Expansion (Recommended)
Focus on the most important clauses first:

1. **Section A (General Disclosures)** - ~30 clauses
   - Corporate identity, products, operations
   - Usually straightforward to verify

2. **High-Impact Principles** - ~50 clauses
   - Principle 1 (Ethics & Governance)
   - Principle 3 (Employee Wellbeing)
   - Principle 6 (Environment)

### Full Expansion
All ~265 clauses across all sections

**Time estimate**: 2-3 hours per company with AI assistance

**Script to use**:
```bash
# Modify ai_fill_ground_truth.py to parse all sections
# Then run:
python backend/ai_fill_ground_truth.py --full
```

## 📝 Files Reference

| File | Purpose |
|------|---------|
| `Company Reports/BRSR Ground Truth/TCS Ground Truth.json` | TCS ground truth (9 clauses) |
| `Company Reports/BRSR Ground Truth/RIL Ground Truth.json` | RIL ground truth (9 clauses) |
| `Company Reports/BRSR Ground Truth/TATA Motors Ground Truth.json` | TATA Motors ground truth (9 clauses) |
| `backend/ai_fill_ground_truth.py` | AI-powered ground truth generator |
| `backend/auto_generate_ground_truth.py` | Template generator for manual review |
| `backend/test_ground_truth.py` | Validation script |
| `GROUND_TRUTH_SETUP_COMPLETE.md` | Technical summary |

## ✅ Success Criteria

You'll know it's working when:
1. ✓ Backend starts without errors
2. ✓ New report shows `ground_truth_loaded = 9`
3. ✓ Accuracy metrics display with Precision/Recall/F1 values
4. ✓ "Ground Truth Accuracy" section is visible (blue panel)

---

**Ready to test!** Restart your backend and generate a new TCS BRSR report.
