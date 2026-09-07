"""Pydantic schemas and data transfer models for RescueMesh."""

from enum import Enum
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field


class ReviewState(str, Enum):
    AI_CANDIDATE = "AI_CANDIDATE"
    VERIFIED = "VERIFIED"
    DISPATCHED = "DISPATCHED"
    DISMISSED = "DISMISSED"


class PriorityLevel(str, Enum):
    P1 = "P1"
    P2 = "P2"
    P3 = "P3"
    P4 = "P4"
    # Legacy alias support
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class DismissalReason(str, Enum):
    CLOUD_SHADOW = "CLOUD_SHADOW"
    ROOF_TEXTURE_ARTIFACT = "ROOF_TEXTURE_ARTIFACT"
    ALREADY_RESOLVED = "ALREADY_RESOLVED"
    NON_CRITICAL_INFRASTRUCTURE = "NON_CRITICAL_INFRASTRUCTURE"
    OTHER = "OTHER"


class RecommendedAction(str, Enum):
    AMPHIBIOUS_OR_BOAT_RECONNAISSANCE = "AMPHIBIOUS_OR_BOAT_RECONNAISSANCE"
    RAPID_GROUND_SAR_DEPLOYMENT = "RAPID_GROUND_SAR_DEPLOYMENT"
    AERIAL_UAV_SURVEY_REQUIRED = "AERIAL_UAV_SURVEY_REQUIRED"
    STANDARD_FIELD_VERIFICATION = "STANDARD_FIELD_VERIFICATION"


class InfrastructureType(str, Enum):
    HOSPITAL = "hospital"
    POWER_SUBSTATION = "power_substation"
    WATER_TREATMENT = "water_treatment"
    FIRE_STATION = "fire_station"
    EMERGENCY_SHELTER = "emergency_shelter"
    COMMUNICATION_TOWER = "communication_tower"
    MAJOR_INTERSECTION = "major_intersection"


class GeoPoint(BaseModel):
    latitude: float = Field(..., ge=-90.0, le=90.0)
    longitude: float = Field(..., ge=-180.0, le=180.0)


class GeoPolygon(BaseModel):
    coordinates: List[List[float]] = Field(..., description="List of [lon, lat] pairs forming polygon")


class DamageScoreBreakdown(BaseModel):
    structural_damage_score: float = Field(..., ge=0.0, le=1.0)
    flood_inundation_score: float = Field(..., ge=0.0, le=1.0)
    critical_infrastructure_score: float = Field(..., ge=0.0, le=1.0)
    population_vulnerability_score: float = Field(..., ge=0.0, le=1.0)
    access_isolation_score: float = Field(..., ge=0.0, le=1.0)
    composite_triage_score: float = Field(..., ge=0.0, le=100.0)


class ScoreBreakdown(BaseModel):
    damage_density: str = Field(..., description="Fractional score representation, e.g. '31.2/34.0'")
    road_isolation: str = Field(..., description="Fractional score representation, e.g. '18.5/22.0'")
    vulnerability_proxy: str = Field(..., description="Fractional score representation, e.g. '14.0/20.0'")
    scale_of_impact: str = Field(..., description="Fractional score representation, e.g. '11.2/14.0'")
    uncertainty_penalty: str = Field(..., description="Fractional score representation, e.g. '7.5/10.0'")


class ReviewAuditRecord(BaseModel):
    timestamp: str
    actor: str
    previous_state: ReviewState
    new_state: ReviewState
    reason: Optional[str] = None
    notes: Optional[str] = None


class ReviewActionRequest(BaseModel):
    action: ReviewState = Field(..., description="Target lifecycle state: VERIFIED, DISPATCHED, or DISMISSED")
    analyst_id: str = Field(..., description="ID or callsign of the human analyst")
    analyst_notes: Optional[str] = Field(default=None, description="Optional operational remarks")
    dismissal_reason: Optional[DismissalReason] = Field(default=None, description="Required when action is DISMISSED")


