"use client";

import React, { useState, useMemo } from "react";
import { ClusterTelemetry } from "@/types/triage";
import {
  Search,
  Users,
  Flame,
  AlertTriangle,
  Compass,
} from "lucide-react";

interface TriageQueueProps {
  clusters: ClusterTelemetry[];
  selectedClusterId: string | null;
  onSelectCluster: (cluster: ClusterTelemetry) => void;
}

export const TriageQueue: React.FC<TriageQueueProps> = ({
  clusters,
  selectedClusterId,
  onSelectCluster,
}) => {
  const [filterChip, setFilterChip] = useState<"ALL" | "P1" | "P2" | "DISPATCHED">("ALL");
  const [searchQuery, setSearchQuery] = useState<string>("");

  const filteredClusters = useMemo(() => {
    return clusters.filter((c) => {
      // Filter chip matching
      if (filterChip === "P1" && c.priority !== "P1" && c.priority !== "CRITICAL") return false;
      if (filterChip === "P2" && c.priority !== "P2" && c.priority !== "HIGH") return false;
      if (filterChip === "DISPATCHED" && c.state !== "DISPATCHED") return false;

      // Text search matching
      if (searchQuery.trim()) {
        const query = searchQuery.toLowerCase();
        const matchId = c.cluster_id.toLowerCase().includes(query);
        const matchAction = c.recommended_action.toLowerCase().includes(query);
        return matchId || matchAction;
      }
      return true;
    });
  }, [clusters, filterChip, searchQuery]);

  return (
    <div className="h-full flex flex-col select-none font-sans overflow-hidden">
      {/* Search and Filter Section */}
      <div className="p-3 border-b border-zinc-800/80 space-y-2.5">
        <div className="relative">
          <Search className="h-3.5 w-3.5 absolute left-2.5 top-2.5 text-zinc-500" />
          <input
            type="text"
            placeholder="Filter sector or action..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full bg-zinc-900/90 text-zinc-200 text-xs pl-8 pr-3 py-1.5 rounded-md border border-zinc-800 focus:outline-none focus:border-zinc-500 placeholder:text-zinc-500 transition-colors"
          />
        </div>

        {/* Filter Chips */}
        <div className="grid grid-cols-4 gap-1 text-[11px]">
          {[
            { id: "ALL", label: `All (${clusters.length})` },
            { id: "P1", label: "Critical" },
            { id: "P2", label: "Priority" },
            { id: "DISPATCHED", label: "Dispatched" },
          ].map((chip) => (
            <button
              key={chip.id}
              onClick={() => setFilterChip(chip.id as any)}
              className={`py-1 px-1.5 rounded text-center truncate border transition-colors ${
                filterChip === chip.id
                  ? "bg-zinc-800 text-zinc-200 border-zinc-700 font-medium shadow-sm"
                  : "bg-transparent text-zinc-400 border-transparent hover:text-zinc-300 hover:bg-zinc-900/60"
              }`}
            >
              {chip.label}
            </button>
          ))}
        </div>
      </div>

      {/* Queue Meta Header */}
      <div className="px-3 py-2 border-b border-zinc-800/80 flex items-center justify-between text-[11px] text-zinc-400 font-mono">
        <span>PRIORITIZED SECTORS</span>
        <span>{filteredClusters.length} TARGETS</span>
      </div>

      {/* Ranked Cluster Cards */}
      <div className="flex-1 overflow-y-auto p-2.5 space-y-2">
        {filteredClusters.length === 0 ? (
          <div className="p-8 text-center text-xs text-zinc-500">
            No sectors match filter criteria.
          </div>
        ) : (
          filteredClusters.map((cluster) => {
            const isSelected = cluster.cluster_id === selectedClusterId;
            const isP1 = cluster.priority === "P1" || cluster.priority === "CRITICAL";
            const isP2 = cluster.priority === "P2" || cluster.priority === "HIGH";

            return (
              <div
                key={cluster.cluster_id}
                onClick={() => onSelectCluster(cluster)}
                className={`p-3 rounded-lg border transition-all cursor-pointer text-left relative overflow-hidden ${
                  isSelected
                    ? "bg-zinc-800/50 border-zinc-700 border-l-2 border-l-white/90 shadow-sm"
                    : "bg-zinc-900/60 border-zinc-800/80 hover:border-zinc-700 hover:bg-zinc-900/90"
                }`}
              >
                {/* Top Row: Priority Indicator Dot, Sector ID, State Pill */}
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <span
                      className={`w-2 h-2 rounded-full flex-shrink-0 ${
                        isP1 ? "bg-rose-500" : isP2 ? "bg-amber-400" : "bg-zinc-400"
                      }`}
                    />
                    <span className="text-xs font-semibold text-zinc-100 tracking-tight">
                      {cluster.cluster_id}
                    </span>
                    <span className="text-[10px] font-mono text-zinc-500">
                      TI: {cluster.triage_index}
                    </span>
                  </div>

                  <span
                    className={`text-[10px] px-2 py-0.5 rounded border font-mono ${
                      cluster.state === "DISPATCHED"
                        ? "bg-zinc-800 text-zinc-200 border-zinc-600"
                        : cluster.state === "VERIFIED"
                        ? "bg-emerald-950/50 text-emerald-300 border-emerald-800"
                        : cluster.state === "DISMISSED"
                        ? "bg-zinc-900 text-zinc-500 border-zinc-800 line-through"
                        : "bg-zinc-900 text-zinc-400 border-zinc-800"
                    }`}
                  >
                    {cluster.state.replace(/_/g, " ")}
                  </span>
                </div>

                {/* Recommended Action Tag */}
                <div className="flex items-center gap-1.5 text-xs text-zinc-300 font-mono truncate mb-2">
                  <Compass className="h-3.5 w-3.5 text-zinc-400 flex-shrink-0" />
                  <span className="truncate">
                    {cluster.recommended_action.replace(/_/g, " ")}
                  </span>
                </div>

                {/* Sub-Metrics Strip */}
                <div className="grid grid-cols-3 gap-1 text-[11px] pt-2 border-t border-zinc-800/80 text-zinc-400 font-mono">
                  <div className="flex items-center gap-1 truncate" title="Total Assets">
                    <Users className="h-3 w-3 text-zinc-500" />
                    <span>Assets: <strong className="text-zinc-200 font-normal">{cluster.asset_count}</strong></span>
                  </div>
                  <div className="flex items-center gap-1 truncate" title="Severe Damage Assets">
                    <Flame className="h-3 w-3 text-rose-500" />
                    <span>Severe: <strong className="text-rose-400 font-normal">{cluster.severe_damage_count}</strong></span>
                  </div>
                  <div className="flex items-center gap-1 truncate" title="Road Isolation Ratio">
                    <AlertTriangle className="h-3 w-3 text-amber-500" />
                    <span>Isol: <strong className="text-amber-400 font-normal">{Math.round(cluster.road_isolation_score * 100)}%</strong></span>
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};
