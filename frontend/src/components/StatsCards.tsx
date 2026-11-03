"use client";

import { motion } from "framer-motion";
import { Car, Bike, ParkingSquare, AlertTriangle, Activity, Clock } from "lucide-react";
import type { AnalysisResult } from "@/types/api";
import { cn } from "@/lib/utils";

interface StatsCardsProps {
  result: AnalysisResult;
}

export function StatsCards({ result }: StatsCardsProps) {
  const occupancyPct = Math.round(result.occupancy_ratio * 100);
  const availabilityPct = 100 - occupancyPct;

  const stats = [
    {
      icon: Car,
      label: "Cars Detected",
      value: result.vehicles.cars,
      sub: `${result.vehicles.trucks ?? 0} trucks`,
      color: "green",
      glow: "shadow-glow-green",
    },
    {
      icon: Bike,
      label: "Bikes / Motos",
      value: result.vehicles.bikes,
      sub: "motorcycles",
      color: "yellow",
      glow: "shadow-glow-yellow",
    },
    {
      icon: ParkingSquare,
      label: "Empty Slots (Cars)",
      value: result.estimated_capacity.cars,
      sub: `${result.estimated_capacity.scooters} scooter spots`,
      color: "blue",
      glow: "",
    },
    {
      icon: Activity,
      label: "Occupancy",
      value: `${occupancyPct}%`,
      sub: `${availabilityPct}% available`,
      color: occupancyPct > 80 ? "red" : occupancyPct > 50 ? "yellow" : "green",
      glow: occupancyPct > 80 ? "shadow-glow-red" : "shadow-glow-green",
    },
  ];

  const colorMap = {
    green: {
      icon: "text-accent-green",
      bg: "bg-accent-green/10",
      border: "border-accent-green/20",
      value: "text-accent-green",
    },
    yellow: {
      icon: "text-accent-yellow",
      bg: "bg-accent-yellow/10",
      border: "border-accent-yellow/20",
      value: "text-accent-yellow",
    },
    blue: {
      icon: "text-accent-blue",
      bg: "bg-accent-blue/10",
      border: "border-accent-blue/20",
      value: "text-accent-blue",
    },
    red: {
      icon: "text-accent-red",
      bg: "bg-accent-red/10",
      border: "border-accent-red/20",
      value: "text-accent-red",
    },
  };

  return (
    <div className="grid grid-cols-2 gap-3">
      {stats.map((stat, i) => {
        const Icon = stat.icon;
        const colors = colorMap[stat.color as keyof typeof colorMap];

        return (
          <motion.div
            key={i}
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.07, duration: 0.4 }}
            className={cn(
              "glass rounded-xl p-4 border transition-all duration-300 hover:-translate-y-0.5",
              colors.border,
              stat.glow
            )}
          >
            <div className="flex items-start justify-between mb-3">
              <div
                className={cn(
                  "w-8 h-8 rounded-lg flex items-center justify-center",
                  colors.bg
                )}
              >
                <Icon size={15} className={colors.icon} />
              </div>
            </div>
            <div className={cn("text-2xl font-display font-bold", colors.value)}>
              {stat.value}
            </div>
            <div className="text-white/60 text-xs mt-0.5 font-medium">
              {stat.label}
            </div>
            <div className="text-white/30 text-xs mt-1">{stat.sub}</div>
          </motion.div>
        );
      })}

      {/* Video-specific extra stats */}
      {result.media_type === "video" && result.duration_seconds && (
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.35 }}
          className="col-span-2 glass rounded-xl p-4 border border-white/[0.06]"
        >
          <div className="flex items-center gap-2 mb-3">
            <Clock size={13} className="text-accent-purple" />
            <span className="text-xs text-white/50 font-medium uppercase tracking-wider">
              Video Summary
            </span>
          </div>
          <div className="grid grid-cols-3 gap-4">
            {[
              { label: "Duration", value: `${result.duration_seconds}s` },
              { label: "Frames Analyzed", value: result.frames_analyzed ?? "—" },
              {
                label: "Peak Occupancy",
                value: `${Math.round((result.peak_occupancy_ratio ?? 0) * 100)}%`,
              },
            ].map((item) => (
              <div key={item.label}>
                <div className="text-white font-display font-semibold text-lg">
                  {item.value}
                </div>
                <div className="text-white/35 text-xs">{item.label}</div>
              </div>
            ))}
          </div>
        </motion.div>
      )}
    </div>
  );
}
