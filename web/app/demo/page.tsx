"use client";

import { useState, useMemo } from "react";
import {
  cseEntities,
  assessmentDimensions,
  findings as allFindings,
  reviewQueue,
  trendData,
  categorySummary,
  signalCategoryLabels,
  priorityColors,
  statusLabels,
  riskColors,
  type CSEEntity,
  type Finding,
  type SignalCategory,
  type ReviewPriority,
} from "@/app/data/mock-data";

// ─── Sub-components ──────────────────────────────────────────────

function DemoWarning() {
  return (
    <div className="demo-warning" id="demo-warning">
      <div className="demo-warning-title">
        ⚠️ ONLINE DEMONSTRATION — NOT THE OFFLINE PRODUCTION BUILD
      </div>
      <div className="demo-warning-text">
        <ul>
          <li>This hosted version requires internet access and runs entirely in the browser.</li>
          <li>All data shown is synthetic and illustrative — not connected to any real CSE, SOC, SIEM, or government network.</li>
          <li>This demo does not demonstrate air-gapped or offline operation.</li>
          <li>The full AudMi application is intended to support local, offline execution.</li>
          <li>Do not upload real or sensitive SOC data to this public demo.</li>
          <li>The Python analytics engine is not running — results shown are pre-computed fixtures.</li>
          <li>For results computed live by the Python engine, start the local API and open the Live Analysis screen.</li>
        </ul>
      </div>
    </div>
  );
}

function StatCard({ value, label, color }: { value: string | number; label: string; color?: string }) {
  return (
    <div className="card stat" id={`stat-${label.toLowerCase().replace(/\s+/g, "-")}`}>
      <div className="stat-value" style={color ? { color } : undefined}>{value}</div>
      <div className="stat-label">{label}</div>
    </div>
  );
}

function BarChart() {
  const maxFindings = Math.max(...trendData.map((d) => d.findings));
  return (
    <div className="card" id="trend-chart">
      <h3 style={{ fontSize: "var(--text-sm)", fontWeight: 600, marginBottom: "var(--sp-4)" }}>
        Monthly Findings Trend <span className="badge badge-gray" style={{ marginLeft: "var(--sp-2)" }}>Illustrative</span>
      </h3>
      <div className="chart-bar">
        {trendData.map((d) => (
          <div className="chart-bar-item" key={d.month}>
            <div className="chart-bar-value">{d.findings}</div>
            <div
              className="chart-bar-fill"
              style={{
                height: `${(d.findings / maxFindings) * 100}%`,
                background: d.findings >= 20 ? "var(--amber-400)" : "var(--teal-500)",
              }}
            />
            <div className="chart-bar-label">{d.month}</div>
          </div>
        ))}
      </div>
    </div>
  );
}

function CategoryChart() {
  const maxCount = Math.max(...categorySummary.map((c) => c.count));
  return (
    <div className="card" id="category-chart">
      <h3 style={{ fontSize: "var(--text-sm)", fontWeight: 600, marginBottom: "var(--sp-4)" }}>
        Findings by Category <span className="badge badge-gray" style={{ marginLeft: "var(--sp-2)" }}>Illustrative</span>
      </h3>
      <div className="chart-bar">
        {categorySummary.map((c) => (
          <div className="chart-bar-item" key={c.category}>
            <div className="chart-bar-value">{c.count}</div>
            <div
              className="chart-bar-fill"
              style={{
                height: `${(c.count / maxCount) * 100}%`,
                background: c.color,
              }}
            />
            <div className="chart-bar-label">{c.label}</div>
          </div>
        ))}
      </div>
    </div>
  );
}

