import json

import torch
import torch.nn.functional as F
from comfy_api.latest import io

from .backend import run_inference
from .model_paths import MODEL_ROOT, discover_models, resolve_model, sam2_models
from .contracts import TASKS, boxes_per_image, parse_points


class WeVisOnePerception(io.ComfyNode):
    @classmethod
    def define_schema(cls):
        return io.Schema(
            node_id="WeVisOnePerception", display_name="WeVisOne · Unified Perception", category="WeVisOne",
            description="Detection, OCR, segmentation and alpha matting with the official WeVisOne-VL model.",
            inputs=[
                io.Image.Input("images", display_name="Images", tooltip="Input images. A batch is processed one image at a time."),
                io.Combo.Input("model_name", display_name="Model", options=list(discover_models()) or ["Download a WeVisOne-VL model first"], tooltip="Select a complete local model directory, including mask_decoder.pt. See README for downloads."),
                io.Combo.Input("task", display_name="Task", options=list(TASKS), default="matting", tooltip="Choose the perception task. Task values are stable identifiers used by saved workflows."),
                io.String.Input("query", display_name="Query", default="person", multiline=True, tooltip="One category per line, or a complete referring expression. In freeform mode, this is the raw prompt."),
                io.BoundingBox.Input("bboxes", display_name="Boxes", optional=True, force_input=True, socketless=False, tooltip="Native pixel-space boxes. visual_prompt finds similar objects; box_matting mattes the supplied boxes."),
                io.Combo.Input("device", display_name="Device", options=["auto", "cpu"], default="auto", advanced=True, tooltip="auto uses the device selected by ComfyUI; cpu forces CPU inference."),
                io.Combo.Input("dtype", display_name="dtype", options=["bfloat16", "float16", "float32"], default="bfloat16", advanced=True, tooltip="Model computation precision. CPU inference uses float32."),
                io.Int.Input("max_pixels", display_name="Max image pixels", default=1024 * 1024, min=16 * 1024, max=16777216, step=1024, advanced=True, tooltip="Maximum image pixels used by the VLM processor. Higher values can use more VRAM."),
                io.Int.Input("max_new_tokens", display_name="Max new Tokens", default=4096, min=1, max=32768, advanced=True, tooltip="Maximum number of generated Tokens. Dense detections or OCR may need a higher limit."),
                io.Int.Input("decoder_batch_size", display_name="Decoder batch size", default=1, min=1, max=128, advanced=True, tooltip="Number of object masks decoded together. Lower values reduce peak VRAM use."),
                io.Float.Input("temperature", display_name="Temperature", default=0.0, min=0.0, max=2.0, step=0.05, advanced=True, tooltip="0 uses greedy decoding. Values above 0 enable random sampling."),
                io.Int.Input("seed", display_name="Seed", default=0, min=0, max=0xFFFFFFFF, control_after_generate=True, advanced=True, tooltip="Random seed for sampling. With temperature 0, greedy decoding does not use sampling randomness."),
            ],
            outputs=[
                io.Image.Output("preview", tooltip="Visualization of predicted boxes, points, labels and masks."),
                io.Mask.Output("mask", tooltip="One merged mask per input image. White is foreground; matting preserves continuous alpha."),
                io.BoundingBox.Output("bboxes", tooltip="Native pixel-space boxes, grouped by input image."),
                io.String.Output("response", is_output_list=True, tooltip="Unmodified model response, one string per input image."),
                io.String.Output("result_json", is_output_list=True, tooltip="Structured coordinates, counts, prompt and response, one JSON string per input image."),
                io.Mask.Output("instance_masks", is_output_list=True, tooltip="One instance MASK batch per image. It is empty when no instance is found; see instance_count in the JSON."),
            ],
        )

    @classmethod
    def execute(cls, images, model_name, task, query, bboxes=None, device="auto", dtype="bfloat16",
                max_pixels=1024 * 1024, max_new_tokens=4096, decoder_batch_size=1, temperature=0.0, seed=0):
        if task not in TASKS:
            raise ValueError(f"Unknown task: {task}")
        boxes = boxes_per_image(bboxes, len(images))
        if task in {"visual_prompt", "box_matting"} and any(not item for item in boxes):
            raise ValueError(f"{task} requires at least one connected box per image.")
        path = resolve_model(model_name)
        request = dict(kind="vl", model=str(path), task=task, query=query, boxes=boxes,
                       device=device, dtype=dtype, max_pixels=max_pixels, max_new_tokens=max_new_tokens,
                       decoder_batch_size=decoder_batch_size, temperature=temperature, seed=seed)
        preview, alpha, instances, records = run_inference(request, images)
        return io.NodeOutput(preview, alpha, [r["bboxes"] for r in records],
                             [r["response"] for r in records],
                             [json.dumps(r, ensure_ascii=False, indent=2) for r in records], instances)


