# AudMi — Project Context

> Read this first. It explains what AudMi is, what is actually built, how it works, what we measured, and where we are going.
> Verified on **5 Nov 2026** against the tip of branch `phase0/base` (Phase 0, 6 commits ahead of `main`). Phase 0 is not yet in `main` (`4d55104`); `origin/main` is still `72d0b80`. On 5 Nov 2026 `develop` and all six `feature/*` branches were reset onto `phase0/base` (they previously sat on `520728d "first commit"`). See `docs/design/phase0.md`. If you change anything listed under "Implemented", update this file in the same PR.

**AudMi (Auditor's Microscope)** — SIH 2026, Problem Statement SIHPS26157, *Supervisory Analytics Tool for SOC Assessment (SAT-SA)*, NTRO / NCIIPC. Team Elite Sixx.

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
| 1 | **Demonstrated in the UI** (mock data) | Full examiner journey in `web/`: entity overview, 8 capability views, ranked findings, evidence drill-down, review actions. Everything reads from `web/app/data/mock-data.ts`. |
| 2 | **Implemented and testable** | Evidence model, evidence JSON schema, synthetic generator + ground truth, **Finding schema v1** (+ JSON Schema), **Sigma-like rule registry** (`rules/*.yaml`), 3 execution-gap rules driven by the registry, **evaluation harness** (`python -m src.validation.evaluate`), 49 passing tests. |
| 3 | **Proposed / not yet integrated** | Ingestion and data-quality reports, storage, API, negative space, peer benchmarking, text similarity, workflow sequences, report-vs-record reconciliation, review-activity analytics, prioritisation score, SATPACK exchange, offline packaging, offline CI, `audmi` CLI entry point, frontend↔backend link. |

## 4. Repository map

```
audmi/
├── src/
│   ├── core/findings.py                  IMPLEMENTED  Finding schema v1 (shared output contract)
│   ├── core/registry.py                  IMPLEMENTED  loads + validates rules/*.yaml
│   ├── normalization/evidence_model.py   IMPLEMENTED  canonical record types + validation
│   ├── analytics/execution_gaps.py       IMPLEMENTED  loader + 3 registry-driven rules
│   ├── validation/evaluate.py            IMPLEMENTED  eval harness vs ground truth
│   └── ingestion/ evidence/ explainability/ prioritization/ review/
│                                         EMPTY        placeholder packages for planned work
├── rules/*.yaml                          IMPLEMENTED  Sigma-like rule definitions (thresholds live here)
├── data/
│   ├── schemas/core-evidence.schema.json IMPLEMENTED  JSON Schema mirror of the evidence model
│   ├── schemas/finding.schema.json       IMPLEMENTED  JSON Schema mirror of Finding v1
│   ├── outputs/                          GITIGNORED   eval_report.json and other run output
│   └── synthetic/
│       ├── generator.py                  IMPLEMENTED  deterministic dataset generator (seed 42)
│       └── golden_dataset/*.json         GENERATED    14,206 records + ground_truth.json
├── tests/                                IMPLEMENTED  49 tests (model, generator, findings, registry, rules, eval)
├── web/                                  DEMO         Next.js 16 / React 19 UI on mock data
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

### 5.2 Synthetic generator (`data/synthetic/generator.py`)
Real SOC data is sensitive and we don't have any. The generator builds a fake but structured world with a fixed random seed, so every run produces identical output:

| CSEs | Assets | Alerts | Cases | Investigations | Escalations | Remediations |
|---|---|---|---|---|---|---|
| 6 | 300 | 10,000 | 2,000 | 1,500 | 300 | 100 |

It **plants known problems** and writes them only to `ground_truth.json`. The operational files carry no labels, so the rules can't cheat.

| Planted condition | Where | Size |
|---|---|---|
| Missing escalation | CSE-02 (+ small mixed cohort in CSE-06) | 100 + 10 cases |
| Unusually short investigation | CSE-04 (+ CSE-06) | 100 + 5 investigations |
| Repeated alerts without remediation | CSE-03 | 8 critical assets |
| Negative space: critical assets with no alerts | CSE-05 | 8 assets |

### 5.3 The three rules (`src/analytics/execution_gaps.py`)
Each rule's thresholds live in `rules/<rule_id>.yaml` (Sigma-like: id, version, status, level, capability, category, parameters, false_positives) and are loaded by `src/core/registry.py`. Each rule returns **Finding v1** objects (`src/core/findings.py`): `finding_id`, `rule_id` + `rule_version`, `capability` (one of the 8), `category`, `cse_id`, `subject_type` + `subject_id`, a plain-language `reason`, `supporting_record_ids` (the evidence chain), a `baseline` dict with the numbers behind the decision, and `data_quality_notes`.

1. **`missing_escalation`.** The case's alert is high or critical, an investigation exists, and there's no escalation record. This is a pure expected-vs-observed check.
2. **`unusually_short_investigation`.** The rule takes the log of every investigation's duration, then finds the median and the **MAD** (median absolute deviation). It flags anything below `median − 3.5 × 1.4826 × MAD`.
   - *Why MAD and not mean/standard deviation?* A few extreme values drag the mean around; the median barely moves. Robust statistics suit messy operational data.
   - *Why log?* Durations are skewed (minutes vs days), and the log makes "10× shorter" comparable across the whole range.
3. **`repeated_alerts_without_remediation`.** An asset's alert count must be above its CSE's robust fence (median + 3·MAD, and at least 2× the median). It also needs ≥3 cases, with ≤10% of those cases having any remediation record.

A finding is a **potential** indicator. Missing evidence isn't proof of missing activity: the submission may just be incomplete.

### 5.4 Measured results (seed 42, full ground truth)

| Rule | Flagged | Seeded | Seeded caught | Flagged outside ground truth |
|---|---:|---:|---:|---:|
| missing_escalation | 581 | 110 | **110** | 471 |
| unusually_short_investigation | 105 | 105 | **105** | 0 |
| repeated_alerts_without_remediation | 8 assets | 8 assets | **8** | 0 |
| negative space (low activity) | — | 8 assets | no detector yet | — |

**How to read this honestly:**
- **Missing escalation.** Recall is complete. The 471 extra flags are *unclassified*, not proven false positives. The background data escalates only ~12% of high/critical cases in **every** CSE, so the data can't tell the planted cases apart from normal behaviour. That's a generator realism problem.
- **Short investigation.** Planted durations are 30–179 s and every normal one is ≥1,800 s. The two groups never overlap, so any threshold would pass. This proves the plumbing works, **not** that the method is good.
- **Repeated alerts.** Correct at asset level. Ground truth also lists case IDs, so score this at **asset** level.
- The evaluation harness now exists: `python -m src.validation.evaluate` reproduces this table per cohort and writes `data/outputs/eval_report.json`. Flags outside ground truth are reported as *unclassified*, and precision is a lower bound.
- **Don't quote** precision, recall or accuracy figures in slides until generator v2 makes the test meaningful.

## 6. How to run (Windows PowerShell, from `D:\audmi`)

```powershell
pip install -r requirements.txt                  # PyYAML + pytest
python -m pytest -q                              # 49 tests should pass
python -m src.analytics.execution_gaps           # prints finding counts
python -m src.validation.evaluate                # precision/recall table vs ground truth
python -m data.synthetic.generator --seed 42     # regenerate dataset
python check_counts.py                           # record counts per file
cd web; npm install; npm run dev                 # demo UI at http://localhost:3000
```

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
| Robust statistics (median/MAD) | Operational data is skewed and full of outliers |
| Findings carry record IDs + baseline numbers | The examiner must be able to see *why*, not just trust a score |
| Python stdlib + PyYAML only | Air-gapped deployment: every dependency has to be carried in offline. PyYAML is the one exception, because rule files need comments for reviewers |
| Thresholds in versioned YAML rules, not code | Examiners can read them; every finding cites the rule version that produced it |
| One shared Finding schema | Six workstreams can build rules, API and UI in parallel against one output shape |
| Outside-ground-truth flags are "unclassified" | Ground truth only labels planted problems; an unlabelled flag isn't proven wrong |
| Demo UI built ahead of the backend | SIH idea stage: show the full workflow while the engine is being built |

## 9. Known issues

1. The generator's background escalation rate is unrealistically low everywhere, so missing-escalation results are noisy (see 5.4).
2. Short-investigation test data is trivially separable.
3. There is no negative-space detector, even though ground truth exists for one.
4. Missing from the evidence model:
   - periods/submissions
   - sector and multiple peer groups (all CSEs are `regional`)
   - alert disposition
   - closure analyst
   - investigation notes
   - reported KPIs
   - escalation policy
5. The loader silently skips malformed rows. It should produce a data-quality report instead.
6. `web/app/globals.css` imports Google Fonts, which breaks offline use. Mock numbers don't match the golden dataset. Links still point at `rudythetechy/audmi`; the repo has moved to **`EliteSixx/audmi`**.
7. Branch layout: `phase0/base` holds Phase 0 and is the current baseline. `develop` and the six `feature/*` branches were reset onto it on 5 Nov 2026. `main` (`4d55104`) and `origin/main` (`72d0b80`) are still behind and should be fast-forwarded at the phase-end merge. `README.md` is partially stale: its status table now marks evaluation as implemented, but it still links to `rudythetechy/audmi` and describes some planned work as if it were the design target.

## 10. Where we're going

See **[`TEAM_PLAN.md`](TEAM_PLAN.md)** for phases, the six workstreams and who owns what.
