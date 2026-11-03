"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Eye, Layers, Download, ExternalLink, ChevronRight } from "lucide-react";
import type { AnalysisResult } from "@/types/api";
import { assetUrl, b64ToDataUri } from "@/lib/api";
import { cn } from "@/lib/utils";
import { StatsCards } from "./StatsCards";
import { OccupancyChart } from "./OccupancyChart";

interface ResultsPanelProps {
  result: AnalysisResult;
}

type ViewMode = "annotated" | "heatmap";

export function ResultsPanel({ result }: ResultsPanelProps) {
  const [viewMode, setViewMode] = useState<ViewMode>("annotated");

  const imgSrc =
    viewMode === "annotated"
      ? result.annotated_b64
        ? b64ToDataUri(result.annotated_b64)
        : assetUrl(result.annotated_media_url)
      : result.heatmap_b64
      ? b64ToDataUri(result.heatmap_b64)
      : assetUrl(result.heatmap_url);

  const isVideo = result.media_type === "video";

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="space-y-6"
    >
      {/* ── Media viewer ──────────────────────────────────────────────────────── */}
      <div className="glass rounded-2xl overflow-hidden border border-white/[0.06]">
        {/* Toolbar */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-white/[0.06]">
          <div className="flex gap-1">
            {[
              { id: "annotated" as ViewMode, icon: Eye, label: "Detected" },
              { id: "heatmap" as ViewMode, icon: Layers, label: "Heatmap" },
            ].map(({ id, icon: Icon, label }) => (
              <button
                key={id}
                onClick={() => setViewMode(id)}
                className={cn(
                  "flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all duration-200",
                  viewMode === id
                    ? "bg-accent-green/15 text-accent-green border border-accent-green/30"
                    : "text-white/40 hover:text-white/60 hover:bg-white/[0.04]"
                )}
              >
                <Icon size={11} />
                {label}
              </button>
            ))}
          </div>

          <div className="flex items-center gap-2">
            <a
              href={assetUrl(
                viewMode === "annotated"
                  ? result.annotated_media_url
                  : result.heatmap_url
              )}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-xs text-white/40 hover:text-white/60 hover:bg-white/[0.04] transition-all"
            >
              <ExternalLink size={11} />
              Open
            </a>
            <a
              href={assetUrl(
                viewMode === "annotated"
                  ? result.annotated_media_url
                  : result.heatmap_url
              )}
              download
              className="flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-xs text-white/40 hover:text-white/60 hover:bg-white/[0.04] transition-all"
            >
              <Download size={11} />
              Download
            </a>
          </div>
        </div>

        {/* Image / Video display */}
        <div className="relative bg-black/40 min-h-[280px] flex items-center justify-center">
          <AnimatePresence mode="wait">
            <motion.div
              key={viewMode}
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.2 }}
              className="w-full"
            >
              {isVideo && viewMode === "annotated" ? (
                <video
                  src={assetUrl(result.annotated_media_url)}
                  controls
                  className="w-full max-h-[420px] object-contain"
                />
              ) : (
                <img
                  src={imgSrc}
                  alt={viewMode === "annotated" ? "Detected vehicles" : "Heatmap overlay"}
                  className="w-full max-h-[420px] object-contain"
                />
              )}
            </motion.div>
          </AnimatePresence>

          {/* Occupancy badge */}
          <div className="absolute top-3 right-3">
            <OccupancyBadge ratio={result.occupancy_ratio} />
          </div>
        </div>

        {/* Capacity legend bar */}
        <CapacityBar result={result} />
      </div>

      {/* ── Stats cards ───────────────────────────────────────────────────────── */}
      <StatsCards result={result} />

      {/* ── Timeline chart (video only) ───────────────────────────────────────── */}
      {result.timeline && result.timeline.length > 1 && (
        <OccupancyChart timeline={result.timeline} />
      )}

      {/* ── Free regions list ─────────────────────────────────────────────────── */}
      {result.free_regions && result.free_regions.length > 0 && (
        <FreeRegionsList regions={result.free_regions} />
      )}
    </motion.div>
  );
}

