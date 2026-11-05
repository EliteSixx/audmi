"""Fail if product code reaches for the network or a CDN.

AudMi must run air-gapped (AGENTS.md rule 4). This check is deliberately
simple and conservative: it catches the mistakes we are most likely to make
(importing an HTTP client, or pulling a font/script from a CDN) without trying
to prove the absence of every possible network call.

Run locally or in CI:

    python scripts/check_offline.py
"""

from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]

PYTHON_ROOTS = (REPOSITORY_ROOT / "src", REPOSITORY_ROOT / "data" / "synthetic")
WEB_ROOT = REPOSITORY_ROOT / "web" / "app"

# Modules that make outbound network calls. ``http.server`` is allowed: the
# local API listens on loopback and never calls out.
FORBIDDEN_MODULES = frozenset(
    {"requests", "httpx", "aiohttp", "urllib.request", "socket", "ftplib", "telnetlib"}
)

# Hosts that would make the UI depend on the internet at render time.
FORBIDDEN_URL_PATTERNS = (
    re.compile(r"fonts\.googleapis\.com", re.IGNORECASE),
    re.compile(r"fonts\.gstatic\.com", re.IGNORECASE),
    re.compile(r"cdn\.jsdelivr\.net", re.IGNORECASE),
    re.compile(r"unpkg\.com", re.IGNORECASE),
    re.compile(r"cdnjs\.cloudflare\.com", re.IGNORECASE),
    re.compile(r"api\.openai\.com", re.IGNORECASE),
    re.compile(r"api\.anthropic\.com", re.IGNORECASE),
    re.compile(r"generativelanguage\.googleapis\.com", re.IGNORECASE),
)

WEB_SUFFIXES = {".ts", ".tsx", ".js", ".jsx", ".css", ".html"}


def _python_files() -> list[Path]:
    files: list[Path] = []
    for root in PYTHON_ROOTS:
        if root.is_dir():
            files.extend(sorted(root.rglob("*.py")))
    return files


def check_python_imports() -> list[str]:
    problems: list[str] = []
    for path in _python_files():
        relative = path.relative_to(REPOSITORY_ROOT)
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(relative))
        except SyntaxError as error:
            problems.append(f"{relative}: cannot parse Python ({error})")
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                names = [node.module]
            else:
                continue
            for name in names:
                if name in FORBIDDEN_MODULES:
                    problems.append(
                        f"{relative}:{node.lineno}: forbidden network import {name!r}"
                    )
    return problems


def check_web_assets() -> list[str]:
    problems: list[str] = []
    if not WEB_ROOT.is_dir():
        return problems
    for path in sorted(WEB_ROOT.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in WEB_SUFFIXES:
            continue
        relative = path.relative_to(REPOSITORY_ROOT)
        text = path.read_text(encoding="utf-8", errors="replace")
        for lineno, line in enumerate(text.splitlines(), start=1):
            for pattern in FORBIDDEN_URL_PATTERNS:
                if pattern.search(line):
                    problems.append(
                        f"{relative}:{lineno}: remote dependency {pattern.pattern}"
                    )
    return problems


def main() -> int:
    problems = check_python_imports() + check_web_assets()
    if problems:
        print("Offline-safety check failed:\n")
        for problem in problems:
            print(f"  - {problem}")
        print("\nProduct code must not call the network or load remote assets.")
        return 1
    print("Offline-safety check passed: no network imports or remote assets found.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
