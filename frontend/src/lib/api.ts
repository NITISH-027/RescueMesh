import {
  AOISummary,
  ClusterTelemetry,
  ClusterDetail,
  ReviewState,
  DismissalReason,
  SituationReport,
  TriageHeuristicWeights,
  SectorCluster,
  TileAnalysisResult,
  SARUnit,
  DispatchFieldRequest,
  DispatchFieldResponse,
  FieldDispatchResponse,
} from "@/types/triage";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8001/api/v1";

// ─── ROBUST STATIC MOCK FALLBACKS (FULLY OFFLINE CAPABLE) ──────────────────────

export const MOCK_CLUSTERS: ClusterTelemetry[] = [
  {
    cluster_id: "HARVEY-CL-001",
    priority: "CRITICAL",
    triage_index: 94,
    centroid_lat: 29.7604,
    centroid_lon: -95.3698,
    radius_meters: 500,
    area_km2: 0.78,
    asset_count: 14,
    severe_damage_count: 9,
    road_isolation_score: 0.88,
    state: "AI_CANDIDATE",
    recommended_action: "IMMEDIATE_AIR_EVAC",
    score_breakdown: {
      damage_density: "32.0/34.0",
      road_isolation: "20.5/22.0",
      vulnerability_proxy: "18.0/20.0",
      scale_of_impact: "12.5/14.0",
      uncertainty_penalty: "8.5/10.0",
    },
    osm_telemetry: {
      access_road_score: 0.12,
      nearby_critical_facilities: 3,
      nearest_hospital_dist_km: 1.4,
      osm_feature_tags: ["residential", "hospital_nearby", "submerged_arterial"],
      access_status: "CUT_OFF",
      topological_edges_evaluated: 24,
    },
    bounding_box: [-95.38, 29.75, -95.36, 29.77],
  },
  {
    cluster_id: "HARVEY-CL-002",
    priority: "HIGH",
    triage_index: 82,
    centroid_lat: 29.754,
    centroid_lon: -95.358,
    radius_meters: 400,
    area_km2: 0.5,
    asset_count: 8,
    severe_damage_count: 5,
    road_isolation_score: 0.42,
    state: "VERIFIED",
    recommended_action: "WATER_RESCUE_DEPLOY",
    score_breakdown: {
      damage_density: "26.0/34.0",
      road_isolation: "16.0/22.0",
      vulnerability_proxy: "14.5/20.0",
      scale_of_impact: "9.0/14.0",
      uncertainty_penalty: "6.5/10.0",
    },
    osm_telemetry: {
      access_road_score: 0.58,
      nearby_critical_facilities: 1,
      nearest_hospital_dist_km: 3.1,
      osm_feature_tags: ["residential_zone", "cul_de_sac", "drainage_canal"],
      access_status: "PARTIALLY_BLOCKED",
      topological_edges_evaluated: 18,
    },
    bounding_box: [-95.365, 29.748, -95.35, 29.76],
  },
  {
    cluster_id: "HARVEY-CL-003",
    priority: "CRITICAL",
    triage_index: 91,
    centroid_lat: 29.768,
    centroid_lon: -95.378,
    radius_meters: 650,
    area_km2: 1.32,
    asset_count: 19,
    severe_damage_count: 12,
    road_isolation_score: 0.95,
    state: "AI_CANDIDATE",
    recommended_action: "ELDERLY_CARE_EVACUATION",
    score_breakdown: {
      damage_density: "31.0/34.0",
      road_isolation: "21.0/22.0",
      vulnerability_proxy: "19.5/20.0",
      scale_of_impact: "13.0/14.0",
      uncertainty_penalty: "9.0/10.0",
    },
    osm_telemetry: {
      access_road_score: 0.05,
      nearby_critical_facilities: 2,
      nearest_hospital_dist_km: 2.2,
      osm_feature_tags: ["nursing_home", "dense_senior_living", "submerged_creek"],
      access_status: "CUT_OFF",
      topological_edges_evaluated: 32,
    },
    bounding_box: [-95.388, 29.76, -95.368, 29.776],
  },
];

export const MOCK_WEIGHTS: TriageHeuristicWeights = {
  structural_damage: 0.35,
  flood_inundation: 0.3,
  critical_infrastructure: 0.15,
  population_vulnerability: 0.1,
  access_isolation: 0.1,
};

