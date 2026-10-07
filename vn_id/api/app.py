"""FastAPI REST Service for VN_ID CCCD extraction pipeline."""
from typing import Annotated
from fastapi import FastAPI, File, UploadFile, Query
from vn_id.core.schemas import FinalCCCDResult
from vn_id.pipeline import CCCDPipeline
import vn_id

app = FastAPI(
    title="VN_ID CCCD Extraction API",
    version=vn_id.__version__,
    description="API trích xuất và đối soát thông tin Căn cước công dân đa định dạng 2 mặt.",
)

# Cached pipeline instances
_real_pipeline: CCCDPipeline | None = None
_mock_pipeline: CCCDPipeline | None = None


def get_pipeline(mock: bool = False) -> CCCDPipeline:
    global _real_pipeline, _mock_pipeline
    if mock:
        if _mock_pipeline is None:
            _mock_pipeline = CCCDPipeline(mock_mode=True)
        return _mock_pipeline
    else:
        if _real_pipeline is None:
            _real_pipeline = CCCDPipeline(mock_mode=False)
        return _real_pipeline


@app.get("/health", summary="Health check")
def health():
    pipeline = get_pipeline(mock=False)
    return {
        "status": "ok",
        "version": vn_id.__version__,
        "device": pipeline.device,
    }


@app.post("/api/v1/extract", response_model=FinalCCCDResult, summary="Trích xuất ảnh CCCD 1 mặt")
async def extract_single(
    file: Annotated[UploadFile, File(description="File ảnh mặt trước hoặc mặt sau")],
    mock: Annotated[bool, Query(description="Chế độ giả lập (mock) để test nhanh")] = False,
):
    pipeline = get_pipeline(mock=mock)
    image_bytes = await file.read()
    result = pipeline.process(image_bytes)
    return result


@app.post("/api/v1/extract-both", response_model=FinalCCCDResult, summary="Trích xuất đồng thời 2 mặt CCCD")
async def extract_both(
    front: Annotated[UploadFile, File(description="Ảnh mặt trước CCCD")],
    back: Annotated[UploadFile, File(description="Ảnh mặt sau CCCD")],
    mock: Annotated[bool, Query(description="Chế độ giả lập (mock) để test nhanh")] = False,
):
    pipeline = get_pipeline(mock=mock)
    front_bytes = await front.read()
    back_bytes = await back.read()
    result = pipeline.process_both_sides(front_image=front_bytes, back_image=back_bytes)
    return result

