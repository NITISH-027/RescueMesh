"""Real Tile Ingestion & Geospatial Mapping Pipeline for RescueMesh.

Ingests real satellite image patches from Kaggle Hurricane Harvey dataset (test_another/damage & test_another/no_damage),
runs neural inference and Grad-CAM saliency extraction, maps them onto Houston, TX coordinates,
clusters them with Haversine DBSCAN, computes MCDA triage scores, generates tactical SITREPs,
and writes the operational payload directly to backend/data/seed_aoi.json.
"""

import os
import sys
import json
import glob
import io
import base64
import random
import datetime
from typing import List, Dict, Any, Optional

import numpy as np
import cv2
from PIL import Image

try:
    from tqdm import tqdm
except ImportError:
    def tqdm(iterable, desc=None, **kwargs):
        return iterable

# Ensure backend root is in sys.path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_ROOT = os.path.dirname(SCRIPT_DIR)
if BACKEND_ROOT not in sys.path:
    sys.path.insert(0, BACKEND_ROOT)

from app.services.vision_core import VisionCoreService
from app.services.clustering import cluster_damage_assets
from app.services.triage_engine import triage_engine
from app.services.sitrep_generator import generate_cluster_sitrep
from app.models.schemas import PriorityLevel, RecommendedAction, ReviewState

DEFAULT_DATASET_DIR = os.path.join(BACKEND_ROOT, "data", "dataset")
DEFAULT_SEED_FILE = os.path.join(BACKEND_ROOT, "data", "seed_aoi.json")
MODEL_CHECKPOINT = os.path.join(BACKEND_ROOT, "app", "models", "damage_classifier.pth")


def load_image_bytes(file_path: str) -> bytes:
    with open(file_path, "rb") as f:
        return f.read()


