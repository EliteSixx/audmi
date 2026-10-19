# AudMi: Auditor's Microscope

**Supervisory Analytics for SOC Assessment** · SIH26157 (SAT-SA) · NTRO · Team Elite Six

AudMi is an offline-first supervisory analytics tool designed to help human examiners assess the operational capabilities of Security Operations Centres (SOCs) through periodic alert and case-management submissions.

It aims to surface evidence-backed operational gaps, identify potentially missing evidence, and help examiners prioritize records for manual review.

AudMi is not a SIEM, a real-time SOC, a SOC replacement, or a monitoring platform. It does not independently determine compliance or declare an entity at fault. Its outputs are potential supervisory signals that require human examination.

> **Guiding principle:** AudMi does not replace the examiner. It helps the examiner see where to look.

## Current Status

AudMi is a research prototype developed for Smart India Hackathon 2026. All demonstration and testing data is synthetic. No real NCIIPC or Critical Sector Entity (CSE) data is used.

The current repository contains the evidence model, synthetic dataset generator, execution-gap analytics, and a web demonstration. The complete end-to-end offline product is still under development.

| Component | Status |
|---|---|
| Canonical evidence model and JSON schema | Implemented and tested |
| Deterministic synthetic dataset generator | Implemented and tested |
| Execution-gap analytics | Implemented and tested |
| Negative-space analytics | Planned |
| Peer and contextual analysis | Planned |
| Workflow pattern analysis | Planned |
| External SOC data ingestion and validation | Planned |
| Evidence-linked prioritization and review workflow | Planned |
| Ground-truth-based precision and recall evaluation | Planned |
| Offline packaging and air-gapped verification | Planned |
| Next.js web demonstration | Implemented with mock synthetic data |

**Deployment goal:** Local, controlled, offline operation without dependence on cloud services or external AI APIs. Air-gapped operation has not yet been verified.

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
│   │   └── execution_gaps.py
│   ├── ingestion/
│   ├── evidence/
│   ├── explainability/
│   ├── prioritization/
│   ├── review/
│   └── validation/
├── tests/
│   ├── test_evidence_model.py
│   ├── test_execution_gaps.py
│   └── test_synthetic_generator.py
├── web/
│   └── Next.js demonstration application
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

The dataset generated with seed `42` contains:

| Record type | Expected count |
|---|---:|
| CSEs | 6 |
| Assets | 300 |
| Alerts | 10,000 |
| Cases | 2,000 |
| Investigations | 1,500 |
| Escalations | 300 |
| Remediations | 100 |

The dataset includes seeded conditions and a separate `ground_truth.json` file containing expected labels.

This separation is intended to support future evaluation of detection performance without placing ground-truth labels directly into the operational records being analyzed.

The counts describe the configured synthetic dataset, not real-world SOC activity or supervisory findings.

AudMi includes a reproducible synthetic dataset generated with seed 42, comprising 14,206 operational records across six Critical Sector Entities (CSEs).

The accompanying ground-truth file defines seeded test conditions for:

- [ ] Missing escalation records
- [ ] Repeated alerts without remediation
- [ ] Unusually short investigations
- [ ] Critical assets exhibiting low activity

These conditions provide known scenarios for testing supervisory analytics. The ground-truth references are not a complete record-level labelling of the operational dataset, and detection accuracy has not yet been established.

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

The existing Python modules use the standard library. No additional Python packages are required to run the implemented generator and analytics module.

### 1. Clone the Repository

```bash
git clone https://github.com/rudythetechy/audmi.git
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

### 3. Run the Execution-Gap Analytics

The current implementation supports deterministic execution-gap analysis.

Run the module from the repository root:

```bash
python -m src.analytics.execution_gaps
```

The module reports potential signals for supported conditions, including:

- Cases with missing escalation records
- Investigations with unusually short durations
- Repeated alerts without corresponding remediation records

The output represents rule-based signals on synthetic data. It is not a set of confirmed incidents, proof of non-compliance, or a measurement of detection accuracy.

Rule thresholds and detection performance still require systematic evaluation against the synthetic ground truth.

### 4. Run the Tests

Install `pytest` if necessary:

```bash
python -m pip install pytest
```

Run the test suite from the repository root:

```bash
python -m pytest -v
```

The tests cover the evidence model, execution-gap analytics, and synthetic dataset generator.

### 5. Access the Web Demonstration

The hosted Vercel deployment is the primary demonstration interface for evaluation. Use the deployment URL supplied with the SIH submission.

The web demonstration uses mock synthetic data. It is a separate frontend and does not currently execute the Python analytics modules.

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

To check whether the frontend can produce a production build:

```bash
npm run build
```

These commands build or run the web interface only. They do not install the complete supervisory analytics backend or establish offline operation.

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

The planned ingestion layer will initially target periodic SOC submissions in CSV and JSON formats.

Incoming records will be mapped to the canonical evidence model. Validation is intended to check:

- Required fields and data types
- Identifiers and entity relationships
- Timestamp formats and consistency
- Schema compatibility
- Missing or incomplete records

Invalid or incomplete submissions should generate a validation report rather than silently entering the analytics pipeline.

Missing records must be interpreted in context. AudMi should distinguish between evidence that is genuinely absent and evidence that was not supplied in the input dataset.

Additional database or API integrations will be introduced where required and supported by the deployment environment.

### 4. Supervisory Analytics

The planned analytics workflow will process validated submissions using deterministic, explainable methods.

**Execution-gap analysis**

Identifies potentially missing or incomplete workflow steps. The initial implementation already includes rules for missing escalation records, unusually short investigations, and repeated alerts without corresponding remediation records.

**Negative-space analysis**

Intended to identify expected evidence or telemetry that is absent, where the available data supports that conclusion.

**Workflow pattern analysis**

Intended to surface repeated or potentially templated investigation patterns for human review.

**Peer and contextual analysis**

Intended to compare entities where sufficient, comparable data is available. Comparisons must account for differences in data coverage and operational context.

**Evidence-linked prioritization**

Intended to organize potential signals for manual review and preserve references to supporting records and the rules that generated them.

Only execution-gap analytics are implemented in the current prototype. The other capabilities remain planned.

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
- The web demonstration uses mock synthetic data and does not execute the Python analytics.
- Only the execution-gap analytics module is currently implemented.
- Negative-space, peer/contextual, workflow-pattern, and prioritization capabilities remain planned.
- External SOC data ingestion and the complete review workflow remain planned.
- Detection thresholds have not been fully validated against ground truth.
- No verified precision, recall, or production performance figures are available.
- Offline and air-gapped operation has not yet been verified.
- Potential signals require human review and must not be treated as definitive findings of fault.

## Team

**Team Elite Six**

Smart India Hackathon 2026  
Problem Statement: SIH26157  
Theme: Blockchain & Cybersecurity  
Organization: NTRO