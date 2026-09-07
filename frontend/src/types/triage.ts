export type ReviewState = "AI_CANDIDATE" | "VERIFIED" | "DISPATCHED" | "DISMISSED";

export type PriorityLevel = "P1" | "P2" | "P3" | "P4" | "CRITICAL" | "HIGH" | "MEDIUM" | "LOW";

export type DismissalReason =
  | "CLOUD_SHADOW"
  | "ROOF_TEXTURE_ARTIFACT"
  | "ALREADY_RESOLVED"
  | "NON_CRITICAL_INFRASTRUCTURE"
  | "OTHER";

export interface GeoPoint {
  latitude: number;
  longitude: number;
}

export interface ScoreBreakdown {
  damage_density: string;
  road_isolation: string;
  vulnerability_proxy: string;
  scale_of_impact: string;
  uncertainty_penalty: string;
}

export interface SITREPReport {
  report_id: string;
  timestamp: string;
  priority: PriorityLevel;
  triage_index: number;
  score_decomposition: Record<string, any>;
  tactical_summary: string;
  recommended_action: string;
  action_detail?: string;
  operational_caveat: string;
}

export interface DamageScoreBreakdown {
  structural_damage_score: number;
  flood_inundation_score: number;
  critical_infrastructure_score: number;
  population_vulnerability_score: number;
  access_isolation_score: number;
  composite_triage_score: number;
}

export interface TileAnalysisResult {
  tile_id: string;
  filename: string;
  location: GeoPoint;
  bounds: [number, number, number, number];
  priority: PriorityLevel;
  scores: DamageScoreBreakdown;
  detected_hazards: string[];
  nearby_infrastructure: string[];
  gradcam_overlay_url?: string;
  gradcam_overlay_base64?: string;
  processed_at: string;
}

export interface ReviewAuditRecord {
  timestamp: string;
  actor: string;
  previous_state: string;
  new_state: string;
  reason?: string;
  notes?: string;
}

export interface OSMTelemetry {
  access_road_score: number;
  nearby_critical_facilities: number;
  nearest_hospital_dist_km: number;
  osm_feature_tags: string[];
  access_status: "ACCESSIBLE" | "PARTIALLY_BLOCKED" | "ISOLATED" | string;
  topological_edges_evaluated: number;
}

export interface ClusterTelemetry {
  cluster_id: string;
  priority: PriorityLevel;
  triage_index: number;
  centroid_lat: number;
  centroid_lon: number;
  radius_meters: number;
  area_km2: number;
  asset_count: number;
  severe_damage_count: number;
  road_isolation_score: number;
  state: ReviewState;
  recommended_action: string;
  score_breakdown: ScoreBreakdown;
  osm_telemetry?: OSMTelemetry;
  bounding_box?: [number, number, number, number];
  geometry?: any;
}

export interface ClusterDetail extends ClusterTelemetry {
  gradcam_overlay_base64?: string;
  raw_tile_base64?: string;
  raw_tile_url?: string;
  gradcam_url?: string;
  sitrep?: SITREPReport;
  audit_history: ReviewAuditRecord[];
  evidence_tiles?: TileAnalysisResult[];
}

export interface SectorCluster {
  sector_id: string;
  sector_name: string;
  center: GeoPoint;
  bounding_box: [number, number, number, number];
  tile_count: number;
  mean_triage_score: number;
  max_triage_score: number;
  urgency_level: PriorityLevel;
  primary_threat: string;
  estimated_isolated_pop: number;
  recommended_action: string;
  tiles: TileAnalysisResult[];
}

export interface AOISummary {
  aoi_id: string;
  name: string;
  event_name: string;
  center: GeoPoint;
  bounding_box: [number, number, number, number];
  total_tiles_processed: number;
  critical_sectors_count: number;
  high_sectors_count: number;
  estimated_affected_population: number;
  flood_coverage_sq_km: number;
}

export interface TriageHeuristicWeights {
  structural_damage: number;
  flood_inundation: number;
  critical_infrastructure: number;
  population_vulnerability: number;
  access_isolation: number;
}

export interface SituationReport {
  report_id: string;
  generated_at: string;
  incident_name: string;
  executive_summary: string;
  key_priorities: string[];
  sector_breakdown: SectorCluster[];
  resource_allocation_recommendations: string[];
  weather_hazards: string;
  operational_period: string;
}

export interface SARUnit {
  unit_id: string;
  callsign: string;
  phone: string;
  capability: string;
  lat: number;
  lon: number;
  status: string;
  personnel: number;
  vehicle: string;
  equipment: string[];
  distance_km?: number;
  eta_minutes?: number;
  capability_match?: boolean;
}

export interface DispatchFieldRequest {
  unit_id?: string;
  analyst_id?: string;
  analyst_notes?: string;
}

export interface DispatchFieldResponse {
  dispatch_id: string;
  timestamp: string;
  cluster_id: string;
  assigned_unit: SARUnit;
  sms_payload: string;
  recipient_phone: string;
  analyst_id: string;
  analyst_notes: string;
  transmission_status: string;
  updated_cluster: ClusterTelemetry;
}

export interface FieldDispatchResponse {
  cluster_id: string;
  status: ReviewState;
  matched_unit: SARUnit;
  distance_km: number;
  sms_payload: string;
  nav_url: string;
  dispatched_at: string;
}
