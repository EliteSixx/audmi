import type { Metadata } from "next";
import Nav from "@/app/components/Nav";
import Footer from "@/app/components/Footer";
import "./globals.css";

export const metadata: Metadata = {
  title: "AudMi — Auditor's Microscope | Supervisory Analytics for SOC Assessment",
  description:
    "AudMi helps supervisory examiners inspect SOC assessment evidence, identify potential operational gaps, and prioritize findings for human review. SIH 2026 problem statement SIH26157.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        <Nav />
        <main>{children}</main>
        <Footer />
      </body>
    </html>
  );
}
