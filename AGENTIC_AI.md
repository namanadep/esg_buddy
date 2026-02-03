# ESGBuddy - Agentic AI Implementation

## 🤖 Overview

ESGBuddy now features **Agentic AI** with Chain-of-Thought reasoning and Self-Reflection, making compliance decisions more accurate, transparent, and trustworthy.

## 🧠 How It Works

### Traditional Pipeline (Before):

```
Evidence → LLM → Decision
```

### Agentic Pipeline (Now):

```
Evidence → Chain-of-Thought → Self-Reflection → [Revision if needed] → Final Decision
```

---

## 📋 Three-Stage Agentic Process

### Stage 1: Chain-of-Thought Reasoning

The LLM explicitly thinks through the problem step-by-step:

1. **Evidence Quality Assessment**

   - Evaluates relevance and quality of each evidence piece
   - Checks similarity scores and context

2. **Requirement Matching**

   - Maps evidence to specific clause requirements
   - Identifies which aspects are covered

3. **Evidence Type Validation**

   - Verifies if evidence matches required types (numeric, descriptive, policy)
   - Checks for appropriate documentation

4. **Completeness Analysis**

   - Identifies gaps in evidence coverage
   - Flags missing requirements

5. **Compliance Determination**
   - Synthesizes findings into a compliance status
   - Assigns confidence score

**Output**: Explicit reasoning steps stored for transparency

---

### Stage 2: Self-Reflection

The LLM critically reviews its own analysis:

- **Logical Consistency**: Are the reasoning steps sound?
- **Evidence Coverage**: Was all relevant evidence considered?
- **Bias Check**: Are there hidden assumptions?
- **Completeness**: Were all clause aspects addressed?
- **Alternative Interpretations**: Could evidence mean something else?
- **Confidence Calibration**: Is the confidence score appropriate?

**Output**:

- Reflection summary
- List of identified issues
- Decision: needs_revision (true/false)

---

### Stage 3: Revision (Conditional)

If reflection identifies issues, the LLM revises its analysis:

- Addresses specific issues found
- Reconsiders evidence interpretation
- Adjusts confidence score if needed
- Provides updated reasoning

**Output**: Revised decision with documented changes

---

## 💡 Benefits

### 1. **Higher Accuracy**

- Self-correction catches errors before finalizing
- Step-by-step thinking reduces logical jumps
- Critical review identifies biases

### 2. **Transparency**

- Reasoning steps are visible and auditable
- Reflection process documents quality checks
- Revisions show what changed and why

### 3. **Confidence Calibration**

- Self-reflection improves confidence accuracy
- Uncertainty is identified explicitly
- Over-confident decisions are caught

### 4. **Regulatory Compliance**

- Audit trail shows decision-making process
- Explainable AI for compliance officers
- Traceable reasoning for stakeholders

---

## 📊 Cost & Performance

### LLM Calls per Clause:

| Stage               | Calls   | Purpose                       |
| ------------------- | ------- | ----------------------------- |
| Chain-of-Thought    | 1       | Step-by-step reasoning        |
| Self-Reflection     | 1       | Critical review               |
| Revision (optional) | 0-1     | Fix identified issues         |
| **Total**           | **2-3** | Vs. 1 in traditional pipeline |

### Performance Impact:

- **Latency**: +2-3 seconds per clause (acceptable for compliance)
- **Cost**: ~2-3x LLM calls (worthwhile for accuracy gain)
- **Accuracy Improvement**: Expected +10-15% precision (needs benchmarking)

---

## 🎯 When Agentic AI Triggers

### Revision Triggers:

The system revises analysis when reflection identifies:

- Logical inconsistencies in reasoning
- Missing evidence considerations
- Overconfident assessments
- Misinterpretation of evidence

### Typical Revision Rate:

- **10-20%** of clauses need revision
- More common for complex/ambiguous clauses
- Less common for clear-cut cases

---

