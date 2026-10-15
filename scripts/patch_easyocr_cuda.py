"""Update EasyOCR DBNet's CUDA dispatch calls for current PyTorch.

Run with the project interpreter after installing/reinstalling EasyOCR:
    uv run python scripts/patch_easyocr_cuda.py
"""

from importlib.metadata import distribution
from pathlib import Path
import re


def patch_dispatch(source: str) -> str:
    return re.sub(
        r"(AT_DISPATCH_FLOATING_TYPES_AND_HALF\(\s*\w+)\.type\(\)",
        r"\1.scalar_type()",
        source,
    )


def main() -> None:
    # Locate package data without importing EasyOCR (which can trigger compilation).
    root = Path(distribution("easyocr").locate_file("easyocr/DBNet/assets/ops/dcn/src"))
    for name in ("deform_conv_cuda_kernel.cu", "deform_pool_cuda_kernel.cu"):
        path = root / name
        original = path.read_text(encoding="utf-8")
        updated = patch_dispatch(original)
        if updated != original:
            path.write_text(updated, encoding="utf-8")
            print(f"Patched {name}")
        else:
            print(f"No legacy CUDA dispatch calls in {name}")


if __name__ == "__main__":
    main()