function DimensionTable({ dimensions }: { dimensions: typeof assessmentDimensions }) {
  return (
    <div className="card" id="dimension-table">
      <h3 style={{ fontSize: "var(--text-sm)", fontWeight: 600, marginBottom: "var(--sp-4)" }}>
        Assessment Dimension Scores <span className="badge badge-gray" style={{ marginLeft: "var(--sp-2)" }}>Illustrative</span>
      </h3>
      <div className="table-wrap">
        <table className="table">
          <thead>
            <tr>
              <th>Dimension</th>
              <th>Score</th>
              <th>Findings</th>
              <th>Trend</th>
            </tr>
          </thead>
          <tbody>
            {dimensions.map((d) => (
              <tr key={d.dimension}>
                <td style={{ fontWeight: 500 }}>{d.dimension}</td>
                <td>
                  <div style={{ display: "flex", alignItems: "center", gap: "var(--sp-2)" }}>
                    <div
                      style={{
                        width: 60,
                        height: 6,
                        borderRadius: "var(--radius-full)",
                        background: "var(--gray-200)",
                        overflow: "hidden",
                      }}
                    >
                      <div
                        style={{
                          width: `${d.score}%`,
                          height: "100%",
                          borderRadius: "var(--radius-full)",
                          background:
                            d.score >= 75
                              ? "var(--teal-500)"
                              : d.score >= 55
                                ? "var(--amber-400)"
                                : "var(--red-400)",
                        }}
                      />
                    </div>
                    <span style={{ fontSize: "var(--text-sm)", fontWeight: 600 }}>{d.score}</span>
                  </div>
                </td>
                <td>
                  <span className={`badge ${d.findingsCount >= 8 ? "badge-red" : d.findingsCount >= 4 ? "badge-amber" : "badge-gray"}`}>
                    {d.findingsCount}
                  </span>
                </td>
                <td>
                  <span style={{ fontSize: "var(--text-sm)" }}>
                    {d.trend === "improving" ? "↑" : d.trend === "declining" ? "↓" : "→"} {d.trend}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function FindingDetail({ finding, onClose }: { finding: Finding; onClose: () => void }) {
  return (
    <div className="detail-panel" id="finding-detail">
      <div className="detail-header">
        <div className="detail-title">{finding.findingId} — {finding.signalLabel}</div>
        <button className="btn btn-ghost btn-sm" onClick={onClose} id="finding-detail-close">
          ✕ Close
        </button>
      </div>
      <div className="detail-body">
        <div className="detail-row">
          <div className="detail-label">Finding ID</div>
          <div className="detail-value"><code className="mono">{finding.findingId}</code></div>
        </div>
        <div className="detail-row">
          <div className="detail-label">CSE</div>
          <div className="detail-value"><code className="mono">{finding.cseId}</code></div>
        </div>
        <div className="detail-row">
          <div className="detail-label">Assessment Dimension</div>
          <div className="detail-value">{finding.dimension}</div>
        </div>
        <div className="detail-row">
          <div className="detail-label">Signal Category</div>
          <div className="detail-value">{signalCategoryLabels[finding.signalCategory]}</div>
        </div>
        <div className="detail-row">
          <div className="detail-label">Explanation</div>
          <div className="detail-value">{finding.explanation}</div>
        </div>
        <div className="detail-row">
          <div className="detail-label">Supporting Record IDs</div>
          <div className="detail-value">
            <div style={{ display: "flex", flexWrap: "wrap", gap: "var(--sp-1)" }}>
              {finding.supportingRecordIds.map((id) => (
                <code className="mono" key={id} style={{ fontSize: "var(--text-xs)" }}>{id}</code>
              ))}
            </div>
          </div>
        </div>
        <div className="detail-row">
          <div className="detail-label">Context / Baseline</div>
          <div className="detail-value">{finding.contextBaseline}</div>
        </div>
        <div className="detail-row">
          <div className="detail-label">Why This May Warrant Review</div>
          <div className="detail-value">{finding.whyItMatters}</div>
        </div>
        <div className="detail-row">
          <div className="detail-label">Suggested Review Priority</div>
          <div className="detail-value">
            <span className={`badge ${priorityColors[finding.reviewPriority]}`}>
              {finding.reviewPriority.toUpperCase()}
            </span>
          </div>
        </div>
        <div className="detail-row">
          <div className="detail-label">Examiner Decision Status</div>
          <div className="detail-value">
            <span className="badge badge-navy">{statusLabels[finding.reviewStatus]}</span>
            <span style={{ fontSize: "var(--text-xs)", color: "var(--text-muted)", marginLeft: "var(--sp-2)" }}>
              (Simulated — no real examiner action in this demo)
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}

// ─── Main Demo Page ──────────────────────────────────────────────

type DemoTab = "overview" | "findings" | "queue" | "dimensions";

export default function DemoPage() {
  const [selectedCse, setSelectedCse] = useState<string | null>(null);
  const [selectedFinding, setSelectedFinding] = useState<Finding | null>(null);
  const [activeTab, setActiveTab] = useState<DemoTab>("overview");
  const [categoryFilter, setCategoryFilter] = useState<string>("all");
  const [priorityFilter, setPriorityFilter] = useState<string>("all");
  const [queueSort, setQueueSort] = useState<"priority" | "cse" | "dimension">("priority");

  // Filter findings
  const filteredFindings = useMemo(() => {
    let result = allFindings;
    if (selectedCse) {
      result = result.filter((f) => f.cseId === selectedCse);
    }
    if (categoryFilter !== "all") {
      result = result.filter((f) => f.signalCategory === categoryFilter);
    }
    if (priorityFilter !== "all") {
      result = result.filter((f) => f.reviewPriority === priorityFilter);
    }
    return result;
  }, [selectedCse, categoryFilter, priorityFilter]);

  // Sort queue
  const sortedQueue = useMemo(() => {
    let items = selectedCse
      ? reviewQueue.filter((q) => q.cseId === selectedCse)
      : [...reviewQueue];
    if (queueSort === "cse") items.sort((a, b) => a.cseId.localeCompare(b.cseId));
    else if (queueSort === "dimension") items.sort((a, b) => a.dimension.localeCompare(b.dimension));
    return items;
  }, [selectedCse, queueSort]);

  const selectedCseData: CSEEntity | undefined = selectedCse
    ? cseEntities.find((c) => c.cseId === selectedCse)
    : undefined;

  const tabs: { key: DemoTab; label: string }[] = [
    { key: "overview", label: "Overview" },
    { key: "findings", label: `Findings (${filteredFindings.length})` },
    { key: "queue", label: "Review Queue" },
    { key: "dimensions", label: "Dimensions" },
  ];

  return (
    <div className="demo-layout" id="demo-page">
      {/* Sidebar */}
      <aside className="demo-sidebar" id="demo-sidebar">
        <div className="demo-sidebar-label">Entities</div>
        <div
          className={`demo-sidebar-item${!selectedCse ? " active" : ""}`}
          onClick={() => { setSelectedCse(null); setSelectedFinding(null); }}
          id="sidebar-all"
        >
          📊 All Entities
        </div>
        {cseEntities.map((cse) => (
          <div
            key={cse.cseId}
            className={`demo-sidebar-item${selectedCse === cse.cseId ? " active" : ""}`}
            onClick={() => { setSelectedCse(cse.cseId); setSelectedFinding(null); }}
            id={`sidebar-${cse.cseId}`}
          >
            <span className={`badge ${riskColors[cse.overallRisk]}`} style={{ width: 8, height: 8, padding: 0, borderRadius: "50%" }} />
            {cse.cseId}
          </div>
        ))}

        <div className="demo-sidebar-label mt-8">Quick Filters</div>
        <div className="demo-sidebar-label" style={{ textTransform: "none", letterSpacing: 0, fontWeight: 400, marginBottom: "var(--sp-2)" }}>
          Category
        </div>
        <select
          className="filter-select w-full mb-4"
          value={categoryFilter}
          onChange={(e) => setCategoryFilter(e.target.value)}
          id="filter-category"
        >
          <option value="all">All Categories</option>
          {(Object.keys(signalCategoryLabels) as SignalCategory[]).map((key) => (
            <option key={key} value={key}>{signalCategoryLabels[key]}</option>
          ))}
        </select>

        <div className="demo-sidebar-label" style={{ textTransform: "none", letterSpacing: 0, fontWeight: 400, marginBottom: "var(--sp-2)" }}>
          Priority
        </div>
        <select
          className="filter-select w-full"
          value={priorityFilter}
          onChange={(e) => setPriorityFilter(e.target.value)}
          id="filter-priority"
        >
          <option value="all">All Priorities</option>
          <option value="critical">Critical</option>
          <option value="high">High</option>
          <option value="moderate">Moderate</option>
          <option value="low">Low</option>
        </select>
      </aside>

      {/* Main content */}
      <div className="demo-main" id="demo-main">
        <DemoWarning />

        {/* Header */}
        <div style={{ marginBottom: "var(--sp-6)" }}>
          <h1 style={{ fontSize: "var(--text-2xl)", fontWeight: 700, color: "var(--primary)", marginBottom: "var(--sp-1)" }}>
            {selectedCseData
              ? `${selectedCseData.cseId} — ${selectedCseData.name}`
              : "Supervisory Dashboard"}
          </h1>
          <p style={{ fontSize: "var(--text-sm)", color: "var(--text-muted)" }}>
            {selectedCseData
              ? `${selectedCseData.sector} · ${selectedCseData.peerGroup} peer group`
              : "Overview of all sample Critical Sector Entities"}
          </p>
        </div>

        {/* Tabs */}
        <div className="tabs" id="demo-tabs">
          {tabs.map((tab) => (
            <button
              key={tab.key}
              className={`tab${activeTab === tab.key ? " active" : ""}`}
              onClick={() => { setActiveTab(tab.key); setSelectedFinding(null); }}
              id={`tab-${tab.key}`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Tab: Overview */}
        {activeTab === "overview" && (
          <div id="tab-content-overview">
            {/* Stats */}
            <div className="grid-4 mb-6">
              <StatCard
                value={selectedCseData ? selectedCseData.totalAssets : cseEntities.reduce((s, c) => s + c.totalAssets, 0)}
                label="Total Assets"
              />
              <StatCard
                value={selectedCseData ? selectedCseData.totalAlerts.toLocaleString() : cseEntities.reduce((s, c) => s + c.totalAlerts, 0).toLocaleString()}
                label="Total Alerts"
              />
              <StatCard
                value={selectedCseData ? selectedCseData.totalCases : cseEntities.reduce((s, c) => s + c.totalCases, 0).toLocaleString()}
                label="Total Cases"
              />
              <StatCard
                value={filteredFindings.length}
                label="Findings"
                color="var(--amber-500)"
              />
            </div>

            {/* Charts */}
            <div className="grid-2 mb-6">
              <BarChart />
              <CategoryChart />
            </div>

            {/* CSE Overview Table */}
            <div className="card" id="cse-overview-table">
              <h3 style={{ fontSize: "var(--text-sm)", fontWeight: 600, marginBottom: "var(--sp-4)" }}>
                Entity Overview
              </h3>
              <div className="table-wrap">
                <table className="table">
                  <thead>
                    <tr>
                      <th>CSE ID</th>
                      <th>Sector</th>
                      <th>Assets</th>
                      <th>Alerts</th>
                      <th>Cases</th>
                      <th>Risk</th>
                      <th>Findings</th>
                    </tr>
                  </thead>
                  <tbody>
                    {cseEntities.map((cse) => (
                      <tr
                        key={cse.cseId}
                        className="clickable"
                        onClick={() => { setSelectedCse(cse.cseId); setSelectedFinding(null); }}
                        id={`row-${cse.cseId}`}
                      >
                        <td><code className="mono">{cse.cseId}</code></td>
                        <td>{cse.sector}</td>
                        <td>{cse.totalAssets}</td>
                        <td>{cse.totalAlerts.toLocaleString()}</td>
                        <td>{cse.totalCases}</td>
                        <td><span className={`badge ${riskColors[cse.overallRisk]}`}>{cse.overallRisk}</span></td>
                        <td><span className={`badge ${cse.findingsCount >= 6 ? "badge-red" : cse.findingsCount >= 4 ? "badge-amber" : "badge-gray"}`}>{cse.findingsCount}</span></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {/* Tab: Findings */}
        {activeTab === "findings" && (
          <div id="tab-content-findings">
            {selectedFinding ? (
              <FindingDetail finding={selectedFinding} onClose={() => setSelectedFinding(null)} />
            ) : (
              <div className="card" id="findings-table">
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "var(--sp-4)", flexWrap: "wrap", gap: "var(--sp-3)" }}>
                  <h3 style={{ fontSize: "var(--text-sm)", fontWeight: 600 }}>
                    {filteredFindings.length} Finding{filteredFindings.length !== 1 ? "s" : ""}
                    {selectedCse ? ` for ${selectedCse}` : ""}
                  </h3>
                  <span className="badge badge-gray">Click a row to inspect details</span>
                </div>
                <div className="table-wrap">
                  <table className="table">
                    <thead>
                      <tr>
                        <th>ID</th>
                        <th>CSE</th>
                        <th>Signal</th>
                        <th>Dimension</th>
                        <th>Priority</th>
                        <th>Status</th>
                      </tr>
                    </thead>
                    <tbody>
                      {filteredFindings.length === 0 ? (
                        <tr>
                          <td colSpan={6} style={{ textAlign: "center", color: "var(--text-muted)", padding: "var(--sp-8)" }}>
                            No findings match the current filters.
                          </td>
                        </tr>
                      ) : (
                        filteredFindings.map((f) => (
                          <tr
                            key={f.findingId}
                            className="clickable"
                            onClick={() => setSelectedFinding(f)}
                            id={`finding-row-${f.findingId}`}
                          >
                            <td><code className="mono">{f.findingId}</code></td>
                            <td><code className="mono">{f.cseId}</code></td>
                            <td style={{ maxWidth: 200 }}>
                              <div className="truncate">{f.signalLabel}</div>
                            </td>
                            <td>{f.dimension}</td>
                            <td><span className={`badge ${priorityColors[f.reviewPriority]}`}>{f.reviewPriority}</span></td>
                            <td><span className="badge badge-navy">{statusLabels[f.reviewStatus]}</span></td>
                          </tr>
                        ))
                      )}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Tab: Review Queue */}
        {activeTab === "queue" && (
          <div id="tab-content-queue">
            <div className="card">
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "var(--sp-4)", flexWrap: "wrap", gap: "var(--sp-3)" }}>
                <h3 style={{ fontSize: "var(--text-sm)", fontWeight: 600 }}>
                  Review Priority Queue
                </h3>
                <div className="filter-bar" style={{ marginBottom: 0 }}>
                  <span style={{ fontSize: "var(--text-xs)", color: "var(--text-muted)" }}>Sort by:</span>
                  <select
                    className="filter-select"
                    value={queueSort}
                    onChange={(e) => setQueueSort(e.target.value as typeof queueSort)}
                    id="queue-sort"
                    style={{ minWidth: 120 }}
                  >
                    <option value="priority">Priority</option>
                    <option value="cse">CSE</option>
                    <option value="dimension">Dimension</option>
                  </select>
                </div>
              </div>
              <div className="table-wrap">
                <table className="table">
                  <thead>
                    <tr>
                      <th>#</th>
                      <th>Finding</th>
                      <th>CSE</th>
                      <th>Dimension</th>
                      <th>Priority</th>
                      <th>Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {sortedQueue.map((q, i) => (
                      <tr
                        key={q.findingId}
                        className="clickable"
                        onClick={() => {
                          const found = allFindings.find((f) => f.findingId === q.findingId);
                          if (found) {
                            setSelectedFinding(found);
                            setActiveTab("findings");
                          }
                        }}
                        id={`queue-row-${q.findingId}`}
                      >
                        <td style={{ color: "var(--text-muted)" }}>{i + 1}</td>
                        <td>
                          <code className="mono">{q.findingId}</code>
                          <div style={{ fontSize: "var(--text-xs)", color: "var(--text-muted)", marginTop: 2 }}>
                            {q.signalLabel}
                          </div>
                        </td>
                        <td><code className="mono">{q.cseId}</code></td>
                        <td>{q.dimension}</td>
                        <td><span className={`badge ${priorityColors[q.priority]}`}>{q.priority}</span></td>
                        <td><span className="badge badge-navy">{statusLabels[q.status]}</span></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {/* Tab: Dimensions */}
        {activeTab === "dimensions" && (
          <div id="tab-content-dimensions">
            <DimensionTable dimensions={assessmentDimensions} />
          </div>
        )}
      </div>
    </div>
  );
}
