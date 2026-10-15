"""Run inside the service: sudo docker compose exec -T vn-id python < scripts/check_docker_gpu.py

Loads OCR models in a separate process; allow free GPU memory before running.
Exceptions are intentionally not caught so the failing stage has a traceback.
"""
import hashlib
from importlib.metadata import version
from pathlib import Path

import numpy as np
from PIL import Image
import torch
from torchvision.ops import deform_conv2d

import vn_id


def main():
    for package in ("torch", "torchvision", "easyocr", "vietocr", "qreader"):
        print(package, version(package), flush=True)
    root = Path(vn_id.__file__).parent
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*.py")):
        digest.update(str(path.relative_to(root)).encode())
        digest.update(path.read_bytes())
    print("Source SHA256:", digest.hexdigest(), flush=True)
    print("CUDA runtime:", torch.version.cuda, flush=True)
    assert torch.cuda.is_available(), "FAIL: PyTorch cannot access NVIDIA GPU"
    print("GPU:", torch.cuda.get_device_name(0), flush=True)
    x = torch.randn(1, 1, 5, 5, device="cuda")
    weight = torch.randn(1, 1, 3, 3, device="cuda")
    offset = torch.zeros(1, 18, 3, 3, device="cuda")
    assert deform_conv2d(x, offset, weight).is_cuda
    torch.cuda.synchronize()
    print("PASS: torchvision CUDA convolution", flush=True)

    from vn_id.ocr import OCREngine
    engine = OCREngine(device="cuda")
    print("Loading DBNet (legacy EasyOCR import warnings may appear)...", flush=True)
    reader = engine._get_detector()
    assert next(reader.detector.model.parameters()).is_cuda, "FAIL: DBNet is on CPU"
    # Call models directly: engine.recognize() catches errors and returns empty OCR.
    reader.detect(np.full((320, 512, 3), 255, dtype=np.uint8), canvas_size=320)
    torch.cuda.synchronize()
    print("PASS: DBNet CUDA inference", flush=True)

    print("Loading VietOCR...", flush=True)
    recognizer = engine._get_recognizer()
    assert next(recognizer.model.parameters()).is_cuda, "FAIL: VietOCR is on CPU"
    recognizer.predict(Image.new("RGB", (160, 48), "white"))
    torch.cuda.synchronize()
    print("PASS: VietOCR CUDA inference", flush=True)
    print("GPU checks passed. Real-image accuracy and SSH forwarding are separate checks.", flush=True)


if __name__ == "__main__":
    main()
