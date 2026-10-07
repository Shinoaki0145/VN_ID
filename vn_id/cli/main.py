"""Command-line interface (CLI) for VN_ID pipeline."""
import json
import os
import sys
import click
from vn_id.pipeline import CCCDPipeline
import vn_id


@click.group()
@click.version_option(version=vn_id.__version__)
def cli():
    """VN_ID: Công cụ trích xuất CCCD đa định dạng 2 mặt."""
    pass


@cli.command("extract")
@click.argument("image", required=False, type=click.Path(exists=True))
@click.option("--front", type=click.Path(exists=True), help="Đường dẫn ảnh mặt trước")
@click.option("--back", type=click.Path(exists=True), help="Đường dẫn ảnh mặt sau")
@click.option("--output", "-o", type=click.Path(), help="Đường dẫn file JSON xuất kết quả")
@click.option("--mock", is_flag=True, default=False, help="Chạy ở chế độ Mock giả lập để test nhanh")
@click.option("--device", default="auto", help="Thiết bị xử lý: 'auto', 'cpu', 'cuda'")
def extract(image, front, back, output, mock, device):
    """Trích xuất thông tin từ ảnh CCCD (1 ảnh đơn hoặc cặp 2 mặt)."""
    pipeline = CCCDPipeline(device=device, mock_mode=mock)

    if front and back:
        result = pipeline.process_both_sides(front_image=front, back_image=back)
    elif image:
        result = pipeline.process(image)
    elif front:
        from vn_id.core.schemas import CardSide
        result = pipeline.process(front, force_side=CardSide.FRONT)
    elif back:
        from vn_id.core.schemas import CardSide
        result = pipeline.process(back, force_side=CardSide.BACK)
    else:
        click.echo("Lỗi: Vui lòng cung cấp ít nhất 1 ảnh (hoặc --front và --back).", err=True)
        sys.exit(1)

    result_dict = result.model_dump()

    if output:
        with open(output, "w", encoding="utf-8") as f:
            json.dump(result_dict, f, ensure_ascii=False, indent=2)
        click.echo(f"Đã lưu kết quả thành công vào: {output}")
    else:
        click.echo(json.dumps(result_dict, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    cli()
