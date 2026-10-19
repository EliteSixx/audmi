# Phase 0 · Base — design note

> Branch `phase0/base`. Workstream W1 (core contracts, evaluation). Written 19 Oct 2026.
> Every number below was produced by running the code on the seed-42 golden dataset. None are estimates.

## 1. What was built

| Piece | Where | Category |
|---|---|---|
| Finding schema v1 (dataclass + JSON Schema) | `src/core/findings.py`, `data/schemas/finding.schema.json` | Implemented and testable |
| Rule registry (Sigma-like YAML + loader) | `rules/*.yaml`, `src/core/registry.py` | Implemented and testable |
| 3 execution-gap rules read their thresholds from the registry and emit Finding v1 | `src/analytics/execution_gaps.py` | Implemented and testable |
| Evaluation harness | `src/validation/evaluate.py` (`python -m src.validation.evaluate`) | Implemented and testable |
| Tests for all of the above | `tests/test_findings.py`, `test_registry.py`, `test_evaluate.py`, updated `test_execution_gaps.py` | 49 passed |

Commands:

```powershell
pip install -r requirements.txt          # PyYAML + pytest
python -m pytest -q                      # 49 passed, 9 subtests passed
python -m src.analytics.execution_gaps   # 581 / 8 / 105 findings, unchanged
python -m src.validation.evaluate        # table below + data/outputs/eval_report.json
```

## 2. Why — the ideas behind it

### 2.1 One shared Finding schema lets six people work in parallel

Before Phase 0, a "finding" was whatever `execution_gaps.py` happened to return: fields like `case_id`, `asset_id`, `duration_seconds` that only made sense for one rule each. If W5 (negative space) had added a rule, they would have invented their own fields. W6 (API/UI) would then need special code for every rule, and W1's evaluation would need special code too.

A **contract** fixes that. Every rule, by any team member, returns the same `Finding`:

```
finding_id, rule_id, rule_version, capability, category,
cse_id, subject_type, subject_id, reason,
supporting_record_ids, baseline, data_quality_notes
```

Now the six workstreams only meet at two points: the evidence model (input) and the Finding (output). Samir can write a negative-space rule without asking Brajesh how the API will show it, and the API will show it anyway. It's the same reason SIEMs normalise logs into one schema before writing detections.

The two generic fields that make this work:
- `subject_type` + `subject_id` say *what the finding is about* (a case, an investigation, an asset or a whole entity). This replaces the per-rule `case_id` / `asset_id` / `investigation_id` fields.
- `baseline` is a dict holding the numbers the rule used (threshold, median, observed value). Each rule fills it differently, but the examiner always finds "why" in the same place. AGENTS.md rule 2 says: no unexplained scores.

The dataclass also **guards the language rule** (AGENTS.md rule 3). A finding's `reason` must contain "potential" and must not contain "non-compliant", "negligent" or "failed". Code can't be merged that breaks this, because the `Finding` refuses to be created.

### 2.2 Sigma-style rules: thresholds out of code, into versioned YAML

