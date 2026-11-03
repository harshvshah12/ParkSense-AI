"use client";

import { useState, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Zap, RotateCcw, Info } from "lucide-react";

import { Header } from "@/components/Header";
import { UploadZone } from "@/components/UploadZone";
import { ProcessingIndicator } from "@/components/ProcessingIndicator";
import { ResultsPanel } from "@/components/ResultsPanel";
import { uploadFile, pollJob } from "@/lib/api";
import type { AnalysisResult, JobStatus } from "@/types/api";
import { cn } from "@/lib/utils";

type AppState = "idle" | "uploading" | "processing" | "done" | "error";

export default function HomePage() {
  const [file, setFile] = useState<File | null>(null);
  const [appState, setAppState] = useState<AppState>("idle");
  const [job, setJob] = useState<JobStatus | null>(null);
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // ── Handlers ────────────────────────────────────────────────────────────────
  const handleFileSelected = useCallback((f: File) => {
    setFile(f);
    setResult(null);
    setJob(null);
    setErrorMsg(null);
    setAppState("idle");
  }, []);

  const handleAnalyse = useCallback(async () => {
    if (!file) return;
    setErrorMsg(null);
    setAppState("uploading");
    setJob({ job_id: "", status: "queued", progress: 5 });

    try {
      // 1. Upload
      const { job_id } = await uploadFile(file);

      setAppState("processing");

      // 2. Poll
      const finalJob = await pollJob(job_id, (j) => setJob(j));

      if (finalJob.result) {
        setResult(finalJob.result);
        setAppState("done");
      } else {
        throw new Error("No result returned");
      }
    } catch (err: any) {
      setErrorMsg(err?.message || "Processing failed");
      setAppState("error");
    }
  }, [file]);

  const handleReset = useCallback(() => {
    setFile(null);
    setJob(null);
    setResult(null);
    setErrorMsg(null);
    setAppState("idle");
  }, []);

  const isProcessing = appState === "uploading" || appState === "processing";
  const canAnalyse = !!file && !isProcessing;

  // ── Render ───────────────────────────────────────────────────────────────────
  return (
    <div className="min-h-screen flex flex-col bg-surface-0">
      {/* Grid background */}
      <div
        className="fixed inset-0 pointer-events-none"
        style={{
          backgroundImage:
            "linear-gradient(rgba(255,255,255,0.025) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.025) 1px, transparent 1px)",
          backgroundSize: "48px 48px",
        }}
      />
      {/* Glow accent top-left */}
      <div className="fixed top-0 left-1/4 w-96 h-96 bg-accent-green/5 rounded-full blur-3xl pointer-events-none" />
      <div className="fixed bottom-0 right-1/4 w-64 h-64 bg-accent-blue/5 rounded-full blur-3xl pointer-events-none" />

      <Header />

      <main className="flex-1 max-w-7xl mx-auto w-full px-4 sm:px-6 py-10">
        <div className="grid grid-cols-1 lg:grid-cols-[420px_1fr] gap-8 items-start">
          {/* ── Left Panel ──────────────────────────────────────────────────── */}
          <div className="space-y-5">
            {/* Hero text */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="space-y-3"
            >
              <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-accent-green/10 border border-accent-green/20 text-accent-green text-xs font-medium">
                <Zap size={11} />
                AI-Powered Parking Intelligence
              </div>
              <h1 className="font-display font-extrabold text-3xl sm:text-4xl text-white leading-tight">
                Detect. Analyse.{" "}
                <span className="gradient-text">Optimise.</span>
              </h1>
              <p className="text-white/40 text-sm leading-relaxed">
                Upload a parking lot image or video. YOLOv8 detects all vehicles,
                identifies empty zones, and estimates how many cars and scooters
                can fit — with a colour-coded heatmap overlay.
              </p>
            </motion.div>

            {/* Upload zone */}
            <motion.div
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1 }}
            >
              <UploadZone
                onFileSelected={handleFileSelected}
                disabled={isProcessing}
              />
            </motion.div>

            {/* Action buttons */}
            <motion.div
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.15 }}
              className="flex gap-3"
            >
              <button
                onClick={handleAnalyse}
                disabled={!canAnalyse}
                className={cn(
                  "flex-1 flex items-center justify-center gap-2 py-3 px-5 rounded-xl font-display font-semibold text-sm transition-all duration-300",
                  canAnalyse
                    ? "bg-accent-green text-black hover:bg-accent-green/90 shadow-glow-green hover:-translate-y-0.5 active:translate-y-0"
                    : "bg-white/[0.04] text-white/25 cursor-not-allowed"
                )}
              >
                <Zap size={15} />
                {isProcessing ? "Analysing…" : "Analyse Parking Lot"}
              </button>

              {(result || errorMsg) && (
                <button
                  onClick={handleReset}
                  className="p-3 rounded-xl border border-white/10 text-white/40 hover:text-white/60 hover:bg-white/[0.04] transition-all"
                  title="Start over"
                >
                  <RotateCcw size={15} />
                </button>
              )}
            </motion.div>

            {/* Processing indicator */}
            <AnimatePresence>
              {(isProcessing || appState === "done") && job && (
                <motion.div
                  initial={{ opacity: 0, y: 12 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -12 }}
                >
                  <ProcessingIndicator
                    progress={job.progress}
                    status={job.status}
                    filename={job.filename ?? file?.name}
                  />
                </motion.div>
              )}
            </AnimatePresence>

            {/* Error */}
            <AnimatePresence>
              {errorMsg && (
                <motion.div
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0 }}
                  className="glass rounded-xl p-4 border border-accent-red/30 bg-accent-red/5 text-accent-red text-sm"
                >
                  {errorMsg}
                </motion.div>
              )}
            </AnimatePresence>

            {/* Info card */}
            {!file && (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.3 }}
                className="glass rounded-xl p-4 border border-white/[0.06] space-y-3"
              >
                <div className="flex items-center gap-2">
                  <Info size={13} className="text-accent-blue" />
                  <span className="text-xs text-white/40 font-medium uppercase tracking-wider">
                    How it works
                  </span>
                </div>
                <div className="space-y-2">
                  {[
                    ["1", "Upload an aerial or angled parking lot photo/video"],
                    ["2", "YOLOv8 detects all cars, bikes, and trucks"],
                    ["3", "Geometric reasoning finds empty zones"],
                    ["4", "Heatmap + capacity estimates are generated"],
                  ].map(([num, text]) => (
                    <div key={num} className="flex gap-2.5 text-xs text-white/35">
                      <span className="font-mono text-accent-green/60 font-bold w-3 flex-shrink-0">
                        {num}
                      </span>
                      <span>{text}</span>
                    </div>
                  ))}
                </div>
              </motion.div>
            )}
          </div>

          {/* ── Right Panel (Results) ────────────────────────────────────────── */}
          <div className="min-h-[400px]">
            <AnimatePresence mode="wait">
              {result ? (
                <motion.div
                  key="results"
                  initial={{ opacity: 0, x: 20 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: 20 }}
                  transition={{ duration: 0.4 }}
                >
                  <ResultsPanel result={result} />
                </motion.div>
              ) : (
                <motion.div
                  key="empty"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  className="flex flex-col items-center justify-center h-full min-h-[400px] gap-4 text-center"
                >
                  <EmptyState />
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </div>
      </main>
    </div>
  );
}

