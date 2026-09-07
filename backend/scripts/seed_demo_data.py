"""Demo Data Seeder for RescueMesh.

Generates realistic geospatial telemetry, real optical photographic satellite patches from the
Hurricane Harvey dataset, alpha-blended Grad-CAM heatmap overlays, and MCDA scores.
Saves data directly to backend/data/seed_aoi.json.
"""

import os
import io
import json
import base64
import datetime
import sys
from pathlib import Path
import numpy as np
import cv2

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from app.services.saliency import generate_tactical_saliency_overlay
from app.services.pipeline import enrich_cluster

DATA_FILE = os.path.join(PROJECT_ROOT, "data", "seed_aoi.json")


def create_demo_clusters():
    """Generates the 4 standardized Houston Hurricane Harvey operational clusters with real satellite imagery."""
    now_utc = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

    damage_dir = os.path.join(PROJECT_ROOT, "data", "dataset", "train_another", "damage")
    no_damage_dir = os.path.join(PROJECT_ROOT, "data", "dataset", "train_another", "no_damage")

    damage_files = []
    if os.path.exists(damage_dir):
        damage_files = [os.path.join(damage_dir, f) for f in os.listdir(damage_dir) if f.endswith((".jpeg", ".jpg", ".png"))]

    no_damage_files = []
    if os.path.exists(no_damage_dir):
        no_damage_files = [os.path.join(no_damage_dir, f) for f in os.listdir(no_damage_dir) if f.endswith((".jpeg", ".jpg", ".png"))]

    p1_a_path = damage_files[0] if len(damage_files) > 0 else ""
    p1_b_path = damage_files[1] if len(damage_files) > 1 else p1_a_path
    p2_path = damage_files[2] if len(damage_files) > 2 else p1_a_path
    p4_path = no_damage_files[0] if len(no_damage_files) > 0 else ""

    res_p1_a = generate_tactical_saliency_overlay(p1_a_path, damage_intensity=0.92)
    res_p1_b = generate_tactical_saliency_overlay(p1_b_path, damage_intensity=0.85)
    res_p2 = generate_tactical_saliency_overlay(p2_path, damage_intensity=0.60)
    res_p4 = generate_tactical_saliency_overlay(p4_path, damage_intensity=0.15)

    clusters = [
        {
            "cluster_id": "HARVEY-CL-001",
            "priority": "P1",
            "triage_index": 88,
            "centroid_lat": 29.7604,
            "centroid_lon": -95.3698,
            "radius_meters": 420.0,
            "area_km2": 0.554,
            "asset_count": 14,
            "severe_damage_count": 11,
            "road_isolation_score": 0.82,
            "state": "AI_CANDIDATE",
            "recommended_action": "AMPHIBIOUS_OR_BOAT_RECONNAISSANCE",
            "score_breakdown": {
                "damage_density": "31.5/34.0",
                "road_isolation": "19.2/22.0",
                "vulnerability_proxy": "16.8/20.0",
                "scale_of_impact": "12.5/14.0",
                "uncertainty_penalty": "8.0/10.0"
            },
            "bounding_box": [-95.3780, 29.7530, -95.3610, 29.7680],
            "geometry": {
                "type": "Polygon",
                "coordinates": [[
                    [-95.3780, 29.7530],
                    [-95.3610, 29.7530],
                    [-95.3610, 29.7680],
                    [-95.3780, 29.7680],
                    [-95.3780, 29.7530]
                ]]
            },
            "raw_tile_url": res_p1_a["raw_tile_url"],
            "gradcam_url": res_p1_a["gradcam_url"],
            "raw_tile_base64": res_p1_a["raw_tile_base64"],
            "gradcam_overlay_base64": res_p1_a["gradcam_overlay_base64"],
            "sitrep": {
                "report_id": "SITREP-TX-HARVEY-CL-001",
                "timestamp": now_utc,
                "priority": "P1",
                "triage_index": 88,
                "score_decomposition": {
                    "damage_density": "31.5/34.0",
                    "road_isolation": "19.2/22.0",
                    "vulnerability_proxy": "16.8/20.0",
                    "scale_of_impact": "12.5/14.0",
                    "uncertainty_penalty": "8.0/10.0"
                },
                "tactical_summary": "Tactical Cluster HARVEY-CL-001 centered at Buffalo Bayou (29.7604°N, 95.3698°W) spans 0.554 km² encompassing 14 assets with 11 catastrophic structural breaches. 3 of 4 access roads are submerged (blocked ratio: 82%). Memorial Care Senior Center is 320m away. Directive: Deploy Swift Water Rescue Teams (SWRTs) and high-clearance amphibious transport.",
                "recommended_action": "AMPHIBIOUS_OR_BOAT_RECONNAISSANCE",
                "action_detail": "Deploy Swift Water Rescue Teams and amphibious craft due to severe bayou inundation.",
                "operational_caveat": "Remote-sensing evidence supports triage prioritization only. Occupancy and life-safety status require on-ground confirmation."
            },
            "audit_history": [
                {
                    "timestamp": now_utc,
                    "actor": "RESCUEMESH-VISION-CORE",
                    "previous_state": "AI_CANDIDATE",
                    "new_state": "AI_CANDIDATE",
                    "reason": "INITIAL_INGESTION",
                    "notes": "Autonomous post-landfall Maxar tile ingest and ConvNeXt feature extraction."
                }
            ]
        },
        {
            "cluster_id": "HARVEY-CL-002",
            "priority": "P1",
            "triage_index": 82,
            "centroid_lat": 29.7420,
            "centroid_lon": -95.3850,
            "radius_meters": 310.0,
            "area_km2": 0.302,
            "asset_count": 8,
            "severe_damage_count": 6,
            "road_isolation_score": 0.55,
            "state": "AI_CANDIDATE",
            "recommended_action": "RAPID_GROUND_SAR_DEPLOYMENT",
            "score_breakdown": {
                "damage_density": "29.0/34.0",
                "road_isolation": "15.0/22.0",
                "vulnerability_proxy": "17.0/20.0",
                "scale_of_impact": "12.0/14.0",
                "uncertainty_penalty": "9.0/10.0"
            },
            "bounding_box": [-95.3920, 29.7360, -95.3780, 29.7480],
            "geometry": {
                "type": "Polygon",
                "coordinates": [[
                    [-95.3920, 29.7360],
                    [-95.3780, 29.7360],
                    [-95.3780, 29.7480],
                    [-95.3920, 29.7480],
                    [-95.3920, 29.7360]
                ]]
            },
            "raw_tile_url": res_p1_b["raw_tile_url"],
            "gradcam_url": res_p1_b["gradcam_url"],
            "raw_tile_base64": res_p1_b["raw_tile_base64"],
            "gradcam_overlay_base64": res_p1_b["gradcam_overlay_base64"],
            "sitrep": {
                "report_id": "SITREP-TX-HARVEY-CL-002",
                "timestamp": now_utc,
                "priority": "P1",
                "triage_index": 82,
                "score_decomposition": {
                    "damage_density": "29.0/34.0",
                    "road_isolation": "15.0/22.0",
                    "vulnerability_proxy": "17.0/20.0",
                    "scale_of_impact": "12.0/14.0",
                    "uncertainty_penalty": "9.0/10.0"
                },
                "tactical_summary": "Tactical Cluster HARVEY-CL-002 in Montrose / Mid-Town corridor spans 0.302 km² encompassing 8 structures with heavy roof shearing and structural debris. Ground network partially accessible (blocked ratio: 55%). Directive: Immediate deployment of Type-1 Urban Search & Rescue ground task forces.",
                "recommended_action": "RAPID_GROUND_SAR_DEPLOYMENT",
                "action_detail": "Immediate deployment of Type-1 US&R teams via viable south ingress corridors.",
                "operational_caveat": "Remote-sensing evidence supports triage prioritization only. Occupancy and life-safety status require on-ground confirmation."
            },
            "audit_history": [
                {
                    "timestamp": now_utc,
                    "actor": "RESCUEMESH-VISION-CORE",
                    "previous_state": "AI_CANDIDATE",
                    "new_state": "AI_CANDIDATE",
                    "reason": "INITIAL_INGESTION",
                    "notes": "Autonomous structural damage detection via ConvNeXt-Tiny."
                }
            ]
        },
        {
            "cluster_id": "HARVEY-CL-003",
            "priority": "P2",
            "triage_index": 68,
            "centroid_lat": 29.7810,
            "centroid_lon": -95.3520,
            "radius_meters": 260.0,
            "area_km2": 0.212,
            "asset_count": 6,
            "severe_damage_count": 2,
            "road_isolation_score": 0.20,
            "state": "AI_CANDIDATE",
            "recommended_action": "STANDARD_FIELD_VERIFICATION",
            "score_breakdown": {
                "damage_density": "22.0/34.0",
                "road_isolation": "8.0/22.0",
                "vulnerability_proxy": "15.0/20.0",
                "scale_of_impact": "14.0/14.0",
                "uncertainty_penalty": "9.0/10.0"
            },
            "bounding_box": [-95.3590, 29.7750, -95.3450, 29.7870],
            "geometry": {
                "type": "Polygon",
                "coordinates": [[
                    [-95.3590, 29.7750],
                    [-95.3450, 29.7750],
                    [-95.3450, 29.7870],
                    [-95.3590, 29.7870],
                    [-95.3590, 29.7750]
                ]]
            },
            "raw_tile_url": res_p2["raw_tile_url"],
            "gradcam_url": res_p2["gradcam_url"],
            "raw_tile_base64": res_p2["raw_tile_base64"],
            "gradcam_overlay_base64": res_p2["gradcam_overlay_base64"],
            "sitrep": {
                "report_id": "SITREP-TX-HARVEY-CL-003",
                "timestamp": now_utc,
                "priority": "P2",
                "triage_index": 68,
                "score_decomposition": {
                    "damage_density": "22.0/34.0",
                    "road_isolation": "8.0/22.0",
                    "vulnerability_proxy": "15.0/20.0",
                    "scale_of_impact": "14.0/14.0",
                    "uncertainty_penalty": "9.0/10.0"
                },
                "tactical_summary": "Tactical Cluster HARVEY-CL-003 in Near Northside encompasses 6 assets with moderate surface flooding and partial roof damage. Ingress routes remain open. Directive: Standard field verification and community welfare check.",
                "recommended_action": "STANDARD_FIELD_VERIFICATION",
                "action_detail": "Dispatch secondary reconnaissance units for ground-truth validation.",
                "operational_caveat": "Remote-sensing evidence supports triage prioritization only. Occupancy and life-safety status require on-ground confirmation."
            },
            "audit_history": [
                {
                    "timestamp": now_utc,
                    "actor": "RESCUEMESH-VISION-CORE",
                    "previous_state": "AI_CANDIDATE",
                    "new_state": "AI_CANDIDATE",
                    "reason": "INITIAL_INGESTION",
                    "notes": "Moderate flood inundation detection."
                }
            ]
        },
        {
            "cluster_id": "HARVEY-CL-004",
            "priority": "P4",
            "triage_index": 38,
            "centroid_lat": 29.7250,
            "centroid_lon": -95.4100,
            "radius_meters": 180.0,
            "area_km2": 0.102,
            "asset_count": 3,
            "severe_damage_count": 0,
            "road_isolation_score": 0.15,
            "state": "AI_CANDIDATE",
            "recommended_action": "AERIAL_UAV_SURVEY_REQUIRED",
            "score_breakdown": {
                "damage_density": "8.0/34.0",
                "road_isolation": "4.0/22.0",
                "vulnerability_proxy": "10.0/20.0",
                "scale_of_impact": "6.0/14.0",
                "uncertainty_penalty": "10.0/10.0"
            },
            "bounding_box": [-95.4160, 29.7200, -95.4040, 29.7300],
            "geometry": {
                "type": "Polygon",
                "coordinates": [[
                    [-95.4160, 29.7200],
                    [-95.4040, 29.7200],
                    [-95.4040, 29.7300],
                    [-95.4160, 29.7300],
                    [-95.4160, 29.7200]
                ]]
            },
            "raw_tile_url": res_p4["raw_tile_url"],
            "gradcam_url": res_p4["gradcam_url"],
            "raw_tile_base64": res_p4["raw_tile_base64"],
            "gradcam_overlay_base64": res_p4["gradcam_overlay_base64"],
            "sitrep": {
                "report_id": "SITREP-TX-HARVEY-CL-004",
                "timestamp": now_utc,
                "priority": "P4",
                "triage_index": 38,
                "score_decomposition": {
                    "damage_density": "8.0/34.0",
                    "road_isolation": "4.0/22.0",
                    "vulnerability_proxy": "10.0/20.0",
                    "scale_of_impact": "6.0/14.0",
                    "uncertainty_penalty": "10.0/10.0"
                },
                "tactical_summary": "Tactical Cluster HARVEY-CL-004 in West University Fringe exhibits low structural disruption (Q_i = 0.88). Insufficient damage evidence to warrant immediate tactical diversion. Directive: Task aerial drone (sUAS) routine oblique survey.",
                "recommended_action": "AERIAL_UAV_SURVEY_REQUIRED",
                "action_detail": "Task tactical drone (sUAS) low-altitude flight for confirmation.",
                "operational_caveat": "Remote-sensing evidence supports triage prioritization only. Occupancy and life-safety status require on-ground confirmation."
            },
            "audit_history": [
                {
                    "timestamp": now_utc,
                    "actor": "RESCUEMESH-VISION-CORE",
                    "previous_state": "AI_CANDIDATE",
                    "new_state": "AI_CANDIDATE",
                    "reason": "INITIAL_INGESTION",
                    "notes": "Routine background surveillance analysis."
                }
            ]
        }
    ]

    for c in clusters:
        enrich_cluster(c)

    payload = {
        "event_id": "HOUSTON-HARVEY-2017-08",
        "aoi_name": "Houston Metropolitan Tactical Response Zone",
        "generated_at": now_utc,
        "clusters": clusters
    }

    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    print(f"[Seed] Successfully generated 4 tactical clusters and saved to {DATA_FILE}")


if __name__ == "__main__":
    create_demo_clusters()
