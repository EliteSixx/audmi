import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Installation Guide — AudMi Local Deployment",
  description:
    "How to run the AudMi prototype locally: ingestion and SHA-256 integrity, analytics, the offline loopback API, tests, and the Next.js interface. Distinguishes what works today from what is planned.",
};

export default function InstallationPage() {
  return (
    <>
      {/* Header */}
      <div className="page-header" id="installation-header">
        <div className="container">
          <span className="section-label">Local Deployment</span>
          <h1 className="page-title">Installation Guide</h1>
          <p className="page-subtitle">
            How to run the AudMi prototype locally. This page separates what is
            available today from what is still planned.
          </p>
        </div>
      </div>

      {/* Architecture */}
      <section className="section" id="architecture-section">
        <div className="container" style={{ maxWidth: 880 }}>
          <div className="section-header text-left" style={{ margin: "0 0 var(--sp-8)" }}>
            <span className="section-label">Architecture</span>
            <h2 className="section-title" style={{ textAlign: "left" }}>Local Deployment Stack</h2>
          </div>

          <div className="grid-2 mb-8">
            <div className="card">
              <h3 className="feature-title">Frontend</h3>
              <p className="feature-desc">Next.js, React, TypeScript</p>
              <p className="feature-desc mt-2" style={{ color: "var(--gray-400)" }}>Served from localhost:3000</p>
            </div>
            <div className="card">
              <h3 className="feature-title">Backend</h3>
              <p className="feature-desc">Python standard library HTTP server</p>
              <p className="feature-desc mt-2" style={{ color: "var(--gray-400)" }}>Loopback only: 127.0.0.1:8000</p>
            </div>
            <div className="card">
              <h3 className="feature-title">Evidence</h3>
              <p className="feature-desc">Canonical JSON files + SHA-256 manifest</p>
              <p className="feature-desc mt-2" style={{ color: "var(--gray-400)" }}>No external database server required</p>
            </div>
            <div className="card">
              <h3 className="feature-title">Analytics</h3>
              <p className="feature-desc">Four versioned, registry-driven rules</p>
              <p className="feature-desc mt-2" style={{ color: "var(--gray-400)" }}>Runs locally, no cloud APIs</p>
            </div>
          </div>

          <div className="card mb-8" id="local-workflow">
            <h3 style={{ fontSize: "var(--text-sm)", fontWeight: 600, marginBottom: "var(--sp-4)" }}>
              Local Workflow
            </h3>
            <div className="code-block">
              <div className="code-block-header">Current Architecture</div>
              Browser (localhost:3000) ↔ Local API (127.0.0.1:8000) ↔ Python analytics ↔ JSON evidence + SHA-256 manifest
            </div>
          </div>

          <div className="alert-banner alert-banner-info mb-8">
            <span className="alert-banner-icon">ℹ️</span>
            <div>
              The Python engine, ingestion layer, and loopback API are implemented and
              tested. The hosted <code className="mono">/demo</code> page runs entirely in
              the browser on fixtures; the <code className="mono">/live</code> page
              renders results from the local Python API.
            </div>
          </div>
        </div>
      </section>

      {/* Section A: Available Now */}
      <section className="section" id="available-now" style={{ background: "var(--white)" }}>
        <div className="container" style={{ maxWidth: 880 }}>
          <div style={{ display: "flex", alignItems: "center", gap: "var(--sp-3)", marginBottom: "var(--sp-6)" }}>
            <span className="status-badge status-available">✓ Available Now</span>
            <h2 className="section-title" style={{ marginBottom: 0 }}>A. Currently Available</h2>
          </div>

          <p className="feature-desc mb-6" style={{ lineHeight: 1.7 }}>
            The following components exist in the repository and are covered by tests:
          </p>

          <div className="step-list mb-8">
            <div className="step">
              <div className="step-number" style={{ background: "var(--teal-600)" }}>✓</div>
              <div className="step-content">
                <h3 className="step-title">Canonical evidence model</h3>
                <p className="step-desc">
                  Seven validated data structures (CSE, Asset, Alert, Case, Investigation, Escalation, Remediation) with timezone-aware UTC timestamps.
                  Located in <code className="mono">src/normalization/evidence_model.py</code>.
                </p>
              </div>
            </div>
            <div className="step">
              <div className="step-number" style={{ background: "var(--teal-600)" }}>✓</div>
              <div className="step-content">
                <h3 className="step-title">Synthetic generator v2</h3>
                <p className="step-desc">
                  Deterministic dataset with 6 CSEs, 300 assets, 10,000 alerts, 2,000 cases, 1,500 investigations, realistic escalation baselines, overlapping durations, decoys, peer groups, and separate ground truth.
                  Located in <code className="mono">data/synthetic/golden_dataset/</code>.
                </p>
              </div>
            </div>
            <div className="step">
              <div className="step-number" style={{ background: "var(--teal-600)" }}>✓</div>
              <div className="step-content">
                <h3 className="step-title">Execution-gap rules</h3>
                <p className="step-desc">
                  Missing escalations, unusually short investigations (robust log-duration median/MAD baseline), and repeated alerts without remediation.
                  Located in <code className="mono">src/analytics/execution_gaps.py</code>.
                </p>
              </div>
            </div>
            <div className="step">
              <div className="step-number" style={{ background: "var(--teal-600)" }}>✓</div>
              <div className="step-content">
                <h3 className="step-title">Negative-space rule</h3>
                <p className="step-desc">
                  Flags critical/high assets with no alerts while their CSE peer group is active. Located in <code className="mono">src/analytics/negative_space.py</code>.
                </p>
              </div>
            </div>
            <div className="step">
              <div className="step-number" style={{ background: "var(--teal-600)" }}>✓</div>
              <div className="step-content">
                <h3 className="step-title">Ingestion and integrity</h3>
                <p className="step-desc mb-4">
                  Validates every row, reports duplicates/broken references/timestamp-order problems, and writes a SHA-256 submission manifest.
                </p>
                <div className="code-block">
                  <div className="code-block-header">Shell</div>
                  python -m src.ingestion{"\n"}
                  <span style={{ color: "var(--navy-400)" }}># writes data/outputs/quality_report.json</span>{"\n"}
                  <span style={{ color: "var(--navy-400)" }}># and data/outputs/submission_manifest.json</span>
                </div>
              </div>
            </div>
            <div className="step">
              <div className="step-number" style={{ background: "var(--teal-600)" }}>✓</div>
              <div className="step-content">
                <h3 className="step-title">Offline loopback API and live screen</h3>
                <p className="step-desc mb-4">
                  Standard-library JSON API on <code className="mono">127.0.0.1</code>, plus a Next.js screen at <code className="mono">/live</code> that renders fresh results.
                </p>
                <div className="code-block">
                  <div className="code-block-header">Terminal 1 — API</div>
                  python -m src.api --port 8000{"\n\n"}
                  <div className="code-block-header">Terminal 2 — web</div>
                  cd web{"\n"}
                  npm install{"\n"}
                  npm run dev{"\n\n"}
                  <span style={{ color: "var(--navy-400)" }}># open http://localhost:3000/live</span>
                </div>
              </div>
            </div>
            <div className="step">
              <div className="step-number" style={{ background: "var(--teal-600)" }}>✓</div>
              <div className="step-content">
                <h3 className="step-title">Test suite and offline guard</h3>
                <p className="step-desc mb-4">
                  93 tests cover the model, generator, rules, registry, evaluator, ingestion, and API. The guard blocks network imports and remote assets in product code.
                </p>
                <div className="code-block">
                  <div className="code-block-header">Shell</div>
                  python -m pytest -q{"\n"}
                  python scripts/check_offline.py
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Section B: Setup steps */}
      <section className="section" id="local-setup">
        <div className="container" style={{ maxWidth: 880 }}>
          <div style={{ display: "flex", alignItems: "center", gap: "var(--sp-3)", marginBottom: "var(--sp-6)" }}>
            <span className="status-badge status-available">✓ Runnable</span>
            <h2 className="section-title" style={{ marginBottom: 0 }}>B. Run It Locally</h2>
          </div>

          <div className="step-list mb-8">
            <div className="step">
              <div className="step-number">1</div>
              <div className="step-content">
                <h3 className="step-title">Obtain the repository</h3>
                <p className="step-desc mb-4">
                  Clone the repository. Cloning and dependency installation need connectivity; everything after that can run offline.
                </p>
                <div className="code-block">
                  <div className="code-block-header">Shell</div>
                  git clone https://github.com/EliteSixx/audmi.git{"\n"}
                  cd audmi
                </div>
              </div>
            </div>

            <div className="step">
              <div className="step-number">2</div>
              <div className="step-content">
                <h3 className="step-title">Install runtime dependencies</h3>
                <p className="step-desc mb-4">
                  Python 3.11+ and Node.js 18+ are required. The Python analytics use the standard library plus PyYAML (for rule files) and pytest.
                </p>
                <div className="grid-2">
                  <div className="code-block">
                    <div className="code-block-header">Python</div>
                    python -m venv .venv{"\n"}
                    <span style={{ color: "var(--navy-400)" }}># Windows PowerShell:</span>{"\n"}
                    .\.venv\Scripts\Activate.ps1{"\n"}
                    <span style={{ color: "var(--navy-400)" }}># Linux/macOS:</span>{"\n"}
                    <span style={{ color: "var(--navy-400)" }}># source .venv/bin/activate</span>{"\n"}
                    pip install -r requirements.txt
                  </div>
                  <div className="code-block">
                    <div className="code-block-header">Frontend</div>
                    cd web{"\n"}
                    npm install
                  </div>
                </div>
              </div>
            </div>

            <div className="step">
              <div className="step-number">3</div>
              <div className="step-content">
                <h3 className="step-title">Validate the submission and run the rules</h3>
                <p className="step-desc mb-4">
                  Ingestion first, then analytics and the ground-truth evaluation.
                </p>
                <div className="code-block">
                  <div className="code-block-header">Shell</div>
                  python -m src.ingestion{"\n"}
                  python -m src.analytics.execution_gaps{"\n"}
                  python -m src.validation.evaluate
                </div>
              </div>
            </div>

            <div className="step">
              <div className="step-number">4</div>
              <div className="step-content">
                <h3 className="step-title">Start the backend API</h3>
                <p className="step-desc mb-4">
                  The API serves JSON on loopback and reads only the local evidence directory.
                </p>
                <div className="code-block">
                  <div className="code-block-header">Shell</div>
                  python -m src.api --port 8000
                </div>
              </div>
            </div>

            <div className="step">
              <div className="step-number">5</div>
              <div className="step-content">
                <h3 className="step-title">Start the frontend</h3>
                <p className="step-desc mb-4">
                  Next.js serves the fixture demo and the live analysis screen.
                </p>
                <div className="code-block">
                  <div className="code-block-header">Shell</div>
                  cd web{"\n"}
                  npm run dev
                </div>
              </div>
            </div>

            <div className="step">
              <div className="step-number">6</div>
              <div className="step-content">
                <h3 className="step-title">Open the local URL</h3>
                <p className="step-desc">
                  <code className="mono">http://localhost:3000/demo</code> for fixtures, or{" "}
                  <code className="mono">http://localhost:3000/live</code> for engine results.
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Section C: Planned */}
      <section className="section" id="planned-local" style={{ background: "var(--white)" }}>
        <div className="container" style={{ maxWidth: 880 }}>
          <div style={{ display: "flex", alignItems: "center", gap: "var(--sp-3)", marginBottom: "var(--sp-6)" }}>
            <span className="status-badge status-planned">◐ Planned</span>
            <h2 className="section-title" style={{ marginBottom: 0 }}>C. Not Yet Available</h2>
          </div>

          <div className="alert-banner alert-banner-warning mb-6">
            <span className="alert-banner-icon">⚠️</span>
            <div>
              These items are design goals. Do not assume they work yet; the
              commands above are the current runnable set.
            </div>
          </div>

          <div className="step-list">
            <div className="step">
              <div className="step-number">1</div>
              <div className="step-content">
                <h3 className="step-title">CSV import and persistent storage</h3>
                <p className="step-desc">
                  The prototype ingests canonical JSON. A CSV column-mapping import and a
                  SQLite/DuckDB store are planned.
                </p>
              </div>
            </div>
            <div className="step">
              <div className="step-number">2</div>
              <div className="step-content">
                <h3 className="step-title">Review write-actions and audit log</h3>
                <p className="step-desc">
                  Confirm/dismiss/note actions with an audit trail are planned. The API is
                  currently read-only.
                </p>
              </div>
            </div>
            <div className="step">
              <div className="step-number">3</div>
              <div className="step-content">
                <h3 className="step-title">More analytics</h3>
                <p className="step-desc">
                  Critical alerts closed unusually fast, closure bursts, analyst-level
                  patterns, template/near-duplicate notes, ATT&amp;CK coverage mapping, and
                  broader peer percentiles are planned.
                </p>
              </div>
            </div>
            <div className="step">
              <div className="step-number">4</div>
              <div className="step-content">
                <h3 className="step-title">Packaged, air-gapped install</h3>
                <p className="step-desc">
                  A bundled offline image tested with networking disabled is not yet built.
                  See section D for the current offline status.
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Section D: Offline Operation */}
      <section className="section" id="offline-operation">
        <div className="container" style={{ maxWidth: 880 }}>
          <div style={{ display: "flex", alignItems: "center", gap: "var(--sp-3)", marginBottom: "var(--sp-6)" }}>
            <span className="status-badge status-planned">◐ Partial</span>
            <h2 className="section-title" style={{ marginBottom: 0 }}>D. Offline Operation</h2>
          </div>

          <p className="feature-desc mb-6" style={{ lineHeight: 1.7 }}>
            Product code makes no outbound calls. Ingestion, analytics, the API, and the
            UI all run from local files. What is missing is a verified, packaged
            air-gapped installation.
          </p>

          <div className="grid-2 mb-6">
            <div className="card">
              <h3 className="feature-title" style={{ color: "var(--teal-600)" }}>Runs Without the Internet</h3>
              <ul style={{ paddingLeft: "var(--sp-5)", listStyle: "disc" }}>
                <li className="feature-desc mb-2">Evidence ingestion and normalization</li>
                <li className="feature-desc mb-2">All four supervisory-analytics rules</li>
                <li className="feature-desc mb-2">Finding generation and local JSON API</li>
                <li className="feature-desc mb-2">Demo and live findings screens</li>
                <li className="feature-desc">SHA-256 submission manifest</li>
              </ul>
            </div>
            <div className="card">
              <h3 className="feature-title" style={{ color: "var(--amber-600)" }}>Requires Internet</h3>
              <ul style={{ paddingLeft: "var(--sp-5)", listStyle: "disc" }}>
                <li className="feature-desc mb-2">Initial setup: cloning the repository</li>
                <li className="feature-desc mb-2">Dependency installation (pip, npm)</li>
                <li className="feature-desc mb-2">Software updates</li>
              </ul>
              <p className="feature-desc mt-4" style={{ fontStyle: "italic" }}>
                These can be performed in advance on a connected machine.
              </p>
            </div>
          </div>

          <div className="alert-banner alert-banner-info">
            <span className="alert-banner-icon">ℹ️</span>
            <div>
              <code className="mono">python scripts/check_offline.py</code> fails CI if
              product code imports a network library or loads a remote asset. This is a
              static guard, not a substitute for testing on an isolated machine.
            </div>
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="section-sm" id="installation-cta" style={{ textAlign: "center" }}>
        <div className="container">
          <p className="feature-desc mb-6" style={{ maxWidth: 560, margin: "0 auto var(--sp-6)" }}>
            Explore the fixture demo, or run the Python API to see live engine results.
          </p>
          <div className="hero-actions">
            <Link href="/demo" className="btn btn-accent btn-lg" id="install-cta-demo">
              Try the Demo →
            </Link>
            <Link href="/live" className="btn btn-outline btn-lg" id="install-cta-live">
              Open Live Analysis
            </Link>
          </div>
        </div>
      </section>
    </>
  );
}
