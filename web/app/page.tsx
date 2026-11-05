import Link from "next/link";

const dimensions = [
  { icon: "🎯", title: "Threat Detection", desc: "Assess whether detection mechanisms are generating expected alert coverage across critical assets." },
  { icon: "🔍", title: "Investigation", desc: "Evaluate whether investigations are proportionate in depth and duration to the severity of triggering alerts." },
  { icon: "📤", title: "Escalation", desc: "Identify cases where investigation evidence exists but no corresponding escalation record was submitted." },
  { icon: "🛡️", title: "Incident Response", desc: "Examine remediation coverage and response patterns across high-volume and recurring alert sources." },
  { icon: "⚙️", title: "Security Operations", desc: "Review operational workflows for consistency, completeness, and alignment with stated procedures." },
  { icon: "📋", title: "Governance & Oversight", desc: "Surface oversight indicators such as review cadence, audit trail completeness, and policy adherence." },
  { icon: "📊", title: "Operational Discipline", desc: "Detect deviations from baseline operational patterns through statistical and contextual analysis." },
  { icon: "🔄", title: "Cyber Resilience", desc: "Assess an entity's capacity to sustain detection and response capabilities under varying conditions." },
];

const capabilities = [
  { icon: "📐", title: "Execution-Gap Analysis", desc: "Identifies cases where expected workflow steps — such as escalation after investigation — are absent from the evidence record." },
  { icon: "👁️", title: "Negative-Space Analysis", desc: "Detects what is missing: critical assets with no alert activity, time periods with no cases, or expected records that do not exist." },
  { icon: "📈", title: "Contextual & Peer Benchmarking", desc: "Compares entity metrics against peer-group baselines using robust statistical methods rather than fixed thresholds." },
  { icon: "🔗", title: "Workflow Pattern Analysis", desc: "Analyzes the sequence and timing of investigation, escalation, and remediation records to surface unusual patterns." },
  { icon: "🏷️", title: "Evidence Traceability", desc: "Every finding links directly to the supporting record IDs, baselines, and reasoning that produced it." },
  { icon: "📌", title: "Supervisory Prioritization", desc: "Ranks findings by review priority so human examiners can focus on the patterns most likely to warrant attention." },
];

const workflowSteps = [
  "SOC Submissions",
  "Evidence Normalization",
  "Supervisory Analytics",
  "Evidence-Backed Findings",
  "Human Review",
];

