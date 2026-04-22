"use client";
import dynamic from "next/dynamic";
import { useEffect, useState } from "react";
import type { Controls } from "@/types";

const Plot = dynamic(() => import("react-plotly.js"), { ssr: false });

interface Props {
  controls: Controls;
}

export function VolumePanel({ controls }: Props) {
  const [figData, setFigData] = useState<{ data: unknown[]; layout: unknown } | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setLoading(true);
    fetch(
      `http://localhost:8000/plot3d?dataset=${controls.dataset}&slice_type=${controls.slice_type}&slice_idx=${controls.slice_idx}`
    )
      .then(r => r.json())
      .then(j => setFigData(j))
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [controls.dataset, controls.slice_type, controls.slice_idx]);

  return (
    <div className="flex flex-col h-full" style={{ background: "var(--navy-2)" }}>
      {/* Header */}
      <div
        className="flex shrink-0 items-center justify-between px-4 py-2 border-b"
        style={{ borderColor: "rgba(0,229,195,0.1)" }}
      >
        <div className="flex items-center gap-3">
          <span className="section-tag" style={{ fontSize: 9 }}>3D Volume</span>
          <span
            className="text-[9px] px-2 py-0.5"
            style={{
              fontFamily: "var(--mono)",
              letterSpacing: "0.08em",
              background: "rgba(0,229,195,0.08)",
              color: "var(--teal)",
              border: "1px solid rgba(0,229,195,0.2)",
            }}
          >
            {controls.slice_type.toUpperCase()} {controls.slice_idx}
          </span>
        </div>
        <span
          className="text-[9px]"
          style={{ fontFamily: "var(--mono)", color: "var(--slate-2)", letterSpacing: "0.06em" }}
        >
          drag · scroll · gold = slice
        </span>
      </div>

      {/* Plot area */}
      <div className="flex-1 min-h-0">
        {loading ? (
          <div
            className="flex h-full items-center justify-center gap-2"
            style={{ fontFamily: "var(--mono)", fontSize: 11, color: "var(--slate-2)" }}
          >
            <div
              className="h-4 w-4 animate-spin rounded-full border border-transparent"
              style={{ borderTopColor: "var(--teal)" }}
            />
            rendering volume…
          </div>
        ) : figData ? (
          <Plot
            data={figData.data as Plotly.Data[]}
            layout={{
              ...(figData.layout as object),
              autosize: true,
              paper_bgcolor: "transparent",
              plot_bgcolor:  "transparent",
            }}
            config={{ displayModeBar: false, responsive: true }}
            style={{ width: "100%", height: "100%" }}
            useResizeHandler
          />
        ) : (
          <div
            className="flex h-full items-center justify-center"
            style={{ fontFamily: "var(--mono)", fontSize: 11, color: "var(--slate-2)" }}
          >
            failed to load 3D view
          </div>
        )}
      </div>
    </div>
  );
}
