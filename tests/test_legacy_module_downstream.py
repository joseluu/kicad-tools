"""Regression tests: legacy ``(module ...)`` boards through downstream walkers.

PR #4879 taught ``PCB._parse()`` (and every tag-keyed walk in
``schema/pcb.py``) to accept ``(module ...)`` as the pre-KiCad-6 spelling of
``(footprint ...)``, so ``pcb.footprints`` is now populated for legacy-dialect
boards. But six other modules still walked the raw S-expression tree with a
bare ``find_all("footprint")`` (or an equivalent ``== "footprint"`` tag
comparison) and were never updated to recognize the ``module`` alias:

- ``zones.fill_clearance``
- ``lvs.board_lvs``
- ``drc.repair_clearance``
- ``drc.repair_silkscreen``
- ``panel.panel``
- ``cli.runner``

Before this fix, a legacy board reached these modules with a populated
``pcb.footprints`` component graph (via ``schema.pcb.PCB``) while these
modules' own tree walks still saw zero footprints -- a confusing
partial/inconsistent failure mode, worse than the prior uniform blindness
(issue #4886).

Each ``TestXxxLegacyModuleBoard`` class below pins one module's affected
code path against a minimal ``(module ...)`` fixture, proving the walker now
finds the same footprints/pads a modern ``(footprint ...)`` board would
produce.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from kicad_tools.sexp import SExp, parse_string

# ---------------------------------------------------------------------------
# zones.fill_clearance
# ---------------------------------------------------------------------------

shapely = pytest.importorskip("shapely", reason="Shapely required for zone-fill tests")


def _pad_zone_connect(doc: SExp, pad_uuid: str) -> int | None:
    """Look up a pad's ``(zone_connect N)`` value by UUID.

    Walks both the modern ``footprint`` and legacy ``module`` tags directly
    (rather than importing the code under test) so the test assertion is
    independent of the fix it is verifying.
    """
    for child in doc.children:
        if child.name not in ("footprint", "module"):
            continue
        for pad in child.find_all("pad"):
            u = pad.find("uuid")
            if u is not None and u.get_string(0) == pad_uuid:
                zc = pad.find("zone_connect")
                return zc.get_int(0) if zc is not None else None
    raise AssertionError(f"pad {pad_uuid} not found")


class TestFillClearanceLegacyModuleBoard:
    """``zones/fill_clearance.py`` walks the board via ``_find_all_footprints``."""

    # Foreign-net (GND) pad inside a legacy ``module`` block, sitting under a
    # VCC zone's fill.  Same shape as ``test_zones_fill_clearance.py``'s
    # ``_BOARD`` fixture but with the pre-KiCad-6 ``module`` spelling.
    _OBSTACLE_BOARD = """
    (kicad_pcb
      (version 4)
      (host pcbnew "(2017-11-30)")
      (net 0 "")
      (net 1 "VCC")
      (net 3 "GND")
      (module lib:foreign (layer F.Cu) (tedit 0) (at 5 5)
        (fp_text reference U1 (at 0 1) (layer F.SilkS))
        (pad 1 thru_hole rect (at 0 0) (size 1.7 1.7) (drill 1.0)
          (layers *.Cu *.Mask) (net 3 GND))
      )
      (zone
        (net "VCC")
        (layer F.Cu)
        (uuid test-zone)
        (hatch edge 0.5)
        (connect_pads (clearance 0.3))
        (min_thickness 0.25)
        (fill yes (thermal_gap 0.3) (thermal_bridge_width 0.4))
        (polygon (pts (xy 0 0) (xy 20 0) (xy 20 20) (xy 0 20)))
        (filled_polygon
          (layer F.Cu)
          (pts (xy 0 0) (xy 20 0) (xy 20 20) (xy 0 20))
        )
      )
    )
    """

    def test_apply_foreign_pad_clearance_finds_pad_in_module_block(self) -> None:
        """``_collect_obstacles`` must see the pad inside the ``module`` block."""
        from kicad_tools.zones.fill_clearance import apply_foreign_pad_clearance

        doc = parse_string(self._OBSTACLE_BOARD)
        modified = apply_foreign_pad_clearance(doc)

        # Before the fix, _collect_obstacles's bare find_all("footprint")
        # saw zero obstacles on a module-only board -- the fill would be
        # returned untouched (modified == 0).
        assert modified >= 1

        zone = doc.find_all("zone")[0]
        filled = zone.find("filled_polygon")
        pts = filled.find("pts")
        ring = [(xy.get_float(0), xy.get_float(1)) for xy in pts.find_all("xy")]
        fill = shapely.geometry.Polygon(ring)
        foreign_pad = shapely.geometry.box(5.0 - 0.85, 5.0 - 0.85, 5.0 + 0.85, 5.0 + 0.85)

        # The fill must no longer overlap the foreign-net pad.
        assert fill.intersection(foreign_pad).area == pytest.approx(0.0, abs=1e-6)

    # A GND zone with a small module pad that cannot host 2 thermal spokes,
    # plus a same-net large pad that can.
    _SELECTIVE_BOARD = """
    (kicad_pcb
      (version 4)
      (host pcbnew "(2017-11-30)")
      (net 0 "")
      (net 1 "GND")
      (module lib:small (layer F.Cu) (tedit 0) (at 5 5)
        (pad 1 smd rect (at 0 0) (size 0.5 0.5) (layers F.Cu)
          (net 1 GND) (uuid pad-small)))
      (module lib:big (layer F.Cu) (tedit 0) (at 10 10)
        (pad 1 smd rect (at 0 0) (size 3.0 3.0) (layers F.Cu)
          (net 1 GND) (uuid pad-big)))
      (zone
        (net 1)
        (net_name GND)
        (layer F.Cu)
        (uuid z1)
        (hatch edge 0.5)
        (connect_pads (clearance 0.3))
        (min_thickness 0.25)
        (fill yes (thermal_gap 0.3) (thermal_bridge_width 0.4))
        (polygon (pts (xy 0 0) (xy 20 0) (xy 20 20) (xy 0 20)))
      )
    )
    """

    def test_selective_pad_connection_forces_solid_on_small_module_pad(self) -> None:
        """``_apply_selective_pad_connection`` walks module pads too."""
        from kicad_tools.zones.fill_clearance import normalize_zone_pad_connection

        doc = parse_string(self._SELECTIVE_BOARD)
        changed = normalize_zone_pad_connection(doc)  # default: selective

        # Before the fix, the selective walker's bare find_all("footprint")
        # saw zero footprints, so changed would be 0 regardless of pad size.
        assert changed == 1
        assert _pad_zone_connect(doc, "pad-small") == 2  # forced solid
        assert _pad_zone_connect(doc, "pad-big") is None  # kept thermal relief

    def test_force_solid_on_pads_by_uuid_finds_module_pad(self) -> None:
        """``force_solid_on_pads_by_uuid`` walks module pads too."""
        from kicad_tools.zones.fill_clearance import force_solid_on_pads_by_uuid

        doc = parse_string(self._SELECTIVE_BOARD)
        changed = force_solid_on_pads_by_uuid(doc, {"pad-big"})

        assert changed == 1
        assert _pad_zone_connect(doc, "pad-big") == 2


# ---------------------------------------------------------------------------
# lvs.board_lvs
# ---------------------------------------------------------------------------


class TestBoardLVSLegacyModuleBoard:
    """``lvs/board_lvs.py``'s ``_pcb_pin_to_net`` walks the raw PCB tree."""

    _BOARD = """(kicad_pcb (version 4) (host pcbnew "(2017-11-30)")
  (general (thickness 1.6))
  (page A4)
  (layers (0 F.Cu signal) (31 B.Cu signal))
  (net 0 "")
  (net 1 GND)
  (net 2 SIG)
  (module R_0603 (layer F.Cu) (tedit 5A1F2B3C) (at 5 5)
    (fp_text reference R1 (at 0 1.5) (layer F.SilkS))
    (fp_text value 10K (at 0 -1.5) (layer F.Fab))
    (pad 1 smd rect (at -0.8 0) (size 0.9 0.8) (layers F.Cu F.Paste F.Mask) (net 1 GND))
    (pad 2 smd rect (at 0.8 0) (size 0.9 0.8) (layers F.Cu F.Paste F.Mask) (net 2 SIG))
  )
)
"""

    def test_pcb_pin_to_net_reads_pads_inside_module_blocks(self, tmp_path: Path) -> None:
        from kicad_tools.lvs.board_lvs import _pcb_pin_to_net

        pcb_path = tmp_path / "legacy.kicad_pcb"
        pcb_path.write_text(self._BOARD, encoding="utf-8")

        # Before the fix this returned {} -- the bare find_all("footprint")
        # walk saw zero footprints on a module-only board.
        pin_map = _pcb_pin_to_net(pcb_path)

        assert pin_map == {
            ("R1", "1"): "GND",
            ("R1", "2"): "SIG",
        }

    def test_compare_netlists_is_clean_against_module_board(self, tmp_path: Path) -> None:
        import kicad_tools.lvs.board_lvs as board_lvs_mod

        pcb_path = tmp_path / "legacy.kicad_pcb"
        pcb_path.write_text(self._BOARD, encoding="utf-8")

        sch_map = {("R1", "1"): "GND", ("R1", "2"): "SIG"}

        # Exercise via a light monkeypatch of the schematic side only, so the
        # PCB side genuinely goes through the fixed _pcb_pin_to_net.
        orig = board_lvs_mod._schematic_pin_to_net
        try:
            board_lvs_mod._schematic_pin_to_net = lambda _p: dict(sch_map)
            result = board_lvs_mod.compare_netlists("dummy.kicad_sch", pcb_path)
        finally:
            board_lvs_mod._schematic_pin_to_net = orig

        assert result.clean is True
        assert result.mismatches == ()


