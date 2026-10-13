"""Use installed torchvision kernels for EasyOCR DBNet inference.

EasyOCR 1.7's custom extensions depend on old PyTorch C++ APIs. The native
torchvision operator supports the same weights, offsets and modulation mask
on CPU and CUDA, without compiling a separate extension at startup.
"""


def _deform_conv(image, offset, weight, stride, padding, dilation, *_):
    from torchvision.ops import deform_conv2d
    return deform_conv2d(image, offset, weight, stride=stride,
                         padding=padding, dilation=dilation)


def _modulated_deform_conv(image, offset, mask, weight, bias, stride, padding, dilation, *_):
    from torchvision.ops import deform_conv2d
    return deform_conv2d(image, offset, weight, bias, stride=stride,
                         padding=padding, dilation=dilation, mask=mask)


def use_torchvision_ops():
    from importlib import import_module
    modules = import_module("easyocr.DBNet.assets.ops.dcn.modules.deform_conv")
    # All DBNet convolution layers, including the packed variants, call these
    # module globals. torchvision infers convolution/offset groups from shapes.
    modules.deform_conv = _deform_conv
    modules.modulated_deform_conv = _modulated_deform_conv
