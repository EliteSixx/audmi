# AudMi: Auditor's Microscope

**Supervisory Analytics for SOC Assessment** · SIH26157 (SAT-SA) · NTRO · Team Elite Six

AudMi is an offline-first supervisory analytics tool designed to help human examiners assess the operational capabilities of Security Operations Centres (SOCs) through periodic alert and case-management submissions.

It aims to surface evidence-backed operational gaps, identify potentially missing evidence, and help examiners prioritize records for manual review.

AudMi is not a SIEM, a real-time SOC, a SOC replacement, or a monitoring platform. It does not independently determine compliance or declare an entity at fault. Its outputs are potential supervisory signals that require human examination.

> **Guiding principle:** AudMi does not replace the examiner. It helps the examiner see where to look.

## Current Status

AudMi is a research prototype developed for Smart India Hackathon 2026. All demonstration and testing data is synthetic. No real NCIIPC or Critical Sector Entity (CSE) data is used.

The current repository contains the evidence model, synthetic dataset generator v2, four registry-driven analytics rules, an ingestion/data-quality and SHA-256 integrity layer, an offline loopback JSON API, and a web application with both a fixture demo and a live findings screen.

| Component | Status |
|---|---|
| Canonical evidence model and JSON schema | Implemented and tested |
| Deterministic synthetic dataset generator v2 (realistic baselines, decoys, peer groups) | Implemented and tested |
| Execution-gap analytics (3 registry-driven rules) | Implemented and tested |
| Negative-space analytics (silent high-value assets vs peer group) | Implemented and tested |
| Finding schema v1 and Sigma-like rule registry | Implemented and tested |
| Submission ingestion, data-quality report and SHA-256 manifest | Implemented and tested |
| Offline loopback JSON API | Implemented and tested |
| Live findings screen reading the API | Implemented and tested (`/live`) |
| Peer and contextual analysis (beyond alert volume) | Planned |
| Workflow pattern analysis | Planned |
| External SOC CSV import and persistent storage | Planned |
| Evidence-linked prioritization and review write-actions | Planned |
| Ground-truth-based precision and recall evaluation | Implemented and tested (synthetic data only; read the caveats in `docs/PROJECT_CONTEXT.md` §5.4) |
| Offline packaging and air-gapped verification | Planned (a static offline guard exists) |
| Next.js web demonstration | Implemented with mock synthetic data (`/demo`) and live API data (`/live`) |

**Deployment goal:** Local, controlled, offline operation without dependence on cloud services or external AI APIs. The product code makes no outbound calls and `scripts/check_offline.py` guards that, but a full air-gapped installation has not yet been verified.

## Repository Structure

```text
audmi/
├── data/
│   ├── schemas/
│   │   └── core-evidence.schema.json
│   └── synthetic/
│       ├── generator.py
│       └── golden_dataset/
│           ├── cse.json
│           ├── assets.json
│           ├── alerts.json
│           ├── cases.json
│           ├── investigations.json
│           ├── escalations.json
│           ├── remediations.json
│           ├── ground_truth.json
│           └── dataset_manifest.json
├── src/
│   ├── normalization/
│   │   └── evidence_model.py
│   ├── analytics/
│   │   ├── common.py
│   │   ├── execution_gaps.py
│   │   └── negative_space.py
│   ├── ingestion/
│   │   ├── quality.py
│   │   └── manifest.py
│   ├── api/
│   │   └── server.py
│   ├── evidence/
│   ├── explainability/
│   ├── prioritization/
│   ├── review/
│   └── validation/
├── rules/
│   ├── missing_escalation.yaml
│   ├── unusually_short_investigation.yaml
│   ├── repeated_alerts_without_remediation.yaml
│   └── negative_space_low_activity.yaml
├── scripts/
│   └── check_offline.py
├── .github/
│   └── workflows/
│       └── ci.yml
├── tests/
│   ├── test_evidence_model.py
│   ├── test_synthetic_generator.py
│   ├── test_execution_gaps.py
│   ├── test_negative_space.py
│   ├── test_ingestion.py
│   ├── test_api.py
│   ├── test_registry.py
│   └── test_evaluate.py
├── web/
│   └── Next.js application (`/demo` fixtures, `/live` API-backed)
├── docs/
│   ├── ARCHITECTURE.html
│   └── AudMi_Architecture.pdf
├── README.md
└── requirements.txt
```

