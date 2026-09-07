"""In-Memory Thread-Safe State Store for RescueMesh.

Manages cluster lifecycles, Human-in-the-Loop (HITL) review transitions,
audit history logs, and tactical field exports (RFC 7946 GeoJSON & Cursor-on-Target CoT XML).
"""

import json
import os
import datetime
import threading
from typing import Dict, List, Optional, Any
from xml.sax.saxutils import escape as xml_escape

from app.config import settings
from app.models.schemas import (
    ReviewState,
    PriorityLevel,
    DismissalReason,
    RecommendedAction,
    ScoreBreakdown,
    ReviewAuditRecord,
    ReviewActionRequest,
    TileAnalysisResult,
    ClusterTelemetry,
    ClusterDetail,
    GeoPoint,
    DamageScoreBreakdown,
)
from shapely.geometry import Polygon
from app.services.clustering import cluster_damage_assets
from app.services.triage_engine import triage_engine
from app.services.sitrep_generator import generate_cluster_sitrep
from app.services.vision_core import vision_core
from app.services.osm_service import osm_engine
from app.services.pipeline import enrich_cluster


class ClusterStateStore:
    """Thread-safe state manager for triage clusters and HITL workflow."""

    def __init__(self):
        self._lock = threading.RLock()
        self._clusters: Dict[str, ClusterDetail] = {}
        self._initialized = False

    def initialize_store(self, force_reload: bool = False):
        """Loads seed tiles, executes DBSCAN clustering, MCDA triage, and populates store."""
        with self._lock:
            if self._initialized and not force_reload:
                return

            seed_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                settings.SEED_AOI_PATH
            )
            if not os.path.exists(seed_path):
                seed_path = settings.SEED_AOI_PATH

            with open(seed_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Check if pre-calibrated clusters are present in seed data
            if "clusters" in data and len(data["clusters"]) > 0:
                self._clusters.clear()
                for c in data["clusters"]:
                    cluster_id = c["cluster_id"]
                    score_b = c.get("score_breakdown", {})
                    score_breakdown_obj = ScoreBreakdown(
                        damage_density=score_b.get("damage_density", "20.0/34.0"),
                        road_isolation=score_b.get("road_isolation", "15.0/22.0"),
                        vulnerability_proxy=score_b.get("vulnerability_proxy", "15.0/20.0"),
                        scale_of_impact=score_b.get("scale_of_impact", "10.0/14.0"),
                        uncertainty_penalty=score_b.get("uncertainty_penalty", "8.0/10.0"),
                    )

                    try:
                        p_level = PriorityLevel(c.get("priority", "P2"))
                    except ValueError:
                        p_level = PriorityLevel.P2

                    try:
                        rec_action = RecommendedAction(c.get("recommended_action", "STANDARD_FIELD_VERIFICATION"))
                    except ValueError:
                        rec_action = RecommendedAction.STANDARD_FIELD_VERIFICATION

                    try:
                        state_val = ReviewState(c.get("state", "AI_CANDIDATE"))
                    except ValueError:
                        state_val = ReviewState.AI_CANDIDATE

                    audit_list = []
                    for a in c.get("audit_history", []):
                        audit_list.append(ReviewAuditRecord(
                            timestamp=a.get("timestamp", datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")),
                            actor=a.get("actor", "RESCUEMESH-SYSTEM"),
                            previous_state=ReviewState(a.get("previous_state", "AI_CANDIDATE")),
                            new_state=ReviewState(a.get("new_state", "AI_CANDIDATE")),
                            reason=a.get("reason"),
                            notes=a.get("notes"),
                        ))

                    centroid_lat = float(c.get("centroid_lat", 29.7604))
                    centroid_lon = float(c.get("centroid_lon", -95.3698))
                    cluster_poly = Polygon([
                        (centroid_lon - 0.0025, centroid_lat - 0.0025),
                        (centroid_lon + 0.0025, centroid_lat - 0.0025),
                        (centroid_lon + 0.0025, centroid_lat + 0.0025),
                        (centroid_lon - 0.0025, centroid_lat + 0.0025),
                    ])
                    c_enriched = enrich_cluster(c)
                    osm_telemetry = c_enriched.get("osm_telemetry")

                    detail = ClusterDetail(
                        cluster_id=cluster_id,
                        priority=p_level,
                        triage_index=int(c.get("triage_index", 50)),
                        centroid_lat=centroid_lat,
                        centroid_lon=centroid_lon,
                        radius_meters=float(c.get("radius_meters", 300.0)),
                        area_km2=float(c.get("area_km2", 0.3)),
                        asset_count=int(c.get("asset_count", 5)),
                        severe_damage_count=int(c.get("severe_damage_count", 1)),
                        road_isolation_score=float(osm_telemetry.get("access_road_score", c.get("road_isolation_score", 0.4))),
                        state=state_val,
                        recommended_action=rec_action,
                        score_breakdown=score_breakdown_obj,
                        osm_telemetry=osm_telemetry,
                        bounding_box=c.get("bounding_box"),
                        geometry=c.get("geometry"),
                        raw_tile_base64=c.get("raw_tile_base64"),
                        gradcam_overlay_base64=c.get("gradcam_overlay_base64"),
                        raw_tile_url=c.get("raw_tile_url") or c.get("raw_tile_base64"),
                        gradcam_url=c.get("gradcam_url") or c.get("gradcam_overlay_base64"),
                        sitrep=c.get("sitrep"),
                        audit_history=audit_list,
                    )
                    self._clusters[cluster_id] = detail

                self._initialized = True
                return

            # Fallback 1. Ingest seed tiles dynamically
            tiles: List[TileAnalysisResult] = []
            asset_dicts: List[Dict[str, Any]] = []

            for item in data.get("sample_tiles", []):
                features = vision_core.analyze_tile_features(
                    tile_id=item["tile_id"],
                    lat=item["lat"],
                    lon=item["lon"],
                )
                scores = triage_engine.calculate_score(features)
                priority = triage_engine.determine_priority(scores.composite_triage_score)

                tile = TileAnalysisResult(
                    tile_id=item["tile_id"],
                    filename=item["filename"],
                    location=GeoPoint(latitude=item["lat"], longitude=item["lon"]),
                    bounds=item["bounds"],
                    priority=priority,
                    scores=scores,
                    detected_hazards=features["hazards"],
                    nearby_infrastructure=features["nearby_infrastructure"],
                    gradcam_overlay_url=f"/static/gradcam_{item['tile_id'].lower()}.png",
                    processed_at="2026-08-29T08:00:00Z"
                )
                tiles.append(tile)

                asset_dicts.append({
                    "id": item["tile_id"],
                    "tile_id": item["tile_id"],
                    "filename": item["filename"],
                    "lat": item["lat"],
                    "lon": item["lon"],
                    "evidence_score": scores.composite_triage_score / 100.0,
                    "observability_score": 0.88,
                    "damage_probability": scores.structural_damage_score,
                    "flood_proxy": scores.flood_inundation_score,
                    "scores": scores.dict(),
                    "tile_obj": tile,
                })

            # 2. Run DBSCAN Haversine Clustering
            raw_clusters = cluster_damage_assets(
                asset_dicts,
                eps_meters=800.0,
                min_samples=2,
                evidence_threshold=0.0
            )

            # 3. Build ClusterDetail entities
            self._clusters.clear()
            for idx, c in enumerate(raw_clusters):
                cluster_id = c["cluster_id"]
                triage_eval = triage_engine.evaluate_cluster_triage(c)
                sitrep_payload = generate_cluster_sitrep(c, triage_eval)

                # Format exact point breakdown
                pts = triage_eval["score_breakdown"]
                score_breakdown_obj = ScoreBreakdown(
                    damage_density=pts["damage_density"],
                    road_isolation=pts["isolation"],
                    vulnerability_proxy=pts["vulnerability"],
                    scale_of_impact=pts["scale_of_destruction"],
                    uncertainty_penalty=pts["information_gap"],
                )

                member_tiles = [
                    item["tile_obj"] for item in c["member_assets"]
                    if "tile_obj" in item and isinstance(item["tile_obj"], TileAnalysisResult)
                ]

                # Map recommended action
                action_str = sitrep_payload.get("recommended_action", "STANDARD_FIELD_VERIFICATION")
                try:
                    rec_action = RecommendedAction(action_str)
                except ValueError:
                    rec_action = RecommendedAction.STANDARD_FIELD_VERIFICATION

                # Map priority
                p_str = triage_eval["priority"]
                try:
                    p_level = PriorityLevel(p_str)
                except ValueError:
                    p_level = PriorityLevel.P2

                telemetry_data = triage_eval.get("telemetry", {})

                initial_audit = ReviewAuditRecord(
                    timestamp=datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
                    actor="RESCUEMESH-SYSTEM-AI",
                    previous_state=ReviewState.AI_CANDIDATE,
                    new_state=ReviewState.AI_CANDIDATE,
                    reason="INITIAL_INGESTION",
                    notes="Autonomous geospatial cluster discovery and MCDA triage indexing."
                )

                detail = ClusterDetail(
                    cluster_id=cluster_id,
                    priority=p_level,
                    triage_index=triage_eval["triage_index"],
                    centroid_lat=c["centroid"]["latitude"],
                    centroid_lon=c["centroid"]["longitude"],
                    radius_meters=c["radius_meters"],
                    area_km2=c["area_km2"],
                    asset_count=len(c["member_assets"]),
                    severe_damage_count=telemetry_data.get("severe_damage_count", 1),
                    road_isolation_score=telemetry_data.get("blocked_road_ratio", 0.45),
                    state=ReviewState.AI_CANDIDATE,
                    recommended_action=rec_action,
                    score_breakdown=score_breakdown_obj,
                    bounding_box=c["bounding_box"],
                    geometry=c["geometry"],
                    evidence_tiles=member_tiles,
                    gradcam_overlay_base64=None,
                    sitrep=sitrep_payload,
                    audit_history=[initial_audit],
                )

                self._clusters[cluster_id] = detail

            self._initialized = True

    def get_clusters(
        self,
        priority: Optional[PriorityLevel] = None,
        state: Optional[ReviewState] = None,
        min_score: Optional[float] = None,
    ) -> List[ClusterTelemetry]:
        """Returns filtered list of ClusterTelemetry objects sorted by triage_index descending."""
        self.initialize_store()
        with self._lock:
            results: List[ClusterTelemetry] = []
            for cluster in self._clusters.values():
                if priority is not None and cluster.priority != priority:
                    continue
                if state is not None and cluster.state != state:
                    continue
                if min_score is not None and cluster.triage_index < min_score:
                    continue
                results.append(ClusterTelemetry(**cluster.dict()))

            results.sort(key=lambda c: c.triage_index, reverse=True)
            return results

    def get_cluster_detail(self, cluster_id: str) -> Optional[ClusterDetail]:
        """Retrieves full detail and audit history for a single cluster."""
        self.initialize_store()
        with self._lock:
            return self._clusters.get(cluster_id.upper())

    def review_cluster(
        self,
        cluster_id: str,
        request: ReviewActionRequest,
    ) -> ClusterDetail:
        """Executes a Human-in-the-Loop (HITL) review state transition and appends audit log."""
        self.initialize_store()
        with self._lock:
            cluster = self._clusters.get(cluster_id.upper())
            if not cluster:
                raise KeyError(f"Cluster '{cluster_id}' does not exist")

            # Validate DISMISSED requires dismissal_reason
            if request.action == ReviewState.DISMISSED and not request.dismissal_reason:
                raise ValueError("A valid dismissal_reason is required when marking a cluster as DISMISSED.")

            now_utc = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
            previous_state = cluster.state
            new_state = request.action

            audit_entry = ReviewAuditRecord(
                timestamp=now_utc,
                actor=request.analyst_id,
                previous_state=previous_state,
                new_state=new_state,
                reason=request.dismissal_reason.value if request.dismissal_reason else None,
                notes=request.analyst_notes,
            )

            # Mutate cluster state
            cluster.state = new_state
            cluster.audit_history.append(audit_entry)

            return cluster

    def export_geojson(self) -> Dict[str, Any]:
        """Generates valid RFC 7946 GeoJSON FeatureCollection."""
        self.initialize_store()
        with self._lock:
            features = []
            for cluster in self._clusters.values():
                geom = cluster.geometry or {
                    "type": "Point",
                    "coordinates": [cluster.centroid_lon, cluster.centroid_lat]
                }
                sitrep_text = cluster.sitrep.get("tactical_summary", "") if cluster.sitrep else ""

                props = {
                    "cluster_id": cluster.cluster_id,
                    "priority": cluster.priority.value,
                    "triage_index": cluster.triage_index,
                    "state": cluster.state.value,
                    "recommended_action": cluster.recommended_action.value,
                    "asset_count": cluster.asset_count,
                    "severe_damage_count": cluster.severe_damage_count,
                    "area_km2": cluster.area_km2,
                    "radius_meters": cluster.radius_meters,
                    "sitrep_summary": sitrep_text,
                }

                features.append({
                    "type": "Feature",
                    "id": cluster.cluster_id,
                    "geometry": geom,
                    "properties": props,
                })

            return {
                "type": "FeatureCollection",
                "crs": {
                    "type": "name",
                    "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"}
                },
                "features": features,
            }

    def export_cot_xml(self) -> str:
        """Generates tactical Cursor-on-Target (CoT XML) event stream formatted for ATAK/iTAK."""
        self.initialize_store()
        with self._lock:
            now = datetime.datetime.utcnow()
            stale = now + datetime.timedelta(hours=6)
            utc_now_str = now.strftime("%Y-%m-%dT%H:%M:%SZ")
            utc_stale_str = stale.strftime("%Y-%m-%dT%H:%M:%SZ")

            events = []
            events.append('<?xml version="1.0" standalone="yes"?>')
            events.append('<events version="2.0">')

            for cluster in self._clusters.values():
                uid = f"RESCUEMESH-{cluster.cluster_id}"
                callsign = f"TRIAGE-{cluster.priority.value}-{cluster.cluster_id}"
                remarks = (
                    f"TI: {cluster.triage_index} | "
                    f"Action: {cluster.recommended_action.value} | "
                    f"State: {cluster.state.value} | "
                    f"Assets: {cluster.asset_count}"
                )

                event_xml = (
                    f'  <event version="2.0" uid="{xml_escape(uid)}" type="a-f-G-U-C" '
                    f'time="{utc_now_str}" start="{utc_now_str}" stale="{utc_stale_str}" how="m-g">\n'
                    f'    <point lat="{cluster.centroid_lat:.6f}" lon="{cluster.centroid_lon:.6f}" hae="0.0" ce="10.0" le="10.0"/>\n'
                    f'    <detail>\n'
                    f'      <contact callsign="{xml_escape(callsign)}"/>\n'
                    f'      <remarks>{xml_escape(remarks)}</remarks>\n'
                    f'      <triage index="{cluster.triage_index}" priority="{cluster.priority.value}" '
                    f'severe_assets="{cluster.severe_damage_count}"/>\n'
                    f'    </detail>\n'
                    f'  </event>'
                )
                events.append(event_xml)

            events.append('</events>')
            return "\n".join(events)


state_store = ClusterStateStore()
