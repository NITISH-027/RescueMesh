"use client";

import React from "react";
import { ScoreBreakdown } from "@/types/triage";

interface ScoreDecompositionProps {
  scoreBreakdown: ScoreBreakdown;
  triageIndex: number;
}

export const ScoreDecomposition: React.FC<ScoreDecompositionProps> = ({
  scoreBreakdown,
  triageIndex,
}) => {
  const parsePct = (fractionStr: string): number => {
    if (!fractionStr || !fractionStr.includes("/")) return 50;
    const [num, den] = fractionStr.split("/").map((v) => parseFloat(v));
    if (isNaN(num) || isNaN(den) || den === 0) return 50;
    return Math.min(100, Math.max(0, (num / den) * 100));
  };

  const criteria = [
    {
      label: "Damage Density (D_c)",
      fraction: scoreBreakdown.damage_density || "0.0/34.0",
      pct: parsePct(scoreBreakdown.damage_density),
      barColor: "bg-[#FB7185]",
      textColor: "text-[#FB7185]",
    },
    {
      label: "Road Isolation (A_c)",
      fraction: scoreBreakdown.road_isolation || "0.0/22.0",
      pct: parsePct(scoreBreakdown.road_isolation),
      barColor: "bg-[#FBBF24]",
      textColor: "text-[#FBBF24]",
    },
    {
      label: "Critical Vulnerability (V_c)",
      fraction: scoreBreakdown.vulnerability_proxy || "0.0/20.0",
      pct: parsePct(scoreBreakdown.vulnerability_proxy),
      barColor: "bg-[#A1A1AA]",
      textColor: "text-[#A1A1AA]",
    },
    {
      label: "Scale of Impact (S_c)",
      fraction: scoreBreakdown.scale_of_impact || "0.0/14.0",
      pct: parsePct(scoreBreakdown.scale_of_impact),
      barColor: "bg-[#E4E4E7]",
      textColor: "text-[#E4E4E7]",
    },
    {
      label: "Information Gap (U_c)",
      fraction: scoreBreakdown.uncertainty_penalty || "0.0/10.0",
      pct: parsePct(scoreBreakdown.uncertainty_penalty),
      barColor: "bg-[#71717A]",
      textColor: "text-[#71717A]",
    },
  ];

  return (
    <div className="space-y-2.5 bg-zinc-900/60 p-3.5 rounded-lg border border-zinc-800/80 text-xs font-sans">
      <div className="flex items-center justify-between pb-1.5 border-b border-zinc-800/80">
        <span className="font-medium text-zinc-200 text-xs tracking-tight">
          MCDA Multi-Criteria Breakdown
        </span>
        <span className="text-zinc-500 font-mono text-xs">
          TI: <strong className="text-zinc-100 font-normal">{triageIndex}</strong> / 100
        </span>
      </div>

      <div className="space-y-2.5 pt-1">
        {criteria.map((item, idx) => (
          <div key={idx} className="space-y-1">
            <div className="flex justify-between items-center text-xs">
              <span className="text-zinc-400">
                {item.label}
              </span>
              <span className={`font-mono text-[11px] ${item.textColor}`}>
                {item.fraction}
              </span>
            </div>
            {/* 3px Slate Track */}
            <div className="h-[3px] w-full bg-zinc-800 rounded-full overflow-hidden">
              <div
                className={`h-full ${item.barColor} rounded-full transition-all duration-300`}
                style={{ width: `${item.pct}%` }}
              />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
