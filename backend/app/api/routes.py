"""API Routes for RescueMesh."""

import json
import os
from typing import List, Optional
from fastapi import APIRouter, HTTPException, status, UploadFile, File, Query, Response
from app.config import settings, TriageHeuristicWeights
from app.models.schemas import (
    AOISummary,
    TileAnalysisResult,
    SectorCluster,
    SituationReport,
    TriageWeightUpdate,
    GeoPoint,
    DamageScoreBreakdown,
    PriorityLevel,
    ClusterTelemetry,
    ClusterDetail,
    ReviewActionRequest,
    SARUnitTelemetry,
    DispatchFieldRequest,
    DispatchFieldResponse,
    FieldDispatchResponse,
)
from app.services import (
    vision_core,
    triage_engine,
    clustering_service,
    sitrep_generator,
    state_store,
    dispatcher_service,
)

router = APIRouter()


def _load_seed_tiles() -> List[TileAnalysisResult]:
    """Helper to load and score seed tiles."""
    seed_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        settings.SEED_AOI_PATH
    )
    if not os.path.exists(seed_path):
        seed_path = settings.SEED_AOI_PATH

    with open(seed_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    results: List[TileAnalysisResult] = []
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
        results.append(tile)

    return results


# ============================================================================
# CLUSTER LIFECYCLE & HITL TRIAGE ENDPOINTS
# ============================================================================

@router.get(
    "/clusters",
    response_model=List[ClusterTelemetry],
    summary="Get Triage Clusters (Sorted by Triage Index Descending)"
)
async def get_clusters(
    priority: Optional[PriorityLevel] = Query(default=None, description="Filter by priority tier (P1, P2, P3, P4)"),
    state: Optional[ReviewState] = Query(default=None, description="Filter by review state (AI_CANDIDATE, VERIFIED, DISPATCHED, DISMISSED)"),
    min_score: Optional[float] = Query(default=None, description="Minimum triage index threshold (0-100)"),
):
    """Returns list of all active triage clusters filtered by priority, HITL state, or score."""
    return state_store.get_clusters(priority=priority, state=state, min_score=min_score)


@router.get(
    "/clusters/{cluster_id}/evidence",
    response_model=ClusterDetail,
    summary="Get Full Cluster Detail, Evidence Tiles, Grad-CAM, and Audit History"
)
async def get_cluster_evidence(cluster_id: str):
    """Returns comprehensive evidence payload for a specific cluster including base64 Grad-CAM overlays and HITL audit log."""
    cluster = state_store.get_cluster_detail(cluster_id)
    if not cluster:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Triage cluster '{cluster_id}' not found."
        )
    return cluster


@router.post(
    "/clusters/{cluster_id}/review",
    response_model=ClusterTelemetry,
    summary="Execute Human-in-the-Loop (HITL) State Transition"
)
async def review_cluster(cluster_id: str, request: ReviewActionRequest):
    """Transitions a cluster lifecycle state:

    AI_CANDIDATE -> VERIFIED -> DISPATCHED | DISMISSED.
    Appends an immutable audit log record.
    """
    try:
        updated_cluster = state_store.review_cluster(cluster_id, request)
        return ClusterTelemetry(**updated_cluster.dict())
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Triage cluster '{cluster_id}' not found."
        )
    except ValueError as val_err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(val_err)
        )


@router.get(
    "/sar-fleet",
    response_model=List[SARUnitTelemetry],
    summary="Get Status of All Active SAR Field Units"
)
async def get_sar_fleet():
    """Returns active SAR fleet registry with live callsigns, capabilities, and readiness status."""
    return dispatcher_service.get_fleet_status()


@router.get(
    "/clusters/{cluster_id}/nearest-unit",
    response_model=SARUnitTelemetry,
    summary="Get Nearest SAR Unit Preview for a Sector"
)
async def get_nearest_sar_unit(
    cluster_id: str,
    unit_id: Optional[str] = Query(default=None, description="Optional manual unit ID override")
):
    """Calculates Haversine distance and capability match for nearest SAR unit without dispatching."""
    cluster = state_store.get_cluster_detail(cluster_id)
    if not cluster:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Triage cluster '{cluster_id}' not found."
        )

    matched = dispatcher_service.match_nearest_unit(
        target_lat=cluster.centroid_lat,
        target_lon=cluster.centroid_lon,
        recommended_action=cluster.recommended_action.value if hasattr(cluster.recommended_action, 'value') else str(cluster.recommended_action),
        preferred_unit_id=unit_id,
    )
    return matched


