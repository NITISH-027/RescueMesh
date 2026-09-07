"use client";

import React, { useState } from "react";
import {
  FileCode,
  Radio,
  Sliders,
  RefreshCw,
} from "lucide-react";
import { exportGeoJSON, exportCoT } from "@/lib/api";

interface CommandHeaderProps {
  activeP1Count: number;
  totalAssetsCount: number;
  isLoading: boolean;
  onRefresh: () => void;
  onOpenWeights?: () => void;
}

export const CommandHeader: React.FC<CommandHeaderProps> = ({
  activeP1Count,
  totalAssetsCount,
  isLoading,
  onRefresh,
  onOpenWeights,
}) => {
  const [isExportingGeo, setIsExportingGeo] = useState(false);
  const [isExportingCoT, setIsExportingCoT] = useState(false);

  const handleExportGeoJSON = async () => {
    setIsExportingGeo(true);
    try {
      await exportGeoJSON();
    } catch (e) {
      console.error("GeoJSON export error:", e);
      alert("Failed to export GeoJSON");
    } finally {
      setIsExportingGeo(false);
    }
  };

  const handleExportCoT = async () => {
    setIsExportingCoT(true);
    try {
      await exportCoT();
    } catch (e) {
      console.error("CoT export error:", e);
      alert("Failed to export CoT XML");
    } finally {
      setIsExportingCoT(false);
    }
  };

  return (
    <header className="h-11 backdrop-blur-md bg-zinc-950/80 border border-zinc-800/80 rounded-xl px-4 flex items-center justify-between select-none font-sans shadow-xl">
      {/* Left Brand Section */}
      <div className="flex items-center space-x-3.5">
        <div className="flex items-center space-x-2">
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
          <span className="font-medium tracking-tight text-zinc-100 text-sm">
            RescueMesh
          </span>
        </div>

        <span className="text-zinc-700">|</span>

        <span className="text-[10px] px-2 py-0.5 rounded bg-zinc-900 text-zinc-400 border border-zinc-800 font-mono tracking-wider">
          HOUSTON AOI // HARVEY
        </span>
      </div>

      {/* Middle Quick Metrics Inline Data Row */}
      <div className="hidden lg:flex items-center space-x-4 text-xs font-mono text-zinc-400">
        <span>
          AOI: <strong className="text-zinc-200 font-normal">12.4 km²</strong>
        </span>
        <span className="text-zinc-700">•</span>
        <span>
          Assets: <strong className="text-zinc-200 font-normal">{totalAssetsCount}</strong>
        </span>
        <span className="text-zinc-700">•</span>
        <span>
          Confidence: <strong className="text-zinc-200 font-normal">91.4%</strong>
        </span>
        <span className="text-zinc-700">•</span>
        <span>
          Critical: <strong className="text-rose-400 font-normal">{activeP1Count}</strong>
        </span>
      </div>

      {/* Right Quick Actions (Minimal Ghost Outline Buttons) */}
      <div className="flex items-center space-x-1.5">
        {onOpenWeights && (
          <button
            onClick={onOpenWeights}
            className="bg-zinc-900/60 hover:bg-zinc-800 text-zinc-300 border border-zinc-700/50 rounded-md text-xs px-2.5 py-1 transition-all flex items-center gap-1.5"
            title="Adjust MCDA Triage Weights"
          >
            <Sliders className="h-3.5 w-3.5 text-zinc-400" />
            <span className="hidden sm:inline text-[11px]">Weights</span>
          </button>
        )}

        <button
          onClick={handleExportGeoJSON}
          disabled={isExportingGeo}
          className="bg-zinc-900/60 hover:bg-zinc-800 text-zinc-300 border border-zinc-700/50 rounded-md text-xs px-2.5 py-1 transition-all flex items-center gap-1.5 disabled:opacity-50"
          title="Export RFC 7946 GeoJSON FeatureCollection"
        >
          <FileCode className="h-3.5 w-3.5 text-zinc-400" />
          <span className="hidden sm:inline text-[11px]">GeoJSON</span>
        </button>

        <button
          onClick={handleExportCoT}
          disabled={isExportingCoT}
          className="bg-zinc-900/60 hover:bg-zinc-800 text-zinc-300 border border-zinc-700/50 rounded-md text-xs px-2.5 py-1 transition-all flex items-center gap-1.5 disabled:opacity-50"
          title="Export Cursor-on-Target (CoT XML) for ATAK/iTAK"
        >
          <Radio className="h-3.5 w-3.5 text-zinc-400" />
          <span className="hidden sm:inline text-[11px]">ATAK CoT</span>
        </button>

        <button
          onClick={onRefresh}
          disabled={isLoading}
          className="p-1 rounded-md bg-zinc-900/60 hover:bg-zinc-800 text-zinc-400 hover:text-zinc-200 border border-zinc-700/50 transition-all disabled:opacity-50"
          title="Refresh Telemetry Stream"
        >
          <RefreshCw className={`h-3.5 w-3.5 ${isLoading ? "animate-spin text-zinc-200" : ""}`} />
        </button>
      </div>
    </header>
  );
};
