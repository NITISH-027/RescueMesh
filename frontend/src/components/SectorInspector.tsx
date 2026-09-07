"use client";

import React, { useState } from "react";
import {
  ClusterDetail,
  ReviewState,
  DismissalReason,
  FieldDispatchResponse,
} from "@/types/triage";
import { getPriorityColor, getStateBadgeColor } from "@/lib/utils";
import { ScoreDecomposition } from "./ScoreDecomposition";
import DispatchModal from "./DispatchModal";
import { dispatchFieldRescuer } from "@/lib/api";
import {
  X,
  CheckCircle2,
  XCircle,
  Radio,
  Eye,
  FileText,
  AlertOctagon,
  History,
  ShieldCheck,
  Zap,
  Compass,
} from "lucide-react";

interface SectorInspectorProps {
  cluster: ClusterDetail | null;
  isLoadingEvidence: boolean;
  onClose: () => void;
  onReviewAction: (
    action: ReviewState,
    notes?: string,
    dismissalReason?: DismissalReason
  ) => Promise<void>;
  onRefresh?: () => void;
}

export const SectorInspector: React.FC<SectorInspectorProps> = ({
  cluster,
  isLoadingEvidence,
  onClose,
  onReviewAction,
  onRefresh,
}) => {
  const [activeImageTab, setActiveImageTab] = useState<"GRADCAM" | "RAW">("GRADCAM");
  const [showDismissModal, setShowDismissModal] = useState<boolean>(false);
  const [showDispatchModal, setShowDispatchModal] = useState<boolean>(false);
  const [dispatchData, setDispatchData] = useState<FieldDispatchResponse | null>(null);
  const [dismissalReason, setDismissalReason] = useState<DismissalReason>("ROOF_TEXTURE_ARTIFACT");
  const [analystNotes, setAnalystNotes] = useState<string>("");
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);

  if (!cluster) {
    return (
      <div className="h-full flex items-center justify-center p-8 text-center text-xs text-zinc-500 font-sans select-none">
        Select a disaster sector from the queue or map to inspect evidence and execute triage review.
      </div>
    );
  }

  const priorityStyles = getPriorityColor(cluster.priority);
  const stateBadge = getStateBadgeColor(cluster.state);

  const handleAction = async (action: ReviewState, reason?: DismissalReason) => {
    setIsSubmitting(true);
    try {
      await onReviewAction(action, analystNotes, reason);
      setShowDismissModal(false);
      setAnalystNotes("");
      if (onRefresh) onRefresh();
    } catch (e: any) {
      alert(e.message || "Failed to execute review action");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDirectDispatch = async () => {
    setIsSubmitting(true);
    try {
      const resp = await dispatchFieldRescuer(cluster.cluster_id);
      setDispatchData(resp);
      setShowDispatchModal(true);
      await onReviewAction(
        "DISPATCHED",
        `Direct field handoff to ${resp.matched_unit?.callsign || "SAR Unit"} (${resp.distance_km.toFixed(1)}km away).`
      );
      if (onRefresh) onRefresh();
    } catch (e: any) {
      alert(e.message || "Failed to dispatch field rescuer");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="h-full flex flex-col overflow-y-auto select-none font-sans space-y-4">
      {/* Sector Header */}
      <div className="border-b border-zinc-800/80 pb-3 space-y-2.5">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <h2 className="text-sm font-semibold text-zinc-100 tracking-tight">
              {cluster.cluster_id}
            </h2>
            <span
              className={`text-[10px] font-mono font-medium px-2 py-0.5 rounded ${priorityStyles.badge}`}
            >
              {cluster.priority}
            </span>
            <span
              className={`text-[10px] px-2 py-0.5 rounded border ${stateBadge}`}
            >
              {cluster.state.replace(/_/g, " ")}
            </span>
          </div>

          <button
            onClick={onClose}
            className="p-1 rounded text-zinc-400 hover:text-white hover:bg-zinc-800 transition-colors"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Minimal Composite Triage Index */}
        <div className="p-3 rounded-lg bg-zinc-900/60 border border-zinc-800/80 space-y-2">
          <div className="flex items-center justify-between">
            <div>
              <span className="text-[11px] text-zinc-400 block font-medium">
                Triage Priority Index
              </span>
              <div className="flex items-baseline gap-1">
                <span className="text-2xl font-bold font-mono text-zinc-100">
                  {cluster.triage_index}
                </span>
                <span className="text-xs font-mono text-zinc-500">/100</span>
              </div>
            </div>

            <div className="text-right text-xs font-mono text-zinc-400 space-y-0.5">
              <div>{cluster.centroid_lat.toFixed(4)}°N</div>
              <div>{Math.abs(cluster.centroid_lon).toFixed(4)}°W</div>
            </div>
          </div>

          {/* Thin 3px Progress Indicator Line */}
          <div className="h-[3px] w-full bg-zinc-800 rounded-full overflow-hidden">
            <div
              className={`h-full rounded-full ${
                cluster.triage_index >= 75
                  ? "bg-rose-500"
                  : cluster.triage_index >= 50
                  ? "bg-amber-400"
                  : "bg-zinc-400"
              }`}
              style={{ width: `${cluster.triage_index}%` }}
            />
          </div>
        </div>
      </div>

      {/* Saliency / Satellite Image Frame */}
      <div className="space-y-2 bg-zinc-900/60 p-3 rounded-lg border border-zinc-800/80">
        <div className="flex items-center justify-between">
          <span className="text-xs font-medium text-zinc-300 flex items-center gap-1.5">
            <Eye className="h-3.5 w-3.5 text-zinc-400" />
            Satellite Evidence
          </span>

          {/* Segmented Control */}
          <div className="flex bg-zinc-950 rounded-md p-0.5 border border-zinc-800 text-[11px]">
            <button
              onClick={() => setActiveImageTab("GRADCAM")}
              className={`px-2 py-0.5 rounded transition-colors ${
                activeImageTab === "GRADCAM"
                  ? "bg-zinc-800 text-zinc-100 font-medium shadow-sm"
                  : "text-zinc-400 hover:text-zinc-300"
              }`}
            >
              Grad-CAM
            </button>
            <button
              onClick={() => setActiveImageTab("RAW")}
              className={`px-2 py-0.5 rounded transition-colors ${
                activeImageTab === "RAW"
                  ? "bg-zinc-800 text-zinc-100 font-medium shadow-sm"
                  : "text-zinc-400 hover:text-zinc-300"
              }`}
            >
              Raw Tile
            </button>
          </div>
        </div>

        {/* Image Container */}
        <div className="relative h-44 w-full bg-zinc-950 rounded-lg border border-zinc-800 flex items-center justify-center overflow-hidden">
          {(cluster.gradcam_url || cluster.gradcam_overlay_base64) && activeImageTab === "GRADCAM" ? (
            <img
              src={cluster.gradcam_url || cluster.gradcam_overlay_base64}
              alt="Grad-CAM Saliency Overlay"
              className="h-44 w-full object-cover rounded-lg"
            />
          ) : (cluster.raw_tile_url || cluster.raw_tile_base64) && activeImageTab === "RAW" ? (
            <img
              src={cluster.raw_tile_url || cluster.raw_tile_base64}
              alt="Raw Satellite Building Patch"
              className="h-44 w-full object-cover rounded-lg"
            />
          ) : (
            <div className="flex flex-col items-center justify-center text-zinc-500 text-xs space-y-1 p-4">
              <span className="text-[11px] text-zinc-400">
                {activeImageTab === "GRADCAM"
                  ? "Structural Debris Saliency Map"
                  : "High-Resolution Satellite Building Patch"}
              </span>
            </div>
          )}
        </div>
      </div>

      {/* MCDA Score Decomposition */}
      <ScoreDecomposition
        scoreBreakdown={cluster.score_breakdown}
        triageIndex={cluster.triage_index}
      />

      {/* Dynamic OpenStreetMap Topological Context */}
      {cluster.osm_telemetry && (
        <div className="bg-zinc-900/60 p-3 rounded-lg border border-zinc-800/80 space-y-2 text-xs font-sans">
          <div className="flex items-center justify-between border-b border-zinc-800/80 pb-1.5">
            <span className="font-medium text-zinc-200 text-xs flex items-center gap-1.5">
              <Compass className="h-3.5 w-3.5 text-zinc-400" />
              OpenStreetMap Context
            </span>
            <span
              className={`text-[10px] font-mono font-medium px-2 py-0.5 rounded border ${
                cluster.osm_telemetry.access_status === "ACCESSIBLE"
                  ? "bg-emerald-950/50 text-emerald-300 border-emerald-800"
                  : cluster.osm_telemetry.access_status === "PARTIALLY_BLOCKED"
                  ? "bg-amber-950/50 text-amber-300 border-amber-800"
                  : "bg-rose-950/50 text-rose-300 border-rose-800"
              }`}
            >
              {cluster.osm_telemetry.access_status.replace(/_/g, " ")}
            </span>
          </div>

          <div className="grid grid-cols-2 gap-2 text-[11px] font-mono text-zinc-400">
            <div>
              Nearest Medical: <strong className="text-zinc-200 font-normal">{cluster.osm_telemetry.nearest_hospital_dist_km} km</strong>
            </div>
            <div>
              Evaluated Edges: <strong className="text-zinc-200 font-normal">{cluster.osm_telemetry.topological_edges_evaluated}</strong>
            </div>
          </div>

          {cluster.osm_telemetry.osm_feature_tags && cluster.osm_telemetry.osm_feature_tags.length > 0 && (
            <div className="pt-1.5 border-t border-zinc-800/60 flex flex-wrap gap-1">
              {cluster.osm_telemetry.osm_feature_tags.slice(0, 3).map((tag, idx) => (
                <span key={idx} className="text-[10px] bg-zinc-950 px-1.5 py-0.5 rounded border border-zinc-800 text-zinc-400 font-mono">
                  {tag}
                </span>
              ))}
            </div>
          )}
        </div>
      )}

      {/* SITREP Executive Briefing Memorandum */}
      <div className="bg-zinc-950/60 border border-zinc-800/80 rounded-lg p-3 text-xs leading-relaxed text-zinc-300 font-sans space-y-2.5">
        <div className="flex items-center justify-between border-b border-zinc-800/80 pb-1.5 text-xs text-zinc-400">
          <span className="flex items-center gap-1.5 text-zinc-200 font-medium">
            <FileText className="h-3.5 w-3.5 text-zinc-400" />
            SITREP Briefing
          </span>
          <span className="text-[10px] font-mono text-zinc-500">
            {cluster.sitrep?.report_id || `SITREP-TX-${cluster.cluster_id}`}
          </span>
        </div>

        <p className="text-xs text-zinc-300 leading-relaxed font-sans">
          {cluster.sitrep?.tactical_summary ||
            `Tactical Sector ${cluster.cluster_id} encompasses ${cluster.asset_count} asset(s), with ${cluster.severe_damage_count} severe structural breaches detected. Ingress routes compromised.`}
        </p>

        <div className="p-2.5 rounded bg-zinc-900/60 border-l-2 border-l-rose-500 border border-zinc-800 text-[11px] text-zinc-400 flex items-start gap-2">
          <AlertOctagon className="h-3.5 w-3.5 text-rose-400 flex-shrink-0 mt-0.5" />
          <span>
            <strong className="text-zinc-300 font-medium">Operational Caveat:</strong> Remote-sensing evidence supports triage prioritization. Occupancy requires on-ground verification.
          </span>
        </div>
      </div>

      {/* Review Audit History */}
      {cluster.audit_history && cluster.audit_history.length > 0 && (
        <div className="space-y-1.5 bg-zinc-900/40 p-3 rounded-lg border border-zinc-800/80 text-xs">
          <span className="text-zinc-400 font-medium text-[11px] flex items-center gap-1">
            <History className="h-3.5 w-3.5 text-zinc-500" />
            Audit Log ({cluster.audit_history.length})
          </span>
          <div className="space-y-1.5 max-h-24 overflow-y-auto pt-1 font-mono text-[10px]">
            {cluster.audit_history.map((record, i) => (
              <div key={i} className="p-2 bg-zinc-950 rounded border border-zinc-800 text-zinc-300">
                <div className="flex justify-between text-zinc-500 text-[9px]">
                  <span>{record.actor}</span>
                  <span>{record.timestamp.replace("T", " ").replace("Z", "")}</span>
                </div>
                <div className="font-semibold text-zinc-200 mt-0.5">
                  {record.previous_state} → {record.new_state}
                </div>
                {record.notes && <div className="text-zinc-400 italic mt-0.5">"{record.notes}"</div>}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Decision & Dispatch Control Deck */}
      <div className="space-y-2 pt-2 border-t border-zinc-800/80 mt-auto">
        <div className="flex items-center justify-between text-xs text-zinc-400 mb-1">
          <span className="flex items-center gap-1 font-medium text-zinc-300">
            <ShieldCheck className="h-3.5 w-3.5 text-zinc-400" />
            Decision Actions
          </span>
          <span className="text-[11px] font-mono text-zinc-500">OP-LEAD-01</span>
        </div>

        <div className="grid grid-cols-2 gap-2">
          <button
            onClick={() => handleAction("VERIFIED")}
            disabled={isSubmitting || cluster.state === "VERIFIED"}
            className="px-3 py-2 bg-zinc-900/80 hover:bg-zinc-800 text-zinc-200 rounded-lg font-medium text-xs flex items-center justify-center gap-1.5 transition-colors disabled:opacity-50 border border-zinc-700/60"
          >
            <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400" />
            Verify Target
          </button>

          {/* Primary Dispatch Button (Clean Solid Zinc-100) */}
          <button
            onClick={handleDirectDispatch}
            disabled={isSubmitting || cluster.state === "DISPATCHED"}
            className="bg-zinc-100 hover:bg-white text-zinc-950 font-semibold py-2 rounded-lg text-xs tracking-wide shadow-md transition-all flex items-center justify-center gap-1.5 disabled:opacity-50"
          >
            <Zap className="h-3.5 w-3.5 fill-current" />
            ⚡ Dispatch SAR
          </button>
        </div>

        <div className="grid grid-cols-2 gap-2 pt-1">
          <button
            onClick={() => handleAction("AI_CANDIDATE")}
            disabled={isSubmitting}
            className="px-3 py-1.5 bg-transparent hover:bg-zinc-800 text-zinc-400 hover:text-zinc-200 rounded-lg text-xs flex items-center justify-center gap-1 transition-colors border border-zinc-800"
          >
            <Radio className="h-3.5 w-3.5 text-zinc-500" />
            Aerial Recon
          </button>

          <button
            onClick={() => setShowDismissModal(true)}
            disabled={isSubmitting}
            className="px-3 py-1.5 bg-transparent hover:bg-rose-500/10 text-zinc-400 hover:text-rose-400 rounded-lg text-xs flex items-center justify-center gap-1 transition-colors border border-zinc-800 hover:border-rose-500/30"
          >
            <XCircle className="h-3.5 w-3.5" />
            Dismiss Target
          </button>
        </div>
      </div>

      {/* Field Rescuer Proximity & SMS Dispatch Modal */}
      {showDispatchModal && (
        <DispatchModal
          isOpen={showDispatchModal}
          cluster={cluster}
          dispatchData={dispatchData}
          onClose={() => setShowDispatchModal(false)}
        />
      )}

      {/* Dismissal Reason Modal */}
      {showDismissModal && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-md flex items-center justify-center p-4">
          <div className="bg-zinc-950 border border-zinc-800 rounded-xl max-w-md w-full p-4.5 space-y-3.5 shadow-2xl text-zinc-200">
            <div className="flex items-center justify-between border-b border-zinc-800 pb-2">
              <span className="font-semibold text-zinc-100 text-xs flex items-center gap-1.5">
                <XCircle className="h-4 w-4 text-rose-400" />
                Dismiss False Positive: {cluster.cluster_id}
              </span>
              <button
                onClick={() => setShowDismissModal(false)}
                className="text-zinc-400 hover:text-white"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            <div className="space-y-2 text-xs">
              <label className="text-zinc-300 block font-medium">Mandatory Dismissal Reason:</label>
              <select
                value={dismissalReason}
                onChange={(e) => setDismissalReason(e.target.value as DismissalReason)}
                className="w-full bg-zinc-900 border border-zinc-800 rounded-lg p-2 text-zinc-200 focus:outline-none focus:border-zinc-500 text-xs"
              >
                <option value="ROOF_TEXTURE_ARTIFACT">Roof Texture Artifact</option>
                <option value="CLOUD_SHADOW">Cloud Shadow / Illumination Artifact</option>
                <option value="ALREADY_RESOLVED">Already Resolved by Local Units</option>
                <option value="NON_CRITICAL_INFRASTRUCTURE">Non-Critical Infrastructure / Vacant</option>
                <option value="OTHER">Other Justification</option>
              </select>

              <label className="text-zinc-300 block mt-2 font-medium">Analyst Operational Notes:</label>
              <textarea
                rows={3}
                placeholder="Explain justification for audit log..."
                value={analystNotes}
                onChange={(e) => setAnalystNotes(e.target.value)}
                className="w-full bg-zinc-900 border border-zinc-800 rounded-lg p-2 text-zinc-200 focus:outline-none focus:border-zinc-500 text-xs"
              />
            </div>

            <div className="flex justify-end gap-2 pt-2 border-t border-zinc-800">
              <button
                onClick={() => setShowDismissModal(false)}
                className="px-3 py-1.5 rounded-lg text-zinc-400 hover:text-zinc-200 text-xs transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={() => handleAction("DISMISSED", dismissalReason)}
                disabled={isSubmitting}
                className="px-3.5 py-1.5 bg-rose-600 hover:bg-rose-500 text-white rounded-lg text-xs font-medium transition-colors"
              >
                Confirm Dismissal
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