function getMockClusterDetail(clusterId: string): ClusterDetail {
  const base = MOCK_CLUSTERS.find((c) => c.cluster_id === clusterId) || MOCK_CLUSTERS[0];
  return {
    ...base,
    gradcam_overlay_base64: "",
    raw_tile_url: "",
    gradcam_url: "",
    sitrep: {
      report_id: `SITREP-TX-${base.cluster_id}`,
      timestamp: "2026-09-07T12:00:00Z",
      priority: base.priority,
      triage_index: base.triage_index,
      score_decomposition: {},
      tactical_summary: `Sector ${base.cluster_id} encompasses ${base.asset_count} asset(s), with ${base.severe_damage_count} severe structural breaches detected. Road access status is evaluated as ${base.osm_telemetry?.access_status || "CUT_OFF"}.`,
      recommended_action: base.recommended_action,
      action_detail: `Mobilize tactical rescue task force to coordinates ${base.centroid_lat.toFixed(4)}°N, ${Math.abs(base.centroid_lon).toFixed(4)}°W.`,
      operational_caveat: "Remote-sensing evidence supports triage prioritization. Ground assessment required for occupancy verification.",
    },
    audit_history: [
      {
        timestamp: "2026-09-07T11:45:00Z",
        actor: "AUTOMATED_AI_AGENT",
        previous_state: "RAW_SATELLITE_FEED",
        new_state: "AI_CANDIDATE",
        notes: "High confidence structural anomaly detected via multispectral satellite imagery.",
      },
      {
        timestamp: "2026-09-07T12:15:00Z",
        actor: "OP-LEAD-01",
        previous_state: "AI_CANDIDATE",
        new_state: base.state,
        notes: "Analyst verified flood inundation perimeter and confirmed tactical priority queue rank.",
      },
    ],
    evidence_tiles: [],
  };
}

function downloadFile(content: string, filename: string, mimeType: string) {
  if (typeof window === "undefined") return;
  const blob = new Blob([content], { type: mimeType });
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  window.URL.revokeObjectURL(url);
  document.body.removeChild(a);
}

// ─── API CLIENT FUNCTIONS ──────────────────────────────────────────────────────

export async function fetchClusters(params?: {
  priority?: string;
  state?: string;
  min_score?: number;
}): Promise<ClusterTelemetry[]> {
  try {
    const searchParams = new URLSearchParams();
    if (params?.priority && params.priority !== "ALL") searchParams.append("priority", params.priority);
    if (params?.state && params.state !== "ALL") searchParams.append("state", params.state);
    if (params?.min_score !== undefined) searchParams.append("min_score", params.min_score.toString());

    const url = `${API_BASE_URL}/clusters${searchParams.toString() ? `?${searchParams.toString()}` : ""}`;
    const res = await fetch(url, { cache: "no-store" });
    if (!res.ok) throw new Error("Failed to fetch triage clusters");
    return await res.json();
  } catch (err) {
    console.warn("Backend offline, loading static demo sectors...", err);
    return MOCK_CLUSTERS;
  }
}

export async function fetchClusterEvidence(clusterId: string): Promise<ClusterDetail> {
  try {
    const res = await fetch(`${API_BASE_URL}/clusters/${encodeURIComponent(clusterId)}/evidence`, {
      cache: "no-store",
    });
    if (!res.ok) throw new Error(`Failed to fetch evidence for cluster ${clusterId}`);
    return await res.json();
  } catch (err) {
    console.warn(`Backend offline, loading static mock evidence for ${clusterId}...`, err);
    return getMockClusterDetail(clusterId);
  }
}

export async function submitReviewAction(
  clusterId: string,
  payload: {
    action: ReviewState;
    analyst_id: string;
    analyst_notes?: string;
    dismissal_reason?: DismissalReason;
  }
): Promise<ClusterTelemetry> {
  try {
    const res = await fetch(`${API_BASE_URL}/clusters/${encodeURIComponent(clusterId)}/review`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "Failed to submit review action");
    }
    return await res.json();
  } catch (err) {
    console.warn("Backend offline, simulating review action locally...", err);
    const cluster = MOCK_CLUSTERS.find((c) => c.cluster_id === clusterId) || MOCK_CLUSTERS[0];
    cluster.state = payload.action;
    return cluster;
  }
}

