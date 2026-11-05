"""Negative-space detector: high-value assets that produce no alert activity.

"Negative space" is what the evidence does *not* contain. A critical asset that
has never raised an alert can mean it is genuinely quiet, but it can also mean
it was never onboarded, its sensor feed is broken, or the detection content does
not cover it. The supervisory question is therefore comparative: is this asset
silent while comparable assets in the same peer group are active?

The rule is intentionally narrow. It only looks at assets whose criticality
says they matter, in peer groups that are demonstrably active, and only when
the asset itself has no (or almost no) alerts. A silent asset in a quiet peer
group is not evidence of anything, so it is not flagged.

Findings are potential indicators for human review, not verdicts. A zero count
is not proof that nothing happened; it may be missing evidence.
"""

from __future__ import annotations

from collections import defaultdict

from src.analytics.common import (
    EvidenceRecords,
    median_absolute_deviation,
    new_finding,
)
from src.core.findings import Finding
from src.core.registry import Rule
from src.normalization.evidence_model import Asset


def find_negative_space_low_activity(
    records: EvidenceRecords, rule: Rule
) -> list[Finding]:
    """Flag critical/high assets with no alerts while their peers are active."""
    criticalities = set(rule.param("criticalities"))
    max_alert_count = rule.param("max_alert_count")
    min_peer_assets = rule.param("min_peer_assets")
    min_peer_median_alerts = rule.param("min_peer_median_alerts")
    max_supporting_peers = rule.param("max_supporting_peers")

    cse_by_id = {item.cse_id: item for item in records.cse}
    alert_count_by_asset: dict[str, int] = defaultdict(int)
    for alert in records.alerts:
        alert_count_by_asset[alert.asset_id] += 1

    # Peer groups are defined on the CSE, not the asset, so two CSEs in the same
    # sector/regulatory group can be compared even when their volumes differ.
    assets_by_peer_group: dict[str, list[Asset]] = defaultdict(list)
    for asset in records.assets:
        cse = cse_by_id.get(asset.cse_id)
        if cse is None:
            continue
        assets_by_peer_group[cse.peer_group].append(asset)

    findings: list[Finding] = []
    for asset in sorted(records.assets, key=lambda value: value.asset_id):
        cse = cse_by_id.get(asset.cse_id)
        if cse is None or asset.criticality not in criticalities:
            continue
        observed = alert_count_by_asset.get(asset.asset_id, 0)
        if observed > max_alert_count:
            continue

        peers = [
            peer for peer in assets_by_peer_group[cse.peer_group]
            if peer.asset_id != asset.asset_id
        ]
        if len(peers) < min_peer_assets:
            continue
        peer_counts = [float(alert_count_by_asset.get(peer.asset_id, 0)) for peer in peers]
        median, mad = median_absolute_deviation(peer_counts)
        if median < min_peer_median_alerts:
            # A quiet peer group tells us nothing about this asset.
            continue

        examples = sorted(
            peers,
            key=lambda peer: (-alert_count_by_asset.get(peer.asset_id, 0), peer.asset_id),
        )[:max_supporting_peers]
        supporting = (asset.asset_id,) + tuple(peer.asset_id for peer in examples)
        baseline = {
            "expectation": (
                "a critical or high asset in an active peer group should produce "
                "some alert or telemetry evidence"
            ),
            "method": "peer-group alert-volume comparison",
            "peer_group": cse.peer_group,
            "required_criticalities": sorted(criticalities),
            "peer_asset_count": len(peers),
            "peer_median_alert_count": round(median, 3),
            "peer_alert_count_mad": round(mad, 3),
            "minimum_peer_median_alert_count": min_peer_median_alerts,
            "minimum_peer_asset_count": min_peer_assets,
            "maximum_alert_count_for_signal": max_alert_count,
            "observed_alert_count": observed,
            "example_active_peer_asset_ids": [peer.asset_id for peer in examples],
        }
        findings.append(
            new_finding(
                rule,
                finding_id=f"NEG-SPACE-LOW-ACTIVITY-{asset.asset_id}",
                cse_id=asset.cse_id,
                subject_id=asset.asset_id,
                reason=(
                    "Potential negative-space indicator: this high-value asset has "
                    "no alert activity while comparable assets in its peer group do."
                ),
                supporting_record_ids=supporting,
                baseline=baseline,
                data_quality_notes=(
                    "Zero alerts can also mean the asset is genuinely quiet, newly "
                    "commissioned, or not yet onboarded; onboarding records are not "
                    "part of this evidence, so a reviewer should confirm.",
                    "Missing activity is not evidence that no activity occurred.",
                ),
            )
        )
    return findings