class WeVisOneMask2Alpha(io.ComfyNode):
    @classmethod
    def define_schema(cls):
        return io.Schema(
            node_id="WeVisOneMask2Alpha", display_name="WeVisOne · Mask2Alpha Matting", category="WeVisOne",
            description="Refine a coarse mask, box or point prompt into a continuous alpha matte using official Mask2Alpha.",
            inputs=[
                io.Image.Input("images", display_name="Images", tooltip="Input images. A batch is processed one image at a time."),
                io.Combo.Input("sam2_checkpoint", display_name="SAM2 checkpoint", options=list(sam2_models()) or ["Download the official SAM2.1-B+ checkpoint first"], tooltip="Official SAM2.1-B+ checkpoint. Its SHA256 is verified against the upstream value."),
                io.Combo.Input("mode", display_name="Prompt mode", options=["mask", "bbox", "point"], default="mask", tooltip="mask refines a coarse mask; bbox uses one box per image; point uses positive and negative clicks."),
                io.Mask.Input("mask", display_name="Coarse MASK", optional=True, tooltip="Required in mask mode. White is foreground. One mask may be shared across the image batch."),
                io.BoundingBox.Input("bboxes", display_name="Box", optional=True, force_input=True, socketless=False, tooltip="Required in bbox mode: exactly one native pixel-space box per image."),
                io.String.Input("positive_coords", display_name="Positive points", default="[]", optional=True, tooltip='Foreground clicks in KJNodes PointsEditor format: [{"x": 100, "y": 200}]. Coordinates are input-image pixels.'),
                io.String.Input("negative_coords", display_name="Negative points", default="[]", optional=True, tooltip='Background clicks in KJNodes PointsEditor format: [{"x": 100, "y": 200}]. Coordinates are input-image pixels.'),
                io.Float.Input("mask_threshold", display_name="Mask threshold", default=0.0, min=0.0, max=1.0, step=0.01, advanced=True, tooltip="In mask mode, pixels above this threshold become foreground in the coarse prompt mask."),
                io.Combo.Input("device", display_name="Device", options=["auto", "cpu"], default="auto", advanced=True, tooltip="auto uses the device selected by ComfyUI; cpu forces CPU inference."),
                io.Combo.Input("precision", display_name="Precision", options=["bf16", "fp32"], default="bf16", advanced=True, tooltip="bf16 enables BF16 autocast on CUDA; fp32 uses full precision."),
            ],
            outputs=[
                io.Mask.Output("alpha", tooltip="Continuous foreground alpha at the original image resolution."),
                io.Mask.Output("prompt_mask", tooltip="The binary prompt mask supplied to the refinement head."),
                io.String.Output("result_json", is_output_list=True, tooltip="Prompt mode, image dimensions and timing, one JSON string per input image."),
            ],
        )

    @classmethod
    def execute(cls, images, sam2_checkpoint, mode, mask=None, bboxes=None, positive_coords="[]",
                negative_coords="[]", mask_threshold=0.0, device="auto", precision="bf16"):
        if mode not in {"mask", "bbox", "point"}:
            raise ValueError(f"Unknown prompt mode: {mode}")
        checkpoint = sam2_models().get(sam2_checkpoint)
        head = MODEL_ROOT / "Mask2Alpha/mask2alpha_sam2_bplus.pt"
        if checkpoint is None or not head.is_file():
            raise FileNotFoundError("Missing the official SAM2.1-B+ checkpoint or Mask2Alpha head. Follow the model download instructions in README.")
        boxes, points, labels = None, None, None
        if mode == "mask":
            if mask is None:
                raise ValueError("mask mode requires a connected MASK with white foreground.")
            if mask.ndim == 2:
                mask = mask.unsqueeze(0)
            if len(mask) == 1:
                mask = mask.expand(len(images), -1, -1)
            if len(mask) != len(images):
                raise ValueError("The MASK batch size must be 1 or match the image batch size.")
            mask = F.interpolate(mask[:, None].float(), images.shape[1:3], mode="nearest")[:, 0]
            mask = (mask > mask_threshold).float()
            if not torch.all(mask.flatten(1).any(dim=1)):
                raise ValueError("Mask2Alpha requires a non-empty foreground mask.")
        elif mode == "bbox":
            boxes = boxes_per_image(bboxes, len(images))
            if any(len(item) != 1 for item in boxes):
                raise ValueError("Mask2Alpha bbox mode requires one box per image. Use list mapping for multiple instances.")
        else:
            points, labels = parse_points(positive_coords, negative_coords)
        request = dict(kind="mask2alpha", model=str(checkpoint), head=str(head), mode=mode,
                       boxes=boxes, points=points, labels=labels, device=device, precision=precision)
        _, alpha, prompts, records = run_inference(request, images, mask if mode == "mask" else None)
        return io.NodeOutput(alpha, torch.cat(prompts), [json.dumps(r, ensure_ascii=False) for r in records])
