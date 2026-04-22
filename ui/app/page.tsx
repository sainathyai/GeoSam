"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { AttributeRow } from "@/components/AttributeRow";
import { VolumePanel } from "@/components/VolumePanel";
import { fetchDatasets, fetchSAM, fetchSlice } from "@/lib/api";
import type { Controls, Dataset, ModelSize, SAMInput, SAMResult, SliceResponse } from "@/types";
import { INPUT_META, SAM_INPUTS } from "@/types";

const DEFAULT_CONTROLS: Controls = {
  dataset:          "synthetic_large",
  slice_type:       "inline",
  slice_idx:        50,
  model_size:       "tiny",
  points_per_side:  16,
  iou_thresh:       0.70,
  stability_thresh: 0.80,
};

const MODEL_TIERS: { size: ModelSize; label: string; title: string }[] = [
  { size: "tiny",      label: "T",  title: "Tiny — fastest, 38M params" },
  { size: "small",     label: "S",  title: "Small — 46M params" },
  { size: "base_plus", label: "B+", title: "Base+ — 80M params" },
  { size: "large",     label: "L",  title: "Large — best quality, 224M params" },
];

/* ── tiny shared atoms ─────────────────────────────────────────── */
function CtrlDivider() {
  return <div style={{ height: 1, background: "rgba(0,229,195,0.08)", margin: "0 -16px" }} />;
}

function ParamSlider({
  label, value, min, max, step, format, onChange,
}: {
  label: string; value: number; min: number; max: number; step: number;
  format?: (v: number) => string; onChange: (v: number) => void;
}) {
  return (
    <div className="flex flex-col gap-1.5 flex-1">
      <div className="flex items-center justify-between">
        <span style={{ fontFamily: "var(--mono)", fontSize: "clamp(8px,0.7vw,10px)", color: "var(--slate-2)", letterSpacing: "0.1em", textTransform: "uppercase" }}>
          {label}
        </span>
        <span style={{ fontFamily: "var(--mono)", fontSize: "clamp(9px,0.75vw,11px)", color: "var(--teal)" }}>
          {format ? format(value) : value}
        </span>
      </div>
      <input type="range" min={min} max={max} step={step} className="amber"
        value={value} onChange={e => onChange(Number(e.target.value))} />
    </div>
  );
}