export default function Home() {
  return (
    <>
      {/* Hero */}
      <section className="hero" id="hero">
        <div className="container">
          <span className="hero-tagline">SIH 2026 — SIH26157 · SAT-SA</span>
          <h1 className="hero-title">
            AudMi — Auditor&apos;s Microscope
          </h1>
          <p className="hero-desc">
            Inspect the evidence. Surface the gaps. Prioritize the review.
            <br />
            A supervisory analytics tool that helps human examiners identify potential operational gaps in SOC assessment submissions.
          </p>
          <div className="hero-actions">
            <Link href="/demo" className="btn btn-accent btn-lg" id="hero-cta-demo">
              Explore Demo →
            </Link>
            <Link href="/how-to-use" className="btn btn-outline btn-lg" id="hero-cta-how">
              How It Works
            </Link>
          </div>
        </div>
      </section>

      {/* Problem */}
      <section className="section" id="problem" style={{ background: "var(--white)" }}>
        <div className="container">
          <div className="section-header">
            <span className="section-label">The Challenge</span>
            <h2 className="section-title">Manual SOC Assessment Review Has Limits</h2>
            <p className="section-subtitle">
              Periodic SOC assessments from Critical Sector Entities generate large volumes of structured evidence — alerts, cases, investigations, escalations, and remediations. Human reviewers must identify operational gaps, verify procedural compliance, and prioritize follow-up across hundreds or thousands of records.
            </p>
          </div>
          <div className="grid-3">
            <div className="card card-flat" style={{ borderLeft: "3px solid var(--amber-400)" }}>
              <h3 className="feature-title">Volume</h3>
              <p className="feature-desc">
                A single entity may submit thousands of alert, case, and investigation records per assessment period. Reviewing each one manually is impractical.
              </p>
            </div>
            <div className="card card-flat" style={{ borderLeft: "3px solid var(--amber-400)" }}>
              <h3 className="feature-title">Subtlety</h3>
              <p className="feature-desc">
                Operational gaps are often not visible in individual records. They emerge from patterns — missing escalations, unusually short investigations, silent assets — that span many records.
              </p>
            </div>
            <div className="card card-flat" style={{ borderLeft: "3px solid var(--amber-400)" }}>
              <h3 className="feature-title">Consistency</h3>
              <p className="feature-desc">
                Different examiners may apply different thresholds and focus on different aspects. Analytics can provide a consistent baseline for supervisory review.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Solution */}
      <section className="section" id="solution">
        <div className="container">
          <div className="section-header">
            <span className="section-label">The Approach</span>
            <h2 className="section-title">Evidence-Backed Supervisory Analytics</h2>
            <p className="section-subtitle">
              AudMi processes structured SOC assessment submissions to surface potential operational gaps, provide contextual baselines, and help examiners prioritize their review.
            </p>
          </div>

          {/* Workflow */}
          <div className="card mb-8" id="workflow-pipeline">
            <div className="workflow">
              {workflowSteps.map((step, i) => (
                <span key={step} style={{ display: "contents" }}>
                  <span className="workflow-step">{step}</span>
                  {i < workflowSteps.length - 1 && <span className="workflow-arrow">→</span>}
                </span>
              ))}
            </div>
          </div>

          {/* Capabilities */}
          <div className="grid-3">
            {capabilities.map((cap) => (
              <div className="card" key={cap.title}>
                <div className="feature-icon feature-icon-teal">{cap.icon}</div>
                <h3 className="feature-title">{cap.title}</h3>
                <p className="feature-desc">{cap.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Dimensions */}
      <section className="section" id="dimensions" style={{ background: "var(--white)" }}>
        <div className="container">
          <div className="section-header">
            <span className="section-label">Assessment Framework</span>
            <h2 className="section-title">Eight SAT-SA Assessment Dimensions</h2>
            <p className="section-subtitle">
              AudMi organizes its analysis around eight dimensions of SOC operational assessment, as defined by the SAT-SA framework.
            </p>
          </div>
          <div className="grid-4">
            {dimensions.map((dim) => (
              <div className="card" key={dim.title}>
                <div className="feature-icon feature-icon-navy">{dim.icon}</div>
                <h3 className="feature-title">{dim.title}</h3>
                <p className="feature-desc">{dim.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Human Examiner */}
      <section className="section" id="human-examiner">
        <div className="container">
          <div className="section-header">
            <span className="section-label">Design Principle</span>
            <h2 className="section-title">Supporting Human Examiners, Not Replacing Them</h2>
            <p className="section-subtitle">
              AudMi does not make compliance judgments, issue findings of non-compliance, or determine fault. All detected patterns are presented as potential signals that require human review and professional judgment.
            </p>
          </div>
          <div className="grid-2">
            <div className="card card-flat">
              <h3 className="feature-title">What AudMi Does</h3>
              <ul style={{ paddingLeft: "var(--sp-5)", listStyle: "disc" }}>
                <li className="feature-desc mb-2">Surfaces potential execution gaps and negative-space signals</li>
                <li className="feature-desc mb-2">Provides contextual baselines and peer comparisons</li>
                <li className="feature-desc mb-2">Links every finding to its supporting evidence records</li>
                <li className="feature-desc mb-2">Prioritizes findings for human review</li>
                <li className="feature-desc">Explains why each pattern may warrant attention</li>
              </ul>
            </div>
            <div className="card card-flat">
              <h3 className="feature-title">What AudMi Does Not Do</h3>
              <ul style={{ paddingLeft: "var(--sp-5)", listStyle: "disc" }}>
                <li className="feature-desc mb-2">Does not make final compliance or non-compliance determinations</li>
                <li className="feature-desc mb-2">Does not attribute intent or assign blame</li>
                <li className="feature-desc mb-2">Does not operate as a real-time SIEM or SOC replacement</li>
                <li className="feature-desc mb-2">Does not replace the examiner&apos;s professional judgment</li>
                <li className="feature-desc">Does not claim government endorsement or adoption</li>
              </ul>
            </div>
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="section" id="cta-section" style={{ background: "var(--navy-950)", color: "var(--white)", textAlign: "center" }}>
        <div className="container">
          <h2 style={{ fontSize: "var(--text-3xl)", fontWeight: 700, marginBottom: "var(--sp-4)", letterSpacing: "-.02em" }}>
            Ready to Explore?
          </h2>
          <p style={{ color: "var(--navy-200)", maxWidth: 560, margin: "0 auto var(--sp-8)", lineHeight: 1.7 }}>
            Try the interactive demonstration with synthetic data, or read the installation guide for the planned local deployment.
          </p>
          <div className="hero-actions">
            <Link href="/demo" className="btn btn-accent btn-lg" id="cta-explore-demo">
              Interactive Demo →
            </Link>
            <Link href="/installation" className="btn btn-outline btn-lg" id="cta-installation" style={{ borderColor: "var(--navy-600)", color: "var(--navy-100)" }}>
              Installation Guide
            </Link>
          </div>
        </div>
      </section>
    </>
  );
}