# ---------------------------------------------------------------------------
# drc.repair_clearance
# ---------------------------------------------------------------------------


class TestRepairClearanceLegacyModuleBoard:
    """``drc/repair_clearance.py``'s ``ClearanceRepairer`` walks the raw tree."""

    _BOARD = """(kicad_pcb (version 4) (host pcbnew "(2017-11-30)")
  (general (thickness 1.6))
  (page A4)
  (layers (0 F.Cu signal) (31 B.Cu signal))
  (net 0 "")
  (net 1 GND)
  (module R_0603 (layer F.Cu) (tedit 5A1F2B3C) (at 100 100)
    (fp_text reference R1 (at 0 1.5) (layer F.SilkS))
    (pad 1 smd rect (at 0 0) (size 0.9 0.8) (layers F.Cu F.Paste F.Mask) (net 1 GND))
  )
)
"""

    def _repairer(self, tmp_path: Path):
        from kicad_tools.drc.repair_clearance import ClearanceRepairer

        pcb_path = tmp_path / "legacy.kicad_pcb"
        pcb_path.write_text(self._BOARD, encoding="utf-8")
        return ClearanceRepairer(pcb_path)

    def test_find_pads_near_locates_pad_inside_module_block(self, tmp_path: Path) -> None:
        repairer = self._repairer(tmp_path)

        # Before the fix, _find_pads_near's bare find_all("footprint") saw
        # zero footprints -- this returned [] regardless of radius/point.
        results = repairer._find_pads_near(100.0, 100.0, radius=1.0, layer=None, nets=None)

        assert len(results) == 1
        pad_node, kind, abs_x, abs_y, pad_layer, net_name = results[0]
        assert kind == "pad"
        assert abs_x == pytest.approx(100.0)
        assert abs_y == pytest.approx(100.0)
        assert net_name == "GND"

    def test_find_footprint_by_ref_locates_module_footprint(self, tmp_path: Path) -> None:
        repairer = self._repairer(tmp_path)

        # Before the fix this returned None -- the bare find_all("footprint")
        # never found the ref-bearing module.
        info = repairer._find_footprint_by_ref("R1")

        assert info is not None
        _fp_node, ref, x, y, _locked, pad_count, _is_connector = info
        assert ref == "R1"
        assert x == pytest.approx(100.0)
        assert y == pytest.approx(100.0)
        assert pad_count == 1