@router.post(
    "/clusters/{cluster_id}/dispatch-field",
    response_model=FieldDispatchResponse,
    summary="Execute Field Rescuer Proximity Dispatch and Send Tactical SMS"
)
async def dispatch_field_team(cluster_id: str, request: Optional[DispatchFieldRequest] = None):
    """Validates cluster existence, matches nearest SAR unit, compiles 160-char SMS,

    transitions state to DISPATCHED, and returns FieldDispatchResponse.
    """
    cluster = state_store.get_cluster_detail(cluster_id)
    if not cluster:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Triage cluster '{cluster_id}' not found."
        )

    rec_action_str = cluster.recommended_action.value if hasattr(cluster.recommended_action, 'value') else str(cluster.recommended_action)
    priority_str = cluster.priority.value if hasattr(cluster.priority, 'value') else str(cluster.priority)

    analyst_id = request.analyst_id if request and request.analyst_id else "INCIDENT_COMMAND_DISPATCHER"
    analyst_notes = request.analyst_notes if request and request.analyst_notes else None

    # 1. Execute dispatch calculations & SMS compilation
    dispatch_receipt = dispatcher_service.execute_dispatch(
        cluster_id=cluster_id,
        priority=priority_str,
        triage_index=cluster.triage_index,
        lat=cluster.centroid_lat,
        lon=cluster.centroid_lon,
        recommended_action=rec_action_str,
        asset_count=cluster.asset_count,
        actor=analyst_id,
    )

    # 2. Transition cluster HITL state to DISPATCHED
    from app.models.schemas import ReviewState
    review_req = ReviewActionRequest(
        action=ReviewState.DISPATCHED,
        analyst_id=analyst_id,
        analyst_notes=analyst_notes or f"Direct field handoff to {dispatch_receipt['matched_unit']['callsign']} ({dispatch_receipt['distance_km']}km away).",
    )
    state_store.review_cluster(cluster_id, review_req)

    return FieldDispatchResponse(
        cluster_id=cluster_id,
        status=ReviewState.DISPATCHED,
        matched_unit=dispatch_receipt["matched_unit"],
        distance_km=dispatch_receipt["distance_km"],
        sms_payload=dispatch_receipt["sms_payload"],
        nav_url=dispatch_receipt["nav_url"],
        dispatched_at=dispatch_receipt["dispatched_at"],
    )


# ============================================================================
# TACTICAL EXPORT PIPELINE (RFC 7946 GeoJSON & Cursor-on-Target CoT XML)
# ============================================================================

@router.get(
    "/export/geojson",
    summary="Export Tactical Triage Clusters as RFC 7946 GeoJSON FeatureCollection"
)
async def export_geojson():
    """Generates standard RFC 7946 GeoJSON FeatureCollection containing all cluster polygons and tactical telemetry properties."""
    geojson_data = state_store.export_geojson()
    return geojson_data


@router.get(
    "/export/cot",
    summary="Export Tactical Triage Clusters as Cursor-on-Target (CoT XML) for ATAK/iTAK"
)
async def export_cot():
    """Generates military/SAR standard Cursor-on-Target (CoT XML) event streams for ATAK, iTAK, and WinTAK field units."""
    cot_xml = state_store.export_cot_xml()
    return Response(content=cot_xml, media_type="application/xml")


# ============================================================================
# VISION & SATELLITE TILE INFERENCE ENDPOINTS
# ============================================================================

@router.post("/vision/upload", summary="Upload Satellite Tile for Neural Damage & GradCAM Analysis")
async def upload_tile_for_inference(file: UploadFile = File(...)):
    """Uploads a raw satellite tile (PNG/JPEG/GeoTIFF) and performs complete inference pipeline."""
    contents = await file.read()
    if not contents:
        raise HTTPException(status_code=400, detail="Empty image payload provided")
    result = vision_core.run_inference(contents)
    return result


