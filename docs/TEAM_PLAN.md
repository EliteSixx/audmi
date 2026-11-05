# AudMi — Team Plan

> How six people build AudMi without stepping on each other. Read `PROJECT_CONTEXT.md` first.
> Owners below are a **first proposal**. Swap them by interest and skill in the first team meeting, then update this file.

## 1. The idea in one picture

```
 Submission files ──► [W3 Ingest + validate + hash] ──► canonical evidence (store)
                                                              │
         [W2 Synthetic world + ground truth] ────────────────►│ (test data)
                                                              ▼
                   [W4 Execution-gap rules]   [W5 Negative space + peers]
                                 │                    │
                                 └──► Finding (one shared schema, W1) ◄──┘
                                              │
                         [W1 Rule registry · eval harness · priority score]
                                              │
                          [W6 API ─► Web UI ─► reports · review actions]
```

Everyone writes against **two contracts**:
1. **The evidence model**, which already exists.
2. **The Finding schema**, which W1 defines in Phase 0.

Once both are fixed, all six workstreams can run in parallel.

## 2. Phases

| Phase | Goal | Status | Who |
|---|---|---|---|
| **0 · Base** | `AGENTS.md`, Finding schema v1, rule registry, eval command, offline-safe CI, branches reset | **Done** (`c0d4086`) | Rudy (+ Claude). Everyone else does their **learning task** (section 4) and reads the code. |
| **1 · Parallel build** | Each workstream delivers its first milestone behind the shared contracts | **Started** — generator v2 (P1), negative space (P2), ingestion (P3), API + live screen (P4) | All six |
| **2 · Integration** | One real end-to-end slice: validate → rules → API → one UI screen on real data | **Working slice** — `python -m src.ingestion` → rules → `python -m src.api` → `/live` | All, led by W6 + W1 |
| **3 · Hardening** | Evaluation report, offline Docker image tested with the network off, demo video, docs | **Not started** | All |

**Rule:** nobody starts Phase 1 until Phase 0 is merged. Otherwise six people build on six different assumptions.

## 3. Workstreams

Each one has a supervisory question, so everyone can explain *why* their part exists.

### W1 · Core contracts, evaluation & prioritisation — **Rudy** (`feature/rudy`) · team lead
- **Question:** "Can we trust and rank what AudMi says?"
- **Build:**
  1. `Finding` schema v1 with a rule ID and version, capability tag (one of the 8), evidence IDs, reason, baseline and data-quality notes.
  2. A rule registry in **Sigma-like YAML**: id, title, level, tags, parameters.
  3. `audmi eval`, which prints precision and recall per rule and per cohort against ground truth.
  4. Later: an entity-level priority score that lists its reasons, plus the review-sample ranking.
- **Owns:** `src/core/`, `src/validation/` (eval), `rules/`.
- **Learn:** software architecture, contracts between modules, precision/recall, code review.
- **Lead duties:** merge PRs into `develop`, run the weekly 30-min sync, keep `PROJECT_CONTEXT.md` true.

### W2 · Synthetic world v2 — **Siba** (`feature/siba`)
- **Question:** "Is our test data realistic enough to prove anything?"
- **Build:**
  - normal baselines (~80% of high/critical cases escalated, with one weak CSE at ~50%)
  - overlapping duration distributions
  - **decoys** (legitimate-looking edge cases)
  - multiple quarterly periods, sectors and peer groups
  - ground truth labelled at the level each rule works at (case / asset / entity)
- **Owns:** `data/synthetic/`.
- **Learn:** SOC operational metrics (MTTD, MTTR, disposition), how test design decides whether a result means anything.

### W3 · Ingestion, validation & integrity — **Sinu** (`feature/sinu`)
- **Question:** "Is this submission complete and untampered before we analyse it?"
- **Done (P3):** JSON ingestion with a **data-quality report** (schema errors, duplicates, broken links, CSE mismatches, timestamp order) and a **SHA-256 manifest** with a reproducible combined digest. Run `python -m src.ingestion`.
- **Next:**
  - CSV import with a column-mapping file
  - storage in SQLite or DuckDB
  - a manifest of each analysis *run*, not just each submission
- **Owns:** `src/ingestion/`, `src/evidence/`.
- **Learn:** data validation, referential integrity, hashing for integrity (the I in CIA), the chain of custody idea from DF.

### W4 · Execution-gap analytics — **Ishan** (`feature/ishan`)
- **Question:** "Where do the records show the SOC isn't really doing what it reports?"
- **Done (P1–P2):** the 3 rules are registry-driven and measured against generator v2. Shared plumbing lives in `src/analytics/common.py`.
- **Next:**
  - critical alerts closed unusually fast
  - **closure bursts** (many cases closed in a few minutes)
  - the analyst-level pattern of the same analyst closing everything fast
  - once the model has notes: **template/near-duplicate investigation notes** (TF-IDF + cosine similarity)
