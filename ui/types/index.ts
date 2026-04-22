export type SliceType = "inline" | "crossline" | "timeslice";
export type SAMInput  = "raw" | "envelope" | "dip" | "coherence" | "texture";
export type ModelSize = "tiny" | "small" | "base_plus" | "large";

export interface Dataset {
  id: string;
  label: string;
  shape: { inlines: number; crosslines: number; time_samples: number } | null;
}

export interface SliceImages {
  raw: string;        // base64 PNG
  envelope: string;
  dip: string;
  coherence: string;
  texture: string;
}

export interface SliceResponse {
  slice_type: SliceType;
  slice_idx: number;
  shape: { height: number; width: number };
  images: SliceImages;
}

export interface MaskResult {
  mask_b64: string;        // base64 grayscale PNG — white=inside
  area: number;            // pixel count
  predicted_iou: number;   // SAM confidence [0,1]
  stability_score: number; // boundary stability [0,1]
}

export interface SAMResult {
  sam_input: SAMInput;
  mask_count: number;
  overlay_b64: string;     // base64 RGB PNG — input image + all masks painted
  masks: MaskResult[];
}

export interface Controls {
  dataset:          string;
  slice_type:       SliceType;
  slice_idx:        number;
  model_size:       ModelSize;
  points_per_side:  number;
  iou_thresh:       number;
  stability_thresh: number;
}

export const SAM_INPUTS: SAMInput[] = ["raw", "envelope", "dip", "coherence", "texture"];

export const INPUT_META: Record<SAMInput, { label: string; description: string; color: string }> = {
  raw:       { label: "Raw amplitude",  description: "Red=+amp Blue=−amp. SAM finds reflector bands.", color: "#00e5c3" },
  envelope:  { label: "Envelope",       description: "Amplitude strength. SAM finds bright spots, gas sands.", color: "#f5a623" },
  dip:       { label: "Dip",            description: "Sobel gradient magnitude. SAM finds fault edges, layer boundaries.", color: "#f87171" },
  coherence: { label: "Coherence",      description: "Lateral continuity. SAM finds disruption zones — faults, channels.", color: "#4ade80" },
  texture:   { label: "Texture",        description: "Local std dev. SAM finds lithology changes — turbidites, fractured zones.", color: "#9aadc8" },
};
