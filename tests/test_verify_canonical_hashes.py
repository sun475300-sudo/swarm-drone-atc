from __future__ import annotations

import importlib
from pathlib import Path

import yaml


def test_run_cell_invokes_benchmark_cli(monkeypatch, tmp_path: Path) -> None:
    mod = importlib.import_module("scripts.reproduce.verify_canonical_hashes")
    monkeypatch.setattr(mod, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(mod, "MAIN_PY", tmp_path / "main.py")

    captured: dict[str, object] = {}

    def fake_run(cmd, cwd, check):
        captured["cmd"] = cmd
        captured["cwd"] = cwd
        captured["check"] = check
        out_path = tmp_path / "results" / "01_corridor_crossing" / "sdacs_hybrid" / "seed42.json"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text('{"ok": true}', encoding="utf-8")

    monkeypatch.setattr(mod.subprocess, "run", fake_run)

    out = mod._run_cell("01_corridor_crossing", "sdacs_hybrid", 42)

    assert out == tmp_path / "results" / "01_corridor_crossing" / "sdacs_hybrid" / "seed42.json"
    assert captured["cmd"] == [
        mod.sys.executable,
        str(tmp_path / "main.py"),
        "benchmark",
        "--scenario",
        "01_corridor_crossing",
        "--method",
        "sdacs_hybrid",
        "--seed",
        "42",
        "--output",
        str(out),
        "--hard-wall-s",
        "120",
        "--quiet",
    ]
    assert captured["cwd"] == tmp_path
    assert captured["check"] is True


def test_verify_skips_pending_and_fails_on_mismatch(monkeypatch, tmp_path: Path) -> None:
    mod = importlib.import_module("scripts.reproduce.verify_canonical_hashes")

    def fake_run_cell(scenario: str, method: str, seed: int) -> Path:
        out = tmp_path / f"{scenario}-{method}-{seed}.json"
        out.write_text(f"{scenario}:{method}:{seed}", encoding="utf-8")
        return out

    monkeypatch.setattr(mod, "_run_cell", fake_run_cell)

    good_path = fake_run_cell("01_corridor_crossing", "sdacs_hybrid", 42)
    manifest = {
        "cells": [
            {
                "scenario": "01_corridor_crossing",
                "method": "sdacs_hybrid",
                "seed": 42,
                "status": "pinned",
                "sha256": mod._sha256(good_path),
            },
            {
                "scenario": "02_dense_intersection",
                "method": "sdacs_hybrid",
                "seed": 0,
                "status": "pinned",
                "sha256": "deadbeef",
            },
            {
                "scenario": "07_communication_loss",
                "method": "sdacs_hybrid",
                "seed": 7,
                "status": "pending",
                "sha256": None,
            },
        ]
    }

    rc = mod._verify(manifest)
    assert rc == 1


def test_capture_pins_pending_entries(monkeypatch, tmp_path: Path) -> None:
    mod = importlib.import_module("scripts.reproduce.verify_canonical_hashes")
    manifest_path = tmp_path / "canonical_hashes.yaml"
    monkeypatch.setattr(mod, "_git_head", lambda: "abc123")

    def fake_run_cell(scenario: str, method: str, seed: int) -> Path:
        out = tmp_path / "results" / scenario / method / f"seed{seed}.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(f"{scenario}:{method}:{seed}", encoding="utf-8")
        return out

    monkeypatch.setattr(mod, "_run_cell", fake_run_cell)
    manifest = {
        "cells": [
            {
                "scenario": "01_corridor_crossing",
                "method": "sdacs_hybrid",
                "seed": 42,
                "status": "pending",
                "sha256": None,
                "captured_on": None,
                "captured_commit": None,
            }
        ]
    }

    rc = mod._capture(manifest, manifest_path)

    assert rc == 0
    written = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    cell = written["cells"][0]
    assert cell["status"] == "pinned"
    assert cell["sha256"] == mod._sha256(
        tmp_path / "results" / "01_corridor_crossing" / "sdacs_hybrid" / "seed42.json"
    )
    assert cell["captured_commit"] == "abc123"
    assert cell["captured_on"]


def test_load_manifest_returns_none_on_invalid_yaml(tmp_path: Path) -> None:
    mod = importlib.import_module("scripts.reproduce.verify_canonical_hashes")
    manifest_path = tmp_path / "bad.yaml"
    manifest_path.write_text("cells: [broken", encoding="utf-8")

    assert mod._load_manifest(manifest_path) is None
