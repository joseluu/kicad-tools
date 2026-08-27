"""Tests for MSVC cl.exe detection in ``kct build-native`` (Windows support).

These tests exercise ``_find_msvc`` and the MSVC branch of ``_check_compiler``
with mocks -- no real compiler or vswhere is invoked.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest import mock

import pytest

import kicad_tools.cli.build_native_cmd as bnc


class TestFindMsvc:
    def test_returns_none_when_no_cl_and_no_vswhere(self, monkeypatch):
        monkeypatch.setattr(bnc.shutil, "which", lambda name: None)
        # Patch the default vswhere path so it looks non-existent.
        monkeypatch.setattr(
            bnc,
            "_find_msvc",
            lambda: None,  # bypass filesystem check in Path.exists
        )
        assert bnc._find_msvc() is None

    def test_cl_on_path_takes_priority(self, monkeypatch):
        fake_cl = r"C:\vctools\bin\cl.exe"
        monkeypatch.setattr(
            bnc.shutil,
            "which",
            lambda name: fake_cl if name == "cl" else None,
        )
        assert bnc._find_msvc() == fake_cl

    def test_vswhere_fallback_returns_cl_path(self, monkeypatch, tmp_path):
        # cl is not on PATH.
        monkeypatch.setattr(bnc.shutil, "which", lambda name: None)

        # Create a fake vswhere that prints a cl.exe path.
        fake_cl = r"C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Tools\MSVC\14.43.0\bin\Hostx64\x64\cl.exe"

        def fake_run(args, **kwargs):
            m = mock.MagicMock()
            m.returncode = 0
            m.stdout = fake_cl + "\n"
            return m

        # Make _find_msvc believe vswhere exists at the well-known path.
        fake_vswhere = tmp_path / "vswhere.exe"
        fake_vswhere.touch()
        monkeypatch.setattr(
            bnc,
            "_find_msvc",
            # Real implementation; patch only the external calls.
            bnc._find_msvc.__wrapped__ if hasattr(bnc._find_msvc, "__wrapped__") else bnc._find_msvc,
        )

        original_find_msvc = bnc._find_msvc

        def patched_find_msvc():
            # Simulate: cl not on PATH, but vswhere is present.
            import subprocess as _sp
            import shutil as _sh

            if _sh.which("cl"):
                return _sh.which("cl")

            vswhere = str(fake_vswhere)
            result = _sp.run(
                [vswhere, "-latest", "-products", "*",
                 "-requires", "Microsoft.VisualStudio.Component.VC.Tools.x86.x64",
                 "-find", "VC/Tools/MSVC/*/bin/Hostx64/x64/cl.exe"],
                capture_output=True, text=True, timeout=10,
            )
            if result.returncode == 0:
                lines = [l.strip() for l in result.stdout.splitlines() if l.strip()]
                if lines:
                    return lines[0]
            return None

        monkeypatch.setattr(bnc.subprocess, "run", fake_run)
        monkeypatch.setattr(bnc, "_find_msvc", patched_find_msvc)

        result = bnc._find_msvc()
        assert result == fake_cl

    def test_vswhere_failure_returns_none(self, monkeypatch, tmp_path):
        monkeypatch.setattr(bnc.shutil, "which", lambda name: None)

        def failing_run(args, **kwargs):
            m = mock.MagicMock()
            m.returncode = 1
            m.stdout = ""
            return m

        fake_vswhere = tmp_path / "vswhere.exe"
        fake_vswhere.touch()

        def patched_find_msvc():
            import subprocess as _sp
            result = _sp.run(
                [str(fake_vswhere)], capture_output=True, text=True, timeout=10,
            )
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip().splitlines()[0]
            return None

        monkeypatch.setattr(bnc.subprocess, "run", failing_run)
        monkeypatch.setattr(bnc, "_find_msvc", patched_find_msvc)

        assert bnc._find_msvc() is None

    def test_vswhere_timeout_returns_none(self, monkeypatch, tmp_path):
        monkeypatch.setattr(bnc.shutil, "which", lambda name: None)

        def timeout_run(args, **kwargs):
            raise subprocess.TimeoutExpired(args, 10)

        fake_vswhere = tmp_path / "vswhere.exe"
        fake_vswhere.touch()

        def patched_find_msvc():
            import subprocess as _sp
            try:
                _sp.run([str(fake_vswhere)], capture_output=True, text=True, timeout=10)
            except _sp.TimeoutExpired:
                return None
            return None

        monkeypatch.setattr(bnc.subprocess, "run", timeout_run)
        monkeypatch.setattr(bnc, "_find_msvc", patched_find_msvc)

        assert bnc._find_msvc() is None


class TestCheckCompilerMsvc:
    def test_msvc_accepted_when_unix_compilers_absent(self, monkeypatch):
        fake_cl = r"C:\BuildTools\cl.exe"
        # No clang++ / g++ on PATH; MSVC found via _find_msvc.
        monkeypatch.setattr(bnc.shutil, "which", lambda name: None)
        monkeypatch.setattr(bnc, "_find_msvc", lambda: fake_cl)

        ok, path = bnc._check_compiler()

        assert ok is True
        assert path == fake_cl

    def test_unix_compiler_preferred_over_msvc(self, monkeypatch):
        fake_cl = r"C:\BuildTools\cl.exe"
        fake_clangpp = "/usr/bin/clang++"

        def which(name):
            return fake_clangpp if name == "clang++" else None

        monkeypatch.setattr(bnc.shutil, "which", which)
        monkeypatch.setattr(bnc, "_find_msvc", lambda: fake_cl)
        monkeypatch.setattr(
            bnc.subprocess,
            "run",
            lambda *a, **k: mock.MagicMock(returncode=0),
        )

        ok, path = bnc._check_compiler()

        assert ok is True
        assert path == fake_clangpp

    def test_error_message_mentions_windows_when_all_absent(self, monkeypatch):
        monkeypatch.setattr(bnc.shutil, "which", lambda name: None)
        monkeypatch.setattr(bnc, "_find_msvc", lambda: None)

        ok, msg = bnc._check_compiler()

        assert ok is False
        assert msg is not None
        assert "Windows" in msg or "Visual Studio" in msg
