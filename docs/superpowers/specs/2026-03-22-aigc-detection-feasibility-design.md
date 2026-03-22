# AIGC Detection Feasibility Design

## Context

The repository owner wants to resume feasibility research for an AIGC detection system after completing the cross-session memory workflow.

The requested discussion scope for this round is ordered and constrained:

1. whether a system is technically feasible
2. whether it has practical value in the target scenario
3. whether it is worth building as an MVP product

The user has now confirmed the target boundary for this design:

- modalities: text only
- languages: Chinese and English
- primary scenario: academic papers and course assignments
- product role: risk screening plus assisted judgment, not final adjudication
- target MVP primary user: students / paper authors
- desired output style: report-oriented, similar in spirit to a CNKI-style AIGC report
- public-facing MVP focus: report-based self-checking; rewriting or bypass functionality is not part of the public product framing

## Goals

- Define a realistic product and technical direction for a first-generation AIGC text detection MVP
- Focus on bilingual academic text self-checking for students
- Produce report-style output with document, section, and fragment-level evidence
- Support practical review decisions through layered risk signals
- Keep the system explainable and tunable

## Non-Goals

- Do not build a multimodal detector in this phase
- Do not position the system as a final authority for academic misconduct decisions
- Do not promise compatibility with or guaranteed passing of any third-party commercial detector
- Do not make rewriting or evasion the public-facing core value proposition
- Do not optimize phase 1 around batch institutional review workflows

## Core Judgments

### 1. Technical Feasibility

The system is technically feasible if it is framed as:

- a risk screening system
- an assisted review system
- a report generator based on multiple evidence signals

It is not technically realistic to treat the first version as a final truth machine for determining whether a paper is AI-written.

This is especially true in academic writing because:

- academic text is naturally formulaic
- bilingual and translated writing introduces ambiguity
- human-edited AI text blurs boundaries
- newer models reduce many older detector signals

### 2. Practical Value

The product has practical value if it produces:

- document-level risk summaries
- section-level risk distributions
- fragment-level highlighted evidence
- concise explanations for why a section is risky

Its value comes from:

- reducing review effort
- helping users find suspicious sections quickly
- making self-checking more concrete before submission

Its value does not come from replacing human judgment.

### 3. MVP Product Value

An MVP is worth building if it is positioned as:

> an academic text AIGC risk self-check and report tool

This is commercially and product-wise more credible than selling the product as:

- guaranteed detector bypass
- guaranteed third-party pass
- one-click humanization

The MVP should serve students first, while keeping a future path open for instructor-side workflows.

## Recommended Product Positioning

### Primary User

- students
- paper authors
- assignment submitters

### Core Job To Be Done

Before submission, the user wants to know:

- overall AIGC risk
- which sections look risky
- which fragments deserve manual revision
- why those fragments are risky

### Product Promise

- report-based self-checking
- risk explanation
- revision prioritization

### Product Promise To Avoid

- guaranteed passing of any institutional detector
- definitive authorship judgment
- covert anti-detection positioning in public messaging

## MVP Functional Scope

The MVP should include these capabilities:

### 1. Text / Document Input

- paste academic text directly
- future extension path for `docx` and `pdf`

Phase 1 input contract:

- primary input mode: pasted plain text
- maximum input size for MVP planning: 100,000 characters per document
- accepted language mix: Chinese, English, or mixed Chinese-English text
- section detection for pasted text should use explicit headings when present
  - examples: `1.`, `1.1`, `Chapter 1`, `一、`, `（一）`
- if no reliable headings are found, fall back to paragraph groups of bounded length as pseudo-sections
- sentence segmentation should be language-aware:
  - Chinese punctuation-aware splitting
  - English punctuation-aware splitting
  - mixed-language text handled in a single pipeline with Unicode-safe rules

### 2. Document-Level Risk Score

- one overall AIGC risk score
- one confidence-like summary indicator for user orientation

### 3. Section-Level Risk Distribution

- chapter or section risk values
- visual comparison across the document

### 4. Fragment-Level Highlighting

- highlight suspicious passages
- use three tiers:
  - significant
  - suspected
  - unmarked

### 5. Evidence Explanation

- short explanation per risky fragment
- explanation must be tied to real computed signals, not fabricated natural-language reasoning

### 6. Report Output

- report-like page
- exportable report in a style similar to academic detector result sheets

MVP output contract:

- interactive in-product report page is required
- export format for MVP: HTML report page first, PDF export optional but not required for the first implementation plan
- structured backend output should include:
  - document score
  - section scores
  - fragment spans
  - risk tiers
  - short explanations