/* ── main page ─────────────────────────────────────────────────── */
export default function Dashboard() {
  const [datasets, setDatasets]         = useState<Dataset[]>([]);
  const [controls, setControls]         = useState<Controls>(DEFAULT_CONTROLS);
  const [sliceData, setSliceData]       = useState<SliceResponse | null>(null);
  const [sliceLoading, setSliceLoading] = useState(false);
  const [show3D, setShow3D]             = useState(true);
  const [samTarget, setSamTarget]       = useState<SAMInput | "all">("all");

  const [samResults, setSamResults] = useState<Partial<Record<SAMInput, SAMResult>>>({});
  const [samLoading, setSamLoading] = useState<Partial<Record<SAMInput, boolean>>>({});
  const [samErrors,  setSamErrors]  = useState<Partial<Record<SAMInput, string>>>({});

  const sliceAbort = useRef<AbortController | null>(null);

  useEffect(() => { fetchDatasets().then(setDatasets).catch(console.error); }, []);

  const loadSlice = useCallback(async (ctrl: Controls) => {
    sliceAbort.current?.abort();
    sliceAbort.current = new AbortController();
    setSliceLoading(true);
    try {
      const data = await fetchSlice(ctrl);
      setSliceData(data);
      setSamResults({});
      setSamErrors({});
    } catch (e) {
      if ((e as Error).name !== "AbortError") console.error(e);
    } finally {
      setSliceLoading(false);
    }
  }, []);

  useEffect(() => { loadSlice(controls); }, [controls, loadSlice]);

  const runSAM = async () => {
    const targets = samTarget === "all" ? SAM_INPUTS : [samTarget as SAMInput];
    setSamLoading(prev => ({ ...prev, ...Object.fromEntries(targets.map(k => [k, true])) }));
    setSamErrors(prev => { const n = { ...prev }; targets.forEach(k => delete n[k]); return n; });
    if (samTarget === "all") setSamResults({});
    await Promise.allSettled(targets.map(async (input) => {
      try {
        const result = await fetchSAM(controls, input);
        setSamResults(prev => ({ ...prev, [input]: result }));
      } catch (e) {
        setSamErrors(prev => ({ ...prev, [input]: (e as Error).message }));
      } finally {
        setSamLoading(prev => ({ ...prev, [input]: false }));
      }
    }));
  };

  const set = (patch: Partial<Controls>) => setControls(prev => ({ ...prev, ...patch }));

  const selectedDataset = datasets.find(d => d.id === controls.dataset);
  const maxIdx = selectedDataset
    ? controls.slice_type === "inline"     ? selectedDataset.shape.inlines - 1
    : controls.slice_type === "crossline" ? selectedDataset.shape.crosslines - 1
    : selectedDataset.shape.time_samples - 1
    : 99;

  const anySamRunning = Object.values(samLoading).some(Boolean);
  const totalMasks    = Object.values(samResults).reduce((s, r) => s + (r?.mask_count ?? 0), 0);

  /* viewport-clamp top block height */
  const topH = "clamp(220px, 34vh, 380px)";

  return (
    <div className="flex flex-col h-full overflow-hidden" style={{ background: "var(--navy)" }}>

      {/* ── Header ──────────────────────────────────────────────── */}
      <header
        className="flex shrink-0 items-center justify-between px-5"
        style={{
          height: "clamp(40px,4vh,52px)",
          background: "rgba(7,9,15,0.94)",
          backdropFilter: "blur(18px)",
          borderBottom: "1px solid rgba(0,229,195,0.1)",
          zIndex: 10,
        }}
      >
        {/* Logo */}
        <span style={{ fontFamily: "var(--mono)", fontSize: "clamp(11px,1vw,14px)", fontWeight: 600, letterSpacing: "0.16em", textTransform: "uppercase" }}>
          <span style={{ color: "var(--teal)" }}>GeoSAM</span>
          <span style={{ color: "var(--slate-2)", margin: "0 6px" }}>·</span>
          <span style={{ color: "var(--white-dim)", fontWeight: 300 }}>Seismic</span>
        </span>

        {/* Live status strip */}
        <div className="flex items-center gap-5">
          {SAM_INPUTS.map(inp => (
            <div key={inp} className="flex items-center gap-1.5">
              <div style={{ width: 5, height: 5, background: INPUT_META[inp].color, flexShrink: 0 }} />
              <span style={{ fontFamily: "var(--mono)", fontSize: "clamp(8px,0.65vw,10px)", color: "var(--slate-2)", letterSpacing: "0.07em", textTransform: "uppercase" }}>
                {INPUT_META[inp].label.split(" ")[0]}
              </span>
              {samResults[inp] && (
                <span style={{ fontFamily: "var(--mono)", fontSize: 9, fontWeight: 600, padding: "1px 5px", background: INPUT_META[inp].color, color: "#07090f" }}>
                  {samResults[inp]!.mask_count}
                </span>
              )}
            </div>
          ))}

          {totalMasks > 0 && (
            <div style={{ display: "flex", alignItems: "center", gap: 6, padding: "2px 10px", border: "1px solid rgba(0,229,195,0.2)", background: "rgba(0,229,195,0.06)" }}>
              <span style={{ fontFamily: "var(--mono)", fontSize: "clamp(13px,1.1vw,16px)", fontWeight: 500, color: "var(--teal)", lineHeight: 1 }}>{totalMasks}</span>
              <span style={{ fontFamily: "var(--mono)", fontSize: 9, color: "var(--slate-2)", letterSpacing: "0.08em", textTransform: "uppercase" }}>masks</span>
            </div>
          )}

          <span style={{ fontFamily: "var(--mono)", fontSize: "clamp(8px,0.65vw,10px)", color: "var(--slate-2)", letterSpacing: "0.06em" }}>
            {sliceLoading ? "loading…" : sliceData ? `${sliceData.slice_type.toUpperCase()} ${sliceData.slice_idx} · ${sliceData.shape.height}×${sliceData.shape.width}` : "—"}
          </span>
        </div>
      </header>

      {/* ── Top block: Controls | 3D (two squares) ──────────────── */}
      <div
        className="shrink-0 grid grid-cols-2"
        style={{ height: topH, background: "var(--gap-bg)", gap: 2 }}
      >

        {/* ╔═ Controls panel ══════════════════════════════════════╗ */}
        <div
          className="flex flex-col"
          style={{ background: "var(--navy-2)", padding: "clamp(10px,1.4vh,18px) clamp(12px,1.2vw,20px)", gap: "clamp(8px,1.2vh,14px)" }}
        >

          {/* §1 Dataset + Slice type — horizontal pair */}
          <div className="flex gap-3 items-end">
            {/* Dataset */}
            <div className="flex flex-col gap-1.5" style={{ flex: "1 1 0" }}>
              <span className="label-tag">Dataset</span>
              <select
                value={controls.dataset}
                onChange={e => set({ dataset: e.target.value, slice_idx: 0 })}
                style={{
                  background: "var(--navy-3)",
                  border: "1px solid rgba(0,229,195,0.15)",
                  color: "var(--white)",
                  fontFamily: "var(--mono)",
                  fontSize: "clamp(9px,0.75vw,11px)",
                  letterSpacing: "0.04em",
                  padding: "5px 8px",
                  width: "100%",
                  outline: "none",
                }}
              >
                {datasets.map(d => <option key={d.id} value={d.id}>{d.label}</option>)}
              </select>
            </div>

            {/* Slice type */}
            <div className="flex flex-col gap-1.5" style={{ flex: "1 1 0" }}>
              <span className="label-tag">Slice type</span>
              <div style={{ display: "flex", border: "1px solid rgba(0,229,195,0.12)", background: "var(--gap-bg)", gap: 1 }}>
                {(["inline", "crossline", "timeslice"] as const).map(t => (
                  <button
                    key={t}
                    onClick={() => set({ slice_type: t, slice_idx: 0 })}
                    style={{
                      flex: 1,
                      padding: "5px 0",
                      fontFamily: "var(--mono)",
                      fontSize: "clamp(8px,0.65vw,10px)",
                      letterSpacing: "0.1em",
                      textTransform: "uppercase",
                      border: "none",
                      cursor: "pointer",
                      background: controls.slice_type === t ? "var(--teal)" : "var(--navy-3)",
                      color:      controls.slice_type === t ? "var(--navy)" : "var(--slate-2)",
                      fontWeight: controls.slice_type === t ? 500 : 300,
                      transition: "background 0.15s",
                    }}
                  >
                    {t === "inline" ? "Inline" : t === "crossline" ? "Xline" : "Time"}
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* §2 Slice index */}
          <div className="flex flex-col gap-1.5">
            <div className="flex items-center justify-between">
              <span className="label-tag">Slice index</span>
              <span style={{ fontFamily: "var(--mono)", fontSize: "clamp(9px,0.75vw,11px)", color: "var(--teal)" }}>
                {controls.slice_idx}
                <span style={{ color: "var(--slate-2)" }}> / {maxIdx}</span>
              </span>
            </div>
            <input type="range" min={0} max={maxIdx} step={1}
              value={controls.slice_idx}
              onChange={e => set({ slice_idx: Number(e.target.value) })}
            />
          </div>

          <CtrlDivider />

          {/* §3 SAM params — three sliders in one row */}
          <div className="flex gap-4">
            <ParamSlider label="Pts / side" value={controls.points_per_side} min={4} max={32} step={4}
              onChange={v => set({ points_per_side: v })} />
            <ParamSlider label="IoU thresh" value={controls.iou_thresh} min={0.5} max={0.99} step={0.05}
              format={v => v.toFixed(2)} onChange={v => set({ iou_thresh: v })} />
            <ParamSlider label="Stability" value={controls.stability_thresh} min={0.5} max={0.99} step={0.05}
              format={v => v.toFixed(2)} onChange={v => set({ stability_thresh: v })} />
          </div>

          <CtrlDivider />

          {/* §3.5 Model quality picker */}
          <div className="flex items-center justify-between">
            <span className="label-tag">Quality</span>
            <div style={{ display: "flex", border: "1px solid rgba(0,229,195,0.12)", background: "var(--gap-bg)", gap: 1 }}>
              {MODEL_TIERS.map(({ size, label, title }) => (
                <button
                  key={size}
                  title={title}
                  onClick={() => set({ model_size: size })}
                  style={{
                    padding: "4px clamp(8px,0.8vw,14px)",
                    fontFamily: "var(--mono)",
                    fontSize: "clamp(8px,0.65vw,10px)",
                    letterSpacing: "0.1em",
                    border: "none",
                    cursor: "pointer",
                    background: controls.model_size === size ? "var(--teal)" : "var(--navy-3)",
                    color:      controls.model_size === size ? "var(--navy)" : "var(--slate-2)",
                    fontWeight: controls.model_size === size ? 600 : 300,
                    transition: "background 0.15s",
                  }}
                >
                  {label}
                </button>
              ))}
            </div>
          </div>

          <CtrlDivider />

          {/* §4 Actions row */}
          <div className="flex items-center gap-3">
            {/* Split-button: target select + run */}
            <div className="flex flex-1" style={{ border: "1px solid rgba(0,229,195,0.28)" }}>
              {/* Target dropdown */}
              <select
                value={samTarget}
                onChange={e => setSamTarget(e.target.value as SAMInput | "all")}
                disabled={anySamRunning}
                style={{
                  flexShrink: 0,
                  background: "var(--navy-3)",
                  border: "none",
                  borderRight: "1px solid rgba(0,229,195,0.18)",
                  color: "var(--teal)",
                  fontFamily: "var(--mono)",
                  fontSize: "clamp(8px,0.65vw,10px)",
                  letterSpacing: "0.1em",
                  textTransform: "uppercase",
                  padding: "0 clamp(6px,0.6vw,10px)",
                  cursor: "pointer",
                  outline: "none",
                }}
              >
                <option value="all">ALL</option>
                {SAM_INPUTS.map(inp => (
                  <option key={inp} value={inp}>{inp.toUpperCase()}</option>
                ))}
              </select>

              {/* Run button */}
              <button
                onClick={runSAM}
                disabled={!sliceData || anySamRunning}
                className="btn-teal"
                style={{ flex: 1, padding: "clamp(6px,0.8vh,10px) 0", fontSize: "clamp(9px,0.7vw,11px)", letterSpacing: "0.12em", border: "none" }}
              >
                {anySamRunning ? (
                  <>
                    <span className="h-3 w-3 animate-spin rounded-full border-2 border-transparent border-t-current" style={{ flexShrink: 0 }} />
                    RUNNING…
                  </>
                ) : `▶  RUN SAM`}
              </button>
            </div>

            {/* Mask count badge (appears after run) */}
            {totalMasks > 0 && (
              <div style={{ display: "flex", flexDirection: "column", alignItems: "center", lineHeight: 1, padding: "4px 10px", border: "1px solid rgba(0,229,195,0.2)", background: "rgba(0,229,195,0.05)", flexShrink: 0 }}>
                <span style={{ fontFamily: "var(--mono)", fontSize: "clamp(14px,1.2vw,20px)", fontWeight: 500, color: "var(--teal)" }}>{totalMasks}</span>
                <span style={{ fontFamily: "var(--mono)", fontSize: 8, color: "var(--slate-2)", letterSpacing: "0.1em", textTransform: "uppercase", marginTop: 2 }}>masks</span>
              </div>
            )}

            {/* 3D toggle */}
            <button
              onClick={() => setShow3D(v => !v)}
              style={{
                flexShrink: 0,
                padding: "clamp(6px,0.8vh,10px) 12px",
                fontFamily: "var(--mono)",
                fontSize: "clamp(8px,0.65vw,10px)",
                letterSpacing: "0.1em",
                textTransform: "uppercase",
                background: show3D ? "rgba(0,229,195,0.1)" : "var(--navy-3)",
                border: `1px solid ${show3D ? "rgba(0,229,195,0.25)" : "rgba(255,255,255,0.06)"}`,
                color: show3D ? "var(--teal)" : "var(--slate-2)",
                cursor: "pointer",
                transition: "background 0.2s, color 0.2s",
              }}
            >
              {show3D ? "▼ 3D" : "▲ 3D"}
            </button>
          </div>
        </div>
        {/* ╚══════════════════════════════════════════════════════╝ */}

        {/* ╔═ 3D Volume / placeholder ══════════════════════════════╗ */}
        {show3D ? (
          <VolumePanel controls={controls} />
        ) : (
          <div
            className="flex flex-col items-center justify-center gap-3"
            style={{ background: "var(--navy-2)" }}
          >
            <span style={{ fontFamily: "var(--mono)", fontSize: 10, color: "var(--slate-2)", letterSpacing: "0.12em", textTransform: "uppercase" }}>
              3D volume hidden
            </span>
            <button
              onClick={() => setShow3D(true)}
              style={{ padding: "5px 16px", fontFamily: "var(--mono)", fontSize: 9, letterSpacing: "0.1em", textTransform: "uppercase", background: "rgba(0,229,195,0.08)", border: "1px solid rgba(0,229,195,0.2)", color: "var(--teal)", cursor: "pointer" }}
            >
              ▲ show
            </button>
          </div>
        )}
        {/* ╚══════════════════════════════════════════════════════╝ */}
      </div>

      {/* ── Section separator ────────────────────────────────────── */}
      <div
        className="shrink-0 flex items-center px-5 gap-3"
        style={{ height: "clamp(24px,2.6vh,32px)", background: "var(--navy-3)", borderTop: "1px solid rgba(0,229,195,0.07)", borderBottom: "1px solid rgba(0,229,195,0.07)" }}
      >
        <span className="section-tag" style={{ fontSize: "clamp(8px,0.65vw,10px)" }}>
          Attribute comparison · 5 inputs
        </span>
        <div style={{ flex: 1 }} />
        <span style={{ fontFamily: "var(--mono)", fontSize: "clamp(7px,0.6vw,9px)", color: "var(--slate-2)", letterSpacing: "0.06em" }}>
          input · overlay · masks →
        </span>
      </div>

      {/* ── Attribute rows ────────────────────────────────────────── */}
      <div className="flex-1 overflow-y-auto min-h-0" style={{ background: "var(--navy)" }}>
        {SAM_INPUTS.map(inputName => (
          <AttributeRow
            key={inputName}
            inputName={inputName}
            images={sliceData?.images ?? null}
            samResult={samResults[inputName] ?? null}
            samLoading={samLoading[inputName] ?? false}
            samError={samErrors[inputName] ?? null}
          />
        ))}
      </div>
    </div>
  );
}
