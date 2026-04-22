"use client";
import { MaskTile } from "./MaskTile";
import type { SAMInput, SAMResult, SliceImages } from "@/types";
import { INPUT_META } from "@/types";

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
        className="h-6 w-6 animate-spin rounded-full border-2 border-transparent"
        style={{ borderTopColor: color }}
      />
    </div>
  );
}

function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <div className="px-3 py-1.5 text-[10px] font-semibold uppercase tracking-widest text-slate-600">
      {children}
    </div>
  );
}

export function AttributeColumn({ inputName, images, samResult, samLoading, samError }: Props) {
  const meta   = INPUT_META[inputName];
  const imgSrc = images?.[inputName] ?? null;

  return (
    <div className="flex min-w-[210px] flex-1 flex-col gap-2">

      {/* Column header */}
      <div
        className="rounded-lg px-3 py-2.5 text-center"
        style={{
          background: `linear-gradient(135deg, ${meta.color}18, ${meta.color}08)`,
          border: `1px solid ${meta.color}30`,
        }}
      >
        <div className="text-sm font-bold text-white">{meta.label}</div>
        <div className="mt-0.5 text-[10px] leading-relaxed text-slate-400">{meta.description}</div>
      </div>

      {/* Input image */}
      <div className="card overflow-hidden">
        <SectionLabel>Input image</SectionLabel>
        <div style={{ borderTop: "1px solid var(--border)" }}>
          {imgSrc ? (
            <img src={`data:image/png;base64,${imgSrc}`} alt={meta.label} className="seismic-img" />
          ) : (
            <div className="flex h-24 items-center justify-center text-xs text-slate-700">
              Load a slice
            </div>
          )}
        </div>
      </div>

      {/* SAM overlay */}
      <div className="card overflow-hidden">
        <div className="flex items-center justify-between" style={{ borderBottom: "1px solid var(--border)" }}>
          <SectionLabel>SAM overlay</SectionLabel>
          {samResult && (
            <span
              className="mr-3 rounded-full px-2 py-0.5 text-[10px] font-bold text-black"
              style={{ backgroundColor: meta.color }}
            >
              {samResult.mask_count} masks
            </span>
          )}
        </div>
        <div style={{ minHeight: 80 }}>
          {samLoading ? (
            <div style={{ height: 80 }}><Spinner color={meta.color} /></div>
          ) : samError ? (
            <div className="flex items-center justify-center p-3 text-[11px] text-red-400">{samError}</div>
          ) : samResult ? (
            <img src={`data:image/png;base64,${samResult.overlay_b64}`} alt="SAM overlay" className="seismic-img" />
          ) : (
            <div className="flex h-20 items-center justify-center text-xs text-slate-700">
              Run SAM →
            </div>
          )}
        </div>
      </div>

      {/* Mask gallery — scrollable, fills remaining height */}
      <div className="card flex min-h-0 flex-1 flex-col overflow-hidden">
        <div className="flex shrink-0 items-center justify-between" style={{ borderBottom: "1px solid var(--border)" }}>
          <SectionLabel>
            All masks {samResult ? `(${samResult.mask_count})` : "(0)"}
          </SectionLabel>
          {samLoading && (
            <div
              className="mr-3 h-3 w-3 animate-spin rounded-full border border-transparent"
              style={{ borderTopColor: meta.color }}
            />
          )}
        </div>

        {/* Scrollable area */}
        <div className="min-h-0 flex-1 overflow-y-auto p-2">
          {samResult && samResult.masks.length > 0 ? (
            <div className="grid grid-cols-2 gap-2">
              {samResult.masks.map((mask, i) => (
                <MaskTile key={i} mask={mask} index={i} color={meta.color} />
              ))}
            </div>
          ) : (
            <div className="flex h-full min-h-[60px] items-center justify-center text-xs text-slate-700">
              {samLoading ? "Waiting…" : "No masks yet"}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