- if an API is used internally, JSON should be the canonical machine format and HTML the primary user-facing report format

## Explicitly Deferred Features

- automatic rewriting
- one-click risk reduction
- multimodal detection
- teacher dashboard
- institutional batch review
- third-party pass guarantees

## Recommended Output Structure

The target report structure should be modeled on the observed CNKI-style report pattern, adapted for this product:

### Summary Block

- total risk score
- flagged character count
- total character count
- risk tier explanation

### Distribution Block

- front / middle / rear distribution
- section distribution chart

### Section Result Table

- section name
- section score
- flagged characters / total characters

### Fragment Evidence List

- fragment identifier
- fragment score or risk tier
- short explanation
- original text excerpt

### Risk Legend

- significant
- suspected
- unmarked

## Technical Architecture Recommendation

The recommended MVP architecture is multi-evidence and report-first, not single-model-first.

### Layer 1: Document Parsing

- text ingestion
- Chinese and English normalization
- section splitting
- paragraph splitting
- sentence splitting

### Layer 2: Feature Extraction

The first version should prioritize practical and explainable features:

- stylometric features
  - sentence-length distribution
  - word-length distribution
  - connective usage
  - repetition patterns
- fluency features
  - perplexity
  - burstiness
  - sentence-level variance
- structure features
  - section regularity
  - template-like discourse patterns
  - transition consistency
- local anomaly features
  - fragments whose style differs sharply from surrounding text

Runtime constraint for MVP planning:

- MVP should assume local inference first where practical
- avoid a design that depends on expensive per-request third-party APIs for every scoring step
- if a language-model-dependent feature is used, prefer one clearly named local or self-hostable model family in the implementation plan rather than leaving model choice open

Perplexity / burstiness planning assumption:

- the implementation plan must choose one concrete scoring model path
- acceptable MVP choices:
  - one local bilingual-friendly causal language model for both languages
  - or one Chinese-oriented model plus one English-oriented model with language routing
- MVP should not assume a proprietary paid API unless explicitly chosen later

### Layer 3: Risk Scoring

- document-level score
- section-level score
- fragment-level score
- dual-threshold logic for `significant` and `suspected`

Scoring contract for MVP planning:

- all risk scores should be normalized to `0-100`
- fragment score is the most local signal
- section score aggregates fragment and section-level features for that section
- document score aggregates section-level and whole-document features
- risk tiers should be threshold-based:
  - `significant`
  - `suspected`
  - `unmarked`
- the implementation plan must define provisional thresholds, but the product should treat them as configurable calibration values rather than fixed constants forever
- “confidence-like” summary means a user-facing certainty hint derived from score separation and signal agreement, not a claim of statistical certainty

### Layer 4: Explanation Generation

- rule-bound short explanations
- explanations must map back to measured features

### Layer 5: Reporting

- report rendering
- export support

## Implementation Route Options

### Option A: Rules + Statistical Features + Lightweight Ensemble

Approach:

- hand-designed bilingual academic-writing features
- perplexity and burstiness features
- ensemble scoring with XGBoost or LightGBM

Training assumption for MVP planning:

- MVP should not assume the team already owns a large labeled dataset
- MVP may use a small supervised fusion model only if a compact but reviewed labeled set can be assembled quickly from acceptable sources
- if that dataset is not ready, the implementation plan should define:
  - phase 1a: rule-weighted scoring baseline
  - phase 1b: lightweight trained fusion model after a seed dataset is assembled

Acceptable data sources for MVP planning:

- public human-vs-AI text datasets where licensing permits use
- internally generated bilingual academic-style samples
- small manually reviewed seed sets for threshold calibration
- weakly labeled samples whose source is known and whose noise level is documented
- the implementation plan must explicitly state whether MVP launches with:
  - rule-based fusion only
  - or lightweight supervised fusion with a defined training set

Pros:

- strongest explainability
- easiest threshold tuning
- fastest MVP path
- naturally suited to report generation

Cons:

- limited performance ceiling
- weaker long-term robustness against adversarial rewriting

### Option B: Supervised Classifier + Explanation Layer

Approach:

- train a bilingual academic-text detector
- add separate interpretation and section/fragment scoring layers

Pros:

- stronger long-term learning potential
- easier to improve with new data

Cons:

- explanation quality is less natural in v1
- higher dataset dependency

### Option C: Hybrid Production-Oriented Architecture

Approach:

- combine rule features
- statistical features
- supervised model output
- fragment-level anomaly scoring

Pros:

- best long-term production path
- strongest chance of balancing accuracy and explainability

Cons:

- too heavy for a clean MVP

## Recommended Technical Route