Some directories are scaffolding for planned functionality. Their presence does not mean the corresponding features are implemented.

## Canonical Evidence Model

AudMi uses seven identifier-linked entities to represent SOC operational records:

| Entity | Purpose |
|---|---|
| CSE | Represents the assessed Critical Sector Entity |
| Asset | Represents an asset associated with an entity |
| Alert | Represents a security alert |
| Case | Represents a case associated with SOC activity |
| Investigation | Represents investigation activity for a case |
| Escalation | Represents an escalation record |
| Remediation | Represents a remediation action or record |

The relationships between these entities provide the basis for examining operational workflows and identifying potential execution gaps.

For example, a case without an associated escalation record may warrant review. However, the absence of a record is not automatically proof that the escalation did not occur. The interpretation depends on the available data, expected workflow, and applicable rules.

## Synthetic Validation Dataset

The repository includes a deterministic synthetic dataset for development and testing.

The dataset generated with seed `42` contains **14,730 operational records**:

| Record type | Expected count |
|---|---:|
| CSEs | 6 |
| Assets | 300 |
| Alerts | 10,000 |
| Cases | 2,000 |
| Investigations | 1,500 |
| Escalations | 664 |
| Remediations | 260 |

Two further files sit beside the operational data: `ground_truth.json` (the seeded labels) and `dataset_manifest.json` (generator version, periods, sectors and peer groups).

Generator v2 deliberately makes detection non-trivial: high/critical cases are escalated at roughly 80% per entity (CSE-02 is deliberately weak at ~50%), investigation durations overlap between normal and planted fast cases, 40 legitimate fast decoys exist below the rule's threshold, and remediated decoys are volume-matched to the repeated-alert cases. v1's disjoint distributions made the rules look perfect for the wrong reason.

The operational files carry no labels. `ground_truth.json` is separate, so rules cannot read the answers while analysing the records.

The ground-truth file defines seeded test conditions for:

- [x] Missing escalation records
- [x] Repeated alerts without remediation
- [x] Unusually short investigations
- [x] Critical assets exhibiting low activity (negative space)

These conditions provide known scenarios for testing supervisory analytics. The ground-truth references are not a complete record-level labelling of the operational dataset, and synthetic detection numbers are not real-world accuracy figures.

## Setup and Installation

The instructions below explain how to run the **currently implemented Python prototype** and, optionally, the web interface locally. They do not install the complete planned offline product.

### Prerequisites

For the Python prototype:

- Git
- Python 3.11 or later
- A terminal or command prompt

For local web development:

- Node.js
- npm
- A modern web browser

The analytics and generator use the Python standard library plus **PyYAML** (to read `rules/*.yaml`). Install the pinned requirements before running:

### 1. Clone the Repository

```bash
git clone https://github.com/EliteSixx/audmi.git
cd audmi
```

Verify that Python is installed:

```bash
python --version
```

On Windows, if `python` is not recognized, try:

```powershell
py --version
```

Use the Python command available on your system in the remaining steps.

### 2. Generate the Synthetic Dataset

A generated dataset is already included in the repository. Regeneration is optional.

To regenerate it using seed `42`, run the following command from the repository root:

```bash
python -m data.synthetic.generator --seed 42
```

The generated records are stored in:

```text
data/synthetic/golden_dataset/
```

The generator creates linked synthetic records and seeded conditions for testing the evidence model and analytics.

