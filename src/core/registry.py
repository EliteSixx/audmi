"""Rule registry: loads Sigma-like rule definitions from ``rules/*.yaml``.

Keeping thresholds in versioned YAML (not in Python constants) means an
examiner can read what a rule does and which numbers it uses without reading
code, and every finding can cite the exact rule version that produced it.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any, Iterator, Mapping

import yaml

from src.core.findings import Capability, Category, SubjectType


DEFAULT_RULES_DIR = Path(__file__).resolve().parents[2] / "rules"

STATUSES = frozenset({"experimental", "test", "stable", "deprecated"})
LEVELS = frozenset({"informational", "low", "medium", "high", "critical"})
REQUIRED_KEYS = (
    "id", "title", "version", "status", "level", "capability", "category",
    "subject_type", "description", "parameters", "false_positives",
)
_VERSION_PATTERN = re.compile(r"^\d+\.\d+\.\d+$")


class RuleDefinitionError(ValueError):
    """A rule file is missing a field or has an invalid value."""


@dataclass(frozen=True, slots=True)
class Rule:
    id: str
    title: str
    version: str
    status: str
    level: str
    capability: Capability
    category: Category
    subject_type: SubjectType
    description: str
    parameters: Mapping[str, Any]
    false_positives: tuple[str, ...]
    source_path: Path | None = None

    def param(self, name: str) -> Any:
        """Return a parameter, failing loudly if the YAML does not define it."""
        try:
            return self.parameters[name]
        except KeyError:
            raise RuleDefinitionError(
                f"rule {self.id!r} has no parameter {name!r}"
            ) from None


def rule_from_dict(raw: Mapping[str, Any], source_path: Path | None = None) -> Rule:
    where = source_path or "<dict>"
    if not isinstance(raw, Mapping):
        raise RuleDefinitionError(f"{where}: rule file must contain a mapping")
    missing = [key for key in REQUIRED_KEYS if key not in raw]
    if missing:
        raise RuleDefinitionError(f"{where}: missing keys {missing}")
    for key in ("id", "title", "description"):
        if not isinstance(raw[key], str) or not raw[key].strip():
            raise RuleDefinitionError(f"{where}: {key} must be a non-empty string")
    version = str(raw["version"])
    if not _VERSION_PATTERN.match(version):
        raise RuleDefinitionError(f"{where}: version must look like 1.0.0, got {version!r}")
    if raw["status"] not in STATUSES:
        raise RuleDefinitionError(f"{where}: status must be one of {sorted(STATUSES)}")
    if raw["level"] not in LEVELS:
        raise RuleDefinitionError(f"{where}: level must be one of {sorted(LEVELS)}")
    if not isinstance(raw["parameters"], Mapping):
        raise RuleDefinitionError(f"{where}: parameters must be a mapping")
    if not isinstance(raw["false_positives"], list):
        raise RuleDefinitionError(f"{where}: false_positives must be a list")
    try:
        capability = Capability(raw["capability"])
        category = Category(raw["category"])
        subject_type = SubjectType(raw["subject_type"])
    except ValueError as error:
        raise RuleDefinitionError(f"{where}: {error}") from None
    return Rule(
        id=raw["id"],
        title=raw["title"],
        version=version,
        status=raw["status"],
        level=raw["level"],
        capability=capability,
        category=category,
        subject_type=subject_type,
        description=" ".join(raw["description"].split()),
        parameters=MappingProxyType(dict(raw["parameters"])),
        false_positives=tuple(str(item) for item in raw["false_positives"]),
        source_path=source_path,
    )


class RuleRegistry:
    """Read-only collection of rules keyed by rule id."""

    def __init__(self, rules: Mapping[str, Rule]) -> None:
        self._rules = dict(rules)

    def __getitem__(self, rule_id: str) -> Rule:
        try:
            return self._rules[rule_id]
        except KeyError:
            raise KeyError(f"no rule with id {rule_id!r} in the registry") from None

    def __contains__(self, rule_id: object) -> bool:
        return rule_id in self._rules

    def __iter__(self) -> Iterator[Rule]:
        return iter(sorted(self._rules.values(), key=lambda rule: rule.id))

    def __len__(self) -> int:
        return len(self._rules)

    def ids(self) -> list[str]:
        return sorted(self._rules)


def load_registry(rules_dir: str | Path = DEFAULT_RULES_DIR) -> RuleRegistry:
    """Load and validate every ``*.yaml`` rule in ``rules_dir``."""
    root = Path(rules_dir)
    if not root.is_dir():
        raise FileNotFoundError(f"rules directory not found: {root}")
    rules: dict[str, Rule] = {}
    for path in sorted(root.glob("*.yaml")):
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        rule = rule_from_dict(raw, path)
        if rule.id != path.stem:
            raise RuleDefinitionError(f"{path}: id {rule.id!r} must match the file name")
        if rule.id in rules:
            raise RuleDefinitionError(f"{path}: duplicate rule id {rule.id!r}")
        rules[rule.id] = rule
    return RuleRegistry(rules)
