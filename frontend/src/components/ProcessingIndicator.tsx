"use client";

import { motion } from "framer-motion";
import { Loader2, Scan, Brain, Layers, CheckCircle2 } from "lucide-react";
import { cn } from "@/lib/utils";

interface ProcessingIndicatorProps {
  progress: number;
  status: "queued" | "processing" | "completed" | "failed";
  filename?: string;
}

const STAGES = [
  { icon: Scan, label: "Uploading media", threshold: 0 },
  { icon: Brain, label: "Running YOLOv8 detection", threshold: 25 },
  { icon: Layers, label: "Estimating parking capacity", threshold: 60 },
  { icon: CheckCircle2, label: "Generating heatmap", threshold: 85 },
];

export function ProcessingIndicator({
  progress,
  status,
  filename,
}: ProcessingIndicatorProps) {
  const activeStage = STAGES.reduce(
    (acc, stage, i) => (progress >= stage.threshold ? i : acc),
    0
  );

  return (
    <div className="glass rounded-2xl p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <motion.div
          animate={{ rotate: status === "processing" ? 360 : 0 }}
          transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
          className={cn(
            "w-8 h-8 rounded-full flex items-center justify-center",
            status === "completed"
              ? "bg-accent-green/20"
              : status === "failed"
              ? "bg-accent-red/20"
              : "bg-accent-blue/20"
          )}
        >
          {status === "completed" ? (
            <CheckCircle2 size={16} className="text-accent-green" />
          ) : status === "failed" ? (
            <span className="text-accent-red text-xs">✕</span>
          ) : (
            <Loader2 size={16} className="text-accent-blue" />
          )}
        </motion.div>
        <div>
          <p className="text-white font-display font-semibold text-sm">
            {status === "queued"
              ? "Queued for processing"
              : status === "processing"
              ? "Analysing parking lot..."
              : status === "completed"
              ? "Analysis complete"
              : "Processing failed"}
          </p>
          {filename && (
            <p className="text-white/40 text-xs font-mono truncate max-w-[240px]">
              {filename}
            </p>
          )}
        </div>
      </div>

      {/* Progress bar */}
      <div className="space-y-2">
        <div className="flex justify-between text-xs text-white/40">
          <span>Progress</span>
          <span className="font-mono">{progress}%</span>
        </div>
        <div className="h-1.5 rounded-full bg-white/[0.06] overflow-hidden">
          <motion.div
            className={cn(
              "h-full rounded-full",
              status === "completed"
                ? "bg-accent-green"
                : status === "failed"
                ? "bg-accent-red"
                : "bg-gradient-to-r from-accent-blue to-accent-green"
            )}
            initial={{ width: 0 }}
            animate={{ width: `${progress}%` }}
            transition={{ ease: "easeOut", duration: 0.4 }}
          />
        </div>
      </div>

      {/* Stage indicators */}
      <div className="space-y-3">
        {STAGES.map((stage, i) => {
          const Icon = stage.icon;
          const isDone = i < activeStage || status === "completed";
          const isActive = i === activeStage && status === "processing";
          const isPending = i > activeStage && status !== "completed";

          return (
            <motion.div
              key={i}
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: i * 0.08 }}
              className={cn(
                "flex items-center gap-3 text-sm transition-all duration-300",
                isDone && "text-accent-green",
                isActive && "text-white",
                isPending && "text-white/25"
              )}
            >
              <div
                className={cn(
                  "w-6 h-6 rounded-full flex items-center justify-center flex-shrink-0 transition-all duration-300",
                  isDone && "bg-accent-green/20",
                  isActive && "bg-white/10",
                  isPending && "bg-white/[0.04]"
                )}
              >
                {isDone ? (
                  <CheckCircle2 size={12} className="text-accent-green" />
                ) : isActive ? (
                  <motion.div
                    animate={{ scale: [1, 1.2, 1] }}
                    transition={{ duration: 0.8, repeat: Infinity }}
                  >
                    <Icon size={12} />
                  </motion.div>
                ) : (
                  <Icon size={12} />
                )}
              </div>
              <span>{stage.label}</span>
            </motion.div>
          );
        })}
      </div>
    </div>
  );
}