// ── Empty state ──────────────────────────────────────────────────────────────
function EmptyState() {
  return (
    <div className="space-y-6 py-16">
      {/* Animated parking lot SVG illustration */}
      <motion.div
        animate={{ y: [0, -8, 0] }}
        transition={{ duration: 3, repeat: Infinity, ease: "easeInOut" }}
      >
        <svg width="200" height="140" viewBox="0 0 200 140" fill="none" className="opacity-20 mx-auto">
          {/* Parking lot outline */}
          <rect x="10" y="10" width="180" height="120" rx="8" stroke="white" strokeWidth="1.5" strokeDasharray="4 4" />
          {/* Parking spaces */}
          {[30, 60, 90, 120, 150].map((x, i) => (
            <g key={i}>
              <line x1={x} y1="20" x2={x} y2="120" stroke="white" strokeWidth="0.5" opacity="0.5" />
              {/* Cars in some spaces */}
              {i % 2 === 0 && (
                <rect x={x + 4} y="50" width="22" height="40" rx="4" fill="white" opacity="0.15" />
              )}
            </g>
          ))}
          {/* Empty space highlight */}
          <rect x="60" y="20" width="30" height="100" rx="2" fill="#00e87a" opacity="0.1" />
          <rect x="120" y="20" width="30" height="100" rx="2" fill="#00e87a" opacity="0.1" />
        </svg>
      </motion.div>
      <div className="space-y-2">
        <p className="text-white/25 font-display font-semibold text-lg">
          Results appear here
        </p>
        <p className="text-white/15 text-sm max-w-xs mx-auto">
          Upload a parking lot image or video and click Analyse to see detection results
        </p>
      </div>
    </div>
  );
}