def ingest_real_dataset(
    dataset_dir: str = DEFAULT_DATASET_DIR,
    output_seed_path: str = DEFAULT_SEED_FILE,
    max_damage_samples: int = 16,
    max_no_damage_samples: int = 8,
):
    """Ingests real Kaggle Hurricane Harvey test patches and maps them to Houston operational sectors."""
    print("=" * 70)
    print("RESCUEMESH // KAGGLE HURRICANE HARVEY DATASET INGESTION PIPELINE")
    print("=" * 70)

    # 1. Initialize Vision Core
    checkpoint = MODEL_CHECKPOINT if os.path.exists(MODEL_CHECKPOINT) else None
    print(f"[VisionCore] Initializing with checkpoint: {checkpoint}")
    vision_service = VisionCoreService(checkpoint_path=checkpoint)

    # 2. Discover test image paths
    test_dir = os.path.join(dataset_dir, "test_another")
    if not os.path.exists(test_dir):
        test_dir = os.path.join(dataset_dir, "validation_another")
        if not os.path.exists(test_dir):
            test_dir = os.path.join(dataset_dir, "train_another")

    damage_dir = os.path.join(test_dir, "damage")
    no_damage_dir = os.path.join(test_dir, "no_damage")

    damage_files = sorted(glob.glob(os.path.join(damage_dir, "*.jpeg")) + glob.glob(os.path.join(damage_dir, "*.jpg")) + glob.glob(os.path.join(damage_dir, "*.png")))
    no_damage_files = sorted(glob.glob(os.path.join(no_damage_dir, "*.jpeg")) + glob.glob(os.path.join(no_damage_dir, "*.jpg")) + glob.glob(os.path.join(no_damage_dir, "*.png")))

    print(f"[Dataset] Found {len(damage_files)} damage files and {len(no_damage_files)} no_damage files in {test_dir}")

    # Subsample for balanced operational deployment
    selected_damage = damage_files[:max_damage_samples]
    selected_no_damage = no_damage_files[:max_no_damage_samples]
    all_selected = [(f, 1) for f in selected_damage] + [(f, 0) for f in selected_no_damage]

    if not all_selected:
        print("[Warning] No image files found in dataset directory. Creating synthetic ingest fallback...")
        from scripts.seed_demo_data import create_demo_clusters
        create_demo_clusters()
        return

    # 3. Spatial Anchor Points across Houston AOI (Buffalo Bayou, Montrose, Northside, West U)
    base_anchors = [
        {"center_lat": 29.7604, "center_lon": -95.3698, "name": "Buffalo Bayou / Downtown Corridor"},
        {"center_lat": 29.7420, "center_lon": -95.3850, "name": "Montrose / Mid-Town Basin"},
        {"center_lat": 29.7810, "center_lon": -95.3520, "name": "Near Northside Sector"},
        {"center_lat": 29.7250, "center_lon": -95.4100, "name": "West University Fringe"},
    ]

    processed_assets: List[Dict[str, Any]] = []
    print(f"\n[Inference] Processing {len(all_selected)} real satellite tiles...")

    pbar = tqdm(enumerate(all_selected), total=len(all_selected), desc="Neural Tile Ingest")
    for idx, (img_path, ground_truth_label) in pbar:
        img_bytes = load_image_bytes(img_path)
        filename = os.path.basename(img_path)
        asset_id = f"TILE-HARVEY-{idx+1:03d}"

        # Run full VisionCore neural inference pipeline
        inference_res = vision_service.run_inference(img_bytes)

        # Distribute spatially around Houston anchor centers
        anchor = base_anchors[idx % len(base_anchors)]
        # Offset within ~400-800m
        lat_offset = (random.random() - 0.5) * 0.008
        lon_offset = (random.random() - 0.5) * 0.008
        tile_lat = round(anchor["center_lat"] + lat_offset, 6)
        tile_lon = round(anchor["center_lon"] + lon_offset, 6)

        # Prepare raw tile base64
        pil_img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
        buf = io.BytesIO()
        pil_img.save(buf, format="PNG")
        raw_b64 = f"data:image/png;base64,{base64.b64encode(buf.getvalue()).decode('utf-8')}"

        gradcam_b64 = inference_res.get("gradcam_overlay_base64") or raw_b64

        asset_dict = {
            "id": asset_id,
            "tile_id": asset_id,
            "filename": filename,
            "lat": tile_lat,
            "lon": tile_lon,
            "evidence_score": inference_res["evidence_score"],
            "observability_score": inference_res["observability_score"],
            "damage_probability": inference_res["damage_probability"],
            "predicted_class": inference_res["predicted_class"],
            "ground_truth_label": ground_truth_label,
            "flood_proxy": inference_res["flood_proxy"],
            "texture_contrast_score": inference_res["texture_contrast_score"],
            "raw_tile_base64": raw_b64,
            "gradcam_overlay_base64": gradcam_b64,
            "status": inference_res["status"],
        }
        processed_assets.append(asset_dict)

        print(f"  [{idx+1}/{len(all_selected)}] {filename} -> Lat: {tile_lat}, Lon: {tile_lon} | Pred: {inference_res['predicted_class']} (p={inference_res['damage_probability']:.2f}) | E_i={inference_res['evidence_score']:.2f}")

    # 4. Cluster assets via Haversine DBSCAN
    print(f"\n[Spatial Clustering] Running DBSCAN on {len(processed_assets)} asset evidence points...")
    raw_clusters = cluster_damage_assets(processed_assets, eps_meters=800.0, min_samples=2, evidence_threshold=0.0)

    # 5. Evaluate MCDA Triage Index & Generate SITREPs for each cluster
    now_utc = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    final_clusters: List[Dict[str, Any]] = []

    for idx, c in enumerate(raw_clusters):
        cluster_id = f"HARVEY-CL-{idx+1:03d}"
        c["cluster_id"] = cluster_id

        # Calculate MCDA score breakdown
        triage_eval = triage_engine.evaluate_cluster_triage(c)
        sitrep_payload = generate_cluster_sitrep(c, triage_eval)

        # Grab high-res sample base64 from representative member asset
        rep_asset = next((a for a in c["member_assets"] if a.get("damage_probability", 0) >= 0.5), c["member_assets"][0])

        cluster_entry = {
            "cluster_id": cluster_id,
            "priority": triage_eval["priority"],
            "triage_index": triage_eval["triage_index"],
            "centroid_lat": c["centroid"]["latitude"],
            "centroid_lon": c["centroid"]["longitude"],
            "radius_meters": c["radius_meters"],
            "area_km2": c["area_km2"],
            "asset_count": c["asset_count"],
            "severe_damage_count": triage_eval["telemetry"].get("severe_damage_count", 0),
            "road_isolation_score": triage_eval["telemetry"].get("blocked_road_ratio", 0.4),
            "state": "AI_CANDIDATE",
            "recommended_action": sitrep_payload["recommended_action"],
            "score_breakdown": {
                "damage_density": triage_eval["score_breakdown"]["damage_density"],
                "road_isolation": triage_eval["score_breakdown"]["isolation"],
                "vulnerability_proxy": triage_eval["score_breakdown"]["vulnerability"],
                "scale_of_impact": triage_eval["score_breakdown"]["scale_of_destruction"],
                "uncertainty_penalty": triage_eval["score_breakdown"]["information_gap"],
            },
            "bounding_box": c["bounding_box"],
            "geometry": c["geometry"],
            "raw_tile_base64": rep_asset.get("raw_tile_base64"),
            "gradcam_overlay_base64": rep_asset.get("gradcam_overlay_base64"),
            "sitrep": sitrep_payload,
            "audit_history": [
                {
                    "timestamp": now_utc,
                    "actor": "RESCUEMESH-VISION-CORE",
                    "previous_state": "AI_CANDIDATE",
                    "new_state": "AI_CANDIDATE",
                    "reason": "INITIAL_INGESTION",
                    "notes": f"Ingested {c['asset_count']} real satellite patches from Kaggle Hurricane Harvey test partition.",
                }
            ]
        }
        final_clusters.append(cluster_entry)

    # Sort clusters descending by triage_index
    final_clusters.sort(key=lambda x: x["triage_index"], reverse=True)

    # 6. Save payload to seed_aoi.json
    payload = {
        "aoi_id": "AOI-HARVEY-HOU-01",
        "name": "Greater Houston Metropolitan Hurricane Harvey AOI",
        "event_name": "Hurricane Harvey Category 4 Inundation (Kaggle Real Imagery Ingest)",
        "center": {
            "latitude": 29.7604,
            "longitude": -95.3698
        },
        "bounding_box": [-95.75, 29.50, -95.05, 30.05],
        "clusters": final_clusters,
        "sample_tiles": [
            {
                "tile_id": a["id"],
                "filename": a["filename"],
                "lat": a["lat"],
                "lon": a["lon"],
                "bounds": [a["lon"] - 0.005, a["lat"] - 0.005, a["lon"] + 0.005, a["lat"] + 0.005],
            }
            for a in processed_assets
        ]
    }

    os.makedirs(os.path.dirname(output_seed_path), exist_ok=True)
    with open(output_seed_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    print("\n" + "=" * 70)
    print(f"INGESTION COMPLETE: {len(processed_assets)} tiles -> {len(final_clusters)} operational clusters")
    print(f"Saved directly to: {output_seed_path}")
    print("=" * 70)


if __name__ == "__main__":
    ingest_real_dataset()
