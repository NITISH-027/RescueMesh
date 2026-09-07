"use client";

import React, { useState } from "react";
import { ClusterDetail, FieldDispatchResponse } from "@/types/triage";
import { ExternalLink, Check, Copy, Radio } from "lucide-react";

interface DispatchModalProps {
  isOpen: boolean;
  cluster: ClusterDetail;
  dispatchData: FieldDispatchResponse | null;
  onClose: () => void;
}

export default function DispatchModal({
  isOpen,
  cluster,
  dispatchData,
  onClose,
}: DispatchModalProps) {
  const [copied, setCopied] = useState<boolean>(false);

  if (!isOpen || !dispatchData) return null;

  const unit = dispatchData.matched_unit;
  const navUrl = dispatchData.nav_url;
  const smsText = dispatchData.sms_payload;

  const handleCopySMS = () => {
    navigator.clipboard.writeText(smsText);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-md p-4 animate-in fade-in duration-150 select-none font-sans">
      <div className="bg-zinc-950 border border-zinc-800 rounded-xl shadow-2xl max-w-lg w-full flex flex-col overflow-hidden text-zinc-200">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-3.5 bg-zinc-900/60 border-b border-zinc-800">
          <div className="flex items-center gap-2">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
            <h3 className="text-xs font-semibold text-zinc-100 tracking-tight">
              Field Rescuer Direct SMS Dispatch
            </h3>
          </div>
          <button
            onClick={onClose}
            className="text-zinc-400 hover:text-zinc-200 text-xs transition-colors p-1"
          >
            ✕
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-5 space-y-4 text-xs">
          {/* Status Pill */}
          <div className="flex items-center justify-between p-2.5 bg-zinc-900/40 border border-zinc-800 rounded-lg">
            <div className="flex items-center gap-2">
              <Radio className="h-3.5 w-3.5 text-zinc-400 animate-pulse" />
              <span className="text-xs text-zinc-300 font-medium">
                Tactical Handoff Transmitted via Twilio Gateway
              </span>
            </div>
            <span className="text-[10px] font-mono text-zinc-500">
              {dispatchData.dispatched_at || "JUST NOW"}
            </span>
          </div>

          {/* Assigned Unit Telemetry Card */}
          <div className="p-3.5 bg-zinc-900/40 border border-zinc-800 rounded-lg space-y-2">
            <div className="flex justify-between items-start">
              <div>
                <span className="text-[10px] text-zinc-400 font-medium uppercase block tracking-wider mb-0.5">
                  Assigned SAR Unit
                </span>
                <h4 className="text-sm font-semibold text-zinc-100">
                  {unit?.callsign || "SAR Field Unit"}
                </h4>
                <p className="text-xs text-zinc-400 mt-1">
                  Vehicle: <span className="text-zinc-200">{unit?.vehicle || "Tactical Vehicle"}</span>
                </p>
                <p className="text-xs text-zinc-400 font-mono">
                  Radio / Tel: <span className="text-zinc-300">{unit?.phone || "+1 (832) 555-0100"}</span>
                </p>
              </div>

              <div className="text-right">
                <span className="text-[10px] text-zinc-500 block font-mono">PROXIMITY</span>
                <span className="text-base font-bold font-mono text-emerald-400">
                  {dispatchData.distance_km.toFixed(1)} km
                </span>
                <span className="text-[10px] text-zinc-500 block">from centroid</span>
              </div>
            </div>
          </div>

          {/* Raw SMS Telegram Terminal Box */}
          <div className="space-y-1.5">
            <div className="flex items-center justify-between">
              <label className="text-[11px] text-zinc-400 font-medium">
                SMS Telegram Payload
              </label>
              <div className="flex items-center gap-2">
                <span className="text-[10px] font-mono text-zinc-500">
                  {smsText.length}/160 chars
                </span>
                <button
                  type="button"
                  onClick={handleCopySMS}
                  className="text-[10px] px-2 py-0.5 bg-zinc-800 hover:bg-zinc-700 text-zinc-200 rounded border border-zinc-700/60 flex items-center gap-1 transition-colors"
                >
                  {copied ? (
                    <>
                      <Check className="h-3 w-3 text-emerald-400" />
                      Copied
                    </>
                  ) : (
                    <>
                      <Copy className="h-3 w-3" />
                      Copy SMS
                    </>
                  )}
                </button>
              </div>
            </div>

            <div className="p-3 bg-black/90 border border-zinc-800 rounded-lg text-emerald-400 font-mono text-[11px] leading-relaxed whitespace-pre-wrap select-all">
              {smsText}
            </div>
          </div>
        </div>

        {/* Footer Action Buttons */}
        <div className="flex items-center justify-between px-5 py-3.5 bg-zinc-900/60 border-t border-zinc-800">
          <a
            href={navUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="px-3.5 py-2 rounded-lg text-xs font-medium text-zinc-300 hover:text-white bg-zinc-800/80 hover:bg-zinc-700 border border-zinc-700/60 flex items-center gap-1.5 transition-colors"
          >
            <ExternalLink className="h-3.5 w-3.5 text-zinc-400" />
            Open Navigation Link
          </a>

          <button
            onClick={onClose}
            className="px-4 py-2 rounded-lg text-xs font-semibold bg-zinc-100 hover:bg-white text-zinc-950 flex items-center gap-1.5 shadow-md transition-all"
          >
            <Check className="h-3.5 w-3.5" />
            Confirm Field Handoff
          </button>
        </div>
      </div>
    </div>
  );
}
