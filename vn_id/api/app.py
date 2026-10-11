"""FastAPI REST Service for VN_ID CCCD extraction pipeline."""
from typing import Annotated
from fastapi import FastAPI, File, UploadFile, HTTPException
from vn_id.core.schemas import FinalCCCDResult
from vn_id.pipeline import CCCDPipeline
import vn_id

app = FastAPI(
    title="VN_ID CCCD Extraction API",
    version=vn_id.__version__,
    description="API trích xuất và đối soát thông tin Căn cước công dân đa định dạng 2 mặt.",
)

# Cached pipeline instance
_pipeline: CCCDPipeline | None = None


def get_pipeline() -> CCCDPipeline:
    global _pipeline
    if _pipeline is None:
        _pipeline = CCCDPipeline()
    return _pipeline


@app.get("/health", summary="Health check")
def health():
    pipeline = get_pipeline()
    return {
        "status": "ok",
        "version": vn_id.__version__,
        "device": pipeline.device,
    }


@app.post("/api/v1/extract", response_model=FinalCCCDResult, summary="Trích xuất ảnh CCCD 1 mặt")
def extract_single(
    file: Annotated[UploadFile, File(description="File ảnh mặt trước hoặc mặt sau")],
):
    pipeline = get_pipeline()
    try:
        image = pipeline.load_image(file.file.read())
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return pipeline.process(image)


@app.post("/api/v1/extract-both", response_model=FinalCCCDResult, summary="Trích xuất đồng thời 2 mặt CCCD")
def extract_both(
    front: Annotated[UploadFile, File(description="Ảnh mặt trước CCCD")],
    back: Annotated[UploadFile, File(description="Ảnh mặt sau CCCD")],
):
    pipeline = get_pipeline()
    try:
        front_image = pipeline.load_image(front.file.read())
        back_image = pipeline.load_image(back.file.read())
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return pipeline.process_both_sides(front_image=front_image, back_image=back_image)