Use Option A for the MVP, while preserving an upgrade path toward Option C.

That means:

- MVP detection core: rules + statistical features + lightweight ensemble model
- MVP product form: report-style self-check tool
- future upgrade path: supervised and hybrid detectors

This recommendation matches the user's priorities:

- explainability
- practical delivery speed
- report quality
- risk-tiered output

## Success Criteria

The MVP is successful when:

- users can identify high-risk sections quickly
- fragment-level highlights are useful enough to prioritize manual revision
- the report feels credible and structured, not like a generic score page
- obvious AI-direct or weakly edited samples are consistently surfaced
- clearly human-written samples are not broadly over-flagged
- thresholds are adjustable enough for iterative calibration

## Data Strategy For A Small-Data MVP

The MVP should be planned as a small-data cold-start system, not as a large-data detector platform.

That means the first version should optimize for:

- explainable risk screening
- useful fragment ranking
- threshold calibration on a compact reviewed set
- gradual improvement as reviewed samples accumulate

Recommended dataset structure for MVP planning:

### Tier 1: Seed Dataset

A small but clean bilingual academic-style seed set used for initial calibration and early validation.

Suggested composition:

- real human-written academic text samples
- direct AI-generated academic-style samples
- AI-generated then manually edited samples
- both Chinese and English coverage

Planning assumption:

- a seed dataset in the low hundreds of samples is acceptable for MVP planning
- quality and scenario fit matter more than raw scale at this stage

### Tier 2: Weakly Labeled Expansion Set

A larger but noisier set used to improve heuristics, inspect score distributions, and optionally train a lightweight fusion model.

Acceptable weak labels include:

- samples generated internally from known models
- samples from known human-written sources
- samples whose generation path is recorded even if not fully span-annotated

Guardrail:

- weakly labeled data should not be treated as gold-standard evaluation data

### Tier 3: Human-Reviewed Validation Set

A compact holdout set reserved for acceptance decisions.

Requirements:

- must not be used as the primary tuning set
- should include Chinese, English, and mixed-difficulty cases
- should include:
  - obvious AI-direct text
  - lightly edited AI text
  - clearly human-written text
  - edge cases that are formal, templated, or translation-heavy

## Evaluation And Acceptance Approach

Evaluation for MVP should favor practical report usefulness over headline accuracy claims.

The system should be evaluated at three levels:

### 1. Document-Level Screening

Measure whether the overall document risk is directionally useful for self-checking.

Priority:

- high precision on `significant`
- acceptable recall on obvious AI-direct text
- controlled false positives on clearly human-written academic text

### 2. Section / Fragment Ranking

Measure whether the report surfaces the right places for manual review.

Priority:

- high-risk sections appear near the top of the report
- top-ranked suspicious fragments are frequently judged worth reviewing by a human reader
- lightly edited AI text is surfaced as `suspected` when stronger proof is not available

### 3. Explanation Fidelity

Measure whether report explanations correspond to real triggered signals.

Requirement:

- explanations must be traceable to computed features, anomaly signals, or model outputs
- the system must avoid fabricated natural-language justifications

Evaluation baseline for MVP planning:

- define a held-out bilingual academic-style validation set
- report separate Chinese and English results
- keep a distinct human-reviewed acceptance set
- include at least:
  - obvious AI-direct samples
  - lightly edited AI samples
  - clearly human-written samples
  - formal academic edge cases likely to trigger false positives
- the implementation plan must define measurable provisional targets such as:
  - acceptable false-positive tolerance on clearly human-written samples
  - usable recall on obvious AI-direct samples
  - acceptable reviewer agreement that top flagged fragments are worth inspection
- success for MVP should be judged by usefulness for self-checking, not by perfect authorship attribution

Acceptance should be framed as product-readiness, not scientific finality.

Recommended MVP acceptance framing:

- the report consistently helps users find suspicious sections faster
- the `significant` tier is conservative and credible
- the `suspected` tier is useful for manual follow-up without overstating certainty
- the system does not broadly over-flag normal academic writing
- the report explanation layer remains auditable

## MVP Interfaces

The implementation plan should assume a minimal product-facing interface set:

- one analysis submission path
- one analysis result retrieval path or synchronous result payload
- one report-rendering path

Canonical machine output should include:

- `document_score`
- `document_tier`
- `sections[]`
- `fragments[]`
- `explanations[]`
- `report_metadata`

Each fragment record should minimally include:

- source text span or stable index
- section identifier
- score
- tier
- explanation

## Privacy And Retention Constraints

Because the primary user is students submitting academic text:

