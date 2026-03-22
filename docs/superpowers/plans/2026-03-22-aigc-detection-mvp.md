# AIGC Detection MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a report-first bilingual academic-text AIGC risk screening MVP on top of the existing detection API and report UI.

**Architecture:** Extend the current `detection` backend instead of creating a parallel subsystem. Keep the MVP rule-first and small-data-friendly: add better document parsing, richer section and fragment scoring, auditable explanations, and a CNKI-style report page contract; treat lightweight supervised fusion as a deferred calibration upgrade rather than a launch dependency.

**Tech Stack:** FastAPI, Pydantic, existing backend service layer in `package/backend/app/services/`, React + Vite frontend in `package/frontend/src/`, pytest for backend tests, frontend build plus manual smoke verification

---

## File Structure

- Modify: `package/backend/app/routes/detection.py`
  - Narrow the request/response contract to the MVP report schema and validation rules.
- Modify: `package/backend/app/services/detection_service.py`
  - Refactor the current detector into parsing, scoring, explanation, and report assembly helpers.
- Modify: `package/backend/app/schemas.py`
  - Add typed request/response models for document, section, fragment, and explanation output if the team wants shared schema definitions outside the route file.
- Create: `package/backend/tests/test_detection_service.py`
  - Add focused tests for parsing, tiering, explanation fidelity, and API payload shape.
- Modify: `package/frontend/src/api/index.js`
  - Update detection API helpers if request/response fields change.
- Modify: `package/frontend/src/components/DetectionReport.jsx`
  - Render the MVP report structure: summary, distribution, section table, fragment evidence, and explanation legend.
- Modify: `package/frontend/src/pages/WorkspacePage.jsx`
  - Ensure the detection entry point passes plain text cleanly into the report flow and does not over-promise outcomes.
- Modify: `package/frontend/src/index.css`
  - Add any small report-specific layout utilities only if the existing utility classes become unreadable.
- Create: `docs/detection/dataset_notes.md`
  - Record the seed dataset, weak-label expansion strategy, and human-reviewed validation rules for small-data calibration.
- Modify: `README.md`
  - Document the MVP positioning, limits, and local verification path once implementation is complete.

## Implementation Notes

- Follow the spec in `docs/superpowers/specs/2026-03-22-aigc-detection-feasibility-design.md`.
- Reuse `package/backend/app/routes/detection.py` and `package/backend/app/services/detection_service.py`; do not build a second detection stack.
- Keep MVP output language risk-based and evidence-based. No verdict wording.
- The launch path is rule-first:
  - phase 1a: improved parsing + feature scoring + explanation mapping
  - phase 1b: optional lightweight fusion model only after a reviewed seed dataset exists
- Frontend does not need a new route for MVP if `DetectionReport.jsx` can be upgraded in place.
- Frontend test infrastructure is not committed today, so the plan uses `npm run build` plus manual smoke checks instead of inventing a new JS test stack mid-feature.

### Task 1: Lock The Backend Report Contract

**Files:**
- Modify: `package/backend/app/routes/detection.py`
- Modify: `package/backend/app/schemas.py`
- Test: `package/backend/tests/test_detection_service.py`

- [ ] **Step 1: Write the failing backend contract tests**

Add tests that assert the detection response includes:
- `document_score`
- `document_tier`
- `confidence`
- `sections`
- `fragments`
- `explanations`
- `report_metadata`

Example test shape:

```python
def test_detect_text_returns_report_contract():
    result = asyncio.run(detect_text("第一章\n这是一个足够长的测试段落。"))
    assert "document_score" in result
    assert isinstance(result["sections"], list)
    assert isinstance(result["fragments"], list)
    # MVP fragment contract: text + score + tier (no start/end offsets; inline highlight is v2)
    for frag in result["fragments"]:
        assert "text" in frag
        assert "score" in frag
        assert "tier" in frag
```

- [ ] **Step 2: Run the contract test to confirm it fails against the current payload**

Run: `PYTHONPATH=package/backend pytest package/backend/tests/test_detection_service.py -k report_contract -v`
Expected: FAIL because the current service does not yet expose the full MVP report contract.

