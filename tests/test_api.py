import io
import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient
from vn_id.api.app import app

client = TestClient(app)

def _get_valid_png_bytes() -> bytes:
    img = np.zeros((100, 100, 3), dtype=np.uint8)
    _, buf = cv2.imencode(".png", img)
    return buf.tobytes()

def test_api_health():
    res = client.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert "version" in data
    assert "device" in data

def test_api_extract_single_mock():
    png_bytes = _get_valid_png_bytes()
    fake_img = io.BytesIO(png_bytes)
    res = client.post(
        "/api/v1/extract?mock=true",
        files={"file": ("front.png", fake_img, "image/png")}
    )
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["data"]["id"] == "001098012345"

def test_api_extract_both_mock():
    png_bytes = _get_valid_png_bytes()
    fake_front = io.BytesIO(png_bytes)
    fake_back = io.BytesIO(png_bytes)
    res = client.post(
        "/api/v1/extract-both?mock=true",
        files={
            "front": ("front.png", fake_front, "image/png"),
            "back": ("back.png", fake_back, "image/png")
        }
    )
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["data"]["id"] == "001098012345"
    assert data["data"]["issue_date"] == "24/06/2021"
    assert data["data"]["issue_loc"] == "Cục Cảnh sát Quản lý hành chính về trật tự xã hội"

