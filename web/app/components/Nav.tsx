"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";

const links = [
  { href: "/", label: "Home" },
  { href: "/how-to-use", label: "How to Use" },
  { href: "/demo", label: "Demo" },
  { href: "/live", label: "Live Analysis" },
  { href: "/installation", label: "Installation" },
];

export default function Nav() {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);

  return (
    <nav className="nav" role="navigation" aria-label="Main navigation">
      <div className="nav-inner">
        <Link href="/" className="nav-brand" id="nav-brand">
          <span className="nav-brand-icon" aria-hidden="true">A</span>
          AudMi
        </Link>

        <button
          className="nav-mobile-toggle"
          onClick={() => setOpen(!open)}
          aria-label="Toggle navigation menu"
          aria-expanded={open}
          id="nav-mobile-toggle"
        >
          <svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="2">
            {open ? (
              <path d="M5 5l10 10M15 5L5 15" />
            ) : (
              <path d="M3 5h14M3 10h14M3 15h14" />
            )}
          </svg>
        </button>

        <div className={`nav-links${open ? " open" : ""}`} id="nav-links">
          {links.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              className={`nav-link${pathname === link.href ? " active" : ""}`}
              id={`nav-link-${link.href.replace("/", "") || "home"}`}
              onClick={() => setOpen(false)}
            >
              {link.label}
            </Link>
          ))}
          <Link
            href="/demo"
            className="btn btn-accent btn-sm"
            id="nav-cta-demo"
            onClick={() => setOpen(false)}
          >
            Explore Demo →
          </Link>
        </div>
      </div>
    </nav>
  );
}