- [ ] **Step 3: Define typed request/response models**

Add or update Pydantic models for:
- analysis request
- section result
- fragment result
- explanation item
- top-level report payload

Keep the response fields aligned with the spec and avoid embedding raw speculative prose.

- [ ] **Step 4: Update the route to validate the new contract**

Keep `card_key` auth behavior and text-length validation, but route the response through the typed report schema.

- [ ] **Step 5: Re-run the contract test**

Run: `PYTHONPATH=package/backend pytest package/backend/tests/test_detection_service.py -k report_contract -v`
Expected: PASS

- [ ] **Step 6: Commit the contract work**

```bash
git add package/backend/app/routes/detection.py package/backend/app/schemas.py package/backend/tests/test_detection_service.py
git commit -m "feat: define detection report contract"
```

### Task 2: Refactor Parsing Into Sections And Fragments

**Files:**
- Modify: `package/backend/app/services/detection_service.py`
- Test: `package/backend/tests/test_detection_service.py`

- [ ] **Step 1: Write failing parser tests for bilingual section splitting**

Cover:
- Chinese headings such as `一、`
- numeric headings such as `1.` and `1.1`
- English headings such as `Chapter 1`
- fallback pseudo-sections when headings are absent

Example:

```python
def test_split_document_prefers_explicit_headings():
    sections = split_document_sections("一、引言\n内容A\n\n二、方法\n内容B")
    assert [section["title"] for section in sections] == ["一、引言", "二、方法"]
```

- [ ] **Step 2: Run parser tests and confirm failure**

Run: `PYTHONPATH=package/backend pytest package/backend/tests/test_detection_service.py -k split_document -v`
Expected: FAIL because the helper does not exist or does not honor the new behavior.

- [ ] **Step 3: Implement section and fragment parsing helpers**

Add focused helpers inside `detection_service.py` for:
- language-aware sentence splitting
- explicit heading detection
- pseudo-section fallback
- fragment slicing within each section

Keep helpers small and deterministic so they can be calibrated without an LLM.

- [ ] **Step 4: Re-run parser tests**

Run: `PYTHONPATH=package/backend pytest package/backend/tests/test_detection_service.py -k split_document -v`
Expected: PASS

- [ ] **Step 5: Commit the parsing refactor**

```bash
git add package/backend/app/services/detection_service.py package/backend/tests/test_detection_service.py
git commit -m "feat: add detection document parsing"
```

### Task 3: Build Section And Fragment Risk Scoring

**Files:**
- Modify: `package/backend/app/services/detection_service.py`
- Test: `package/backend/tests/test_detection_service.py`

- [ ] **Step 1: Write failing tests for score normalization and tier mapping**

Cover:
- every score is normalized to `0-100`
- `significant`, `suspected`, `unmarked` mapping uses configurable thresholds
- section scores aggregate fragment and section-level signals

Example:

```python
def test_score_to_tier_uses_dual_thresholds():
    assert score_to_tier(80, high=70, medium=45) == "significant"
    assert score_to_tier(55, high=70, medium=45) == "suspected"
    assert score_to_tier(20, high=70, medium=45) == "unmarked"
```

- [ ] **Step 2: Run the scoring tests to confirm failure**

Run: `PYTHONPATH=package/backend pytest package/backend/tests/test_detection_service.py -k "tier or score" -v`
Expected: FAIL because the current scoring is paragraph-oriented and not yet organized into the MVP aggregation model.

- [ ] **Step 3: Implement explicit scoring helpers**

Refactor the service into helpers for:
- stylometric feature extraction
- local anomaly signals
- fragment scoring
- section aggregation
- document aggregation
- threshold mapping

Keep thresholds centralized so later calibration only changes one configuration surface.

- [ ] **Step 4: Re-run the scoring tests**

Run: `PYTHONPATH=package/backend pytest package/backend/tests/test_detection_service.py -k "tier or score" -v`
Expected: PASS

- [ ] **Step 5: Commit the scoring work**

```bash
git add package/backend/app/services/detection_service.py package/backend/tests/test_detection_service.py
git commit -m "feat: add section and fragment risk scoring"
```

