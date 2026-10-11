"""Run extraction on chosen sample images."""
import argparse
from pathlib import Path

from vn_id import CCCDPipeline, CardSide


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Run VN_ID on one or two card images")
    parser.add_argument("--front", type=Path)
    parser.add_argument("--back", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--device", default="auto", choices=("auto", "cpu", "cuda"))
    args = parser.parse_args(argv)

    pipeline = CCCDPipeline(device=args.device)
    if args.front and args.back:
        result = pipeline.process_both_sides(str(args.front), str(args.back))
    elif args.front:
        result = pipeline.process(str(args.front), force_side=CardSide.FRONT)
    elif args.back:
        result = pipeline.process(str(args.back), force_side=CardSide.BACK)
    else:
        result = pipeline.process_both_sides("image/front_moi_1.jpg", "image/back_moi_1.jpg")
    report = result.model_dump_json(indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(report + "\n", encoding="utf-8")
        print(f"Saved {args.output}")
    else:
        print(report)


if __name__ == "__main__":
    main()
