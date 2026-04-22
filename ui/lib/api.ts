import type { Controls, Dataset, SAMInput, SAMResult, SliceResponse } from "@/types";


const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export async function fetchDatasets(): Promise<Dataset[]> {
  const res = await fetch(`${BASE}/datasets`);
  if (!res.ok) throw new Error("Failed to fetch datasets");
  return res.json();
}

export async function fetchSlice(controls: Controls): Promise<SliceResponse> {
  const res = await fetch(`${BASE}/slice`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      dataset:    controls.dataset,
      slice_type: controls.slice_type,
      slice_idx:  controls.slice_idx,
    }),
  });
  if (!res.ok) throw new Error("Failed to fetch slice");
  return res.json();
}

export async function fetchSAM(controls: Controls, samInput: SAMInput): Promise<SAMResult> {
  const res = await fetch(`${BASE}/sam`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      dataset:          controls.dataset,
      slice_type:       controls.slice_type,
      slice_idx:        controls.slice_idx,
      sam_input:        samInput,
      model_size:       controls.model_size,
      points_per_side:  controls.points_per_side,
      iou_thresh:       controls.iou_thresh,
      stability_thresh: controls.stability_thresh,
    }),
  });
  if (!res.ok) throw new Error(`SAM failed for input: ${samInput}`);
  return res.json();
}