[Sigma](https://github.com/SigmaHQ/sigma) is the open format SOC teams use to share detections. A Sigma rule is a YAML file with an `id`, `title`, `status`, `level`, `tags`, the detection logic, and a `falsepositives` list. AudMi rules follow the same shape:

```yaml
id: unusually_short_investigation
version: 1.0.0
status: experimental
level: medium
capability: investigation       # one of the 8 NCIIPC capabilities (like a Sigma tag)
category: execution_gap
subject_type: investigation
parameters:
  sigma_multiplier: 3.5         # robust standard deviations below the median
  mad_scale: 1.4826
  min_baseline_size: 8
false_positives:
  - Automated or playbook-driven investigations that are legitimately fast.
```

Why bother, when the numbers were working fine as Python constants?
- **An examiner can read it.** A supervisor at NCIIPC can see what "unusually short" means without reading Python.
- **Every finding cites a version.** If someone changes `3.5` to `3.0`, they bump the version to `1.1.0`. Old findings still say `@1.0.0`, so we can always explain what produced them. That's an audit trail.
- **`false_positives` is written down up front.** It forces the rule author to think about how the rule could be wrong *before* anyone sees a finding. This is the same habit Sigma enforces.

Unlike Sigma, the detection logic itself stays in Python (`RULE_FUNCTIONS` in `execution_gaps.py`). Our rules use statistics (median, MAD) across many records, and Sigma's `detection:` syntax only matches single events. Only the *parameters* live in YAML.

### 2.3 Precision vs recall, and why "unclassified" isn't "false positive"

Ground truth lists the problems the generator **planted**. For each rule:

- **Recall** = caught ÷ seeded. *"Of the problems we planted, how many did the rule find?"*
- **Precision** = caught ÷ flagged. *"Of what the rule flagged, how much was a planted problem?"*

You usually trade one for the other. Lower a threshold and you catch more (recall ↑) but also flag more noise (precision ↓). An examiner with limited time cares about both. Low recall means real gaps are missed. Low precision means they waste their review time.

The catch: ground truth only knows what was **planted**. When the rule flags a record that isn't in ground truth, we don't know if it's noise, or a real gap that the random generator created by accident. So the harness calls these **unclassified**, not false positives, and treats the precision figure as a **lower bound**. This is the same honesty rule as "missing evidence isn't proof of missing activity": not being labelled isn't proof of being wrong.

Each condition is scored **at the level its rule works at**: cases for missing escalation, investigations for short investigation, assets for repeated alerts. Ground truth for repeated alerts also lists case IDs, so scoring that rule against case IDs would have produced nonsense.

## 3. Evaluation output (actual run, seed 42)

```
condition                            rule                                       level          cohort  flagged  seeded  caught  missed  unclassified  precision  recall
-----------------------------------  -----------------------------------------  -------------  ------  -------  ------  ------  ------  ------------  ---------  ------
missing_escalation                   missing_escalation@1.0.0                   case           CSE-02      210     100     100       0           110      0.476   1.000
missing_escalation                   missing_escalation@1.0.0                   case           CSE-06       68      10      10       0            58      0.147   1.000
missing_escalation                   missing_escalation@1.0.0                   case           ALL         581     110     110       0           471      0.189   1.000
negative_space_low_activity          no detector                                asset          CSE-05        -       8       -       -             -          -       -
repeated_alerts_without_remediation  repeated_alerts_without_remediation@1.0.0  asset          CSE-03        8       8       8       0             0      1.000   1.000
repeated_alerts_without_remediation  repeated_alerts_without_remediation@1.0.0  asset          ALL           8       8       8       0             0      1.000   1.000
unusually_short_investigation        unusually_short_investigation@1.0.0        investigation  CSE-04      100     100     100       0             0      1.000   1.000
unusually_short_investigation        unusually_short_investigation@1.0.0        investigation  CSE-06        5       5       5       0             0      1.000   1.000
unusually_short_investigation        unusually_short_investigation@1.0.0        investigation  ALL         105     105     105       0             0      1.000   1.000
```

`ALL` includes flags from CSEs with no planted condition (CSE-01, -03, -04, -05 contribute 303 of the 581 missing-escalation flags).

**How to read it honestly** (same caveats as `PROJECT_CONTEXT.md` §5.4):
- *Missing escalation* precision 0.189 is a lower bound. The generator escalates only ~12% of high/critical cases everywhere, so normal cases look like planted ones. This is a test-data problem for W2 (generator v2), not proof the rule is bad.
- *Short investigation* and *repeated alerts* at 1.000 / 1.000 prove the plumbing works. The planted cases are trivially separable from normal ones, so these numbers say nothing yet about real-world quality. **Don't put them on a slide.**
- *Negative space* has ground truth but no detector (W5).

## 4. Decisions made (and why)

These were made without the team lead present. Each can be revisited.

| # | Decision | Why / alternative |
|---|---|---|
| 1 | Added `finding_id` and `schema_version` to the Finding beyond the requested fields | The API and review log need a stable ID to point at. `schema_version` lets future consumers detect v2. `finding_id` keeps the old signal IDs (e.g. `EXG-MISSING-ESCALATION-CAS-00001`), so nothing downstream changes. |
| 2 | Rule `id` is a readable slug equal to the ground-truth `condition_type`, not a Sigma-style UUID | Readable in findings and logs. The registry enforces id == file name and uniqueness. Switch to UUIDs if rules are ever shared outside the team. |
| 3 | Added `subject_type` to the rule YAML (not in the requested key list) | A rule always flags the same level of record. Putting it in the YAML means a Finding's level comes from the registry, and the eval harness can check it. |
| 4 | Capability mapping: missing escalation → `escalation`; short investigation → `investigation`; repeated alerts → `incident_response` | Repeated alerts with no remediation is a gap in the containment/eradication/recovery part of the IR lifecycle. `cyber_resilience` was the alternative. Confirm with the team. |
| 5 | Removed the legacy `Finding` from `execution_gaps.py` and updated tests, instead of keeping a compatibility shim | Two `Finding` classes would let teammates write against the wrong one. Test changes are mechanical (`signal_type`→`rule_id`, `case_id`/`asset_id`/`investigation_id`→`subject_id`, `duration_seconds`→`baseline["observed_duration_seconds"]`). Every assertion means what it meant before. I also checked that the new code produces **the same 694 findings, with the same IDs and evidence chains**, as commit `72d0b80`. A test pins the 581/105/8 counts. |
| 6 | Per-finding values that used to be top-level (`severity`, `duration_seconds`) moved into `baseline` as `observed_*` | Keeps the schema generic. The examiner sees "observed vs threshold" side by side. |
| 7 | Added `data_quality_notes` to missing-escalation and repeated-alerts findings | Both rules rest on the *absence* of a record. The note reminds the examiner that the record may exist outside the submission (AGENTS.md rule 3). |
| 8 | The Finding rejects reasons containing "failed" | AGENTS.md lists it. This could block a future reason like "repeated failed logins". If that happens, narrow the check, don't remove it. |
| 9 | PyYAML added to `requirements.txt` | YAML allows comments, which a rule file reviewed by people needs. JSON doesn't. PyYAML is pure Python and needs no network. Its wheel must be bundled for the air-gapped image (Phase 3). The registry uses `yaml.safe_load` only, so a rule file can't execute code. |
| 10 | The "audmi eval" command is `python -m src.validation.evaluate`, not a console script | There's no packaging (`pyproject.toml`) yet. Add an `audmi` entry point when W6 packages the tool. |
| 11 | Eval cohort = the `cse_id` of each ground-truth condition, plus an `ALL` row | Ground truth defines cohorts by CSE. `ALL` shows flags from CSEs with no planted condition, which per-cohort rows would hide. |
| 12 | Report includes `generated_at` (UTC) and the SHA-256 of `ground_truth.json` | You can always tell which ground truth a report was scored against (the integrity idea from W3). |
| 13 | Push to GitHub not done from this session | The agent's sandbox blocked network access to github.com. Commits are local on `main` (docs) and `phase0/base`. The team lead must push. |

## 5. What this does not do yet

- No negative-space detector (W5). The harness already reports it as "no detector" and will score it automatically once a rule with id `negative_space_low_activity` is registered **and** added to `RULE_FUNCTIONS`.
- No priority score, no API, no data-quality report for skipped rows (the loader still silently drops malformed rows; W3).
- No offline CI configuration yet (Phase 0 item still open).
- Generator v2 (W2) is needed before any precision/recall figure means something.

## 6. How to add a rule (for W4/W5)

1. Write `rules/<rule_id>.yaml` (copy an existing one, set `version: 1.0.0`, `status: experimental`).
2. Write `def find_<thing>(records: EvidenceRecords, rule: Rule) -> list[Finding]`. Read every threshold with `rule.param("name")`. Build findings with `_new_finding(rule, ...)`.
3. Register it in `RULE_FUNCTIONS`.
4. If ground truth has a condition for it, add a `ConditionMapping` in `src/validation/evaluate.py`.
5. Add tests, run `python -m pytest -q` and `python -m src.validation.evaluate`, and paste the table into the PR.
