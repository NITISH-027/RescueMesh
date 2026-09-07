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
} from "@/types/triage";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8001/api/v1';

export async function fetchClusters(params?: {
  priority?: string;
  state?: string;
  min_score?: number;
}): Promise<ClusterTelemetry[]> {
  const searchParams = new URLSearchParams();
  if (params?.priority && params.priority !== "ALL") searchParams.append("priority", params.priority);
  if (params?.state && params.state !== "ALL") searchParams.append("state", params.state);
  if (params?.min_score !== undefined) searchParams.append("min_score", params.min_score.toString());

  const url = `${API_BASE_URL}/clusters${searchParams.toString() ? `?${searchParams.toString()}` : ""}`;
  const res = await fetch(url, { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to fetch triage clusters");
  return res.json();
}

export async function fetchClusterEvidence(clusterId: string): Promise<ClusterDetail> {
  const res = await fetch(`${API_BASE_URL}/clusters/${encodeURIComponent(clusterId)}/evidence`, {
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`Failed to fetch evidence for cluster ${clusterId}`);
  return res.json();
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
  const res = await fetch(`${API_BASE_URL}/clusters/${encodeURIComponent(clusterId)}/review`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Failed to submit review action");
  }
  return res.json();
}

export async function exportGeoJSON(): Promise<void> {
  const res = await fetch(`${API_BASE_URL}/export/geojson`, { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to export GeoJSON");
  const data = await res.json();
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/geo+json" });
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `rescuemesh-triage-export-${new Date().toISOString().replace(/[:.]/g, "-")}.geojson`;
  document.body.appendChild(a);
  a.click();
  window.URL.revokeObjectURL(url);
  document.body.removeChild(a);
}

export async function exportCoT(): Promise<void> {
  const res = await fetch(`${API_BASE_URL}/export/cot`, { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to export Cursor-on-Target XML");
  const text = await res.text();
  const blob = new Blob([text], { type: "application/xml" });
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `rescuemesh-cot-events-${new Date().toISOString().replace(/[:.]/g, "-")}.xml`;
  document.body.appendChild(a);
  a.click();
  window.URL.revokeObjectURL(url);
  document.body.removeChild(a);
}

export async function fetchAOISummary(): Promise<AOISummary> {
  const res = await fetch(`${API_BASE_URL}/aoi`, { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to fetch AOI metadata");
  return res.json();
}

export async function fetchSectors(): Promise<SectorCluster[]> {
  const res = await fetch(`${API_BASE_URL}/sectors`, { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to fetch sectors");
  return res.json();
}

export async function fetchTiles(): Promise<TileAnalysisResult[]> {
  const res = await fetch(`${API_BASE_URL}/tiles`, { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to fetch satellite tiles");
  return res.json();
}

export async function fetchSitRep(): Promise<SituationReport> {
  const res = await fetch(`${API_BASE_URL}/sitrep`, { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to generate SITREP");
  return res.json();
}

export async function fetchWeights(): Promise<TriageHeuristicWeights> {
  const res = await fetch(`${API_BASE_URL}/config/weights`, { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to fetch weights");
  return res.json();
}

export async function updateWeights(weights: TriageHeuristicWeights): Promise<TriageHeuristicWeights> {
  const res = await fetch(`${API_BASE_URL}/config/weights`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(weights),
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || "Failed to update triage weights");
  }
  return res.json();
}

export async function fetchSARFleet(): Promise<SARUnit[]> {
  const res = await fetch(`${API_BASE_URL}/sar-fleet`, { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to fetch active SAR fleet");
  return res.json();
}

export async function fetchNearestSARUnit(clusterId: string, unitId?: string): Promise<SARUnit> {
  const url = unitId
    ? `${API_BASE_URL}/clusters/${clusterId}/nearest-unit?unit_id=${encodeURIComponent(unitId)}`
    : `${API_BASE_URL}/clusters/${clusterId}/nearest-unit`;
  const res = await fetch(url, { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to preview nearest SAR unit");
  return res.json();
}

export async function dispatchFieldUnit(
  clusterId: string,
  payload?: DispatchFieldRequest
): Promise<DispatchFieldResponse> {
  const res = await fetch(`${API_BASE_URL}/clusters/${clusterId}/dispatch-field`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload || {}),
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || "Tactical field dispatch failed");
  }
  return res.json();
}

export async function dispatchFieldRescuer(clusterId: string): Promise<FieldDispatchResponse> {
  const res = await fetch(`${API_BASE_URL}/clusters/${clusterId}/dispatch-field`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
  });
  if (!res.ok) throw new Error("Failed to dispatch field unit");
  return res.json();
}