**Note:** Regenerating the dataset may overwrite the existing generated records. Preserve any local changes you need before running the generator.

### 3. Validate the Submission and Run the Analytics

Ingestion runs first. It validates every row, reports data-quality problems, and writes a SHA-256 manifest without changing the evidence:

```bash
python -m src.ingestion
```

Outputs go to `data/outputs/quality_report.json` and `data/outputs/submission_manifest.json`. The combined digest is reproducible with standard `sha256sum`-style output.

Then run the rules:

```bash
python -m src.analytics.execution_gaps
```

The module reports potential signals for supported conditions:

- Cases with missing escalation records
- Investigations with unusually short durations
- Repeated alerts without corresponding remediation records
- Critical/high assets with no alerts while their peer group is active (negative space)

The output represents rule-based signals on synthetic data. It is not a set of confirmed incidents, proof of non-compliance, or a measurement of real-world detection accuracy.

To score the rules against the seeded ground truth:

```bash
python -m src.validation.evaluate
```

This prints a per-rule, per-cohort table and writes `data/outputs/eval_report.json`. Flags outside ground truth are reported as *unclassified*, not as false positives, and precision is a lower bound.

### 4. Start the Offline API

The API uses the Python standard library and binds to loopback only:

```bash
python -m src.api --port 8000
```

It exposes `/health`, `/summary`, `/entities`, `/findings`, `/findings/{id}` and `/findings/{id}/evidence`. It reads only the local evidence directory and makes no outbound calls.

### 5. Run the Tests

Install `pytest` if necessary:

```bash
python -m pip install pytest
```

Run the test suite from the repository root:

```bash
python -m pytest -v
```

The tests cover the evidence model, generated dataset, all four rules, the rule registry, the evaluation harness, ingestion/manifest behaviour, and the API.

To check that no product code reaches the network:

```bash
python scripts/check_offline.py
```

### 6. Access the Web Application

The hosted Vercel deployment is the primary demonstration interface for evaluation. Use the deployment URL supplied with the SIH submission.

The web application has two modes:

- **`/demo`** — the full examiner journey on illustrative fixtures from `web/app/data/mock-data.ts`. It needs no backend.
- **`/live`** — server-rendered findings computed by the Python engine and read from the local API. Start `python -m src.api --port 8000` first. If the API is down, the page explains how to start it.

To run the web interface locally for development:

```bash
cd web
npm install
npm run dev
```

Open the address printed by Next.js, normally:

```text
http://localhost:3000
```

With the API running, open `http://localhost:3000/live`. Set `AUDMI_API_URL` if the API is on a different loopback port.

To check whether the frontend can produce a production build:

```bash
npm run build
```

`/live` is dynamic, so the build succeeds without the API running. These commands do not install a packaged, air-gapped product.

## Planned Final Product Deployment

This section describes the intended deployment architecture and workflow. The complete workflow is not yet implemented, so these are design goals rather than production installation instructions.

### 1. Deployment Environment

The target is a locally hosted Linux workstation or server operating in a controlled environment.

The final product is intended to operate without internet access, cloud services, SaaS dependencies, or external AI APIs. The core analytics must remain usable without a language model.

The final operating-system support, runtime versions, infrastructure requirements, and packaging method will be determined during implementation and testing.

### 2. Application Components

The planned installation package is expected to include:

- Supervisory analytics backend
- Canonical evidence model and schema validation
- Data ingestion and normalization pipeline
- Deterministic analytics and versioned rule configuration
- Local storage and evidence traceability
- Review interface and findings export workflow
- Versioned application configuration and audit records

Containerized deployment using Docker Compose is a candidate approach. The final container configuration, dependencies, and installation commands have not yet been finalized.

### 3. Data Ingestion and Validation

The current prototype validates canonical JSON submissions and produces a data-quality report plus a SHA-256 manifest before analysis. CSV import with a column-mapping file and a persistent store (SQLite or DuckDB) are planned.