export async function exportGeoJSON(): Promise<void> {
  try {
    const res = await fetch(`${API_BASE_URL}/export/geojson`, { cache: "no-store" });
    if (!res.ok) throw new Error("Failed to export GeoJSON");
    const data = await res.json();
    downloadFile(
      JSON.stringify(data, null, 2),
      `rescuemesh-triage-export-${new Date().toISOString().replace(/[:.]/g, "-")}.geojson`,
      "application/geo+json"
    );
  } catch (err) {
    console.warn("Backend offline, generating offline GeoJSON export...", err);
    const geojson = {
      type: "FeatureCollection",
      features: MOCK_CLUSTERS.map((c) => ({
        type: "Feature",
        geometry: {
          type: "Point",
          coordinates: [c.centroid_lon, c.centroid_lat],
        },
        properties: {
          cluster_id: c.cluster_id,
          priority: c.priority,
          triage_index: c.triage_index,
          state: c.state,
          asset_count: c.asset_count,
          severe_damage_count: c.severe_damage_count,
          recommended_action: c.recommended_action,
          access_status: c.osm_telemetry?.access_status,
        },
      })),
    };
    downloadFile(
      JSON.stringify(geojson, null, 2),
      `rescuemesh-triage-export-${new Date().toISOString().replace(/[:.]/g, "-")}.geojson`,
      "application/geo+json"
    );
  }
}

export async function exportCoT(): Promise<void> {
  try {
    const res = await fetch(`${API_BASE_URL}/export/cot`, { cache: "no-store" });
    if (!res.ok) throw new Error("Failed to export Cursor-on-Target XML");
    const text = await res.text();
    downloadFile(
      text,
      `rescuemesh-cot-events-${new Date().toISOString().replace(/[:.]/g, "-")}.xml`,
      "application/xml"
    );
  } catch (err) {
    console.warn("Backend offline, generating offline CoT XML export...", err);
    const isoNow = new Date().toISOString();
    const xml = `<?xml version="1.0" standalone="yes"?>\n<event version="2.0" uid="RESCUEMESH-OFFLINE" type="a-f-G-U-C" time="${isoNow}" start="${isoNow}" stale="${new Date(
      Date.now() + 3600000
    ).toISOString()}" how="m-g">\n  <point lat="29.7604" lon="-95.3698" hae="10.0" ce="15.0" le="10.0"/>\n  <detail>\n    <contact callsign="RESCUEMESH-CP"/>\n    <remarks>Houston Incident Triage Offline Events Export</remarks>\n  </detail>\n</event>`;
    downloadFile(
      xml,
      `rescuemesh-cot-events-${new Date().toISOString().replace(/[:.]/g, "-")}.xml`,
      "application/xml"
    );
  }
}

export async function fetchAOISummary(): Promise<AOISummary> {
  try {
    const res = await fetch(`${API_BASE_URL}/aoi`, { cache: "no-store" });
    if (!res.ok) throw new Error("Failed to fetch AOI metadata");
    return await res.json();
  } catch (err) {
    console.warn("Backend offline, loading mock AOI summary...", err);
    return {
      aoi_id: "AOI-HOUSTON-HARVEY",
      name: "Houston Metropolitan Area",
      event_name: "Hurricane Harvey Response",
      center: { latitude: 29.7604, longitude: -95.3698 },
      bounding_box: [-95.55, 29.6, -95.15, 29.9],
      total_tiles_processed: 1240,
      critical_sectors_count: 2,
      high_sectors_count: 1,
      estimated_affected_population: 48500,
      flood_coverage_sq_km: 142.6,
    };
  }
}

export async function fetchSectors(): Promise<SectorCluster[]> {
  try {
    const res = await fetch(`${API_BASE_URL}/sectors`, { cache: "no-store" });
    if (!res.ok) throw new Error("Failed to fetch sectors");
    return await res.json();
  } catch (err) {
    console.warn("Backend offline, returning empty mock sectors...", err);
    return [];
  }
}

