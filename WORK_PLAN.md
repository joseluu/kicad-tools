# Work Plan

Prioritized roadmap generated from current GitHub label state. Maintained by the Guide triage agent.

*Last updated: 2026-08-14*

---

## Urgent (Top Priority)

*No issues currently carry the `loom:urgent` label.*

## In Progress (`loom:building`)

*Nothing in flight.* 2 open PRs, both stale Dependabot site bumps (#4835 nanoid, #4836 js-yaml) already satisfied on `main` via the astro 7 upgrade — left for Dependabot auto-close.

## Ready for Work (`loom:issue`)

| Issue | Title |
|-------|-------|
| #4507 | Router Phase 2 (epic #4431): search-time pairwise HV avoidance + C++ `validate_route` domain-matrix extension |
| #4674 | CLI: `--format json` for the remaining prose-only `kct` subcommands (build/pipeline/stitch left) |
| #4799 | Router/planner: pre-route capacity/solvability predictor from the crossover census |
| #4830 | External corpus + benchmark: open-schematics (87k designs) and OmniLayout (slices 2–4) |
| #4831 | pcbplace generative-placement ideas: pad-anchored constraints, local repair, deterministic legaliser (M-stubs) |

## Awaiting Triage

#4848 (C++ pairwise first-band-vs-nearest pricing quirk), #4855 (`kct mcp --transport http` passes host/port `FastMCP.run()` doesn't accept).

## Active Epics (need Architect decomposition)

| Epic | Title |
|------|-------|
| #4431 | Class-pair (net-class × net-class) clearance rules in the router (parent of #4507) |
| #4409 | Coupled diff-pair router must actually couple pairs (board-06: 0/9) |
| #4410 | board-05 unattended manufacturable BLDC generation |
| #3803 | Router/DRC fidelity: kct PASS vs native KiCad DRC violations |
| #3438 | board-07 parallel pad-array bundles (router ↔ placement) |

## LVS Soundness Epic — COMPLETE (2026-06-17)

The independent copper-LVS soundness epic (motivated by #3742) is shipped. A `/loom:sweep` run on 2026-06-16/17 processed the #3762/#3763 Architect proposals and their entire follow-on tree — **16 PRs merged**:

- **Gate + extractor hardening**: independent copper-extracted LVS gate (#3757); label-free pour extraction (#3761); per-zone pour-pad bonding across disjoint fill islands (#3772); foreign-net track-segment carve in zone fill (#3773); layer-aware segment chaining to kill phantom via-less-crossover shorts (#3783/#3792).
- **Fleet rollout**: shared `write_lvs_report` helper + board 00/01 hard gates (#3762); boards 02/06/07 wired (#3779); boards 03/04 advisory (#3780).
- **Board fixes the gate surfaced** (real defects DRC missed): board-03 GND F.Cu/B.Cu plane stitching (#3787); board-04 OSC_IN↔OSC_OUT crystal-pin short re-route (#3785) + GND re-pour (#3791); board-03/04 schematic↔PCB net-drift reconciliation (#3764/#3765); fleet staleness-detection fix (#3767); the 2026-06 parity audit (#3763).

Net result: boards 00/01/02/03 are copper-LVS clean and reproducible; the gate caught (and fixed) genuine shorts on boards 02/03/04 that passed DRC.

## Resolved since the 2026-06-17 refresh

The board-05 blockers listed here previously are done: **#3766 closed 2026-07-08** — 206/206 pads, ship-ready, all 4 ISENSE Kelvin nets routed (#3997/#3998), manufacturing bundle regenerated at jlcpcb-tier1 (#3999). The #3775 relayout question was superseded by the placement-rework + hand-router-toolkit path. Remaining board-05 work is the *unattended-generation* epic #4410 above (generic-library capability, not a board fix).

## Recently Completed

The May 1–8 sprint cleared an enormous backlog of router-pipeline polish, board generation, and CI hardening. Highlights since the last `WORK_PLAN` refresh (2026-03-18):

| Theme | Outcome |
|-------|---------|
| **v0.11.0 release** | Multi-resolution routing, R-tree spatial indexing, crossing-aware A* pathfinding (2026-04-12) |
| **v0.12.0 release** | Manufacturing export pipeline (BOM, CPL, gerber), JLCPCB integration, Jinja2 design report (2026-04-15) |
| **v0.13.0 release** | Two-phase global routing with RSMT decomposition, RUDY congestion estimator, Specctra DSN export (2026-04-28) |
| **v0.14.0 release** | Demo gallery website (kicad-tools.org), zone-fill foreign-pad clearance fix, PCB `page_fit`, oblique 3D + 2D-SVG renders, `kct render` / `board-metrics` / `pcb page-fit` commands, gallery LVS status, ERC/LVS/Manifest meta sub-checks for `kct check` (2026-06-16) |
| **v0.15.0 release** | Router feasibility certificates + constructive escape ordering, coupled diff-pair corridor attractors + C++ joint-state A\* port, slack-budget corridor widening, copper-LVS gates across boards 01–07, LCSC/EasyEDA + cross-library 3D model resolver tiers, thin-copper/silk-clearance/net-0-bridge DRC rules, gallery-hardened board fixtures 00–07 (2026-07-13) |
| **v0.16.0 release** | Region-bounded routing (`--region` + boundary stub reconnection), ampacity-aware net-class min-width + DRC (IPC-2221), copper dedupe (`pcb dedupe` + emission-time), `pcb reinforce` anchor-PTH rows, `pcb padmap` / `sch fix-annotation` / `pcb strip --region`, `net-status --strict` real-geometry connectivity, off-board preflight; pre-tag fleet validation fixed #4226 (junction-dot-gated wire union), #4227 (courtyard bbox-fallback annotation), #4229 (zone-pour plane-pad connectivity) (2026-07-15) |
| **v0.19.0 release** | HV-isolation design loop (`kct creepage --voltage-map`, `zones hv-keepout`, HV-aware placement, `/kct:hv-isolation-loop` skill) + via-in-pad manufacturability (`kct fix-vias` off-pad relocation), `analyze electrical-rating`, `--emit-dru`/`--emit-drc-constraints` rule-identity sidecars (2026-07-20) |
| **v0.20.0 release (current)** | `kct route --complete` completion pass, route-time HV-isolation enforcement in every engine, `.kct_waivers.json` waiver mechanism, `net-status` strict-by-default, KiCad-10 net-dialect / export-manifest / LVS-identity correctness sweep; shipped as a 13-PR train through the Actions outage (2026-08-06) |
| **v0.18.0 release** | HV / analog manufacturing gates — **`kct creepage`** (surface-path creepage audit vs IEC 60664-1/62368-1, #4327/#4332/#4333/#4334/#4338/#4341) and **`kct analyze current-sense`** (analog layout lint: parallel-run + sense-loop area + Kelvin-tap, #4328/#4331/#4335/#4337). Plus real `--nets` route filter (#4325), `pcb reinforce` multi-branch anchoring (#4323), `route --layers auto` inner-layer advisory (#4315), and safety-relevant `kct check` ampacity/stackup false-PASS fixes (#4324/#4326/#4339). IEC values verified against a controlled copy of the standard (#4343). Both new capabilities shipped as phased MVPs (1→3) with tracked follow-ups. (2026-07-20) |
| **v0.17.0 release** | Experimental alternative routing substrate — adaptive octilinear **lattice** engine (`--route-engine lattice`) + constrained-Delaunay **navmesh/mesh** engine (`--route-engine mesh`), both default-OFF (epic #4267, P0→P4); routes large mixed-pitch boards the grid can't fit in memory (softstart rev-C: 74/77 nets DRC-clean at ~3% grid memory). Plus `--max-cells` (#4249), analytical `route --dry-run` (#4266), settable schematic `in_bom`/`dnp` (#4303), `net-status --why` ranked fix recommender (#4261/#4286), parts-catalog fixes (#4295–#4299); board-07 Track A closed placement-bound (#4256–#4258). `--route-engine grid` default byte-identical to 0.16.0 (2026-07-17) |
| **C++ pathfinder hardening** | `cpp_backend` with stale-`.so` build-version guard (#2501), DRC violation cost feedback (#2442), pre-computed blocked bitmap (#2437), pad metal area expansion (#2434), resumable A* (#2449) |
| **Auto-pour zones** | Power-net pour zones generated automatically with proper edge-clearance inset and per-net priority (#2407, #2417, #2422, #2461, #2519) |
| **Boards 02–05 brought online** | Placement and full routing for charlieplex (boards/02), USB joystick (boards/03, polished by #2536), STM32F103 board 04 (#2538, #2545), BLDC controller / DRV8301 (#2535, #2551) |
| **CI hardening** | kicad-cli round-trip smoke test on every emitted PCB (#2507), build-time PCB validity smoke check (#2505), `_routed.kicad_pcb` validation gate (#2552) |
| **Pipeline UX** | `kct pipeline` end-to-end workflow (#1307), `/release` skill for guided semver releases, `--commit` flag for pipeline runs |
| **Differential-pair groundwork** | CoupledPathfinder routing, N-pad coupling (#2478), `--differential-pairs` CLI flag (#2474), HIGH_CURRENT_SIGNAL net class (#2471) — all merged before Epic #2556 was scoped |
| **Loom upgraded to 0.7.1** | Includes #2547 incremental-commit protocol (PR #2554) — builders and doctors must now commit incrementally |

## Backlog Health

| Metric | Value |
|--------|-------|
| Total open issues | 12 |
| Ready for work (`loom:issue`) | 5 |
| Urgent (`loom:urgent`) | 0 |
| Building (`loom:building`) | 0 |
| Blocked (`loom:blocked`) | 0 |
| Awaiting triage (`loom:triage`) | 2 |
| Active epics (`loom:epic`) | 5 |

**Assessment:** Healthy as of 2026-08-14, immediately after the session-9 sweep (41 PRs merged, 8 issues closed — the dependency-modernization batch plus 12 builds; see `.loom/SWEEP-HANDOFF.md` and WORK_LOG). The queue holds five curated, sliceable work streams (HV routing #4507, machine-output sweep #4674, capacity predictor #4799, corpus exploration #4830, placement ideas #4831) and five epics awaiting serialized Architect decomposition (#4431, #4409, #4410, #3803, #3438). Two fresh triage items (#4848, #4855) need a Curator pass.
