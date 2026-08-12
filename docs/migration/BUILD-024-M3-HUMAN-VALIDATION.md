# Build 024 / Milestone 3 — Human Validation Checklist

Engineering completion for M3 (export robustness — post-export verification hardened with a
second, independent Rust-side structural-validation layer; overwrite/TOCTOU behavior
investigated and documented; export retry safety evidence-based decided; real path/Unicode/
spaces/repeated-export/interleaving evidence gathered against the real persistent sidecar) is
covered by automated evidence: see `docs/migration/BUILD-024-M3-EXPORT-ROBUSTNESS.md` and
`scripts/validate-build024-m3.sh`. This document is the interactive click-through a human
tester still needs to do — M3 deliberately does not change the export UI's look or flow from
M2 (Round 2, already Human-Validation-PASS), so this checklist is largely a *regression*
retest plus a few M3-specific additions (Downloads/Documents paths, spaces path), not a new
feature walkthrough.

This environment had no display/GUI access when this checklist was drafted, so every item is
left **unchecked** rather than assumed, per the same allowance used throughout this migration
("Claude leaves unchecked if human clicking unavailable").

## Build under test

A fresh release bundle was built from this milestone's exact HEAD via:

```
./scripts/build-productive-desktop-app.sh release
```

Absolute path (see the final report for the exact commit this was built from):

```
/Users/bernd/Projekte/ZeroRodCAD-App/desktop/src-tauri/target/release/bundle/macos/ZeroRodCAD.app
```

Open command:

```
open "/Users/bernd/Projekte/ZeroRodCAD-App/desktop/src-tauri/target/release/bundle/macos/ZeroRodCAD.app"
```

(Unsigned — first launch needs the standard Gatekeeper override, right-click → Open.)

## Checklist

- [ ] App launches
- [ ] Existing parameter/live preview workflow works
- [ ] Export Model… opens native directory dialog

- [ ] Export to empty directory succeeds
- [ ] STL exists
- [ ] STEP exists
- [ ] report exists
- [ ] exported STL or STEP can be opened externally

- [ ] Export to a directory with spaces in its name succeeds (e.g. create/select a folder
      named "ZeroRod Export Test")
- [ ] Export to a normal `~/Downloads` or `~/Documents` subfolder succeeds

- [ ] Repeat export to same directory
- [ ] overwrite warning appears
- [ ] Cancel preserves existing files
- [ ] Confirm overwrite succeeds

- [ ] Change geometry
- [ ] wait for visible preview
- [ ] export
- [ ] exported model corresponds to visible model

- [ ] Provoke a safe failure if the checklist provides a controlled method (e.g. select a
      destination and revoke write permission via Finder's "Get Info" before exporting, then
      restore it afterward)
- [ ] failure message is understandable
- [ ] next normal export succeeds

- [ ] Preview still rotates/zooms after exports
- [ ] Parameter editing still works
- [ ] App quits cleanly
- [ ] No zerorod-engine process remains after quitting

## Result

| Field | Value |
|---|---|
| Tester | Project Owner |
| Date | 2026-08-12 |
| macOS | 26.5.2 (Build 25F84) |
| Hardware | Apple M4 |
| Result | **PASS** |
| Notes | Reported directly by the Project Owner at the start of the Build 024 M4 mandate: "Project Owner hat das eindeutig identifizierte M3-Artefakt validiert" / "Project Owner result: PASS". The Project Owner's confirmation was communicated at the milestone/overall level in that mandate text, not as a re-transcribed per-line walkthrough of the checklist above — so the individual checkboxes above are intentionally left unticked rather than back-filled from an itemized record that was not separately provided, per this document's own "do not claim tests the Project Owner did not perform" discipline. |

## Artifact identity (independently re-verified during M4)

The mandate identified the validated artifact as `ZeroRodCAD-Build024-M3.app`, built from this
milestone's exact HEAD (`72768bd`), with two independent identity proofs. Both were re-checked
directly against the local `.app` bundle during M4 and confirmed to match exactly:

| Proof | Claimed (mandate) | Re-verified |
|---|---|---|
| Frontend asset filename | `index-CV7-6lJU.js` | Present in `desktop/frontend/dist/assets/` and referenced in the bundled Rust binary's embedded-asset strings (`/assets/index-CV7-6lJU.js`) |
| Frontend asset SHA-256 | `9fd28961e24823f08a728a9db529475f301d1f2d3938ae378d8ed1fbd6b11bde` | `shasum -a 256` on `desktop/frontend/dist/assets/index-CV7-6lJU.js` → **identical match** |
| Compiled Build-024-specific marker | `invalid_export_result` | Present in `Contents/MacOS/zerorod-desktop`'s string table (`strings` search, 1 occurrence) |

This confirms the artifact the Project Owner validated is genuinely the M3 build, not an older
(e.g. M2) bundle — the specific ambiguity risk this milestone's own artifact-identity lesson
(§7/§8 of the Build 024 M4 mandate) exists to guard against.

## Gate BUILD-024-M3 (human component)

**PASS.** The engineering gate (`scripts/validate-build024-m3.sh`) passes independently of this
checklist; both the engineering gate and this human-validation record are now complete. Milestone
3 is fully complete — Gate BUILD-024-M3: PASS (engineering + human).