# ---------------------------------------------------------------------------
# drc.repair_silkscreen
# ---------------------------------------------------------------------------


class TestRepairSilkscreenLegacyModuleBoard:
    """``drc/repair_silkscreen.py``'s ``SilkscreenRepairer`` walks the raw tree.

    Uses the modern ``(stroke (width ...))`` graphic encoding (the width
    format ``_get_stroke_width`` understands) inside a legacy ``module``
    block, isolating exactly the tag-alias fix under test (issue #4886)
    from the unrelated, pre-existing legacy bare-``(width ...)`` stroke
    format gap.
    """

    _BOARD = """(kicad_pcb
  (version 4)
  (host pcbnew "(2017-11-30)")
  (layers (0 F.Cu signal) (36 F.SilkS user))
  (net 0 "")
  (module R_0603 (layer F.Cu) (tedit 5A1F2B3C) (at 100 100)
    (fp_text reference R1 (at 0 1.5) (layer F.SilkS)
      (effects (font (size 0.5 0.5) (thickness 0.05))))
    (fp_line (start -1 -0.4) (end 1 -0.4)
      (stroke (width 0.05) (type solid)) (layer F.SilkS))
  )
)
"""

    def _repairer(self, tmp_path: Path):
        from kicad_tools.drc.repair_silkscreen import SilkscreenRepairer

        pcb_path = tmp_path / "legacy.kicad_pcb"
        pcb_path.write_text(self._BOARD, encoding="utf-8")
        return SilkscreenRepairer(pcb_path)

    def test_repair_line_widths_fixes_fp_line_inside_module(self, tmp_path: Path) -> None:
        repairer = self._repairer(tmp_path)

        # Before the fix, repair_line_widths's bare find_all("footprint")
        # saw zero footprints on a module-only board -- result.fixes == [].
        result = repairer.repair_line_widths(min_width_mm=0.15)

        assert len(result.fixes) == 1
        fix = result.fixes[0]
        assert fix.element_type == "fp_line"
        assert fix.footprint_ref == "R1"
        assert fix.old_width == pytest.approx(0.05)
        assert fix.new_width == pytest.approx(0.15)

    def test_repair_text_heights_fixes_fp_text_inside_module(self, tmp_path: Path) -> None:
        repairer = self._repairer(tmp_path)

        # Before the fix, repair_text_heights's bare find_all("footprint")
        # never reached the module's fp_text reference.
        result = repairer.repair_text_heights(min_height_mm=1.0)

        assert len(result.fixes) == 1
        fix = result.fixes[0]
        assert fix.footprint_ref == "R1"
        assert fix.old_height == pytest.approx(0.5)


