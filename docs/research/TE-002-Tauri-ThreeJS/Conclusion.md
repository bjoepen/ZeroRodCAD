# TE-002 — Conclusion

## Gate D: PASS

Confidence: **MEDIUM** (not HIGH — see rationale below).

### Against the section-23 PASS checklist

Met: Tauri v2 on macOS ARM64 works; all dependencies current and actively maintained (verified
live); Python sidecar starts reliably (100% success rate, if slowly — see below); Python 3.13
used; no-VTK CadQuery path active and verified at five independent evidence layers; a real ZeroRod
model is generated; `PreviewMesh` is serialized successfully; the JSON contract is valid and
independently re-validated on both ends; the Rust command receives and correctly parses the
payload (tested with the real payload, not just synthetic data); Three.js can build correct
`BufferGeometry` from it (tested with the real payload); error cases are handled cleanly
everywhere; no VTK or Qt anywhere in the new path; the existing production app is completely
untouched; dependency governance is documented (`Dependencies.md`).

Not fully met, honestly disclosed rather than papered over: live interactive confirmation
(click → rotate → zoom → visually-correct render) — blocked by environment permissions in this
session, not by any defect found in the architecture (`Preview-Validation.md`). And: "Performance
für diesen Modellumfang plausibel" is true for the *engine and rendering* (sub-200 ms combined) but
not, as currently packaged, for the *full round trip* (~15 s, entirely attributable to onefile
sidecar self-extraction, not to the architecture itself — `Performance.md`).

Neither gap triggers a FAIL condition (section 23): the sidecar architecture is not unreliable
(it's 100% correct, just slow to start), IPC is not structurally problematic (it's a clean,
fully-tested, standard Tauri pattern), Three.js can render the real mesh (proven at the data
layer), VTK/Qt are not needed, and current libraries are clearly sufficient. Nor does either gap
meet the INCONCLUSIVE bar — central evidence about whether the architecture works *was* obtained,
just via automated proxies at the very last mile instead of a human eyeball. **Confidence is
downgraded to MEDIUM specifically because of these two gaps**, mirroring how TE-001.2 handled its
own single visual-confirmation gap (there, rated HIGH because it was the *only* gap; here there are
two, one of which — the round-trip latency — is a real, measured, user-facing characteristic, not
just a missing screenshot).

## The eleven architecture questions (section 34)

**1. Ist Tauri v2 für ZeroRodCAD technisch geeignet?**
Ja. Compiles and runs cleanly on macOS ARM64 with current stable Tauri v2 (2.11.x), current
official APIs throughout, no v1 patterns anywhere.

**2. Ist Python Sidecar ein sinnvoller Engine-Vertrag?**
Ja. It let the *exact* existing `zerorodcad` engine code run unmodified behind a narrow, versioned
contract, with zero changes to `preview.py`/`model.py`/`parameters.py`/`preview_data.py`.

**3. Ist stdin/stdout JSON für ZeroRodCAD ausreichend?**
Ja, at this model's scale (`Performance.md`): ~60 KB payload, sub-millisecond parse time. The
bottleneck found is process-startup packaging, not the protocol.

**4. Ist PreviewMesh ein guter GUI-neutraler Contract?**
Ja — confirmed directly: converting it to the transport contract took ~70 lines
(`mesh_contract.py`) with no changes to the source dataclasses at all. This is strong evidence the
existing TE-001-era design decision (keep `PreviewMesh`/`PreviewScene` renderer-agnostic) was
correct.

**5. Ist Three.js BufferGeometry für die Vorschau geeignet?**
Ja, at the data level (verified with the real payload); pixel-level rendering not independently
confirmed this session (`Preview-Validation.md`).

**6. Wie groß ist der Payload?**
60,079 bytes for the real default model (866 mesh vertices, 850 triangles, 12 line points).

**7. Wie schnell ist der Roundtrip?**
Engine work: ~150 ms. Full process round trip as currently packaged (onefile): ~15 s median,
dominated by PyInstaller self-extraction, not application logic.

**8. Brauchen wir langfristig ein Binärformat?**
Nein, nicht bei diesem Modellumfang — siehe `Performance.md`. Sollte die Vertex-/Dreieckszahl um
Größenordnungen wachsen, wäre das neu zu bewerten; für ZeroRodCAD's aktuelle Modellgröße ist JSON
klar ausreichend.

**9. Kann PySide6 perspektivisch vollständig entfallen?**
Technisch ja für den reinen Preview-/CAD-Pfad — nichts in dieser Kette benötigt PySide6 oder Qt.
Das sagt nichts über die übrige Desktop-App-Funktionalität (Settings, Projektverwaltung,
Exportdialoge etc.) aus, die TE-002 bewusst nicht migriert oder bewertet hat (section 37).

**10. Welche Risiken bleiben?**
- Onefile sidecar startup latency (~15 s) — real UX risk if shipped as-is; known, well-understood
  fix paths exist (onedir sidecar packaging, or a long-lived reused sidecar process instead of a
  fresh spawn per request) but neither was implemented here (deliberate scope discipline).
- Live interactive/visual confirmation was not possible in this environment — a real evidence gap,
  not a found defect, but still a gap a production decision should close with an actual manual
  test on a normal desktop session.
- The `preview` command only supports default parameters in this PoC — a real product would need
  the full `ZeroRodParameters` surface exposed through the contract, not evaluated here.
- No handling yet for an in-flight sidecar process if the user closes the window mid-request — see
  `Tauri-Architecture.md`'s note on this.
- CadQuery still requires the TE-001.1 patch (not yet upstream) — same open question TE-001.1 and
  TE-001.2 already flagged, unchanged by TE-002.

**11. Ist eine produktive Migration technisch gerechtfertigt?**
Noch nicht direkt — siehe Empfehlung unten. Die Architektur ist überzeugend nachgewiesen; die
verbleibenden Risiken sind bekannt, benannt und keiner davon ist architektureller Natur.

## CadQuery patch deployment (carried forward from TE-001.1/TE-001.2, unchanged by TE-002)

No new information — TE-002 reused the already-patched `.venv-novtk-bundle` from TE-001.2 as-is.
The recommendation stands: upstream fix preferred long-term, a version-pinned temporary patch step
viable in the interim (now proven to work through packaging *and* a completely different consumer
architecture — a second independent confirmation that the patch is stable and portable).

## Productive migration: **NOT YET**

Not a NO-GO — the chain works, and every architectural question this PoC set out to answer was
answered favorably. But two concrete, non-architectural items should close first: (1) resolve the
onefile startup-latency risk (a packaging decision, not a redesign), and (2) get a real, human,
interactive confirmation of the on-screen render (a one-session task on a normal desktop, not a
research question). Neither requires revisiting the architecture itself.

## Explicitly not done (section 37, unchanged)

PySide6 was not removed. The existing desktop app was not replaced. The production packaging
pipeline was not touched. No Build 022 was started. No settings/export-dialog migration occurred.
No feature parity was attempted. TE-002 ends at the architecture proof, exactly as scoped.
