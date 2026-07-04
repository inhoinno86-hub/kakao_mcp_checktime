from __future__ import annotations

from pathlib import Path

from checktime_mcp import data_loader


def test_get_data_dir_falls_back_to_cwd_data(monkeypatch, tmp_path: Path) -> None:
    installed_default = tmp_path / "venv" / "lib" / "python3.14" / "data"
    cwd_data = tmp_path / "data"
    cwd_data.mkdir()

    monkeypatch.delenv("CHECKTIME_MCP_DATA_DIR", raising=False)
    monkeypatch.setattr(data_loader, "DEFAULT_DATA_DIR", installed_default)
    monkeypatch.chdir(tmp_path)

    assert data_loader.get_data_dir() == cwd_data.resolve()