# ---------------------------------------------------------------------------
# panel.panel
# ---------------------------------------------------------------------------


class TestPanelLegacyModuleBoard:
    """``panel/panel.py``'s ``Panel`` clones board content via a tag allowlist."""

    _BOARD = """(kicad_pcb (version 4) (host pcbnew "(2017-11-30)")
  (general (thickness 1.6))
  (page A4)
  (layers (0 F.Cu signal) (31 B.Cu signal) (44 Edge.Cuts user))
  (net 0 "")
  (net 1 GND)
  (gr_line (start 0 0) (end 20 0) (layer Edge.Cuts) (width 0.15))
  (gr_line (start 20 0) (end 20 10) (layer Edge.Cuts) (width 0.15))
  (gr_line (start 20 10) (end 0 10) (layer Edge.Cuts) (width 0.15))
  (gr_line (start 0 10) (end 0 0) (layer Edge.Cuts) (width 0.15))
  (module R_0603 (layer F.Cu) (tedit 5A1F2B3C) (at 5 5)
    (fp_text reference R1 (at 0 1.5) (layer F.SilkS))
    (pad 1 smd rect (at -0.8 0) (size 0.9 0.8) (layers F.Cu F.Paste F.Mask) (net 1 GND))
  )
)
"""

    def test_build_clones_module_footprints_into_panel(self, tmp_path: Path) -> None:
        pytest.importorskip("shapely", reason="Shapely required for panel tests")
        from kicad_tools.panel.panel import Panel

        pcb_path = tmp_path / "legacy.kicad_pcb"
        pcb_path.write_text(self._BOARD, encoding="utf-8")

        panel = Panel()
        panel.append_board(pcb_path, rows=1, cols=2, spacing=2.0)
        built = panel.build()

        # Before the fix, "module" was absent from _place_board_copy's
        # content_tags allowlist, so board content -- including every
        # component -- would be silently dropped from the panel output.
        module_nodes = [c for c in built.children if c.name == "module"]
        assert len(module_nodes) == 2  # one clone per board instance


# ---------------------------------------------------------------------------
# cli.runner
# ---------------------------------------------------------------------------


class TestCliRunnerLegacyModuleBoard:
    """``cli/runner.py``'s net-format helpers walk the raw, un-normalized input."""

    # A module pad with corrupted, name-only net format -- the exact shape
    # validate_net_format / _snapshot_element_nets look for.
    _BOARD = """(kicad_pcb (version 4) (host pcbnew "(2017-11-30)")
  (general (thickness 1.6))
  (page A4)
  (layers (0 F.Cu signal) (31 B.Cu signal))
  (net 0 "")
  (net 1 "GND")
  (module R_0603 (layer F.Cu) (tedit 5A1F2B3C) (at 5 5)
    (fp_text reference R1 (at 0 1.5) (layer F.SilkS))
    (pad 1 smd rect (at -0.8 0) (size 0.9 0.8) (layers F.Cu F.Paste F.Mask) (net "GND"))
  )
)
"""

    def test_validate_net_format_detects_corrupt_pad_inside_module(self, tmp_path: Path) -> None:
        from kicad_tools.cli.runner import validate_net_format

        pcb_path = tmp_path / "legacy.kicad_pcb"
        pcb_path.write_text(self._BOARD, encoding="utf-8")

        # Before the fix, this walk's bare "c.name == 'footprint'" filter
        # never reached the module's pad -- report.valid stayed True.
        report = validate_net_format(pcb_path)

        assert report.valid is False
        assert report.name_only_pads == 1

    def test_snapshot_element_nets_captures_module_pad_net(self, tmp_path: Path) -> None:
        from kicad_tools.cli.runner import _snapshot_element_nets

        pcb_path = tmp_path / "legacy.kicad_pcb"
        pcb_path.write_text(self._BOARD, encoding="utf-8")

        # Before the fix this returned {} for a module-only board -- no
        # snapshot meant _restore_net_declarations had nothing to restore
        # after kicad-cli stripped the pad's net assignment.
        snapshot = _snapshot_element_nets(pcb_path)

        assert "R1:1" in snapshot