- MVP should minimize retained raw text by default
- the implementation plan must define whether uploaded text is stored, cached temporarily, or processed ephemerally
- raw text should not be logged in application logs
- any retained report artifact should be explicitly scoped and documented

## Performance Constraints

For MVP planning, assume:

- target single-document analysis latency: within tens of seconds, not minutes
- target document size: up to 100,000 characters
- report generation should be fast enough for interactive self-checking use, not overnight batch processing

## Risks And Constraints

### Risk: Overclaiming Detection Authority

If the product implies final authorship judgment, trust and usability will collapse under ambiguous edge cases.

Control:

- position the product as self-checking and assisted judgment
- avoid final-authority claims
- avoid UI copy that implies proof of cheating, plagiarism, or misconduct
- require the report language to describe risk and evidence, not verdicts

### Risk: Academic Writing False Positives

Academic writing is naturally more regular and formal than general prose.

Control:

- calibrate specifically on academic corpora
- tune thresholds by scenario
- keep explanations visible
- keep the `significant` tier conservative
- allow future calibration by assignment type, language, and document genre

### Risk: Bilingual Variability

Chinese and English academic writing show different structural and stylistic signals.

Control:

- keep language-aware preprocessing
- evaluate language-specific feature behavior
- avoid assuming a single threshold will be equally reliable across languages
- preserve a path for language-routed scoring and calibration

### Risk: Product Drift Toward Evasion

The market may pressure the product toward bypass positioning.

Control:

- keep public positioning focused on self-checking and report interpretation
- defer rewriting features from public MVP scope

### Risk: Small-Data Miscalibration

With a limited seed dataset, thresholds and weights can appear stable during development while failing on new subjects or writing styles.

Control:

- treat early thresholds as provisional
- preserve score distributions for later calibration analysis where policy permits
- keep acceptance standards tied to reviewed validation sets
- avoid marketing claims that exceed the observed evaluation scope

### Risk: Explanation Overreach

Users may interpret natural-language explanations as factual proof even when they are only summaries of risk signals.

Control:

- generate explanations only from known triggered signals
- ban free-form speculative explanation generation in MVP
- ensure each explanation can be traced to a concrete feature, anomaly, or model score

### Risk: Privacy And Academic Sensitivity

Submitted academic text may contain unpublished work, assignments, personal data, or institution-specific material.

Control:

- minimize retained raw text by default
- do not log raw document contents in routine application logs
- define explicit retention windows if temporary storage is required
- make any saved report artifact scope and lifetime visible to the user

## Product Boundary And Compliance Guardrails

The MVP must operate within a narrow product and language boundary.

### Product Boundary

The product should be framed as:

- an academic text self-check tool
- a risk-screening report generator
- an aid for revision prioritization and manual review

The product should not be framed as:

- a disciplinary adjudication system
- a cheating proof generator
- a guaranteed pass predictor for any third-party detector
- a public bypass or anti-detection tool

### Output Language Guardrails

All user-facing result language should remain probabilistic and evidence-based.

Preferred framing examples:

- high AIGC risk
- suspected AI-like fragment
- section requires manual review
- risk signals were detected in this passage

Framing to avoid:

- this paragraph was definitely written by AI
- this user cheated
- this report proves misconduct
- this document will fail a university detector

### Decision Guardrails

The MVP should not produce irreversible or punitive downstream actions by itself.

That means:

- no automatic academic penalty recommendation
- no automatic submission blocking based solely on the score
- no institution-facing final verdict workflow in MVP

### Data And Retention Guardrails

The implementation plan must define:

- whether analysis is ephemeral, cached, or persisted
- what fields are retained in logs
- how reports are stored or deleted
- whether users can remove their submitted text and result artifacts

Default preference for MVP:

- retain derived scores and minimal metadata where possible
- avoid retaining raw text unless the workflow clearly requires it

### Model And Claim Guardrails

The system must not claim universality it has not earned.

That means the MVP should avoid claims such as:

- detects all AI-generated text
- works equally well for every subject and language
- identifies the exact model that wrote the text
- matches or predicts external detector outcomes

Allowed claim style:

- designed for bilingual academic-text risk screening
- optimized for report-based self-checking
- intended to support human review, not replace it

## Recommended MVP Governance Posture

For the first version, governance should stay lightweight but explicit.

Minimum governance expectations:

- maintain versioned threshold settings
- record which signal families contributed to each report
- keep a changelog for scoring logic revisions
- re-run validation after material threshold or feature changes
- document known failure modes in product and internal docs

## Recommended Next Step

Write an implementation plan for the MVP focused on:

- product-level report design
- bilingual academic text preprocessing
- first-pass feature set
- risk scoring pipeline
- report generation flow
