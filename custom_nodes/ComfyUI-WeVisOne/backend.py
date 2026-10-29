"""Official inference methods with ComfyUI-managed model residency."""

import time

import numpy as np
from PIL import Image
import torch

import comfy.model_management as mm
from comfy.model_patcher import ModelPatcher
from comfy.utils import ProgressBar

from .compat import ComfyWeVisOneVL
from .contracts import native_boxes
from .vendor.wevisone_vl.engine import InferenceResult
from .vendor.wevisone_vl.visualization import combined_alpha, parse_predictions
from .visualization import render_overlay


def box_matting(engine, image, query, boxes):
    prompt = "\nLocate a single instance that best matches the following description and provide the alpha mattes: " + (query or "object")
    normalized, masks, responses = [], [], []
    started = time.perf_counter()
    for x1, y1, x2, y2 in boxes:
        mm.throw_exception_if_processing_interrupted()
        box = [x1 / image.width, y1 / image.height, x2 / image.width, y2 / image.height]
        coords = "".join(f"<{max(0, min(1000, round(v * 1000)))}>" for v in box)
        response = f"<ref>{query or 'object'}</ref><box>{coords}<OBJ></box>"
        actual_boxes, actual_masks = engine.decode_masks(image, prompt, response, boxes=[box])
        normalized.extend(actual_boxes)
        masks.extend(actual_masks)
        responses.append(response)
    return InferenceResult("".join(responses), prompt, normalized, masks, time.perf_counter() - started)


def prepare_result(index, image, result, task):
    predictions = parse_predictions(result.response, image.width, image.height)
    masks = np.stack(result.masks).astype(np.float32) if result.masks else np.empty((0, image.height, image.width), dtype=np.float32)
    if task == "segmentation":
        masks = (masks >= 0.5).astype(np.float32)
    alpha = combined_alpha(list(masks), image.width, image.height)
    overlay = np.array(render_overlay(image, result, mask_threshold=0.5 if task == "segmentation" else None))
    record = dict(
        image_index=index, width=image.width, height=image.height, task=task,
        prompt=result.prompt, response=result.response, latency_s=result.latency_s,
        predictions=predictions, bboxes=native_boxes(predictions),
        instance_count=len(masks), spatial_count=sum(len(items) for items in predictions.values()),
        counts_by_label={label: len(items) for label, items in predictions.items()},
        seg_boxes_normalized_xyxy=result.boxes,
        mask_source="provided_boxes" if task == "box_matting" else ("model" if len(masks) else "none"),
        response_source="teacher_forced" if task == "box_matting" else "generated",
    )
    return overlay, alpha, masks, record


def create_vl_session(request):
    device = mm.get_torch_device() if request["device"] == "auto" else torch.device("cpu")
    dtype = torch.float32 if device.type == "cpu" else getattr(torch, request["dtype"])
    engine = ComfyWeVisOneVL(request["model"], dtype, request["max_pixels"], request["decoder_batch_size"])
    modules = torch.nn.ModuleList([engine.model, engine.mask_decoder])
    patcher = ModelPatcher(modules, load_device=device, offload_device=torch.device("cpu"))
    return engine, patcher, device


def run_inference(request, images, prompt_masks=None, session=None):
    if request["device"] not in {"auto", "cpu"}:
        raise ValueError("device must be auto or cpu.")
    if len(images) == 0:
        raise ValueError("The image batch cannot be empty.")
    device = mm.get_torch_device() if request["device"] == "auto" else torch.device("cpu")
    mm.throw_exception_if_processing_interrupted()
    if request["kind"] == "vl":
        engine, patcher, device = session if session is not None else create_vl_session(request)
    else:
        from .vendor.mask2alpha import SAM2AlphaPredictor, build_mask2alpha
        model = build_mask2alpha(request["model"], request["head"], device="cpu")
        modules = torch.nn.ModuleList([model])
        predictor = SAM2AlphaPredictor(model, device=str(device), amp_dtype=request["precision"])
        patcher = ModelPatcher(modules, load_device=device, offload_device=torch.device("cpu"))
    results = []
    progress = ProgressBar(len(images))
    try:
        mm.load_models_gpu([patcher], memory_required=2 * 1024**3, force_full_load=True)
        if request["kind"] == "vl":
            engine.device = device
        rng_devices = [device.index] if device.type == "cuda" else []
        with torch.random.fork_rng(devices=rng_devices):
            if request["kind"] == "vl":
                torch.random.default_generator.manual_seed(request["seed"])
                if device.type == "cuda":
                    with torch.cuda.device(device):
                        torch.cuda.manual_seed(request["seed"])
            for index, frame in enumerate(images):
                mm.throw_exception_if_processing_interrupted()
                array = frame[..., :3].detach().cpu().clamp(0, 1).mul(255).round().to(torch.uint8).numpy()
                if request["kind"] == "vl":
                    image = Image.fromarray(array)
                    if request["task"] == "box_matting":
                        result = box_matting(engine, image, request["query"], request["boxes"][index])
                    else:
                        result = engine.predict(
                            image, task=request["task"], query=request["query"], reference_boxes=request["boxes"][index],
                            max_new_tokens=request["max_new_tokens"], temperature=request["temperature"],
                        )
                    results.append(prepare_result(index, image, result, request["task"]))
                else:
                    kwargs = {}
                    if request["mode"] == "mask":
                        kwargs["masks"] = [prompt_masks[index].detach().cpu().numpy()]
                    elif request["mode"] == "bbox":
                        kwargs["boxes"] = [np.array(request["boxes"][index][0], dtype=np.float32)]
                    else:
                        kwargs["points"] = [np.array(request["points"], dtype=np.float32)]
                        kwargs["point_labels"] = [np.array(request["labels"], dtype=np.int32)]
                    started = time.perf_counter()
                    alphas, prompts = predictor.predict([array], mode=request["mode"], **kwargs)
                    record = dict(image_index=index, mode=request["mode"], width=array.shape[1], height=array.shape[0],
                                  latency_s=time.perf_counter() - started, instance_count=1)
                    results.append((array, alphas[0], np.stack(prompts).astype(np.float32), record))
                progress.update(1)
    finally:
        if session is None:
            mm.unload_model_and_clones(patcher)
    return (torch.stack([torch.from_numpy(r[0]).float() / 255 for r in results]),
            torch.stack([torch.from_numpy(r[1]) for r in results]),
            [torch.from_numpy(r[2]) for r in results], [r[3] for r in results])
