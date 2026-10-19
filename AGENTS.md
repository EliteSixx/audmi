# Instructions for AI coding agents (Claude Code, Codex) and humans

Read `docs/PROJECT_CONTEXT.md` and `docs/TEAM_PLAN.md` before changing anything.

## Ground rules
1. **Three categories.** Every feature is *Demonstrated in UI (mock)*, *Implemented and testable*, or *Proposed*. Check the code before claiming a feature exists. A screen in `web/` isn't proof of a backend.
2. **Evidence first.** Every finding carries: rule id + version, capability tag, plain-language reason, supporting record IDs, and the baseline numbers used. No unexplained scores.
3. **Language.** Findings are "potential" indicators for human review. Never write "non-compliant", "negligent" or "failed". Missing evidence isn't proof of missing activity.
4. **Offline.** No network calls, cloud services, external AI APIs or CDN assets in product code. Each new dependency needs a reason in the PR.
5. **Don't silently change** the evidence schema, `ground_truth.json` semantics, or test assumptions. If a change is needed, say so in the PR.
6. **Tests.** Add tests with every analytical change. Run `python -m pytest -q` and report the real result. Never invent metrics.
7. **Simplicity.** Use the simplest method that answers a defined supervisory question. Rules before ML.
8. **Timestamps** are timezone-aware UTC.
9. **Teach.** This is a student team. In PR descriptions and summaries, explain *why* a design choice was made, in a few sentences.

## Layout
- `src/normalization/evidence_model.py` — canonical records (shared contract)
- `src/analytics/` — rules
- `data/synthetic/` — generator + golden dataset + ground truth
- `tests/` — pytest
- `web/` — Next.js demo (see `web/AGENTS.md`: this Next.js version has breaking changes, read its bundled docs first)

## Commands
```
python -m pytest -q
python -m src.analytics.execution_gaps
python -m data.synthetic.generator --seed 42
```
