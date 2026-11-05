import type { Metadata } from "next";
import Link from "next/link";

export const dynamic = "force-dynamic";

export const metadata: Metadata = {
  title: "Live Analysis — AudMi",
  description:
    "Findings computed by the local AudMi Python engine and served over the offline JSON API. Synthetic evidence, human review required. SIH 2026 problem statement SIH26157.",
};

const API_BASE = process.env.AUDMI_API_URL ?? "http://127.0.0.1:8000";

type Summary = {
  submission_sha256: string;
  ground_truth_sha256: string | null;
  quality: { status: string; error_count: number; warning_count: number };
  counts: Record<string, number>;
  rules: Array<{
    rule_id: string;
    version: string;
    title: string;
    level: string;
    capability: string;
    category: string;
    subject_type: string;
  }>;
  total_findings: number;
  finding_counts: Record<string, number>;
};

type Entity = {
  cse_id: string;
  name: string;
  peer_group: string;
  asset_count: number;
  alert_count: number;
  case_count: number;
  investigation_count: number;
  finding_count: number;
};

type Finding = {
  finding_id: string;
  rule_id: string;
  rule_version: string;
  level: string;
  cse_id: string;
  subject_type: string;
  subject_id: string;
  reason: string;
  supporting_record_ids: string[];
};

type FindingsPage = {
  total: number;
  count: number;
  offset: number;
  limit: number;
  findings: Finding[];
};

type Fetched<T> = { data: T } | { error: string };

async function getJson<T>(path: string): Promise<Fetched<T>> {
  try {
    const response = await fetch(`${API_BASE}${path}`, { cache: "no-store" });
    if (!response.ok) {
      return { error: `API returned HTTP ${response.status}` };
    }
    return { data: (await response.json()) as T };
  } catch {
    return { error: `Could not reach the local API at ${API_BASE}` };
  }
}

function levelBadge(level: string): string {
  if (level === "critical" || level === "high") return "badge-red";
  if (level === "medium") return "badge-amber";
  return "badge-gray";
}

function shortHash(value: string | null): string {
  return value ? `${value.slice(0, 12)}…` : "not available";
}

function Stat({ value, label }: { value: string | number; label: string }) {
  return (
    <div className="card stat">
      <div className="stat-value">{value}</div>
      <div className="stat-label">{label}</div>
    </div>
  );
}