// ── Sub-components ───────────────────────────────────────────────────────────

function OccupancyBadge({ ratio }: { ratio: number }) {
  const pct = Math.round(ratio * 100);
  const color =
    pct > 80 ? "text-accent-red bg-accent-red/20 border-accent-red/30" :
    pct > 50 ? "text-accent-yellow bg-accent-yellow/20 border-accent-yellow/30" :
    "text-accent-green bg-accent-green/20 border-accent-green/30";

  return (
    <span className={cn("px-2.5 py-1 rounded-full text-xs font-mono font-bold border backdrop-blur-sm", color)}>
      {pct}% full
    </span>
  );
}

function CapacityBar({ result }: { result: AnalysisResult }) {
  const totalDetected = result.vehicles.total;
  const totalCap = totalDetected + result.estimated_capacity.cars;
  const occupiedPct = totalCap > 0 ? (totalDetected / totalCap) * 100 : 0;

  return (
    <div className="px-4 py-3 border-t border-white/[0.06] space-y-2">
      <div className="flex justify-between text-xs text-white/40">
        <span>Parking capacity</span>
        <span className="font-mono">
          {totalDetected} / ~{totalCap} slots
        </span>
      </div>
      <div className="h-2 rounded-full bg-white/[0.06] overflow-hidden flex">
        <motion.div
          className="h-full bg-accent-red/80 rounded-l-full"
          initial={{ width: 0 }}
          animate={{ width: `${occupiedPct}%` }}
          transition={{ delay: 0.3, duration: 0.8, ease: "easeOut" }}
        />
        <motion.div
          className="h-full bg-accent-green/60 flex-1"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.5 }}
        />
      </div>
      <div className="flex gap-4 text-xs">
        <span className="flex items-center gap-1.5 text-white/40">
          <span className="w-2 h-2 rounded-full bg-accent-red/80 inline-block" />
          {totalDetected} occupied
        </span>
        <span className="flex items-center gap-1.5 text-white/40">
          <span className="w-2 h-2 rounded-full bg-accent-green/60 inline-block" />
          ~{result.estimated_capacity.cars} cars available
        </span>
        <span className="flex items-center gap-1.5 text-white/40">
          <span className="w-2 h-2 rounded-full bg-accent-blue/60 inline-block" />
          ~{result.estimated_capacity.scooters} scooters
        </span>
      </div>
    </div>
  );
}

function FreeRegionsList({ regions }: { regions: AnalysisResult["free_regions"] }) {
  if (!regions) return null;
  const top = regions.slice(0, 5);

  return (
    <div className="glass rounded-2xl border border-white/[0.06] overflow-hidden">
      <div className="px-4 py-3 border-b border-white/[0.06]">
        <span className="text-xs font-medium text-white/50 uppercase tracking-wider">
          Top Free Zones
        </span>
      </div>
      <div className="divide-y divide-white/[0.04]">
        {top.map((region, i) => (
          <div key={i} className="flex items-center justify-between px-4 py-3 hover:bg-white/[0.02] transition-colors">
            <div className="flex items-center gap-3">
              <div className={cn(
                "w-2 h-2 rounded-full",
                region.zone === "empty" ? "bg-accent-green" : "bg-accent-yellow"
              )} />
              <span className="text-sm text-white/70">Zone {i + 1}</span>
              <span className={cn(
                "text-xs px-2 py-0.5 rounded-full",
                region.zone === "empty"
                  ? "bg-accent-green/10 text-accent-green"
                  : "bg-accent-yellow/10 text-accent-yellow"
              )}>
                {region.zone}
              </span>
            </div>
            <div className="flex items-center gap-4 text-sm">
              <span className="text-white/50">{region.capacity.cars} cars</span>
              <span className="text-white/30">·</span>
              <span className="text-white/50">{region.capacity.scooters} scooters</span>
              <ChevronRight size={12} className="text-white/20" />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