class TileAnalysisResult(BaseModel):
    tile_id: str
    filename: str
    location: GeoPoint
    bounds: List[float] = Field(..., description="[min_lon, min_lat, max_lon, max_lat]")
    priority: PriorityLevel
    scores: DamageScoreBreakdown
    detected_hazards: List[str] = Field(default_factory=list)
    nearby_infrastructure: List[str] = Field(default_factory=list)
    gradcam_overlay_url: Optional[str] = None
    gradcam_overlay_base64: Optional[str] = None
    processed_at: str


class ClusterTelemetry(BaseModel):
    cluster_id: str
    priority: PriorityLevel
    triage_index: int = Field(..., ge=0, le=100)
    centroid_lat: float
    centroid_lon: float
    radius_meters: float
    area_km2: float
    asset_count: int
    severe_damage_count: int
    road_isolation_score: float
    state: ReviewState = Field(default=ReviewState.AI_CANDIDATE)
    recommended_action: RecommendedAction
    score_breakdown: ScoreBreakdown
    osm_telemetry: Optional[Dict[str, Any]] = None
    bounding_box: Optional[List[float]] = None
    geometry: Optional[Dict[str, Any]] = None


class ClusterDetail(ClusterTelemetry):
    raw_tile_base64: Optional[str] = None
    gradcam_overlay_base64: Optional[str] = None
    raw_tile_url: Optional[str] = None
    gradcam_url: Optional[str] = None
    sitrep: Optional[Dict[str, Any]] = None
    audit_history: List[ReviewAuditRecord] = Field(default_factory=list)
    evidence_tiles: List[TileAnalysisResult] = Field(default_factory=list)


class SectorCluster(BaseModel):
    sector_id: str
    sector_name: str
    center: GeoPoint
    bounding_box: List[float]
    tile_count: int
    mean_triage_score: float
    max_triage_score: float
    urgency_level: PriorityLevel
    primary_threat: str
    estimated_isolated_pop: int
    recommended_action: str
    tiles: List[TileAnalysisResult] = Field(default_factory=list)


class AOISummary(BaseModel):
    aoi_id: str
    name: str
    event_name: str
    center: GeoPoint
    bounding_box: List[float]
    total_tiles_processed: int
    critical_sectors_count: int
    high_sectors_count: int
    estimated_affected_population: int
    flood_coverage_sq_km: float


class SituationReport(BaseModel):
    report_id: str
    generated_at: str
    incident_name: str
    executive_summary: str
    key_priorities: List[str]
    sector_breakdown: List[SectorCluster]
    resource_allocation_recommendations: List[str]
    weather_hazards: str
    operational_period: str


class TriageWeightUpdate(BaseModel):
    structural_damage: float = Field(..., ge=0.0, le=1.0)
    flood_inundation: float = Field(..., ge=0.0, le=1.0)
    critical_infrastructure: float = Field(..., ge=0.0, le=1.0)
    population_vulnerability: float = Field(..., ge=0.0, le=1.0)
    access_isolation: float = Field(..., ge=0.0, le=1.0)


class SARUnitTelemetry(BaseModel):
    unit_id: str
    callsign: str
    phone: str
    capability: str
    lat: float
    lon: float
    status: str
    personnel: int
    vehicle: str
    equipment: List[str] = Field(default_factory=list)
    distance_km: Optional[float] = None
    eta_minutes: Optional[int] = None
    capability_match: Optional[bool] = None


class DispatchFieldRequest(BaseModel):
    unit_id: Optional[str] = Field(default=None, description="Optional manual SAR unit override ID")
    analyst_id: str = Field(default="SAR-COMM-CHIEF-01", description="ID/Callsign of dispatching operator")
    analyst_notes: Optional[str] = Field(default=None, description="Operational instructions or dispatch notes")


class DispatchFieldResponse(BaseModel):
    dispatch_id: str
    timestamp: str
    cluster_id: str
    assigned_unit: SARUnitTelemetry
    sms_payload: str
    recipient_phone: str
    analyst_id: str
    analyst_notes: str
    transmission_status: str
    updated_cluster: ClusterTelemetry


class FieldDispatchResponse(BaseModel):
    cluster_id: str
    status: ReviewState = ReviewState.DISPATCHED
    matched_unit: Dict[str, Any]
    distance_km: float
    sms_payload: str
    nav_url: str
    dispatched_at: str
