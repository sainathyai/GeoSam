# Glossary

← [Back to Knowledge Base Index](seismic_kb.md)

---

| Term | Definition |
|---|---|
| **Acquisition design** | Pre-survey engineering of shot positions, geophone spacing, and cable length to guarantee uniform CMP fold across the survey area |
| **Amplitude** | The measured ground velocity at a geophone at a specific time. Proportional to the acoustic impedance contrast at the reflecting boundary |
| **AVO (Amplitude Variation with Offset)** | How amplitude changes with shot-to-geophone distance. Gas sands often show distinctive AVO behaviour — used for fluid detection. Preserved only in prestack data |
| **Bright spot** | Anomalously high amplitude response, typically caused by gas replacing brine in a porous reservoir rock. High impedance contrast = strong reflection |
| **CMP (Common Midpoint)** | The surface midpoint between a shot and a geophone. All shot-geophone pairs sharing the same midpoint are grouped into a CMP gather for NMO and stacking |
| **CMP gather** | A collection of traces sharing the same surface midpoint but recorded with different shot-geophone offsets. Forms a hyperbola in offset-time space |
| **Coherence** | A seismic attribute measuring lateral similarity of adjacent traces. Low coherence indicates disrupted geology (faults, channels) |
| **Depth conversion** | Converting the TWT z-axis to depth in metres using a velocity model. Separate step from time migration |
| **Diffraction** | Wave energy scattered from a point scatterer (fault tip, buried object) that spreads as a hyperbola in time-offset space. Migration collapses diffractions back to their true point location |
| **Dip** | (1) Geological: the angle at which a rock layer tilts from horizontal. (2) Seismic attribute: spatial gradient magnitude of the amplitude slice — highlights edges and boundaries |
| **DMO (Dip Moveout)** | A correction applied before NMO to compensate for the fact that CMP traces don't reflect from the same subsurface point when reflectors are dipping |
| **Envelope** | Seismic attribute: the magnitude of the Hilbert transform — reflector strength without polarity. Always positive |
| **Fold** | Number of traces per CMP gather. Higher fold = more traces to stack = better noise cancellation. Typical: 60–120 |
| **Geophone** | A surface sensor that measures ground particle velocity using a spring-mass coil-and-magnet mechanism. Converts ground motion to voltage |
| **Hilbert transform** | Mathematical operation that produces the analytic signal. Used to compute envelope |
| **Impedance contrast** | The difference in acoustic impedance (velocity × density) between two rock layers. Larger contrast = stronger reflection |
| **Inline** | One horizontal direction across a 3D seismic survey. Slicing at a fixed inline index gives a vertical cross-section |
| **Kirchhoff migration** | A migration method based on ray tracing — traces acoustic rays from the surface to each subsurface point and sums contributions |
| **Migration** | Processing step that repositions amplitude values from CMP midpoint coordinates to their true subsurface reflection point coordinates. Sharpens faults, corrects dipping beds |
| **NMO (Normal Moveout)** | The time delay of a reflection in a CMP gather as a function of offset. NMO correction applies a time shift to each trace to flatten the hyperbola, making traces stackable |
| **Offset** | The distance between a shot and a geophone. Determines the path length and thus the NMO time delay |
| **Poststack migration** | Migration applied to the stacked volume. Cheaper, lower image quality |
| **Prestack migration** | Migration applied to individual offset gathers before stacking. ~120× more expensive but higher quality, preserves AVO |
| **Roll-along acquisition** | Survey technique where the geophone cable leapfrogs forward in large jumps once the shot truck has passed the end of the cable |
| **RTM (Reverse Time Migration)** | The highest-quality migration method. Runs the full wave equation backwards in time. Most computationally expensive |
| **SAM (Segment Anything Model)** | Meta's foundation model (2023) trained on 1B images to segment any object in any image. Used zero-shot in GeoSAM |
| **Sampling interval** | Time between consecutive samples in a trace. Typical: 2ms or 4ms. Limits the maximum frequency that can be recorded (Nyquist) |
| **SEG-Y** | Standard file format for seismic data. Contains binary trace data + trace headers (coordinates, sample info) + binary/text file headers |
| **Seismic attribute** | A mathematical transform of the amplitude slice that isolates a specific geological signal. GeoSAM: envelope, dip, coherence, texture |
| **Shot gather** | All traces recorded by all geophones from one shot. Indexed by (geophone_offset, time) |
| **Stack** | Averaging of NMO-corrected traces within a CMP gather to suppress noise and strengthen signal |
| **Stacked volume** | The 3D array produced after sorting, NMO, and stacking. One trace per CMP midpoint. Approximates zero-offset recording |
| **Texture** | Seismic attribute: local standard deviation of amplitude in a sliding window. Measures lithological heterogeneity |
| **Timeslice** | A horizontal cut through the seismic volume at a fixed time sample. Shows map-view distribution of features at that depth/time |
| **Trace** | The fundamental unit of seismic data. A 1D array of amplitude vs time recorded by one geophone from one shot |
| **TWT (Two-Way Travel Time)** | The elapsed time from a shot firing to a reflected wave arriving back at the surface. The z-axis unit in time-domain seismic data (milliseconds) |
| **Velocity model** | A 3D map of acoustic wave velocity at every subsurface point. Required for NMO correction, migration, and depth conversion |
| **Vibroseis** | A land seismic source — a large truck with a hydraulic vibrating plate. Emits a swept-frequency signal (chirp) rather than an impulse |
| **Volume** | The 3D array `volume[x, y, z] = amplitude` produced by seismic processing. x, y = migrated subsurface coordinates. z = TWT or depth |
| **Zero-offset** | A hypothetical recording where shot and geophone are at the same location (offset=0). Stacking approximates this |
