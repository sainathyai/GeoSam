# Seismic Acquisition

← [Back to Knowledge Base Index](seismic_kb.md)

---

## The Physical Setup

Geophones sit on the **surface**, not buried. They measure ground vibration caused by seismic waves returning from depth.

```
SURFACE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💥 SHOT SOURCE       🎙️ 🎙️ 🎙️ 🎙️ 🎙️ 🎙️  geophones (surface)

      ╲                        ↑
       ╲                       │ reflected wave travels back up
        ╲                      │
         ╲                     │
          ▼                    │
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  Layer boundary 1 (e.g. shale/sandstone)
               ╲              ╱
                ╲            ╱
━━━━━━━━━━━━━━━━━╲━━━━━━━━━━╱━━  Layer boundary 2 (e.g. sandstone/limestone)
                  ╲        ╱
                   ╲      ╱
                    reflection point
```

### Shot Sources

| Type | How it works | Used where |
|---|---|---|
| Dynamite | Explosive charge buried 10–30m | Land surveys, rugged terrain |
| Vibroseis truck | Large hydraulic vibrating plate on the ground | Land surveys, populated areas |
| Air gun | Compressed air released underwater | Marine surveys |

### Geophones

A geophone is a spring-mass device. When the ground moves, the mass stays stationary (inertia) while the coil moves relative to a magnet — generating a voltage proportional to ground velocity. The voltage is the amplitude signal recorded in the trace.

---

## The Seismic Trace

One shot + one geophone = one **trace**: a 1D array of amplitude vs time.

```
Amplitude
    │   ╭╮
    │  ╭╯╰╮        ← reflection from Layer 1 (arrives at ~240ms)
    │  │   │
    │  │   ╰╮╭╮    ← reflection from Layer 2 (arrives at ~480ms)
    │  │    ╰╯ │
    │──────────────────────→ Time (ms)
    0  240  480  800  1200
```

- **Sampling interval**: how often electronics read the geophone. Typical: 2ms or 4ms.
- **Record length**: total recording window = n_samples × sampling_interval. Your synthetic: 300 × 4ms = 1,200ms.
- **Amplitude unit**: proportional to ground particle velocity (volts at the geophone, scaled in processing).

Each spike in the trace is a reflection. The time of the spike tells you how long the wave took to travel down to a boundary and back up (Two-Way Travel Time).

---

## Survey Geometry — How the Spread Works

A **geophone cable** (the spread) is a long cable with receivers every 25m, typically 2–6km total length. The cable stays fixed while the shot source moves.

```
SHOT TRUCK MOVES →

Shot 1   Shot 2   Shot 3   Shot 4   Shot 5
  │        │        │        │        │
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  surface
                                         
  🎙️  🎙️  🎙️  🎙️  🎙️  🎙️  🎙️  🎙️  🎙️   geophone cable (fixed)
```

Each shot is recorded by every geophone in the spread simultaneously. One shot → N_geophones traces, all captured in parallel.

### Roll-Along Acquisition

Once the shot truck passes the end of the cable, the cable is picked up and leapfrogged ahead. Within each cable position, the cable is stationary and the shot truck does all the moving. The leapfrog step size is chosen to maintain continuous coverage with no gaps.

---

## From One Shot to Many Midpoints

For each shot-geophone pair:

```
midpoint = (shot_position + geophone_position) / 2
offset   = |shot_position - geophone_position|
```

One shot fires → N geophones record → N (midpoint, offset) pairs computed.  
Next shot fires (at a new position) → N more pairs, many sharing midpoints with the previous shot.

This natural overlap across shots is what creates the **CMP gathers** used in processing. See [Seismic Processing](seismic_processing.md) for how midpoints are exploited.

---

## What the Raw Data Looks Like

After one shot, you have a **shot gather** — a 2D array indexed by (geophone_offset, time):

```
Offset →  (near)              (far)
Time ↓
  0ms    ──────────────────────────
 100ms         *         *         ← direct wave (travels along surface)
 200ms      *               *
 300ms    *                   *    ← shallow reflector (hyperbola)
 500ms      *               *
 700ms        *           *
 900ms          *       *          ← deeper reflector (wider hyperbola)
1100ms            *   *
```

The hyperbolic shape comes from the extra travel distance for far-offset geophones. NMO correction (see processing) flattens these hyperbolas.

---

## Key Numbers (Synthetic Dataset)

| Parameter | Value |
|---|---|
| Inline positions | 100 |
| Crossline positions | 120 |
| Total surface positions | 12,000 |
| Time samples per trace | 300 |
| Sampling interval | 4ms |
| Total record length | 1,200ms |
| Total amplitude values | 3,600,000 |
| File size (float32) | ~14.4MB (+ SEG-Y headers = 16.5MB) |