Incoming records are mapped to the canonical evidence model. Validation checks:

- Required fields and data types
- Identifiers and entity relationships
- Timestamp formats and consistency
- Schema compatibility
- Missing or incomplete records

Invalid or incomplete submissions generate a validation report rather than silently entering the analytics pipeline. Malformed rows are counted and listed, never repaired or dropped silently.

Missing records must be interpreted in context. AudMi should distinguish between evidence that is genuinely absent and evidence that was not supplied in the input dataset.

Additional database or API integrations will be introduced where required and supported by the deployment environment.

### 4. Supervisory Analytics

The planned analytics workflow will process validated submissions using deterministic, explainable methods.

**Execution-gap analysis**

Identifies potentially missing or incomplete workflow steps. The initial implementation already includes rules for missing escalation records, unusually short investigations, and repeated alerts without corresponding remediation records.

**Negative-space analysis**

Identifies expected evidence or telemetry that is absent. The current rule flags critical/high assets with zero alerts while their CSE peer group is active. ATT&CK-tactic coverage and whole-period checks remain planned.

**Workflow pattern analysis**

Intended to surface repeated or potentially templated investigation patterns for human review.

**Peer and contextual analysis**

Intended to compare entities where sufficient, comparable data is available. Comparisons must account for differences in data coverage and operational context.

**Evidence-linked prioritization**

Intended to organize potential signals for manual review and preserve references to supporting records and the rules that generated them.

Execution-gap analytics and one negative-space rule are implemented in the current prototype. Workflow-pattern, broader peer/contextual, and prioritization capabilities remain planned.

### 5. Findings Review and Export

The planned review workflow will allow an examiner to inspect a potential signal, review its supporting evidence, and decide whether further investigation is warranted.

The intended findings format will retain relevant evidence references, rule identifiers, timestamps, and traceable analysis outputs.

Offline export and exchange packaging are also planned.

AudMi is designed to support human judgment. It will not independently declare an entity compliant or non-compliant.

### 6. Offline Deployment Verification

Air-gapped readiness will be claimed only after the packaged application has been installed and tested in an isolated environment with network access disabled.

Verification should establish that:

- Required dependencies are available locally.
- The application starts without contacting external services.
- Supported local submissions can be processed.
- Analytics and evidence references remain available offline.
- Findings can be reviewed and exported without cloud services.
- Any optional local language model operates without external API calls.

Performance, detection accuracy, and offline readiness will be reported only after the corresponding tests have been completed and documented.

## Architecture Documentation

The architecture document describes the intended system design, including data ingestion, evidence normalization, supervisory analytics, findings traceability, and the planned controlled deployment environment.

- [Architecture diagram and document (HTML)](docs/ARCHITECTURE.html)
- [Architecture document (PDF)](docs/AudMi_Architecture.pdf)

The architecture describes the target design. Components marked as planned should not be interpreted as implemented functionality.

## Limitations

- The repository is a research prototype, not a complete production deployment.
- The web application's `/demo` screen uses mock synthetic data; `/live` does execute the Python analytics through the local API.
- Execution-gap analytics and one negative-space rule are implemented. Broader negative-space, peer/contextual, workflow-pattern, and prioritization capabilities remain planned.
- Canonical JSON ingestion and integrity hashing are implemented; CSV import and persistent storage remain planned.
- Detection thresholds have been measured against synthetic ground truth, not real SOC data.
- Synthetic precision and recall figures are available in `docs/PROJECT_CONTEXT.md` §5.4, but no real-world accuracy figures exist.
- Offline product code is guarded by `scripts/check_offline.py`; full air-gapped operation has not yet been verified.
- Potential signals require human review and must not be treated as definitive findings of fault.

## Team

**Team Elite Six**

Smart India Hackathon 2026  
Problem Statement: SIH26157  
Theme: Blockchain & Cybersecurity  
Organization: NTRO