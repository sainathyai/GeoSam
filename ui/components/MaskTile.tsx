"use client";
import type { MaskResult } from "@/types";

interface Props {
  mask: MaskResult;
  index: number;
  color: string;
  width?: string;
}

export function MaskTile({ mask, index, color, width = "clamp(110px, 11vw, 170px)" }: Props) {
  const iouColor =
    mask.predicted_iou > 0.9 ? "#4ade80"
    : mask.predicted_iou > 0.8 ? "#f5a623"
    : "#f87171";

  return (
    <div
      className="flex flex-col shrink-0 cursor-pointer transition-colors duration-150"
      style={{
        width,
        background: "var(--navy-2)",
        border: "1px solid transparent",
      }}
      onMouseEnter={e => {
        const el = e.currentTarget as HTMLDivElement;
        el.style.border = `1px solid ${color}55`;
        el.style.background = `${color}08`;
      }}
      onMouseLeave={e => {
        const el = e.currentTarget as HTMLDivElement;
        el.style.border = "1px solid transparent";
        el.style.background = "var(--navy-2)";
      }}
    >
      {/* Label tag — matches "input" / "sam overlay" height */}
      <div
        className="shrink-0 flex items-center gap-2"
        style={{
          padding: "2px 8px",
          borderBottom: "1px solid rgba(0,229,195,0.07)",
          background: color,
        }}
      >
        <span
          style={{
            fontFamily: "var(--mono)",
            fontSize: "clamp(7px,0.55vw,9px)",
            fontWeight: 600,
            color: "#07090f",
            letterSpacing: "0.06em",
          }}
        >
          M{index + 1}
        </span>
      </div>

      {/* Mask image */}
      <div className="flex-1 min-h-0 overflow-hidden flex items-center justify-center p-1">
        <img
          src={`data:image/png;base64,${mask.mask_b64}`}
          alt={`Mask ${index + 1}`}
          style={{ width: "100%", height: "100%", objectFit: "cover", imageRendering: "pixelated", display: "block" }}
        />
      </div>

      {/* Stats strip below image */}
      <div
        className="grid grid-cols-3 shrink-0"
        style={{ background: "var(--gap-bg)", gap: 1 }}
      >
        {[
          { label: "area", val: mask.area > 999 ? `${(mask.area / 1000).toFixed(1)}k` : String(mask.area), color: "var(--white-dim)" },
          { label: "IoU",  val: mask.predicted_iou.toFixed(2),    color: iouColor },
          { label: "stab", val: mask.stability_score.toFixed(2),  color: "var(--white-dim)" },
        ].map(stat => (
          <div
            key={stat.label}
            className="flex flex-col items-center justify-center"
            style={{ background: "var(--navy-3)", padding: "2px 0" }}
          >
            <span style={{ fontFamily: "var(--mono)", fontSize: "clamp(6px,0.5vw,8px)", color: "var(--slate-2)", letterSpacing: "0.08em", textTransform: "uppercase" }}>
              {stat.label}
            </span>
            <span style={{ fontFamily: "var(--mono)", fontSize: "clamp(7px,0.55vw,9px)", fontWeight: 500, color: stat.color }}>
              {stat.val}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
