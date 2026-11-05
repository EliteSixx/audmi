import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Installation Guide — AudMi Local Deployment",
  description:
    "How to set up AudMi for local, offline-capable execution. Covers current project status, planned architecture, and intended local workflow.",
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
            How the AudMi application is intended to run locally. This page distinguishes between what is currently available and what is planned.
          </p>
        </div>
      </div>

      {/* Architecture */}
      <section className="section" id="architecture-section">
        <div className="container" style={{ maxWidth: 880 }}>
          <div className="section-header text-left" style={{ margin: "0 0 var(--sp-8)" }}>
            <span className="section-label">Intended Architecture</span>
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
              <p className="feature-desc">Python, FastAPI</p>
              <p className="feature-desc mt-2" style={{ color: "var(--gray-400)" }}>Served from localhost:8000</p>
            </div>
            <div className="card">
              <h3 className="feature-title">Database</h3>
              <p className="feature-desc">SQLite (initial local prototype)</p>
              <p className="feature-desc mt-2" style={{ color: "var(--gray-400)" }}>File-based, no external DB server</p>
            </div>
            <div className="card">
              <h3 className="feature-title">Analytics</h3>
              <p className="feature-desc">Python-based supervisory analytics</p>
              <p className="feature-desc mt-2" style={{ color: "var(--gray-400)" }}>Runs locally, no cloud APIs</p>
            </div>
          </div>

          {/* Local workflow */}
          <div className="card mb-8" id="local-workflow">
            <h3 style={{ fontSize: "var(--text-sm)", fontWeight: 600, marginBottom: "var(--sp-4)" }}>
              Intended Local Workflow
            </h3>
            <div className="code-block">
              <div className="code-block-header">Architecture Diagram</div>
              Browser (localhost:3000) ↔ Local API (localhost:8000) ↔ SQLite + Python Analytics
            </div>
          </div>

          <div className="alert-banner alert-banner-info mb-8">
            <span className="alert-banner-icon">ℹ️</span>
            <div>
              The full local application is under development. The online demo you see on this website runs entirely in the browser with pre-computed synthetic data and does not require or use the Python backend.
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
            The following components exist in the repository and have been validated with tests:
          </p>

          <div className="step-list mb-6">
            <div className="step">
              <div className="step-number" style={{ background: "var(--teal-600)" }}>✓</div>
              <div className="step-content">
                <h3 className="step-title">Canonical Evidence Model</h3>
                <p className="step-desc">
                  Seven validated data structures (CSE, Asset, Alert, Case, Investigation, Escalation, Remediation) with timezone-aware timestamps and referential identity.
                  Located in <code className="mono">src/normalization/evidence_model.py</code>.
                </p>
              </div>
            </div>
            <div className="step">
              <div className="step-number" style={{ background: "var(--teal-600)" }}>✓</div>
              <div className="step-content">
                <h3 className="step-title">Execution-Gap Analytics Module</h3>
                <p className="step-desc">
                  Detects missing escalations, unusually short investigations (using robust log-duration median/MAD baseline), and repeated alerts without remediation.
                  Located in <code className="mono">src/analytics/execution_gaps.py</code>.
                </p>
              </div>
            </div>
            <div className="step">
              <div className="step-number" style={{ background: "var(--teal-600)" }}>✓</div>
              <div className="step-content">
                <h3 className="step-title">Synthetic Golden Dataset</h3>
                <p className="step-desc">
                  Deterministic synthetic dataset with 6 CSEs, 300 assets, 10,000 alerts, 2,000 cases, and ground truth for validation.
                  Located in <code className="mono">data/synthetic/golden_dataset/</code>.
                </p>
              </div>
            </div>
            <div className="step">
              <div className="step-number" style={{ background: "var(--teal-600)" }}>✓</div>
              <div className="step-content">
                <h3 className="step-title">Test Suite</h3>
                <p className="step-desc">
                  Unit tests for the evidence model, execution-gap analytics, and synthetic data generator.
                  Located in <code className="mono">tests/</code>.
                </p>
              </div>
            </div>
            <div className="step">
              <div className="step-number" style={{ background: "var(--teal-600)" }}>✓</div>
              <div className="step-content">
                <h3 className="step-title">Online Demo Website</h3>
                <p className="step-desc">
                  This website — a Next.js/TypeScript frontend with pre-computed synthetic data for demonstration purposes.
                  Located in <code className="mono">web/</code>.
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Section B: Planned Local Execution */}
      <section className="section" id="planned-local">
        <div className="container" style={{ maxWidth: 880 }}>
          <div style={{ display: "flex", alignItems: "center", gap: "var(--sp-3)", marginBottom: "var(--sp-6)" }}>
            <span className="status-badge status-planned">◐ Planned</span>
            <h2 className="section-title" style={{ marginBottom: 0 }}>B. Planned Local Execution</h2>
          </div>

          <div className="alert-banner alert-banner-warning mb-6">
            <span className="alert-banner-icon">⚠️</span>
            <div>
              The following instructions describe the <strong>intended</strong> local setup process. Implementation is in progress. Commands and configuration files listed below are planned and pending validation. Do not assume they will work until the corresponding components are implemented.
            </div>
          </div>

          <p className="feature-desc mb-6" style={{ lineHeight: 1.7 }}>
            Once the local application is complete, the intended setup process is:
          </p>

          <div className="step-list mb-8">
            <div className="step">
              <div className="step-number">1</div>
              <div className="step-content">
                <h3 className="step-title">Obtain the repository</h3>
                <p className="step-desc mb-4">
                  Clone or download the AudMi repository from GitHub.
                </p>
                <div className="code-block">
                  <div className="code-block-header">Shell (planned)</div>
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
                  The project will require Python 3.11+ and Node.js 18+ as runtime dependencies. Exact dependency installation commands will be documented once the backend and API layer are implemented.
                </p>
                <div className="grid-2">
                  <div className="code-block">
                    <div className="code-block-header">Python (planned)</div>
                    python -m venv .venv{"\n"}
                    <span style={{ color: "var(--navy-400)" }}># Windows PowerShell:</span>{"\n"}
                    .\.venv\Scripts\Activate.ps1{"\n"}
                    <span style={{ color: "var(--navy-400)" }}># Linux/macOS:</span>{"\n"}
                    <span style={{ color: "var(--navy-400)" }}># source .venv/bin/activate</span>{"\n"}
                    pip install -r requirements.txt
                  </div>
                  <div className="code-block">
                    <div className="code-block-header">Frontend (planned)</div>
                    cd web{"\n"}
                    npm install
                  </div>
                </div>
              </div>
            </div>

            <div className="step">
              <div className="step-number">3</div>
              <div className="step-content">
                <h3 className="step-title">Configure the local environment</h3>
                <p className="step-desc">
                  Environment variables and configuration files will be documented as the backend API layer is implemented. The initial prototype is expected to use sensible defaults with minimal configuration.
                </p>
              </div>
            </div>

            <div className="step">
              <div className="step-number">4</div>
              <div className="step-content">
                <h3 className="step-title">Start the backend</h3>
                <p className="step-desc mb-4">
                  The Python FastAPI backend will serve the analytics API on localhost:8000.
                </p>
                <div className="code-block">
                  <div className="code-block-header">Shell (planned — command pending implementation)</div>
                  <span style={{ color: "var(--navy-400)" }}># Exact command will be documented once the API server is implemented</span>{"\n"}
                  <span style={{ color: "var(--navy-400)" }}># Expected pattern:</span>{"\n"}
                  python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
                </div>
              </div>
            </div>

            <div className="step">
              <div className="step-number">5</div>
              <div className="step-content">
                <h3 className="step-title">Start the frontend</h3>
                <p className="step-desc mb-4">
                  The Next.js frontend will be available on localhost:3000.
                </p>
                <div className="code-block">
                  <div className="code-block-header">Shell (the demo frontend currently works)</div>
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
                  Open <code className="mono">http://localhost:3000</code> in a browser.
                </p>
              </div>
            </div>

            <div className="step">
              <div className="step-number">7</div>
              <div className="step-content">
                <h3 className="step-title">Load sample data and run analytics</h3>
                <p className="step-desc">
                  Use the provided synthetic dataset or load SOC assessment submissions through the future import interface. Analytics will run locally through the Python backend.
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Section C: Offline Operation */}
      <section className="section" id="offline-operation" style={{ background: "var(--white)" }}>
        <div className="container" style={{ maxWidth: 880 }}>
          <div style={{ display: "flex", alignItems: "center", gap: "var(--sp-3)", marginBottom: "var(--sp-6)" }}>
            <span className="status-badge status-future">◯ Future</span>
            <h2 className="section-title" style={{ marginBottom: 0 }}>C. Offline Operation</h2>
          </div>

          <p className="feature-desc mb-6" style={{ lineHeight: 1.7 }}>
            Once the local application is fully implemented and its dependencies are installed, the core processing workflow is intended to run without internet connectivity.
          </p>

          <div className="grid-2 mb-6">
            <div className="card">
              <h3 className="feature-title" style={{ color: "var(--teal-600)" }}>Offline-Capable (planned)</h3>
              <ul style={{ paddingLeft: "var(--sp-5)", listStyle: "disc" }}>
                <li className="feature-desc mb-2">Evidence ingestion and normalization</li>
                <li className="feature-desc mb-2">Supervisory analytics (execution gaps, negative space, peer analysis)</li>
                <li className="feature-desc mb-2">Finding generation and prioritization</li>
                <li className="feature-desc mb-2">Dashboard and review interface</li>
                <li className="feature-desc">SQLite-based local storage</li>
              </ul>
            </div>
            <div className="card">
              <h3 className="feature-title" style={{ color: "var(--amber-600)" }}>Requires Internet</h3>
              <ul style={{ paddingLeft: "var(--sp-5)", listStyle: "disc" }}>
                <li className="feature-desc mb-2">Initial setup: cloning the repository</li>
                <li className="feature-desc mb-2">Dependency installation (pip, npm)</li>
                <li className="feature-desc mb-2">Any future model or data downloads</li>
                <li className="feature-desc">Software updates</li>
              </ul>
              <p className="feature-desc mt-4" style={{ fontStyle: "italic" }}>
                These can be performed in advance on a connected machine, after which the installed application can operate offline.
              </p>
            </div>
          </div>

          <div className="alert-banner alert-banner-info">
            <span className="alert-banner-icon">ℹ️</span>
            <div>
              Air-gapped deployment patterns (pre-packaging dependencies, bundled model weights) are planned but not yet implemented. The online demo you are viewing now requires internet access and does not demonstrate offline operation.
            </div>
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="section-sm" id="installation-cta" style={{ textAlign: "center" }}>
        <div className="container">
          <p className="feature-desc mb-6" style={{ maxWidth: 560, margin: "0 auto var(--sp-6)" }}>
            While the full local application is being developed, explore the online demonstration to preview the intended workflow.
          </p>
          <div className="hero-actions">
            <Link href="/demo" className="btn btn-accent btn-lg" id="install-cta-demo">
              Try the Online Demo →
            </Link>
            <a
              href="https://github.com/EliteSixx/audmi"
              target="_blank"
              rel="noopener noreferrer"
              className="btn btn-outline btn-lg"
              id="install-cta-github"
            >
              View on GitHub ↗
            </a>
          </div>
        </div>
      </section>
    </>
  );
}
