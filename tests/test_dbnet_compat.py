"""DBNet inference must not require EasyOCR's custom C++/CUDA extensions."""
import pytest


@pytest.mark.parametrize("modulated", [False, True])
def test_dbnet_uses_native_convolution_without_custom_extensions(modulated, monkeypatch):
    torch = pytest.importorskip("torch")
    easyocr = pytest.importorskip("easyocr")
    from easyocr.DBNet.assets.ops.dcn.functions import deform_conv as functions
    from easyocr.DBNet.assets.ops.dcn.modules.deform_conv import DeformConv, ModulatedDeformConv
    from vn_id.ocr import OCREngine

    monkeypatch.setattr(functions, "dcn_cpu_ready", False)
    monkeypatch.setattr(functions, "dcn_cuda_ready", False, raising=False)
    # Make failure explicit even if the developer's site-packages were patched.
    import easyocr.DBNet.assets.ops.dcn.modules.deform_conv as modules
    def unavailable(*args, **kwargs):
        raise RuntimeError("Custom EasyOCR extension is unavailable")
    monkeypatch.setattr(modules, "deform_conv", unavailable)
    monkeypatch.setattr(modules, "modulated_deform_conv", unavailable)
    layer = (ModulatedDeformConv if modulated else DeformConv)(
        4, 4, 3, stride=2, padding=2, dilation=2, groups=2, deformable_groups=2,
    )
    # Avoid model downloads while exercising the engine's initialization hook.
    monkeypatch.setattr(easyocr, "Reader", lambda *args, **kwargs: layer)
    layer = OCREngine(device="cpu")._get_detector()
    image = torch.randn(1, 4, 5, 5)
    offset = torch.zeros(1, 36, 3, 3)
    mask = torch.full((1, 18, 3, 3), .25)
    with torch.no_grad():
        actual = layer(image, offset, mask) if modulated else layer(image, offset)
        expected = torch.nn.functional.conv2d(
            image, layer.weight, stride=2, padding=2, dilation=2, groups=2,
        )
        if modulated:
            expected = expected * .25 + layer.bias.reshape(1, -1, 1, 1)
    torch.testing.assert_close(actual, expected)
