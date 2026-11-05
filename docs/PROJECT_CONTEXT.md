# AudMi — Project Context

> Read this first. It explains what AudMi is, what is actually built, how it works, what we measured, and where we are going.
> Verified on **5 Nov 2026** against `develop` (`0392086`, five commits ahead of `main`). `main`, `origin/main` and `phase0/base` are at `9872743`; `develop` carries P0–P4 and will be fast-forwarded into `main` at the phase-end merge. If you change anything listed under "Implemented", update this file in the same PR.

**AudMi (Auditor's Microscope)** — SIH 2026, Problem Statement SIH26157, *Supervisory Analytics Tool for SOC Assessment (SAT-SA)*, NTRO / NCIIPC. Team Elite Sixx.

*"Inspect the evidence. Surface the gaps. Prioritize the review."*
*AudMi does not replace the examiner. It helps the examiner see where to look.*

---

## 1. The problem in one story

NCIIPC supervises the SOCs of Critical Sector Entities (CSEs): power, banking, telecom and so on. Every CSE sends in reports saying its SOC works well: high closure rates, healthy escalation numbers. Experts know the reports can look fine while the **underlying records** show problems. A critical alert might be closed in 40 seconds, a case might never be escalated, or a critical server might have produced no alerts at all for a year.

Today examiners find these problems by **manually sampling** records, which doesn't scale. AudMi reads the periodic submissions (alerts, cases, investigations, escalations, remediations, asset inventory). It runs explainable checks and gives the examiner a **ranked list of findings**, each linked to the exact records behind it. The examiner decides what it means.

AudMi is **not** a SOC, SIEM or SOAR. It doesn't monitor anything live. It sits **one level above the SOC** and asks whether the evidence supports what the SOC claims.

## 2. Two kinds of weakness we look for

| Type | Meaning | Examples |
|---|---|---|
| **Execution gap** | The paperwork says the control works, but the records say otherwise | Critical case with no escalation; 30-second "investigations"; same asset alerting 50 times with no fix |
| **Negative space** | Evidence that *should* exist doesn't | Critical server with zero alerts; no identity alerts at a bank; no escalations at all in a quarter |

## 3. Status board — the three categories

Every feature is in exactly one of these. **Never present a feature from row 1 or 3 as if it were in row 2.**

| | Category | What's in it |
|---|---|---|
| 1 | **Demonstrated in the UI** (mock data) | Full examiner journey at `/demo` in `web/`: entity overview, 8 capability views, ranked findings, evidence drill-down, review actions. Everything reads from `web/app/data/mock-data.ts`. |
| 2 | **Implemented and testable** | Evidence model, evidence JSON schema, synthetic **generator v2** + ground truth, **Finding schema v1** (+ JSON Schema), **Sigma-like rule registry** (`rules/*.yaml`), **4 rules** (3 execution-gap + 1 negative-space), **evaluation harness** (`python -m src.validation.evaluate`), **submission ingestion** with data-quality report and SHA-256 manifest (`python -m src.ingestion`), **offline JSON API** (`python -m src.api`), **`/live` UI screen** reading that API, offline guard (`scripts/check_offline.py`), CI workflow, **93 tests**. |
| 3 | **Proposed / not yet integrated** | External SOC CSV/column-mapping import, persistent storage (SQLite/DuckDB), additional rules (critical alerts closed fast, closure bursts, analyst patterns, template/near-duplicate notes), ATT&CK coverage mapping, peer percentiles, review write-actions with an audit log, entity priority score, findings report export, SATPACK exchange, offline Docker packaging, `audmi` CLI entry point. |

## 4. Repository map

```
audmi/
├── src/
│   ├── core/findings.py                  IMPLEMENTED  Finding schema v1 (shared output contract)
│   ├── core/registry.py                  IMPLEMENTED  loads + validates rules/*.yaml
│   ├── normalization/evidence_model.py   IMPLEMENTED  canonical record types + validation
│   ├── analytics/common.py               IMPLEMENTED  shared EvidenceRecords + finding/robust-stat helpers
│   ├── analytics/execution_gaps.py       IMPLEMENTED  loader/runner + 3 execution-gap rules
│   ├── analytics/negative_space.py       IMPLEMENTED  negative-space rule (silent high-value assets)
│   ├── ingestion/quality.py              IMPLEMENTED  data-quality report (schema, refs, duplicates, timestamps)
│   ├── ingestion/manifest.py             IMPLEMENTED  SHA-256 submission manifest + verification
│   ├── api/server.py                     IMPLEMENTED  stdlib loopback JSON API + CLI
│   ├── validation/evaluate.py            IMPLEMENTED  eval harness vs ground truth
│   └── evidence/ explainability/ prioritization/ review/
│                                         EMPTY        placeholder packages for planned work
├── rules/*.yaml                          IMPLEMENTED  Sigma-like rule definitions (thresholds live here)
├── data/
│   ├── schemas/core-evidence.schema.json IMPLEMENTED  JSON Schema mirror of the evidence model
│   ├── schemas/finding.schema.json       IMPLEMENTED  JSON Schema mirror of Finding v1
│   ├── outputs/                          GITIGNORED   eval_report.json, quality_report.json, submission_manifest.json
│   └── synthetic/
│       ├── generator.py                  IMPLEMENTED  deterministic dataset generator v2 (seed 42)
│       └── golden_dataset/*.json         GENERATED    14,730 records + ground_truth.json + dataset_manifest.json
├── scripts/check_offline.py              IMPLEMENTED  fails if product code imports network libs or loads remote assets
├── .github/workflows/ci.yml              IMPLEMENTED  tests, ingestion, eval, offline guard, web build
├── tests/                                IMPLEMENTED  93 tests (+9 subtests)
├── web/                                  DEMO         Next.js 16 / React 19 UI; `/demo` fixtures, `/live` reads the API
├── docs/audmi_architecture_document.pdf  architecture doc for SIH
├── docs/design/phase0.md                 Phase 0 design note (why the contracts look like this)
├── check_counts.py                       helper: prints record counts per dataset file
├── docker-compose.yml, models/           PLACEHOLDERS (nothing configured)
└── requirements.txt                      PyYAML (rule files) + pytest
```

## 5. How the implemented parts work

### 5.1 Evidence model (`src/normalization/evidence_model.py`)
Seven frozen dataclasses linked by IDs:

```
CSE ─┬─ Asset ── Alert ── Case ─┬─ Investigation
     │                          ├─ Escalation
     │                          └─ Remediation
```

Every record checks itself on creation:
- required text fields aren't empty
- severity and status come from fixed lists
- **all timestamps are timezone-aware UTC**
- an end time can't come before its start time

*Why UTC?* It's the same rule you learnt for incident reports. When records from six organisations are merged onto one timeline, mixed time zones produce fake anomalies.

*Why one model?* Every rule reads the same shape. Without it, each rule would have to parse each CSE's format on its own.

### 5.2 Synthetic generator v2 (`data/synthetic/generator.py`)
Real SOC data is sensitive and we don't have any. The generator builds a fake but structured world with a fixed random seed, so every run produces identical output:

| CSEs | Assets | Alerts | Cases | Investigations | Escalations | Remediations |
|---|---|---|---|---|---|---|
| 6 | 300 | 10,000 | 2,000 | 1,500 | 664 | 260 |

**Why v2 exists.** v1 escalated only ~10% of high/critical cases in every CSE and put every planted short investigation in a separate duration range. The rules looked perfect for the wrong reason. v2 uses:

- a **~80% per-entity escalation baseline**, with CSE-02 deliberately weak at ~50%
- **log-normal investigation durations that overlap** the planted fast ones
- **40 legitimate fast decoys** (180–720 s) that no ground-truth label covers
- **volume-matched remediated decoys** for the repeated-alert rule
- **four quarters** of activity instead of one narrow window
- sector and **peer-group** metadata in `dataset_manifest.json`

It **plants known problems** and writes them only to `ground_truth.json`. The operational files carry no labels, so the rules can't cheat.

| Planted condition | Where | Size |
|---|---|---|
| Missing escalation | CSE-02 (+ small mixed cohort in CSE-06) | 60 + 10 cases |
| Unusually short investigation | CSE-04 (+ CSE-06) | 100 + 5 investigations |
| Repeated alerts without remediation | CSE-03 | 8 critical assets |
| Negative space: critical assets with no alerts | CSE-05 | 8 assets |

### 5.3 The four rules
Each rule's thresholds live in `rules/<rule_id>.yaml` (Sigma-like: id, version, status, level, capability, category, parameters, false_positives) and are loaded by `src/core/registry.py`. Each rule returns **Finding v1** objects (`src/core/findings.py`): `finding_id`, `rule_id` + `rule_version`, `capability` (one of the 8), `category`, `cse_id`, `subject_type` + `subject_id`, a plain-language `reason`, `supporting_record_ids` (the evidence chain), a `baseline` dict with the numbers behind the decision, and `data_quality_notes`.

1. **`missing_escalation`.** The case's alert is high or critical, an investigation exists, and there's no escalation record. This is a pure expected-vs-observed check.
2. **`unusually_short_investigation`.** The rule takes the log of every investigation's duration, then finds the median and the **MAD** (median absolute deviation). It flags anything below `median − 3.5 × 1.4826 × MAD`.
   - *Why MAD and not mean/standard deviation?* A few extreme values drag the mean around; the median barely moves. Robust statistics suit messy operational data.
   - *Why log?* Durations are skewed (minutes vs days), and the log makes "10× shorter" comparable across the whole range.
3. **`repeated_alerts_without_remediation`.** An asset's alert count must be above its CSE's robust fence (median + 3·MAD, and at least 2× the median). It also needs ≥3 cases, with ≤10% of those cases having any remediation record.
4. **`negative_space_low_activity`.** A critical or high asset is flagged when it has **zero alerts** while its **CSE peer group** (a `peer_group` shared by comparable CSEs) is demonstrably active: at least 20 peers and a peer median of at least 5 alerts. The rule cites up to five active peers so the examiner can see the comparison.
   - *Why peer groups, not the whole dataset?* A silent asset in a quiet group is not evidence of anything. The question is always *compared with what?*
   - *Why only zero alerts?* Raising `max_alert_count` is a one-line YAML change, but each step needs a stated justification. A narrow rule is easier to defend.

A finding is a **potential** indicator. Missing evidence isn't proof of missing activity: the submission may just be incomplete.

### 5.4 Measured results (seed 42, full ground truth)

| Rule | Flagged | Seeded | Seeded caught | Flagged outside ground truth |
|---|---:|---:|---:|---:|
| missing_escalation | 279 | 70 | **70** | 209 |
| unusually_short_investigation | 127 | 105 | **105** | 22 |
| repeated_alerts_without_remediation | 8 assets | 8 assets | **8** | 0 |
| negative_space_low_activity | 8 assets | 8 assets | **8** | 0 |

**How to read this honestly:**
- **Missing escalation.** Recall is complete against the seeded cases. The 209 extra flags are *unclassified*, not proven false positives. With an ~80% background escalation rate, some unlabeled high/critical cases still lack escalation and are plausible real gaps; others are normal variation. The rule's lower-bound precision is **0.251** (`70 / 279`). Do not present the extra flags as errors, and do not call the rule precise.
- **Short investigation.** Planted durations are 120–290 s; the v2 threshold is ≈447 s, and 40 legitimate fast decoys sit at 180–720 s. The 22 unclassified flags are mostly those legitimate fast cases. That overlap is the point: the rule can no longer "win" by separating two disjoint ranges, so the result says something about the method rather than the fixture. It still cannot tell a legitimate rapid triage from a shortcut — a human must.
- **Repeated alerts.** Correct at asset level, with volume-matched decoys that are fully remediated. Ground truth also lists case IDs, so score this at **asset** level.
- **Negative space.** The 8 critical CSE-05 assets with zero alerts are exactly the 8 seeded; no other asset in the dataset is flagged. CSE-03 is the active peer (`communications-critical`, peer median 30 alerts), which is why the comparison is meaningful.
- The evaluation harness reproduces this table per cohort: `python -m src.validation.evaluate` (writes `data/outputs/eval_report.json`). Flags outside ground truth are reported as *unclassified*, and precision is a lower bound.
- These are **synthetic** numbers. They validate plumbing and method behaviour, not real-world detection accuracy.

### 5.5 Ingestion and integrity (`src/ingestion/`)
Before a rule runs, `python -m src.ingestion` answers "is this submission complete and untampered?" without changing it:

- parses every canonical JSON file and validates each row against the evidence model
- reports schema errors, duplicate IDs, broken references, cross-entity CSE mismatches and timestamp-order violations
- counts and lists malformed rows instead of silently dropping them
- writes `data/outputs/quality_report.json` and `data/outputs/submission_manifest.json`

The manifest records the size and SHA-256 of every submission file, then hashes the sorted `digest  name` lines into one combined digest (the same shape as `sha256sum` output). That digest is the chain-of-custody anchor an examiner can reproduce offline.

*Why not repair bad data?* Silent repair hides exactly the evidence an examiner needs. The report says what is wrong; the human decides.

### 5.6 Offline API and live screen (`src/api/`, `web/app/live/`)
`python -m src.api --port 8000` starts a **Python standard-library** `http.server` bound to `127.0.0.1`. It pre-computes findings, the submission manifest and the quality report once, then serves:

```
GET /health
GET /summary
GET /entities
GET /findings?cse_id=&rule_id=&level=&limit=&offset=
GET /findings/{id}
GET /findings/{id}/evidence
```

*Why stdlib and not FastAPI?* Every extra package is another wheel to carry into an air-gapped exam room. The API only needs JSON over loopback, which `http.server` already does. It makes no outbound calls.

`web/app/live/page.tsx` is a server component (`force-dynamic`) that reads `AUDMI_API_URL` (default `http://127.0.0.1:8000`) and renders the summary, filterable findings and entity table. If the API is down it explains how to start it and points back to `/demo`. The fixture demo is unchanged.

## 6. How to run (Windows PowerShell, from `D:\audmi`)

```powershell
pip install -r requirements.txt                  # PyYAML + pytest
python -m pytest -q                              # 93 tests + 9 subtests should pass
python -m src.ingestion                          # validate submission + write quality report and manifest
python -m src.analytics.execution_gaps           # prints finding counts
python -m src.validation.evaluate                # precision/recall table vs ground truth
python -m src.api --port 8000                    # offline loopback JSON API
python -m data.synthetic.generator --seed 42     # regenerate dataset
python check_counts.py                           # record counts per file
python scripts/check_offline.py                  # fail if product code reaches the network
cd web; npm install; npm run dev                 # demo UI at http://localhost:3000 (and /live)
```

To see live engine results, run `python -m src.api --port 8000` in one terminal and `npm run dev` in another, then open `/live`. Without the API the page shows a setup message; `/demo` still works from fixtures.

## 7. Your SOC knowledge → AudMi

What you learnt as an analyst is exactly what AudMi checks from the supervisor's side.

| You learnt (analyst view) | AudMi asks (supervisor view) |
|---|---|
| SOC flow: Alert → Triage → Investigation → Escalation → Containment → Reporting | Does each record have the next stage it *should* have? (expected-vs-observed) |
| IR lifecycle: Preparation → Containment → Eradication → Recovery → Lessons learned | Are there remediation records? Does the same weakness come back (repeated alerts)? |
| MITRE ATT&CK tactics | **Negative space:** a CSE with zero alerts for whole tactics (Credential Access, Lateral Movement) may have a detection blind spot |
| Sigma rules: id, level, tags, detection, condition | **AudMi rules should look like Sigma rules:** versioned YAML with id, severity, capability tag and parameters, kept separate from code |
| Report writing: UTC times, evidence, timeline | Every finding has UTC timestamps, evidence IDs and a reason |
| CIA → Integrity → hashes | SHA-256 manifest of each submission and each analysis run, so results can be audited later |
| DF: Identification → Preservation → Collection → Analysis → Presentation | Same chain for submissions: ingest → hash/preserve → validate → analyse → report |
| Windows event IDs, Sysmon IDs | Why AudMi *avoids* raw logs: the problem statement says to minimise sensitive raw data, so we work on alert/case **metadata** |

New supervisory terms you'll meet:
- **MTTD/MTTR** — mean time to detect / respond.
- **Disposition** — true positive, false positive, benign.
- **Escalation rate** — escalated high/critical cases ÷ all high/critical cases.
- **Peer group** — similar entities to compare against.
- **Baseline** — what normal looks like.
- **Ground truth** — the known answers in test data.
- **Precision** — of what we flagged, how much was right.
- **Recall** — of what was there, how much we caught.

## 8. Decisions so far (and why)

| Decision | Why |
|---|---|
| Deterministic rules before ML | Explainable, testable, and they give a baseline that ML has to beat. The problem statement scores explainability and auditability. |
| Synthetic data with separate ground truth | No access to real SOC data; lets us measure detection without leaking labels |
| Generator v2 with realistic baselines and decoys | v1 made the rules look perfect because the classes were trivially separable. A test that cannot fail proves nothing. |
| Robust statistics (median/MAD) | Operational data is skewed and full of outliers |
| Findings carry record IDs + baseline numbers | The examiner must be able to see *why*, not just trust a score |
| Python stdlib + PyYAML only | Air-gapped deployment: every dependency has to be carried in offline. PyYAML is the one exception, because rule files need comments for reviewers |
| Loopback `http.server` API, not FastAPI | Another package is another offline wheel; JSON over loopback is all the UI needs |
| Thresholds in versioned YAML rules, not code | Examiners can read them; every finding cites the rule version that produced it |
| One shared Finding schema | Six workstreams can build rules, API and UI in parallel against one output shape |
| Outside-ground-truth flags are "unclassified" | Ground truth only labels planted problems; an unlabelled flag isn't proven wrong |
| Ingestion reports bad rows, never repairs them | Silent repair hides the evidence an examiner needs; a human decides |
| Demo UI built ahead of the backend | SIH idea stage: show the full workflow while the engine is being built |
| `/live` is dynamic, `/demo` is fixtures | `next build` must work without the API running; the fixture screen stays a stable demonstration |

## 9. Known issues

1. **Synthetic-only results.** The generator is more realistic than v1, but it still cannot label every real-looking anomaly. Missing-escalation has 209 unclassified flags and short-investigation has 22; neither rule has a defensible precision number yet.
2. **Short investigations overlap by design.** The rule cannot distinguish a legitimate 3-minute triage from a planted shortcut. That is a human-review question, not a threshold tweak.
3. **Negative space is narrow.** It only covers zero-alert critical/high assets in active peer groups. It does not yet map missing alert *categories* to ATT&CK tactics or check whole quarters with no escalations.
4. Missing from the evidence model: periods/submissions, sector and multiple peer groups per asset, alert disposition, closure analyst, investigation notes, reported KPIs, escalation policy.
5. **Ingestion is JSON-only.** No CSV column-mapping import, no persistent store (SQLite/DuckDB), no identity resolution across submissions.
6. **The API is read-only.** No authentication, no review actions, no audit log, and it binds to loopback only — by design for a local examiner workstation, but not a multi-user deployment.
7. **Web state.** `/demo` still uses `mock-data.ts`; `/live` needs the Python API running. There is no packaged or air-gapped-verified image yet, and CI does not run a network-off install test.
8. **Branch state.** `develop` is five commits ahead of `main` and `phase0/base` (`9872743`). Fast-forward `main` at the phase-end merge, then treat `origin/main` as the baseline.
9. The offline guard (`scripts/check_offline.py`) is a static check. It catches network imports and remote asset URLs, not every possible runtime egress path.

## 10. Where we're going

See **[`TEAM_PLAN.md`](TEAM_PLAN.md)** for phases, the six workstreams and who owns what.