## 🔍 Viewing Agentic Reasoning

### In the UI:

When viewing a compliance report detail:

1. **AI Analysis** - Shows final explanation
2. **Chain-of-Thought Reasoning** - Expandable step-by-step logic
3. **Self-Reflection** - Critical review and identified issues
4. **Revised Badge** - Indicates if analysis was revised

---

## 📈 Data Model

### New Fields in `LLMEvaluation`:

```python
class LLMEvaluation(BaseModel):
    status: ComplianceStatus
    confidence: float
    explanation: str
    reasoning: Optional[str]

    # Agentic AI fields
    reasoning_steps: Optional[List[str]]      # CoT steps
    reflection: Optional[str]                  # Self-review
    reflection_issues: Optional[List[str]]     # Found issues
    revised: bool                              # Was it revised?
```

---

## 🛠️ Implementation Details

### Backend Files Modified:

1. **`models.py`**

   - Added agentic fields to `LLMEvaluation`

2. **`compliance_pipeline.py`**
   - `_evaluate_with_llm()` - Main agentic orchestration
   - `_chain_of_thought_reasoning()` - Stage 1 implementation
   - `_self_reflection()` - Stage 2 implementation
   - `_revise_reasoning()` - Stage 3 implementation

### Frontend Files Modified:

1. **`ReportDetail.jsx`**
   - Added Chain-of-Thought reasoning display
   - Added Self-Reflection display
   - Added "REVISED" badge for revised analyses

---

## 🚀 Future Enhancements

### Potential Upgrades:

1. **Multi-Agent System**

   - Separate Researcher, Analyst, and Validator agents
   - Agents critique each other's work
   - Higher accuracy but 3-5x cost

2. **Tool-Calling Agent**

   - LLM decides which tools to use
   - Can request additional evidence
   - More autonomous but less predictable

3. **Memory & Learning**

   - Agent remembers past evaluations
   - Learns from corrections and overrides
   - Improves over time

4. **Confidence Thresholds**
   - Auto-trigger human review for low confidence
   - Adaptive thresholds based on clause criticality
   - Flag uncertain evaluations

---

## 📝 Configuration

### In `.env`:

```bash
# LLM Model (must support JSON mode)
LLM_MODEL=gpt-5-nano

# Temperature settings are in code:
# - CoT: 0.2 (focused reasoning)
# - Reflection: 0.3 (more critical)
# - Revision: 0.2 (focused correction)
```

---

## ✅ Testing

### Verify Agentic AI is Working:

1. Run a compliance evaluation
2. View report detail page
3. Expand a clause evaluation
4. Look for:
   - ✅ Chain-of-Thought steps section
   - ✅ Self-Reflection section
   - ✅ "REVISED" badge (on ~10-20% of clauses)

### Sample Test:

```bash
# Start backend
cd backend
python -m uvicorn app.main:app --reload

# Upload document and run evaluation
# Check logs for:
# - "Agentic LLM evaluation"
# - "Reflection identified issues" (on revisions)
```

---

## 🎓 Learn More

- **Chain-of-Thought**: [Wei et al. 2022](https://arxiv.org/abs/2201.11903)
- **Self-Reflection**: [Shinn et al. 2023 - Reflexion](https://arxiv.org/abs/2303.11366)
- **Agentic AI**: [LangChain Agents](https://python.langchain.com/docs/modules/agents/)

---

## 🆘 Troubleshooting

### Issue: No reasoning steps showing

- Check backend logs for errors
- Verify LLM model supports JSON mode
- Check API key has sufficient credits

### Issue: Every clause is revised

- May indicate prompt issues
- Check if reflection is too critical
- Adjust reflection temperature (currently 0.3)

### Issue: Too slow

- Expected 2-3 seconds per clause
- If slower, check API latency
- Consider caching for re-evaluations

---

**ESGBuddy with Agentic AI** - More accurate, transparent, and trustworthy ESG compliance verification.
