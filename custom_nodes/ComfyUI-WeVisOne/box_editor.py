"""Reuse ComfyUI's BOUNDING_BOXES canvas and coordinate conversion helpers."""

import nodes
from comfy_api.latest import io
from comfy_extras.nodes_bounding_boxes import boxes_to_regions, fractions_to_bbox_frame


class WeVisOneBoxEditor(io.ComfyNode):
    @classmethod
    def define_schema(cls):
        return io.Schema(
            node_id="WeVisOneBoxEditor",
            display_name="WeVisOne · Image Box Editor",
            category="WeVisOne",
            description="Connect an image and drag to draw boxes. Drag edges to resize; press Delete to remove the selected box. Coordinates map back to the original image.",
            inputs=[
                io.Image.Input("background", display_name="Image", tooltip="Image shown on the canvas. The first image is displayed for a batch."),
                io.Int.Input("width", display_name="Canvas width", default=1024, min=16, max=16384, step=16, tooltip="Canvas width managed by the native editor. Output boxes are rescaled to the original image width."),
                io.Int.Input("height", display_name="Canvas height", default=1024, min=16, max=16384, step=16, tooltip="Canvas height managed by the native editor. Output boxes are rescaled to the original image height."),
                io.BoundingBoxes.Input("editor_state", display_name="Boxes", default=[],
                                       tooltip="Drag on the image to draw one or more boxes. Text, descriptions and colors are optional."),
            ],
            outputs=[io.BoundingBox.Output("bboxes", tooltip="Native boxes mapped to original-image pixels. The same selection is shared across an image batch.")],
            is_output_node=True,
        )

    @classmethod
    def execute(cls, background, width, height, editor_state):
        if width <= 0 or height <= 0:
            raise ValueError("Box editor canvas dimensions must be greater than 0.")
        image_height, image_width = background.shape[1:3]
        regions = boxes_to_regions(editor_state or [], width, height)
        boxes = fractions_to_bbox_frame(regions, image_width, image_height)
        saved = nodes.PreviewImage().save_images(background[:1], "wevisone.boxes.background")
        return io.NodeOutput(boxes, ui={"background_images": saved["ui"]["images"]})
