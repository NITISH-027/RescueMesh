"use client";

import React, { useState, useEffect, useCallback, useMemo } from "react";
import {
  ClusterTelemetry,
  ClusterDetail,
  ReviewState,
  DismissalReason,
  TriageHeuristicWeights,
} from "@/types/triage";
import {
  fetchClusters,
  fetchClusterEvidence,
  submitReviewAction,
  fetchWeights,
  updateWeights,
} from "@/lib/api";
import { CommandHeader } from "@/components/CommandHeader";
import { TriageQueue } from "@/components/TriageQueue";
import { OperationalMap } from "@/components/OperationalMap";
import { SectorInspector } from "@/components/SectorInspector";
import { X, Sliders, CheckCircle2 } from "lucide-react";

export default function RescueMeshCommandDashboard() {
  const [clusters, setClusters] = useState<ClusterTelemetry[]>([]);
  const [selectedCluster, setSelectedCluster] = useState<ClusterTelemetry | null>(null);
  const [clusterDetail, setClusterDetail] = useState<ClusterDetail | null>(null);

  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [isLoadingEvidence, setIsLoadingEvidence] = useState<boolean>(false);

  // Weights modal state
  const [showWeightsModal, setShowWeightsModal] = useState<boolean>(false);
  const [weightForm, setWeightForm] = useState<TriageHeuristicWeights>({
    structural_damage: 0.35,
    flood_inundation: 0.30,
    critical_infrastructure: 0.15,
    population_vulnerability: 0.10,
    access_isolation: 0.10,
  });

  // 1. Fetch all clusters from backend
  const loadClusters = useCallback(async (preserveSelectionId?: string) => {
    setIsLoading(true);
    try {
      const data = await fetchClusters();
      setClusters(data);

      if (data.length > 0) {
        const targetId = preserveSelectionId || data[0].cluster_id;
        const matching = data.find((c) => c.cluster_id === targetId) || data[0];
        setSelectedCluster(matching);
        loadEvidence(matching.cluster_id);
      }
    } catch (err) {
      console.error("Error loading clusters:", err);
    } finally {
      setIsLoading(false);
    }
  }, []);

  // 2. Fetch full detail / Grad-CAM evidence for single cluster
  const loadEvidence = async (clusterId: string) => {
    setIsLoadingEvidence(true);
    try {
      const detail = await fetchClusterEvidence(clusterId);
      setClusterDetail(detail);
    } catch (err) {
      console.error(`Failed to fetch evidence for ${clusterId}:`, err);
    } finally {
      setIsLoadingEvidence(false);
    }
  };

  useEffect(() => {
    loadClusters();
    fetchWeights()
      .then((w) => setWeightForm(w))
      .catch(() => {});
  }, [loadClusters]);

  // 3. Cluster selection handler
  const handleSelectCluster = (cluster: ClusterTelemetry) => {
    setSelectedCluster(cluster);
    loadEvidence(cluster.cluster_id);
  };

  // 4. HITL review action handler
  const handleReviewAction = async (
    action: ReviewState,
    notes?: string,
    dismissalReason?: DismissalReason
  ) => {
    if (!selectedCluster) return;

    await submitReviewAction(selectedCluster.cluster_id, {
      action,
      analyst_id: "OP-LEAD-01",
      analyst_notes: notes,
      dismissal_reason: dismissalReason,
    });

    // Refresh cluster list and re-fetch active detail
    await loadClusters(selectedCluster.cluster_id);
  };

  // 5. Update weights handler
  const handleSaveWeights = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await updateWeights(weightForm);
      setShowWeightsModal(false);
      await loadClusters();
    } catch (err: any) {
      alert(err.message || "Failed to update triage heuristic weights");
    }
  };

  // Metrics computation for Header
  const activeP1Count = useMemo(() => {
    return clusters.filter(
      (c) =>
        (c.priority === "P1" || c.priority === "CRITICAL") &&
        c.state !== "DISMISSED"
    ).length;
  }, [clusters]);

  const totalAssetsCount = useMemo(() => {
    return clusters.reduce((acc, c) => acc + c.asset_count, 0);
  }, [clusters]);

  return (
    <div className="relative w-screen h-screen overflow-hidden bg-[#0A0B0E] text-zinc-100 font-sans select-none">
      {/* 1. Full-Bleed Real Interactive Basemap (Fixed Inset 0) */}
      <OperationalMap
        clusters={clusters}
        selectedCluster={selectedCluster}
        onSelectCluster={handleSelectCluster}
      />

      {/* 2. Floating Top Navigation Bar */}
      <div className="fixed top-3 left-4 right-4 z-20">
        <CommandHeader
          activeP1Count={activeP1Count}
          totalAssetsCount={totalAssetsCount}
          isLoading={isLoading}
          onRefresh={() => loadClusters(selectedCluster?.cluster_id)}
          onOpenWeights={() => setShowWeightsModal(true)}
        />
      </div>

      {/* 3. Floating Left Triage Deck (w-80) */}
      <aside className="fixed top-16 left-4 bottom-4 w-80 backdrop-blur-2xl bg-zinc-950/85 border border-white/10 rounded-xl p-3 flex flex-col z-10 shadow-2xl overflow-hidden">
        <TriageQueue
          clusters={clusters}
          selectedClusterId={selectedCluster?.cluster_id || null}
          onSelectCluster={handleSelectCluster}
        />
      </aside>

      {/* 4. Floating Right Sector Inspector (w-96) */}
      {clusterDetail && (
        <aside className="fixed top-16 right-4 bottom-4 w-96 backdrop-blur-2xl bg-zinc-950/85 border border-white/10 rounded-xl p-4 flex flex-col z-10 shadow-2xl overflow-y-auto">
          <SectorInspector
            cluster={clusterDetail}
            isLoadingEvidence={isLoadingEvidence}
            onClose={() => {
              setSelectedCluster(null);
              setClusterDetail(null);
            }}
            onReviewAction={handleReviewAction}
            onRefresh={() => loadClusters(selectedCluster?.cluster_id)}
          />
        </aside>
      )}

      {/* Weights Tuning Modal */}
      {showWeightsModal && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-md flex items-center justify-center p-4">
          <form
            onSubmit={handleSaveWeights}
            className="bg-slate-950 border border-white/10 rounded-xl max-w-md w-full flex flex-col shadow-2xl overflow-hidden text-xs text-slate-200"
          >
            <div className="p-4 border-b border-white/10 flex items-center justify-between bg-slate-900/50">
              <div className="flex items-center gap-2">
                <Sliders className="h-4 w-4 text-blue-400" />
                <h3 className="font-semibold text-white text-sm tracking-tight">
                  MCDA Triage Scoring Weights
                </h3>
              </div>
              <button
                type="button"
                onClick={() => setShowWeightsModal(false)}
                className="p-1 rounded-md text-slate-400 hover:text-white transition-colors"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            <div className="p-5 space-y-4">
              <p className="text-slate-400 text-xs leading-relaxed">
                Adjust multi-criteria decision weights in real time. Total sum must approximate 1.00.
              </p>

              <div className="space-y-3">
                {[
                  { key: "structural_damage", label: "Structural Damage" },
                  { key: "flood_inundation", label: "Flood Inundation" },
                  { key: "critical_infrastructure", label: "Critical Infrastructure" },
                  { key: "population_vulnerability", label: "Population Vulnerability" },
                  { key: "access_isolation", label: "Access Isolation" },
                ].map(({ key, label }) => (
                  <div key={key} className="flex items-center justify-between gap-4">
                    <label className="text-slate-300 w-44 font-medium">{label}</label>
                    <input
                      type="number"
                      step="0.05"
                      min="0.0"
                      max="1.0"
                      value={weightForm[key as keyof TriageHeuristicWeights]}
                      onChange={(e) =>
                        setWeightForm({
                          ...weightForm,
                          [key]: parseFloat(e.target.value) || 0,
                        })
                      }
                      className="w-20 bg-slate-900 border border-white/10 rounded-md px-2 py-1 text-right text-white focus:outline-none focus:border-blue-500 font-mono text-xs"
                    />
                  </div>
                ))}
              </div>
            </div>

            <div className="p-4 border-t border-white/10 flex justify-end gap-2 bg-slate-900/50">
              <button
                type="button"
                onClick={() => setShowWeightsModal(false)}
                className="px-3 py-1.5 rounded-md text-slate-400 hover:text-white text-xs transition-colors"
              >
                Cancel
              </button>
              <button
                type="submit"
                className="px-4 py-1.5 bg-blue-600 hover:bg-blue-500 text-white rounded-md text-xs font-medium flex items-center gap-1.5 shadow-sm transition-all"
              >
                <CheckCircle2 className="h-3.5 w-3.5" />
                Apply & Re-Index
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
}
