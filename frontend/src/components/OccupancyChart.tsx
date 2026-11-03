"use client";

import { motion } from "framer-motion";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import type { TimelineEntry } from "@/types/api";

interface OccupancyChartProps {
  timeline: TimelineEntry[];
}

export function OccupancyChart({ timeline }: OccupancyChartProps) {
  const data = timeline.map((t) => ({
    frame: t.frame,
    occupancy: Math.round(t.occupancy_ratio * 100),
    vehicles: t.vehicles,
  }));

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.3 }}
      className="glass rounded-2xl border border-white/[0.06] p-4"
    >
      <div className="mb-4">
        <p className="text-xs font-medium text-white/50 uppercase tracking-wider">
          Occupancy Over Time
        </p>
        <p className="text-white/30 text-xs mt-0.5">
          Analysed across {timeline.length} frames
        </p>
      </div>

      <ResponsiveContainer width="100%" height={160}>
        <AreaChart data={data} margin={{ top: 4, right: 4, bottom: 0, left: -20 }}>
          <defs>
            <linearGradient id="occGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#00e87a" stopOpacity={0.3} />
              <stop offset="95%" stopColor="#00e87a" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
          <XAxis
            dataKey="frame"
            tick={{ fill: "rgba(255,255,255,0.25)", fontSize: 10 }}
            axisLine={false}
            tickLine={false}
            label={{ value: "Frame", position: "insideBottom", fill: "rgba(255,255,255,0.2)", fontSize: 10 }}
          />
          <YAxis
            domain={[0, 100]}
            tick={{ fill: "rgba(255,255,255,0.25)", fontSize: 10 }}
            axisLine={false}
            tickLine={false}
            tickFormatter={(v) => `${v}%`}
          />
          <Tooltip
            contentStyle={{
              background: "#0d1117",
              border: "1px solid rgba(255,255,255,0.08)",
              borderRadius: "8px",
              fontSize: "12px",
              color: "#e2e8f0",
            }}
            formatter={(value: number, name: string) => [
              name === "occupancy" ? `${value}%` : value,
              name === "occupancy" ? "Occupancy" : "Vehicles",
            ]}
          />
          <Area
            type="monotone"
            dataKey="occupancy"
            stroke="#00e87a"
            strokeWidth={2}
            fill="url(#occGrad)"
            dot={false}
            activeDot={{ r: 4, fill: "#00e87a" }}
          />
        </AreaChart>
      </ResponsiveContainer>
    </motion.div>
  );
}
