"""Convert ComfyUI coordinates to the upstream inference contract."""

import json
import math


TASKS = (
    "detection", "referring", "point", "count_box", "count_point", "ocr",
    "ocr_grounding", "segmentation", "matting", "visual_prompt", "freeform",
    "box_matting",
)


def boxes_per_image(bboxes, batch_size):
    """Accept native BOUNDING_BOX dict, shared boxes, or per-image boxes."""
    if bboxes is None or bboxes == []:
        return [[] for _ in range(batch_size)]
    if isinstance(bboxes, dict):
        frames = [[bboxes]]
    elif isinstance(bboxes, list) and isinstance(bboxes[0], dict):
        frames = [bboxes]
    else:
        frames = bboxes
    if len(frames) == 1:
        frames = frames * batch_size
    if len(frames) != batch_size:
        raise ValueError("The box batch size must be 1 or match the image batch size.")
    converted = []
    for frame in frames:
        coords = []
        for box in frame:
            x, y, w, h = (float(box[k]) for k in ("x", "y", "width", "height"))
            if not all(math.isfinite(v) for v in (x, y, w, h)) or w <= 0 or h <= 0:
                raise ValueError("Box coordinates must be finite, with width and height greater than 0.")
            coords.append([x, y, x + w, y + h])
        converted.append(coords)
    return converted


def parse_points(positive, negative):
    points, labels = [], []
    for text, label in ((positive, 1), (negative, 0)):
        for item in json.loads(text or "[]"):
            pair = [float(item["x"]), float(item["y"])]
            if not all(math.isfinite(v) for v in pair):
                raise ValueError("Point coordinates must be finite pixel coordinates.")
            points.append(pair)
            labels.append(label)
    if not points:
        raise ValueError("point mode requires at least one click coordinate.")
    return points, labels


def native_boxes(predictions):
    return [
        {"x": p["coords"][0], "y": p["coords"][1],
         "width": p["coords"][2] - p["coords"][0],
         "height": p["coords"][3] - p["coords"][1], "label": label}
        for label, items in predictions.items() for p in items if p["type"] == "box"
    ]