export async function fetchTiles(): Promise<TileAnalysisResult[]> {
  try {
    const res = await fetch(`${API_BASE_URL}/tiles`, { cache: "no-store" });
    if (!res.ok) throw new Error("Failed to fetch satellite tiles");
    return await res.json();
  } catch (err) {
    console.warn("Backend offline, returning empty mock tiles...", err);
    return [];
  }
}

export async function fetchSitRep(): Promise<SituationReport> {
  try {
    const res = await fetch(`${API_BASE_URL}/sitrep`, { cache: "no-store" });
    if (!res.ok) throw new Error("Failed to generate SITREP");
    return await res.json();
  } catch (err) {
    console.warn("Backend offline, returning mock situation report...", err);
    return {
      report_id: "SITREP-HOUSTON-ACTIVE",
      generated_at: new Date().toISOString(),
      incident_name: "Hurricane Harvey Rapid Disaster Triage",
      executive_summary: "Multiple residential sectors exhibit critical structural collapse and inundated access roads.",
      key_priorities: [
        "Sector HARVEY-CL-001 medical evacuation via air extraction",
        "Clear debris blockage on North Loop corridor",
      ],
      sector_breakdown: [],
      resource_allocation_recommendations: [
        "Deploy Texas TF-1 swiftwater teams to Sector 001 and 003",
      ],
      weather_hazards: "Intermittent rainfall, receding surface flood waters",
      operational_period: "OP-PERIOD-03 (0600 - 1800 CDT)",
    };
  }
}

export async function fetchWeights(): Promise<TriageHeuristicWeights> {
  try {
    const res = await fetch(`${API_BASE_URL}/config/weights`, { cache: "no-store" });
    if (!res.ok) throw new Error("Failed to fetch weights");
    return await res.json();
  } catch (err) {
    console.warn("Backend offline, loading default triage heuristic weights...", err);
    return MOCK_WEIGHTS;
  }
}

export async function updateWeights(weights: TriageHeuristicWeights): Promise<TriageHeuristicWeights> {
  try {
    const res = await fetch(`${API_BASE_URL}/config/weights`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(weights),
    });
    if (!res.ok) {
      const errorData = await res.json().catch(() => ({}));
      throw new Error(errorData.detail || "Failed to update triage weights");
    }
    return await res.json();
  } catch (err) {
    console.warn("Backend offline, updated weights locally in session...", err);
    return weights;
  }
}

export async function fetchSARFleet(): Promise<SARUnit[]> {
  try {
    const res = await fetch(`${API_BASE_URL}/sar-fleet`, { cache: "no-store" });
    if (!res.ok) throw new Error("Failed to fetch active SAR fleet");
    return await res.json();
  } catch (err) {
    console.warn("Backend offline, returning mock SAR fleet...", err);
    return [
      {
        unit_id: "TX-TF1-SWIFTWATER-4",
        callsign: "TEXAS TF-1 ALPHA",
        phone: "+1-713-555-0199",
        capability: "SWIFTWATER_RESCUE",
        lat: 29.758,
        lon: -95.365,
        status: "READY",
        personnel: 6,
        vehicle: "ZODIAC_MILPRO_INFLATABLE",
        equipment: ["Forward Looking Infrared (FLIR)", "Satellite Mesh Repeater", "Stokes Basket"],
        distance_km: 1.4,
        eta_minutes: 8,
        capability_match: true,
      },
    ];
  }
}

export async function fetchNearestSARUnit(clusterId: string, unitId?: string): Promise<SARUnit> {
  try {
    const url = unitId
      ? `${API_BASE_URL}/clusters/${clusterId}/nearest-unit?unit_id=${encodeURIComponent(unitId)}`
      : `${API_BASE_URL}/clusters/${clusterId}/nearest-unit`;
    const res = await fetch(url, { cache: "no-store" });
    if (!res.ok) throw new Error("Failed to preview nearest SAR unit");
    return await res.json();
  } catch (err) {
    console.warn("Backend offline, returning fallback nearest SAR unit...", err);
    return {
      unit_id: "TX-TF1-SWIFTWATER-4",
      callsign: "TEXAS TF-1 ALPHA",
      phone: "+1-713-555-0199",
      capability: "SWIFTWATER_RESCUE",
      lat: 29.758,
      lon: -95.365,
      status: "READY",
      personnel: 6,
      vehicle: "ZODIAC_MILPRO_INFLATABLE",
      equipment: ["Forward Looking Infrared (FLIR)", "Satellite Mesh Repeater", "Stokes Basket"],
      distance_km: 1.4,
      eta_minutes: 8,
      capability_match: true,
    };
  }
}