- **Owns:** `src/analytics/execution_gaps.py` and new rule modules.
- **Learn:** robust statistics (MAD), text similarity, false-positive thinking.

### W5 · Negative space & peer benchmarking — **Samir** (`feature/samir`)
- **Question:** "What evidence is missing that should be there?"
- **Done (P2):** `negative_space_low_activity` flags critical/high assets with zero alerts in an active CSE peer group. 8 seeded, 8 caught.
- **Next:**
  - expected alert categories that never appear, mapped to **MITRE ATT&CK tactic coverage**
  - periods with no escalations
  - **peer percentiles** inside a peer group
- **Owns:** `src/analytics/negative_space.py`, `src/analytics/peers.py`.
- **Learn:** detection coverage engineering (a real SOC skill), ATT&CK, comparing like with like.

### W6 · API, UI integration & reports — **Brajesh** (`feature/brajesh`)
- **Question:** "Can an examiner actually use this offline?"
- **Done (P0, P4):** dependency-free loopback JSON API (`/summary`, `/entities`, `/findings`, `/findings/{id}`, `/findings/{id}/evidence`), `/live` screen reading it, Google Fonts removed, offline guard added. Chose stdlib `http.server` over FastAPI to avoid another offline wheel.
- **Next:**
  - review actions (confirm / dismiss / note) with an **audit log**
  - switch more `/demo` screens from fixtures to the API
  - findings report export
- **Owns:** `src/api/`, `web/`.
- **Learn:** REST API design, frontend–backend integration, audit trails, offline deployment.

## 4. Phase 0 learning tasks (non-lead members, ~3–4 hours each)

1. Run everything in `PROJECT_CONTEXT.md` §6 on your own machine.
2. Read `evidence_model.py` and the rule in `execution_gaps.py` closest to your workstream.
3. Write a **one-page design note** at `docs/design/<your-workstream>.md` covering:
   - the supervisory question
   - input records
   - rule logic
   - what evidence the finding returns
   - how it could be wrong (false positives)
   - how you'll test it

   This note is your first PR. It's also the paragraph you'll use in interviews.

## 5. Git workflow

**Current state (5 Nov 2026):** `phase0/base`, `main` and `origin/main` are at `9872743`. `develop` is five commits ahead (`c0d4086` P0, `12380de` P1, `4236608` P2, `cd6b290` P3, `0392086` P4). The six `feature/*` branches still sit on `9872743`; start new work from `develop` so you build on P0–P4. Fast-forward `main` to `develop` at the phase-end merge.

If a branch needs recreating, or the baseline moves on, start from the current integration branch:

```powershell
git remote set-url origin https://github.com/EliteSixx/audmi.git
git fetch origin
git checkout -B feature/<name> origin/develop
git push --force-with-lease origin feature/<name>
git checkout -B develop origin/develop        # only if develop must be reset again
git push --force-with-lease origin develop
```

At the end of Phase 0, fast-forward `main` to `develop` (no merge commit needed), push it, and from then on use `origin/main` as the baseline.

Then, every day:

```powershell
git checkout feature/<name>
git pull --rebase origin develop     # get teammates' merged work
# ... work, commit small and often ...
git push
```

Then open a pull request **into `develop`**, small, ideally under 400 lines. `develop` → `main` happens only at phase ends, after tests and `audmi eval` pass.

**Definition of done for any PR:**
- [ ] tests added and `python -m pytest -q` passes
- [ ] `python -m src.validation.evaluate` numbers in the PR description (for rule changes)
- [ ] `python scripts/check_offline.py` passes
- [ ] no network calls, no cloud or SaaS dependency
- [ ] status board in `PROJECT_CONTEXT.md` updated if a feature moved category
- [ ] findings say "potential", never "non-compliant"

## 6. Rhythm (fits around classes)

- **One 30-minute sync per week.** Each person answers: what I finished, what's next, what blocks me.
- Daily updates are async: one line in the group chat.
- **About 6–8 hours per person per week.** Fixed small blocks beat all-nighters.
- During exams, the plan pauses. Say so early and nobody is blocked.

## 7. Resume lines you will earn

Write these only once the work is merged and measured. Fill in real numbers from `audmi eval`.

- *Built explainable SOC-supervision rules (robust statistics, expected-vs-observed checks) over 14k+ synthetic SOC records, validated against seeded ground truth.*
- *Designed a Sigma-style versioned rule registry and evaluation harness reporting per-rule precision/recall.*
- *Built an integrity-preserving ingestion pipeline with data-quality reports and SHA-256 manifests for an air-gapped deployment.*
- *Shipped an end-to-end offline slice: Python engine → loopback JSON API → Next.js live findings screen.*
- *Mapped detection coverage gaps to MITRE ATT&CK tactics across peer entities.*
