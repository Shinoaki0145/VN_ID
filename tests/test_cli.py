import json
import cv2
import numpy as np
import pytest
from click.testing import CliRunner
from vn_id.cli.main import cli

def _get_valid_png_bytes() -> bytes:
    img = np.zeros((100, 100, 3), dtype=np.uint8)
    _, buf = cv2.imencode(".png", img)
    return buf.tobytes()

def test_cli_help():
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "extract" in result.output

def test_cli_extract_mock_single(tmp_path):
    img_file = tmp_path / "test.png"
    img_file.write_bytes(_get_valid_png_bytes())
    
    out_file = tmp_path / "out.json"
    runner = CliRunner()
    result = runner.invoke(cli, ["extract", str(img_file), "--mock", "--output", str(out_file)])
    assert result.exit_code == 0
    assert out_file.exists()
    
    data = json.loads(out_file.read_text())
    assert data["success"] is True
    assert data["data"]["id"] == "001098012345"

def test_cli_extract_mock_both(tmp_path):
    front_file = tmp_path / "front.png"
    back_file = tmp_path / "back.png"
    png_bytes = _get_valid_png_bytes()
    front_file.write_bytes(png_bytes)
    back_file.write_bytes(png_bytes)
    
    runner = CliRunner()
    result = runner.invoke(cli, ["extract", "--front", str(front_file), "--back", str(back_file), "--mock"])
    assert result.exit_code == 0
    assert "001098012345" in result.output
    assert "Cục Cảnh sát Quản lý hành chính về trật tự xã hội" in result.output

