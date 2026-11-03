/** API response types for the parking detection system */

export interface VehicleCounts {
  cars: number;
  bikes: number;
  trucks?: number;
  total: number;
}

export interface CapacityEstimate {
  cars: number;
  scooters: number;
}

export interface FreeRegion {
  bbox: [number, number, number, number];
  area_px: number;
  zone: "empty" | "partial";
  capacity: {
    cars: number;
    scooters: number;
  };
}

export interface TimelineEntry {
  frame: number;
  occupancy_ratio: number;
  vehicles: number;
}

export interface AnalysisResult {
  media_type: "image" | "video";
  frame_shape?: { width: number; height: number };
  vehicles: VehicleCounts;
  empty_spaces: number;
  partial_spaces?: number;
  occupancy_ratio: number;
  peak_occupancy_ratio?: number;
  min_occupancy_ratio?: number;
  estimated_capacity: CapacityEstimate;
  free_regions?: FreeRegion[];
  annotated_media_url: string;
  heatmap_url: string;
  annotated_b64?: string;
  heatmap_b64?: string;
  timeline?: TimelineEntry[];
  duration_seconds?: number;
  frames_analyzed?: number;
}

export interface JobStatus {
  job_id: string;
  status: "queued" | "processing" | "completed" | "failed";
  progress: number;
  media_type?: "image" | "video";
  filename?: string;
  result?: AnalysisResult;
  error?: string;
}

export interface UploadResponse {
  job_id: string;
  status: string;
  media_type: "image" | "video";
}
