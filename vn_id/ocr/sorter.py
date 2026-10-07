"""Reading order sorting algorithm for OCR boxes."""
import time
from vn_id.core.config import LINE_GROUPING_THRESHOLD_PX
from vn_id.core.schemas import TextBox, OCRResult


class ReadingOrderSorter:
    """Sorts detected text bounding boxes in natural reading order (top-to-bottom, left-to-right)."""

    def __init__(self, y_threshold: int = LINE_GROUPING_THRESHOLD_PX):
        self.y_threshold = y_threshold

    def _group_and_sort_lines(self, boxes: list[TextBox]) -> list[list[TextBox]]:
        """Groups bounding boxes into lines based on y_threshold and sorts each line left-to-right."""
        if not boxes:
            return []

        def get_y_center(b: TextBox) -> float:
            return (b.bbox[1] + b.bbox[3]) / 2.0

        def get_x_min(b: TextBox) -> float:
            return float(b.bbox[0])

        sorted_by_y = sorted(boxes, key=get_y_center)
        lines: list[list[TextBox]] = []
        for box in sorted_by_y:
            placed = False
            b_yc = get_y_center(box)
            for line in lines:
                line_yc = sum(get_y_center(b) for b in line) / len(line)
                if abs(b_yc - line_yc) <= self.y_threshold:
                    line.append(box)
                    placed = True
                    break
            if not placed:
                lines.append([box])

        lines.sort(key=lambda line: sum(get_y_center(b) for b in line) / len(line))
        for line in lines:
            line.sort(key=get_x_min)
        return lines

    def sort_boxes(self, boxes: list[TextBox]) -> OCRResult:
        """Groups bounding boxes into lines and sorts them taking column layout into account."""
        start_time = time.time()
        if not boxes:
            return OCRResult(boxes=[], full_text="", time_taken_ms=0.0)

        max_x = max(b.bbox[2] for b in boxes)
        max_y = max(b.bbox[3] for b in boxes)

        # Detect two-column layout in bottom half (e.g. CCCD front: expiry date under portrait vs right info)
        left_col_boxes = [
            b for b in boxes
            if b.bbox[2] <= 0.35 * max_x and b.bbox[1] >= 0.45 * max_y
        ]
        has_right_col = any(
            b.bbox[0] >= 0.30 * max_x and b.bbox[1] >= 0.45 * max_y
            for b in boxes
        )

        if left_col_boxes and has_right_col:
            main_boxes = [b for b in boxes if b not in left_col_boxes]
            all_lines = self._group_and_sort_lines(main_boxes) + self._group_and_sort_lines(left_col_boxes)
        else:
            all_lines = self._group_and_sort_lines(boxes)

        ordered_boxes: list[TextBox] = []
        line_texts: list[str] = []

        for line_idx, line in enumerate(all_lines, start=1):
            for b in line:
                b.line_number = line_idx
                ordered_boxes.append(b)
            line_text = " ".join(b.text.strip() for b in line if b.text.strip())
            if line_text:
                line_texts.append(line_text)

        full_text = "\n".join(line_texts)
        duration_ms = (time.time() - start_time) * 1000.0

        return OCRResult(
            boxes=ordered_boxes,
            full_text=full_text,
            time_taken_ms=duration_ms,
        )

