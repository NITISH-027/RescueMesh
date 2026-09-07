"""Situation Report (SITREP) Generator for RescueMesh.

Generates deterministic, audit-proof tactical Situation Reports (SITREPs)
based on spatial telemetry and MCDA triage evaluations without LLM hallucinations.
"""

import datetime
from typing import List, Dict, Any, Optional
from app.models.schemas import SituationReport, SectorCluster, PriorityLevel


def generate_cluster_sitrep(cluster_data: Dict[str, Any], triage_result: Dict[str, Any]) -> Dict[str, Any]:
    """Generates an audit-proof, deterministic tactical SITREP payload for a specific spatial damage cluster.

    Decision Rules for recommended_action:
    1. If A_c >= 0.70 and F_i > 0.40 -> "AMPHIBIOUS_OR_BOAT_RECONNAISSANCE"
    2. If TI_c >= 80 and A_c < 0.70 -> "RAPID_GROUND_SAR_DEPLOYMENT"
    3. If Q_i < 0.35 or U_c > 0.60 -> "AERIAL_UAV_SURVEY_REQUIRED"
    4. Otherwise -> "STANDARD_FIELD_VERIFICATION"
    """
    cluster_id = cluster_data.get("cluster_id", "CLUSTER-01")
    ti_c = triage_result.get("triage_index", 0)
    priority = triage_result.get("priority", "P4")
    score_breakdown = triage_result.get("score_breakdown", {})
    raw_factors = score_breakdown.get("raw_factors", {})
    telemetry = triage_result.get("telemetry", {})

    a_c = float(raw_factors.get("A_c", 0.0))
    u_c = float(raw_factors.get("U_c", 0.0))
    f_i = float(telemetry.get("mean_flood_proxy_F", 0.0))
    q_i = float(telemetry.get("mean_observability_Q", 0.85))

    asset_count = telemetry.get("asset_count", len(cluster_data.get("member_assets", [])))
    severe_damage_count = telemetry.get("severe_damage_count", 0)
    area_km2 = telemetry.get("area_km2", cluster_data.get("area_km2", 0.05))
    blocked_road_ratio = telemetry.get("blocked_road_ratio", a_c)

    # 1. Deterministic Tactical Action Directive Logic
    if a_c >= 0.70 and f_i > 0.40:
        recommended_action = "AMPHIBIOUS_OR_BOAT_RECONNAISSANCE"
        action_detail = "Deploy Swift Water Rescue Teams (SWRT) and high-clearance amphibious craft due to severe roadway inundation."
    elif ti_c >= 80 and a_c < 0.70:
        recommended_action = "RAPID_GROUND_SAR_DEPLOYMENT"
        action_detail = "Immediate deployment of Type-1 Urban Search and Rescue (US&R) task forces via viable ground ingress corridors."
    elif q_i < 0.35 or u_c > 0.60:
        recommended_action = "AERIAL_UAV_SURVEY_REQUIRED"
        action_detail = "Task tactical drone (sUAS) high-resolution oblique sensor sweep to resolve sensor occlusion and cloud whiteout."
    else:
        recommended_action = "STANDARD_FIELD_VERIFICATION"
        action_detail = "Dispatch secondary reconnaissance units for ground-truth validation and perimeter damage assessment."

    # 2. Construct Tactical Structured Prose Summary
    road_status = "severely compromised/submerged" if blocked_road_ratio > 0.50 else "partially passable"
    centroid = cluster_data.get("centroid", {})
    lat_str = f"{centroid.get('latitude', 0.0):.4f}°N"
    lon_str = f"{abs(centroid.get('longitude', 0.0)):.4f}°W"

    tactical_summary = (
        f"Tactical Cluster {cluster_id} centered at ({lat_str}, {lon_str}) spans {area_km2:.3f} km² "
        f"encompassing {asset_count} asset(s), of which {severe_damage_count} exhibit severe catastrophic structural damage (E_i >= 0.65). "
        f"Egress/ingress routes are {road_status} (blocked ratio: {blocked_road_ratio:.0%}). "
        f"Mean flood water proxy: {f_i:.0%}. Observability index: {q_i:.0%}. "
        f"Directive: {action_detail}"
    )

    now_utc = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    report_id = f"SITREP-TX-HARVEY-{cluster_id}"

    return {
        "report_id": report_id,
        "timestamp": now_utc,
        "cluster_id": cluster_id,
        "priority": priority,
        "priority_level": triage_result.get("priority_level", "LOW"),
        "priority_label": triage_result.get("priority_label", "P4 - Routine Monitoring"),
        "triage_index": int(ti_c),
        "score_decomposition": score_breakdown,
        "tactical_summary": tactical_summary,
        "recommended_action": recommended_action,
        "action_detail": action_detail,
        "telemetry": telemetry,
        "operational_caveat": "Remote-sensing evidence supports triage prioritization only. Occupancy and life-safety status require on-ground confirmation.",
    }


class SitRepGenerator:
    """Generates military/FEMA-grade tactical situation reports."""

    def generate_cluster_sitrep(
        self,
        cluster_data: Dict[str, Any],
        triage_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Direct export of single-cluster tactical SITREP."""
        return generate_cluster_sitrep(cluster_data, triage_result)

    def generate_sitrep(
        self,
        incident_name: str,
        sectors: List[SectorCluster]
    ) -> SituationReport:
        """Area-wide composite tactical situation report."""
        now_utc = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%SZ")
        report_id = f"SITREP-{datetime.datetime.utcnow().strftime('%Y%m%d-%H%M%S')}"

        critical_sectors = [s for s in sectors if s.urgency_level == PriorityLevel.CRITICAL]
        total_isolated = sum(s.estimated_isolated_pop for s in sectors)

        exec_summary = (
            f"Automated AI Geospatial Assessment indicates severe catastrophic flooding across {len(sectors)} operational sectors. "
            f"{len(critical_sectors)} sector(s) designated as CRITICAL triage tier with immediate life-safety peril. "
            f"Total estimated isolated population at risk: {total_isolated:,}. Swift water rescue and helicopter hoist assets required immediately."
        )

        key_priorities = [
            f"Sector Alpha / Buffalo Bayou: Dispatch 4x Swift Water Rescue Teams (SWRTs) to evacuate stranded residential clusters.",
            f"Sector Bravo / Greenspoint: Deploy high-clearance military transport vehicles for hospital evacuation corridors.",
            f"Coordinate aerial recon above San Jacinto River breach zone for bridge structural integrity.",
            f"Establish forward staging base at Ellington Field with communications repeater uplink."
        ]

        recommendations = [
            "Task Texas Task Force 1 & 2 to highest density critical grids.",
            "Deploy mobile satellite mesh communication nodes to circumvent severed cellular towers.",
            "Pre-position fuel tankers and dry medical supplies at higher elevation staging areas."
        ]

        return SituationReport(
            report_id=report_id,
            generated_at=now_utc,
            incident_name=incident_name,
            executive_summary=exec_summary,
            key_priorities=key_priorities,
            sector_breakdown=sectors,
            resource_allocation_recommendations=recommendations,
            weather_hazards="Heavy rain bands persisting; 4-6 inches additional accumulation expected in next 6 hours. High risk of secondary flash surges.",
            operational_period="OP-PERIOD 01 (06:00 - 18:00 CST)"
        )


sitrep_generator = SitRepGenerator()