### Task 4: Make Explanations Auditable

**Files:**
- Modify: `package/backend/app/services/detection_service.py`
- Test: `package/backend/tests/test_detection_service.py`

- [ ] **Step 1: Write failing tests for explanation fidelity**

Assert that explanations:
- exist only when a real signal triggered
- reference known signal identifiers or labels
- do not contain free-form unsupported claims

Example:

```python
def test_fragment_explanations_map_to_real_signals():
    explanation = build_fragment_explanation({"connector_density": 0.9}, ["connector_density"])
    assert "连接词" in explanation["summary"]
    assert explanation["signal_keys"] == ["connector_density"]
```

- [ ] **Step 2: Run explanation tests and confirm failure**

Run: `PYTHONPATH=package/backend pytest package/backend/tests/test_detection_service.py -k explanation -v`
Expected: FAIL because current output is not yet constrained to the new explanation contract.

- [ ] **Step 3: Implement rule-bound explanation assembly**

Build short explanation templates from computed signals only.
Each explanation item should include:
- `summary`
- `signal_keys`
- optional human-readable evidence labels

Do not generate verdict language.

- [ ] **Step 4: Re-run explanation tests**

Run: `PYTHONPATH=package/backend pytest package/backend/tests/test_detection_service.py -k explanation -v`
Expected: PASS

- [ ] **Step 5: Commit the explanation layer**

```bash
git add package/backend/app/services/detection_service.py package/backend/tests/test_detection_service.py
git commit -m "feat: add auditable detection explanations"
```

### Task 5: Integrate Optional LLM Signal Without Making It Mandatory

**Files:**
- Modify: `package/backend/app/services/detection_service.py`
- Test: `package/backend/tests/test_detection_service.py`

- [ ] **Step 1: Write failing tests for degraded mode**

Cover:
- report succeeds when `use_llm=False`
- report succeeds when LLM scoring fails
- `report_metadata` records whether LLM signals were used

- [ ] **Step 2: Run degraded-mode tests and confirm failure**

Run: `PYTHONPATH=package/backend pytest package/backend/tests/test_detection_service.py -k "llm or degraded" -v`
Expected: FAIL because the metadata and graceful degradation path are not yet fully explicit.

- [ ] **Step 3: Refine the LLM scoring integration**

Make LLM signals optional side evidence:
- never the sole source of `significant`
- safe fallback to local-only scoring
- explicit metadata such as `llm_used`, `llm_available`, and `model_name`

- [ ] **Step 4: Re-run degraded-mode tests**

Run: `PYTHONPATH=package/backend pytest package/backend/tests/test_detection_service.py -k "llm or degraded" -v`
Expected: PASS

- [ ] **Step 5: Commit the LLM integration changes**

```bash
git add package/backend/app/services/detection_service.py package/backend/tests/test_detection_service.py
git commit -m "feat: harden optional llm detection path"
```

### Task 6: Upgrade The Frontend Report To The MVP Layout

**Files:**
- Modify: `package/frontend/src/components/DetectionReport.jsx`
- Modify: `package/frontend/src/api/index.js`
- Modify: `package/frontend/src/index.css`
- Test: frontend build and manual smoke check

- [ ] **Step 1: Write a UI checklist before editing**

Define the visible blocks:
- summary score block
- distribution block
- section result table
- fragment evidence list
- risk legend and boundary disclaimer

Expected: The component scope is fixed before JSX changes begin.

- [ ] **Step 2: Update the API adapter if payload fields changed**

Keep request parameters minimal and make the response shape explicit in component usage.

- [ ] **Step 3: Refactor `DetectionReport.jsx` to render the new blocks**

Preserve the existing interaction style where practical, but add:
- section-level comparison
- fragment-level evidence rows
- explanation display bound to backend signals
- language that consistently says risk, not proof

- [ ] **Step 4: Run the frontend build**

Run: `cd package/frontend && npm run build`
Expected: PASS

- [ ] **Step 5: Manually smoke-test the report**