@router.post("/vision/analyze", summary="Run Full Vision Core Inference on Satellite Image")
async def analyze_uploaded_image(file: bytes = None):
    """Raw byte payload inference endpoint."""
    if not file:
        raise HTTPException(status_code=400, detail="No file content received")
    return vision_core.run_inference(file)


# ============================================================================
# TELEMETRY, AOI, & OPERATIONAL SITREP ENDPOINTS
# ============================================================================

@router.get("/health", summary="System Health & Diagnostic Check")
async def health_check():
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "device": settings.VISION.device,
        "active_aoi": settings.DEFAULT_AOI_NAME,
    }


@router.get("/aoi", response_model=AOISummary, summary="Retrieve Current Area of Interest Metadata")
async def get_aoi():
    tiles = _load_seed_tiles()
    sectors = clustering_service.cluster_tiles(tiles)

    critical_count = sum(1 for s in sectors if s.urgency_level in [PriorityLevel.CRITICAL, PriorityLevel.P1])
    high_count = sum(1 for s in sectors if s.urgency_level in [PriorityLevel.HIGH, PriorityLevel.P2])
    affected_pop = sum(s.estimated_isolated_pop for s in sectors)

    return AOISummary(
        aoi_id="AOI-HARVEY-HOU-01",
        name=settings.DEFAULT_AOI_NAME,
        event_name="Hurricane Harvey Category 4 Inundation",
        center=GeoPoint(
            latitude=settings.AOI_BOUNDS.center_lat,
            longitude=settings.AOI_BOUNDS.center_lon,
        ),
        bounding_box=[
            settings.AOI_BOUNDS.min_lon,
            settings.AOI_BOUNDS.min_lat,
            settings.AOI_BOUNDS.max_lon,
            settings.AOI_BOUNDS.max_lat,
        ],
        total_tiles_processed=len(tiles),
        critical_sectors_count=critical_count,
        high_sectors_count=high_count,
        estimated_affected_population=affected_pop,
        flood_coverage_sq_km=412.5,
    )


@router.get("/tiles", response_model=List[TileAnalysisResult], summary="Get Processed Satellite Tiles")
async def get_tiles():
    return _load_seed_tiles()


@router.get("/sectors", response_model=List[SectorCluster], summary="Get Operational Tactical Sectors")
async def get_sectors():
    tiles = _load_seed_tiles()
    return clustering_service.cluster_tiles(tiles)


@router.get("/sectors/{sector_id}", response_model=SectorCluster, summary="Get Single Sector Details")
async def get_sector_detail(sector_id: str):
    tiles = _load_seed_tiles()
    sectors = clustering_service.cluster_tiles(tiles)
    for s in sectors:
        if s.sector_id.upper() == sector_id.upper():
            return s
    raise HTTPException(status_code=404, detail=f"Sector '{sector_id}' not found")


@router.get("/sitrep", response_model=SituationReport, summary="Generate Instant Tactical SITREP")
async def get_sitrep():
    tiles = _load_seed_tiles()
    sectors = clustering_service.cluster_tiles(tiles)
    return sitrep_generator.generate_sitrep(settings.DEFAULT_AOI_NAME, sectors)


@router.get("/config/weights", response_model=TriageHeuristicWeights, summary="Get Active Triage Weights")
async def get_weights():
    return triage_engine.weights


@router.post("/config/weights", response_model=TriageHeuristicWeights, summary="Update Triage Heuristic Weights")
async def update_weights(weights: TriageWeightUpdate):
    total = (
        weights.structural_damage +
        weights.flood_inundation +
        weights.critical_infrastructure +
        weights.population_vulnerability +
        weights.access_isolation
    )
    if abs(total - 1.0) > 0.05:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Triage heuristic weights must sum to approximately 1.0 (Current sum: {total:.2f})"
        )

    new_weights = TriageHeuristicWeights(
        structural_damage=weights.structural_damage,
        flood_inundation=weights.flood_inundation,
        critical_infrastructure=weights.critical_infrastructure,
        population_vulnerability=weights.population_vulnerability,
        access_isolation=weights.access_isolation,
    )
    triage_engine.update_weights(new_weights)
    state_store.initialize_store(force_reload=True)
    return triage_engine.weights
