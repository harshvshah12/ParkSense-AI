"use client";

import { useCallback, useState } from "react";
import { useDropzone } from "react-dropzone";
import { motion, AnimatePresence } from "framer-motion";
import { Upload, Film, ImageIcon, AlertCircle } from "lucide-react";
import { cn } from "@/lib/utils";

interface UploadZoneProps {
  onFileSelected: (file: File) => void;
  disabled?: boolean;
}

const ACCEPTED = {
  "image/*": [".jpg", ".jpeg", ".png", ".webp", ".bmp"],
  "video/*": [".mp4", ".avi", ".mov"],
};

export function UploadZone({ onFileSelected, disabled }: UploadZoneProps) {
  const [error, setError] = useState<string | null>(null);
  const [preview, setPreview] = useState<{
    url: string;
    type: "image" | "video";
    name: string;
  } | null>(null);

  const onDrop = useCallback(
    (accepted: File[], rejected: any[]) => {
      setError(null);
      if (rejected.length > 0) {
        setError("Invalid file type. Please upload JPG, PNG, WEBP, MP4, or AVI.");
        return;
      }
      const file = accepted[0];
      if (!file) return;
      if (file.size > 100 * 1024 * 1024) {
        setError("File too large (max 100 MB).");
        return;
      }
      const isVideo = file.type.startsWith("video/");
      const url = URL.createObjectURL(file);
      setPreview({ url, type: isVideo ? "video" : "image", name: file.name });
      onFileSelected(file);
    },
    [onFileSelected]
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: ACCEPTED,
    maxFiles: 1,
    disabled,
  });

  return (
    <div className="space-y-4">
      <div
        {...getRootProps()}
        className={cn(
          "relative rounded-2xl border-2 border-dashed transition-all duration-300 cursor-pointer overflow-hidden",
          "border-white/10 bg-white/[0.02] hover:border-accent-green/40 hover:bg-white/[0.04]",
          isDragActive && "dropzone-active border-accent-green/60 bg-accent-green/5",
          disabled && "opacity-50 cursor-not-allowed",
          preview ? "p-4" : "p-12"
        )}
      >
        <input {...getInputProps()} />

        <AnimatePresence mode="wait">
          {preview ? (
            <motion.div
              key="preview"
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              className="relative"
            >
              {preview.type === "image" ? (
                <img
                  src={preview.url}
                  alt="Preview"
                  className="w-full max-h-64 object-contain rounded-xl"
                />
              ) : (
                <video
                  src={preview.url}
                  className="w-full max-h-64 object-contain rounded-xl"
                  controls={false}
                  muted
                />
              )}
              <div className="mt-3 flex items-center gap-2 text-sm text-white/50">
                {preview.type === "video" ? (
                  <Film size={14} className="text-accent-blue" />
                ) : (
                  <ImageIcon size={14} className="text-accent-green" />
                )}
                <span className="truncate font-mono text-xs">{preview.name}</span>
              </div>
              <p className="text-center text-xs text-white/30 mt-2">
                Click or drop a new file to replace
              </p>
            </motion.div>
          ) : (
            <motion.div
              key="placeholder"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="flex flex-col items-center gap-5 text-center"
            >
              {/* Animated icon */}
              <motion.div
                animate={isDragActive ? { scale: 1.1 } : { scale: 1 }}
                transition={{ type: "spring", stiffness: 300 }}
                className="relative"
              >
                <div className="w-20 h-20 rounded-2xl bg-accent-green/10 border border-accent-green/20 flex items-center justify-center">
                  <Upload
                    size={32}
                    className={cn(
                      "transition-colors duration-200",
                      isDragActive ? "text-accent-green" : "text-white/30"
                    )}
                  />
                </div>
                {isDragActive && (
                  <motion.div
                    className="absolute inset-0 rounded-2xl border-2 border-accent-green"
                    animate={{ scale: [1, 1.2, 1] }}
                    transition={{ duration: 0.6, repeat: Infinity }}
                    style={{ opacity: 0.4 }}
                  />
                )}
              </motion.div>

              <div>
                <p className="text-white/80 font-display font-semibold text-lg">
                  {isDragActive ? "Drop it here" : "Drop your parking lot media"}
                </p>
                <p className="text-white/40 text-sm mt-1">
                  or{" "}
                  <span className="text-accent-green hover:underline">
                    browse files
                  </span>
                </p>
              </div>

              <div className="flex gap-3">
                {[
                  { icon: ImageIcon, label: "Images", types: "JPG · PNG · WEBP" },
                  { icon: Film, label: "Videos", types: "MP4 · AVI · MOV" },
                ].map(({ icon: Icon, label, types }) => (
                  <div
                    key={label}
                    className="flex items-center gap-2 px-3 py-2 rounded-lg bg-white/[0.03] border border-white/[0.06] text-xs"
                  >
                    <Icon size={12} className="text-white/40" />
                    <div>
                      <div className="text-white/60 font-medium">{label}</div>
                      <div className="text-white/30 font-mono">{types}</div>
                    </div>
                  </div>
                ))}
              </div>

              <p className="text-white/25 text-xs">Max 100 MB</p>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Error */}
      <AnimatePresence>
        {error && (
          <motion.div
            initial={{ opacity: 0, y: -8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            className="flex items-center gap-2 px-4 py-3 rounded-lg bg-accent-red/10 border border-accent-red/20 text-accent-red text-sm"
          >
            <AlertCircle size={14} />
            {error}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
