import Link from "next/link";

export default function Footer() {
  return (
    <footer className="footer" role="contentinfo">
      <div className="container">
        <div className="footer-grid">
          <div>
            <div className="footer-brand">AudMi — Auditor&apos;s Microscope</div>
            <p className="footer-desc">
              Inspect the evidence. Surface the gaps. Prioritize the review.
              <br />
              <br />
              A supervisory analytics tool for SOC assessment review.
              AudMi supports human examiners — it does not replace them.
            </p>
          </div>

          <div>
            <div className="footer-heading">Navigation</div>
            <div className="footer-links">
              <Link href="/" id="footer-link-home">Home</Link>
              <Link href="/how-to-use" id="footer-link-how-to-use">How to Use</Link>
              <Link href="/demo" id="footer-link-demo">Interactive Demo</Link>
              <Link href="/installation" id="footer-link-installation">Installation Guide</Link>
            </div>
          </div>

          <div>
            <div className="footer-heading">Project</div>
            <div className="footer-links">
              <a
                href="https://github.com/EliteSixx/audmi"
                target="_blank"
                rel="noopener noreferrer"
                id="footer-link-github"
              >
                GitHub Repository ↗
              </a>
              <span>SIH 2026 — SIH26157</span>
              <span>SAT-SA Project</span>
            </div>
          </div>
        </div>

        <div className="footer-bottom">
          <span>AudMi is a research prototype. It has not been endorsed or adopted by any government agency.</span>
          <span>Built for SIH 2026 evaluation purposes.</span>
        </div>
      </div>
    </footer>
  );
}
