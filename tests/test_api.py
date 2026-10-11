from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from vn_id.api.app import app
from vn_id.core.config import EASYOCR_STORAGE_DIR, VIETOCR_WEIGHTS_PATH, QR_WEIGHTS_DIR

client = TestClient(app)


def test_api_health():
    res = client.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert "version" in data
    assert "device" in data
    for path in ("/api/v1/extract", "/api/v1/extract-both"):
        parameters = app.openapi()["paths"][path]["post"].get("parameters", [])
        assert parameters == []


@pytest.mark.parametrize("contents", [b"not an image", b""])
def test_api_rejects_invalid_image_with_client_error(contents):
    res = client.post(
        "/api/v1/extract",
        files={"file": ("broken.png", contents, "image/png")},
    )
    assert res.status_code == 400


def test_api_extracts_real_front_image():
    for package in ("easyocr", "vietocr", "qreader"):
        pytest.importorskip(package)
    for weight in (
        EASYOCR_STORAGE_DIR / "pretrained_ic15_res18.pt",
        VIETOCR_WEIGHTS_PATH,
        QR_WEIGHTS_DIR / "qrdet-s.pt",
    ):
        if not weight.is_file():
            pytest.skip(f"Model weight missing: {weight.name}")
    image_path = Path(__file__).resolve().parents[1] / "image/front_moi_1.jpg"
    if not image_path.is_file():
        pytest.skip("Sample image missing")
    with image_path.open("rb") as image:
        result = client.post("/api/v1/extract", files={"file": (image_path.name, image, "image/jpeg")})
    assert result.status_code == 200
    assert result.json()["data"]["id"] == "079183034888"

