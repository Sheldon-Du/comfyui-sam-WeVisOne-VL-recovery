"""Use the installed supervision API for previews, including 0.6 releases."""

import inspect

import cv2
import numpy as np
from PIL import Image
import supervision as sv

from .vendor.wevisone_vl.visualization import (
    COLORS, SV_PALETTE, combined_alpha, parse_predictions, render_overlay as upstream_overlay,
)


def render_overlay(image, result, mask_threshold=None):
    if hasattr(sv, "LabelAnnotator") and "smart_position" in inspect.signature(sv.LabelAnnotator).parameters:
        return upstream_overlay(image, result, mask_threshold=mask_threshold)
    array = np.array(image.convert("RGB"), dtype=np.float32)
    alpha = combined_alpha(result.masks, image.width, image.height)
    if mask_threshold is not None:
        alpha = (alpha >= mask_threshold).astype(np.float32)
    weight = alpha[..., None] * 0.5
    array = np.uint8(array * (1 - weight) + np.array(COLORS[0]) * weight)
    predictions = parse_predictions(result.response, image.width, image.height)
    boxes, labels, classes = [], [], []
    for class_id, (label, items) in enumerate(predictions.items()):
        for item in items:
            if item["type"] == "box":
                boxes.append(item["coords"])
                labels.append(label)
                classes.append(class_id)
            elif item["type"] == "point":
                point = tuple(round(v) for v in item["coords"])
                cv2.circle(array, point, max(6, round(image.width / 85)), COLORS[class_id % len(COLORS)], -1)
    if boxes:
        detections = sv.Detections(xyxy=np.array(boxes, dtype=np.float32), class_id=np.array(classes))
        annotator = sv.BoxAnnotator(color=SV_PALETTE, thickness=max(2, round(image.width / 400)))
        if "labels" in inspect.signature(annotator.annotate).parameters:
            array = annotator.annotate(array, detections, labels=labels)
        else:
            array = annotator.annotate(array, detections)
            array = sv.LabelAnnotator(color=SV_PALETTE).annotate(array, detections, labels=labels)
    return Image.fromarray(array)