Run the local frontend/backend and verify:
- a short but valid academic sample renders a complete report
- sections expand correctly
- fragment evidence appears only when returned
- disclaimer text avoids overclaiming

- [ ] **Step 6: Commit the frontend report work**

```bash
git add package/frontend/src/components/DetectionReport.jsx package/frontend/src/api/index.js package/frontend/src/index.css
git commit -m "feat: add report-first detection ui"
```

### Task 7: Wire The Detection Flow Cleanly Into The Session Detail Page

**Decision:** Detection entry point stays in `SessionDetailPage.jsx` Tab 4 ("AIGC 检测"), not WorkspacePage. WorkspacePage is the text input / optimization launch page and is out of scope for MVP detection.

**Files:**
- Modify: `package/frontend/src/pages/SessionDetailPage.jsx`
- Modify: `package/frontend/src/components/DetectionReport.jsx`
- Test: frontend build and manual session detail smoke check

- [ ] **Step 1: Write a manual workflow checklist**

Verify:
- optimized text from a completed session flows into the detection tab without lossy transformation
- the user sees risk-screening framing before running analysis
- long-text handling still behaves acceptably

- [ ] **Step 2: Update the session detail integration**

Ensure the Tab 4 panel passes the correct final text source into `DetectionReport` and that surrounding copy matches the new product boundary.

- [ ] **Step 3: Re-run the frontend build**

Run: `cd package/frontend && npm run build`
Expected: PASS

- [ ] **Step 4: Manually test the end-to-end session detection flow**

Check:
- navigate to a completed session
- switch to the detection tab
- trigger analysis
- report renders correctly
- retry or second run behavior

- [ ] **Step 5: Commit the workflow integration**

```bash
git add package/frontend/src/pages/SessionDetailPage.jsx package/frontend/src/components/DetectionReport.jsx
git commit -m "feat: integrate detection report into session detail tab"
```

### Task 8: Add Small-Data Calibration Documentation

**Files:**
- Create: `docs/detection/dataset_notes.md`
- Modify: `README.md`
- Test: manual doc review

- [ ] **Step 1: Write the seed dataset note**

Document:
- seed dataset composition
- weak-label expansion rules
- human-reviewed validation set rules
- known limits and prohibited claims

- [ ] **Step 2: Update the README detection section**

Add concise product-language guidance:
- self-checking tool
- report-based screening
- not a final adjudicator

- [ ] **Step 3: Re-read the docs for consistency with the spec**

Run: `sed -n '1,220p' docs/detection/dataset_notes.md && sed -n '1,220p' README.md`
Expected: Terminology matches the spec and does not drift into bypass marketing.

- [ ] **Step 4: Commit the documentation updates**

```bash
git add docs/detection/dataset_notes.md README.md
git commit -m "docs: add detection calibration notes"
```

### Task 9: Run Verification Before Declaring The MVP Slice Ready

**Files:**
- Test: `package/backend/tests/test_detection_service.py`
- Test: manual backend route check
- Test: frontend build and smoke verification

- [ ] **Step 1: Run the backend detection tests**

Run: `PYTHONPATH=package/backend pytest package/backend/tests/test_detection_service.py -q`
Expected: PASS

- [ ] **Step 2: Run the existing backend test suite to catch regressions**

Run: `PYTHONPATH=package/backend pytest package/backend/tests/test_task_plan_features.py -q`
Expected: PASS

- [ ] **Step 3: Run the frontend production build**

Run: `cd package/frontend && npm run build`
Expected: PASS

- [ ] **Step 4: Manually call the detection endpoint**

Run the backend locally and submit one Chinese or English academic sample to `/api/detection/analyze`.
Expected: The payload returns the final report contract with document, section, fragment, explanation, and metadata fields.

- [ ] **Step 5: Manually verify the browser flow**

Check the full UI path from workspace text to rendered report.
Expected: The browser experience matches the MVP framing and does not overclaim certainty.

- [ ] **Step 6: Commit any final fixups**

```bash
git add package/backend package/frontend README.md docs/assistant-memory/aigc_detection_dataset_notes.md
git commit -m "feat: deliver aigc detection mvp slice"
```