export async function dispatchFieldUnit(
  clusterId: string,
  payload?: DispatchFieldRequest
): Promise<DispatchFieldResponse> {
  try {
    const res = await fetch(`${API_BASE_URL}/clusters/${clusterId}/dispatch-field`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload || {}),
    });
    if (!res.ok) {
      const errorData = await res.json().catch(() => ({}));
      throw new Error(errorData.detail || "Tactical field dispatch failed");
    }
    return await res.json();
  } catch (err) {
    console.warn("Backend offline, generating mock dispatch response...", err);
    const cluster = MOCK_CLUSTERS.find((c) => c.cluster_id === clusterId) || MOCK_CLUSTERS[0];
    cluster.state = "DISPATCHED";
    return {
      dispatch_id: `DISP-${Date.now()}`,
      timestamp: new Date().toISOString(),
      cluster_id: clusterId,
      assigned_unit: {
        unit_id: payload?.unit_id || "TX-TF1-SWIFTWATER-4",
        callsign: "TEXAS TF-1 ALPHA",
        phone: "+1-713-555-0199",
        capability: "SWIFTWATER_RESCUE",
        lat: 29.758,
        lon: -95.365,
        status: "DISPATCHED",
        personnel: 6,
        vehicle: "ZODIAC_MILPRO_INFLATABLE",
        equipment: ["FLIR", "Satellite Mesh Repeater"],
        distance_km: 1.4,
        eta_minutes: 8,
      },
      sms_payload: `[RESCUEMESH-TACTICAL-DISPATCH] Target: ${clusterId} | Coord: ${cluster.centroid_lat}°N, ${cluster.centroid_lon}°W | TI: ${cluster.triage_index} | Priority: ${cluster.priority}`,
      recipient_phone: "+1-713-555-0199",
      analyst_id: payload?.analyst_id || "OP-LEAD-01",
      analyst_notes: payload?.analyst_notes || "Field unit dispatched via tactical dashboard fallback.",
      transmission_status: "SENT_LOCAL_BUFFER",
      updated_cluster: cluster,
    };
  }
}

export async function dispatchFieldRescuer(clusterId: string): Promise<FieldDispatchResponse> {
  try {
    const res = await fetch(`${API_BASE_URL}/clusters/${clusterId}/dispatch-field`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
    });
    if (!res.ok) throw new Error("Failed to dispatch field unit");
    return await res.json();
  } catch (err) {
    console.warn("Backend offline, generating mock field rescuer dispatch...", err);
    const cluster = MOCK_CLUSTERS.find((c) => c.cluster_id === clusterId) || MOCK_CLUSTERS[0];
    cluster.state = "DISPATCHED";
    return {
      cluster_id: clusterId,
      status: "DISPATCHED",
      matched_unit: {
        unit_id: "TX-TF1-SWIFTWATER-4",
        callsign: "TEXAS TF-1 ALPHA",
        phone: "+1-713-555-0199",
        capability: "SWIFTWATER_RESCUE",
        lat: 29.758,
        lon: -95.365,
        status: "DISPATCHED",
        personnel: 6,
        vehicle: "ZODIAC_MILPRO_INFLATABLE",
        equipment: ["Forward Looking Infrared (FLIR)", "Satellite Mesh Repeater", "Stokes Basket"],
        distance_km: 1.4,
        eta_minutes: 8,
        capability_match: true,
      },
      distance_km: 1.4,
      sms_payload: `[RESCUEMESH-TACTICAL-DISPATCH] Target Sector: ${clusterId} | Coord: ${cluster.centroid_lat.toFixed(4)}°N, ${Math.abs(cluster.centroid_lon).toFixed(4)}°W | Priority: ${cluster.priority} | Ingress: HARDY TOLL NORTH | Comms: Ch-9`,
      nav_url: `https://www.google.com/maps/dir/?api=1&destination=${cluster.centroid_lat},${cluster.centroid_lon}`,
      dispatched_at: new Date().toISOString(),
    };
  }
}
