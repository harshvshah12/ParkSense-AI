"use client";

import { motion } from "framer-motion";
import { ParkingSquare, Cpu, Github } from "lucide-react";

export function Header() {
  return (
    <header className="relative z-10 border-b border-white/[0.06]">
      <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
        {/* Logo */}
        <motion.div
          initial={{ opacity: 0, x: -16 }}
          animate={{ opacity: 1, x: 0 }}
          className="flex items-center gap-3"
        >
          <div className="relative w-9 h-9">
            <div className="absolute inset-0 bg-accent-green/20 rounded-xl blur-sm" />
            <div className="relative w-9 h-9 rounded-xl bg-accent-green/10 border border-accent-green/30 flex items-center justify-center">
              <ParkingSquare size={18} className="text-accent-green" />
            </div>
          </div>
          <div>
            <span className="font-display font-bold text-white text-lg tracking-tight">
              ParkSense
            </span>
            <span className="text-accent-green font-bold text-lg"> AI</span>
          </div>
        </motion.div>

        {/* Tagline (desktop) */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.2 }}
          className="hidden md:flex items-center gap-2 text-white/30 text-sm"
        >
          <Cpu size={12} className="text-accent-blue" />
          <span>YOLOv8 · OpenCV · FastAPI · Next.js</span>
        </motion.div>

        {/* Links */}
        <motion.div
          initial={{ opacity: 0, x: 16 }}
          animate={{ opacity: 1, x: 0 }}
          className="flex items-center gap-3"
        >
          <a
            href="https://github.com"
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm text-white/40 hover:text-white/70 hover:bg-white/[0.04] transition-all"
          >
            <Github size={14} />
            <span className="hidden sm:inline">GitHub</span>
          </a>
          <a
            href="http://localhost:8000/docs"
            target="_blank"
            rel="noopener noreferrer"
            className="px-3 py-1.5 rounded-lg text-sm text-white/40 hover:text-white/70 hover:bg-white/[0.04] transition-all"
          >
            API Docs
          </a>
        </motion.div>
      </div>
    </header>
  );
}
