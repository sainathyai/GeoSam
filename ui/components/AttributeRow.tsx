"use client";
import type { SAMInput, SAMResult, SliceImages } from "@/types";
import { INPUT_META } from "@/types";
import { MaskTile } from "./MaskTile";

interface Props {
  inputName: SAMInput;
  images: SliceImages | null;
  samResult: SAMResult | null;
  samLoading: boolean;
  samError: string | null;
}

function Spinner({ color }: { color: string }) {
  return (
    <div className="flex h-full items-center justify-center">
      <div
        className="h-4 w-4 animate-spin rounded-full border-2 border-transparent"
        style={{ borderTopColor: color }}
      />
    </div>
  );
}

export function AttributeRow({ inputName, images, samResult, samLoading, samError }: Props) {
  const meta   = INPUT_META[inputName];
  const imgSrc = images?.[inputName] ?? null;

  const rowH = "clamp(130px, 16vh, 210px)";
  const imgW = "clamp(110px, 11vw, 170px)";
  const hdrH = "clamp(22px, 2.2vh, 28px)";

  return (
    <div
      className="flex flex-col border-b shrink-0"
      style={{ borderColor: "rgba(0,229,195,0.07)", height: rowH }}
    >
      {/* ── Header bar ───────────────────────────────────────────── */}
      <div
        className="flex shrink-0 items-center gap-3 px-3"
        style={{
          height: hdrH,
          borderLeft: `3px solid ${meta.color}`,
          borderBottom: "1px solid rgba(0,229,195,0.07)",
          background: "var(--navy-3)",
        }}
      >
        <span
          style={{
            fontFamily: "var(--mono)",
            fontSize: "clamp(8px,0.6vw,10px)",
            color: meta.color,
            letterSpacing: "0.12em",
            textTransform: "uppercase",
            flexShrink: 0,
          }}
        >
          <span style={{ color: "var(--slate-2)" }}>// </span>
          {meta.label}
        </span>

        <span
          style={{
            fontFamily: "var(--sans)",
            fontSize: "clamp(8px,0.55vw,10px)",
            color: "var(--slate-2)",
            fontWeight: 300,
            whiteSpace: "nowrap",
            overflow: "hidden",
            textOverflow: "ellipsis",
          }}
        >
          {meta.description}
        </span>

        <div style={{ flex: 1 }} />

        {samResult ? (
          <span style={{ fontFamily: "var(--mono)", fontSize: "clamp(8px,0.6vw,10px)", color: meta.color, letterSpacing: "0.06em", flexShrink: 0 }}>
            {samResult.mask_count} masks
          </span>
        ) : samLoading ? (
          <span style={{ fontFamily: "var(--mono)", fontSize: "clamp(8px,0.6vw,10px)", color: "var(--slate-2)", flexShrink: 0 }}>running…</span>
        ) : (
          <span style={{ fontFamily: "var(--mono)", fontSize: "clamp(8px,0.6vw,10px)", color: "var(--slate)", flexShrink: 0 }}>awaiting</span>
        )}
      </div>

      {/* ── Image strip — horizontal infinite scroll ──────────────── */}
      <div className="flex-1 overflow-x-auto min-h-0">
        <div
          className="flex h-full"
          style={{ width: "max-content", gap: 1, background: "var(--gap-bg)" }}
        >
          {/* Input image */}
          <div className="flex flex-col shrink-0" style={{ width: imgW, background: "var(--navy-2)" }}>
            <div
              className="label-tag shrink-0"
              style={{ padding: "2px 8px", borderBottom: "1px solid rgba(0,229,195,0.07)" }}
            >
              input
            </div>
            <div className="flex-1 flex items-center justify-center overflow-hidden p-1 min-h-0">
              {imgSrc ? (
                <img src={`data:image/png;base64,${imgSrc}`} alt={meta.label} className="seismic-img" />
              ) : (
                <span style={{ fontFamily: "var(--mono)", fontSize: 9, color: "var(--slate)" }}>load slice</span>
              )}
            </div>
          </div>

          {/* SAM overlay */}
          <div className="flex flex-col shrink-0" style={{ width: imgW, background: "var(--navy-2)" }}>
            <div
              className="label-tag teal shrink-0"
              style={{ padding: "2px 8px", borderBottom: "1px solid rgba(0,229,195,0.07)" }}
            >
              sam overlay
            </div>
            <div className="flex-1 flex items-center justify-center overflow-hidden p-1 min-h-0">
              {samLoading ? (
                <Spinner color={meta.color} />
              ) : samError ? (
                <span style={{ fontFamily: "var(--mono)", fontSize: 9, color: "var(--red)", textAlign: "center", padding: "0 6px" }}>
                  {samError}
                </span>
              ) : samResult ? (
                <img src={`data:image/png;base64,${samResult.overlay_b64}`} alt="SAM overlay" className="seismic-img" />
              ) : (
                <span style={{ fontFamily: "var(--mono)", fontSize: 9, color: "var(--slate)" }}>run SAM →</span>
              )}
            </div>
          </div>

          {/* Individual mask tiles — same width as input/overlay */}
          {samResult && samResult.masks.map((mask, i) => (
            <MaskTile key={i} mask={mask} index={i} color={meta.color} width={imgW} />
          ))}
        </div>
      </div>
    </div>
  );
}
