import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";
import { PriorityLevel, ReviewState } from "@/types/triage";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function getPriorityColor(priority: PriorityLevel) {
  switch (priority) {
    case "P1":
    case "CRITICAL":
      return {
        bg: "bg-rose-500/5",
        border: "border-rose-500/30",
        text: "text-rose-400",
        badge: "bg-rose-500/10 text-rose-300 border border-rose-500/20",
        indicator: "bg-rose-500",
        glow: "shadow-none",
      };
    case "P2":
    case "HIGH":
      return {
        bg: "bg-amber-500/5",
        border: "border-amber-500/30",
        text: "text-amber-400",
        badge: "bg-amber-500/10 text-amber-300 border border-amber-500/20",
        indicator: "bg-amber-400",
        glow: "shadow-none",
      };
    case "P3":
    case "MEDIUM":
      return {
        bg: "bg-zinc-800/30",
        border: "border-zinc-700/40",
        text: "text-zinc-300",
        badge: "bg-zinc-800 text-zinc-300 border border-zinc-700/60",
        indicator: "bg-zinc-400",
        glow: "shadow-none",
      };
    case "P4":
    case "LOW":
    default:
      return {
        bg: "bg-zinc-900/40",
        border: "border-zinc-800",
        text: "text-zinc-500",
        badge: "bg-zinc-900 text-zinc-400 border border-zinc-800",
        indicator: "bg-zinc-600",
        glow: "shadow-none",
      };
  }
}

export function getStateBadgeColor(state: ReviewState) {
  switch (state) {
    case "DISPATCHED":
      return "bg-zinc-800 text-zinc-200 border border-zinc-600/60 font-mono";
    case "VERIFIED":
      return "bg-emerald-950/40 text-emerald-300 border border-emerald-700/40 font-mono";
    case "DISMISSED":
      return "bg-zinc-900 text-zinc-500 border border-zinc-800 line-through font-mono";
    case "AI_CANDIDATE":
    default:
      return "bg-zinc-900 text-zinc-400 border border-zinc-800 font-mono";
  }
}
