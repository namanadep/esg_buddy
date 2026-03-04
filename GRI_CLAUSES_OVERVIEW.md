# GRI Clauses: Why So Many, and Do You Need All?

## Why there are many GRI clauses

1. **One clause per disclosure**  
   Each GRI standard PDF contains multiple **“Disclosure X-Y”** sections (e.g. Disclosure 2-1, 2-2, … 2-30). The parser creates **one clause per disclosure**. So a single PDF can add 5–30+ clauses.

2. **Many standards are included**  
   Even after filtering to “essential” (non–industry-specific) standards, we still include:
   - **Universal (every GRI report):** GRI 1 (Foundation), GRI 2 (General Disclosures), GRI 3 (Material Topics)  
   - **Topic standards:** Economic (201, 205, 207), Environmental (302, 303, 305, 306), Social (401, 403, 404, 405, 413)  

   That’s 16+ PDFs, each with several to dozens of disclosures → **~100–150+ GRI clauses** in “essential” mode.

3. **GRI 2 alone is large**  
   GRI 2 (General Disclosures 2021) has **30 disclosures** (2-1 through 2-30). So the “universal” set (GRI 1 + 2 + 3) alone is already **~35–45 clauses**.

So the high count is by design: we mirror the real GRI structure (one clause per disclosure across many standards). You don’t necessarily need all of them for every use case.

---

## Do you truly need all of them?

**It depends what you want to evaluate.**

- **If you only care that a report “follows GRI” at a general level**  
  You do **not** need every topic standard. Use **core** (see below): GRI 1, 2, and 3 only (~35–45 clauses). That covers foundation, general disclosures, and material topics—the part every GRI report must address.

- **If you need topic-specific checks** (emissions, water, labor, anticorruption, etc.)  
  You need the **essential** set (current default): universal + selected topic standards (~100–150+ clauses).

- **If you need a specific topic** (e.g. only climate)  
  Ideally we’d support “GRI core + 305 only”; that’s not implemented yet. Today the choice is **core** vs **essential**.

So: you do **not** need all of them for a lighter check; you **do** need more of them for full topic coverage.

---

## How to reduce the number of GRI clauses: use “core”

We support three scopes:

| Scope        | What’s included                    | Typical clause count | When to use |
|-------------|-------------------------------------|----------------------|-------------|
| **core**     | Only GRI 1, 2, 3 (universal)        | ~35–45               | Light check; “does the report follow GRI at all?” |
| **standard** (default) | Universal + 201, 205, 207, 302, 303, 305, 306, 401, 404, 405 | **~120** | Balanced set for most reports |
| **essential** | Standard + 403 (OHS), 413 (Local communities) | ~140–150 | Full topic coverage |

To change scope:

1. Set in `backend/.env`:
   ```bash
   GRI_SCOPE=standard   # ~120 clauses (default)
   # GRI_SCOPE=core     # ~40 clauses
   # GRI_SCOPE=essential # ~140+ clauses
   ```
2. Restart the backend and call `POST /system/reparse-standards` (or run `python backend/reparse_standards.py`) so the vector store is rebuilt with the chosen scope.

---

## Summary

- **Why so many?** One clause per disclosure × many disclosures per standard × many standards (even in “essential”) → 100–150+ clauses.
- **Do you need all?** No for a general “GRI-aligned” check; yes if you want topic-level (environmental, social, economic) detail.
- **How to use fewer?** Set `GRI_SCOPE=core` and reparse; you’ll get only GRI 1, 2, 3 (~35–45 clauses).