export default async function LivePage({
  searchParams,
}: {
  searchParams: Promise<{ cse?: string | string[]; rule?: string | string[] }>;
}) {
  const params = await searchParams;
  const selectedCse = typeof params.cse === "string" ? params.cse : "";
  const selectedRule = typeof params.rule === "string" ? params.rule : "";

  const query = new URLSearchParams({ limit: "100" });
  if (selectedCse) query.set("cse_id", selectedCse);
  if (selectedRule) query.set("rule_id", selectedRule);

  const [summaryResult, entitiesResult, findingsResult] = await Promise.all([
    getJson<Summary>("/summary"),
    getJson<{ entities: Entity[] }>("/entities"),
    getJson<FindingsPage>(`/findings?${query.toString()}`),
  ]);

  const header = (
    <div className="page-header" id="live-header">
      <div className="container">
        <span className="section-label">Live Local Analysis</span>
        <h1 className="page-title">Findings from the Python engine</h1>
        <p className="page-subtitle">
          This screen reads the local AudMi JSON API. Every row below was computed
          from the synthetic evidence on disk, not copied from the demo fixtures.
        </p>
      </div>
    </div>
  );

  if ("error" in summaryResult) {
    return (
      <>
        {header}
        <section className="section-sm">
          <div className="container">
            <div className="demo-warning" id="live-unavailable">
              <div className="demo-warning-title">⚠️ LOCAL API NOT REACHABLE</div>
              <div className="demo-warning-text">
                <p>{summaryResult.error}</p>
                <p>Start it from the repository root, then reload this page:</p>
                <pre className="mono">python -m src.api --port 8000</pre>
                <p>
                  The API binds to loopback only and makes no network calls. The{" "}
                  <Link href="/demo">demo dashboard</Link> still works without it,
                  using illustrative fixtures.
                </p>
              </div>
            </div>
          </div>
        </section>
      </>
    );
  }

  const summary = summaryResult.data;
  const entities = "error" in entitiesResult ? [] : entitiesResult.data.entities;
  const findings = "error" in findingsResult ? null : findingsResult.data;

  return (
    <>
      {header}
      <section className="section-sm" id="live-content">
        <div className="container">
          <div className="demo-warning" id="live-notice">
            <div className="demo-warning-title">LIVE RESULTS — SYNTHETIC EVIDENCE</div>
            <div className="demo-warning-text">
              <ul>
                <li>
                  Data is generated by the deterministic synthetic generator and
                  scored by the same rules the tests run.
                </li>
                <li>
                  Findings are potential indicators for human review, never
                  compliance verdicts. Missing evidence is not proof of missing
                  activity.
                </li>
                <li>
                  Submission SHA-256: <code className="mono">{shortHash(summary.submission_sha256)}</code>{" "}
                  · data quality: {summary.quality.status}
                </li>
              </ul>
            </div>
          </div>

          <div className="grid-4 mb-6">
            <Stat value={summary.total_findings} label="Findings" />
            <Stat value={summary.rules.length} label="Active Rules" />
            <Stat value={summary.counts.cases ?? 0} label="Cases" />
            <Stat value={summary.counts.alerts ?? 0} label="Alerts" />
          </div>

          <div className="card mb-6" id="live-filters">
            <form method="get" className="filter-bar" style={{ marginBottom: 0 }}>
              <label htmlFor="live-cse" style={{ fontSize: "var(--text-sm)" }}>
                Entity
              </label>
              <select
                id="live-cse"
                name="cse"
                className="filter-select"
                defaultValue={selectedCse}
              >
                <option value="">All entities</option>
                {entities.map((entity) => (
                  <option key={entity.cse_id} value={entity.cse_id}>
                    {entity.cse_id} — {entity.name}
                  </option>
                ))}
              </select>

              <label htmlFor="live-rule" style={{ fontSize: "var(--text-sm)" }}>
                Rule
              </label>
              <select
                id="live-rule"
                name="rule"
                className="filter-select"
                defaultValue={selectedRule}
              >
                <option value="">All rules</option>
                {summary.rules.map((rule) => (
                  <option key={rule.rule_id} value={rule.rule_id}>
                    {rule.rule_id} (v{rule.version})
                  </option>
                ))}
              </select>

              <button type="submit" className="btn btn-primary btn-sm">
                Apply filters
              </button>
              <Link href="/live" className="btn btn-ghost btn-sm">
                Reset
              </Link>
            </form>
          </div>

          <div className="card" id="live-findings">
            <h2 style={{ fontSize: "var(--text-sm)", fontWeight: 600, marginBottom: "var(--sp-4)" }}>
              {findings ? findings.total : 0} finding
              {findings && findings.total === 1 ? "" : "s"}
              {findings && findings.total > findings.count
                ? ` (showing ${findings.count}; narrow the filters to see the rest)`
                : ""}
            </h2>
            <div className="table-wrap">
              <table className="table">
                <thead>
                  <tr>
                    <th>Finding</th>
                    <th>Entity</th>
                    <th>Rule</th>
                    <th>Level</th>
                    <th>Subject</th>
                    <th>Why it may warrant review</th>
                  </tr>
                </thead>
                <tbody>
                  {!findings || findings.findings.length === 0 ? (
                    <tr>
                      <td colSpan={6} style={{ textAlign: "center", color: "var(--text-muted)", padding: "var(--sp-8)" }}>
                        No findings match the current filters.
                      </td>
                    </tr>
                  ) : (
                    findings.findings.map((finding) => (
                      <tr key={finding.finding_id} id={`live-row-${finding.finding_id}`}>
                        <td><code className="mono">{finding.finding_id}</code></td>
                        <td><code className="mono">{finding.cse_id}</code></td>
                        <td>
                          <code className="mono">{finding.rule_id}</code>
                          <div style={{ fontSize: "var(--text-xs)", color: "var(--text-muted)" }}>
                            v{finding.rule_version}
                          </div>
                        </td>
                        <td>
                          <span className={`badge ${levelBadge(finding.level)}`}>
                            {finding.level}
                          </span>
                        </td>
                        <td><code className="mono">{finding.subject_id}</code></td>
                        <td style={{ maxWidth: 360 }}>{finding.reason}</td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>

          <div className="card mt-6" id="live-entities">
            <h2 style={{ fontSize: "var(--text-sm)", fontWeight: 600, marginBottom: "var(--sp-4)" }}>
              Entity activity and finding counts
            </h2>
            <div className="table-wrap">
              <table className="table">
                <thead>
                  <tr>
                    <th>Entity</th>
                    <th>Peer group</th>
                    <th>Assets</th>
                    <th>Alerts</th>
                    <th>Cases</th>
                    <th>Investigations</th>
                    <th>Findings</th>
                  </tr>
                </thead>
                <tbody>
                  {entities.map((entity) => (
                    <tr key={entity.cse_id}>
                      <td><code className="mono">{entity.cse_id}</code></td>
                      <td>{entity.peer_group}</td>
                      <td>{entity.asset_count}</td>
                      <td>{entity.alert_count.toLocaleString()}</td>
                      <td>{entity.case_count}</td>
                      <td>{entity.investigation_count}</td>
                      <td>
                        <span className={`badge ${entity.finding_count > 0 ? "badge-amber" : "badge-gray"}`}>
                          {entity.finding_count}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </section>
    </>
  );
}
