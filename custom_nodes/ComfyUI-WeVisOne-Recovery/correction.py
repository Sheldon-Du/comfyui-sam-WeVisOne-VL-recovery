import importlib.util
import sys
from pathlib import Path

import torch


def _flybird_node():
    name = "wevisone_flybird_correction"
    if name not in sys.modules:
        root = Path(__file__).resolve().parent.parent / "ComfyUI-WeVisOne"
        if not (root / "__init__.py").is_file():
            raise RuntimeError("找不到 flybirdxx 的 ComfyUI-WeVisOne 插件。")
        spec = importlib.util.spec_from_file_location(name, root / "__init__.py", submodule_search_locations=[str(root)])
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        try:
            spec.loader.exec_module(module)
        except Exception:
            sys.modules.pop(name, None)
            raise
    return sys.modules[name].WeVisOnePerception


def _center(mask, threshold, min_pixels):
    points = torch.nonzero(mask > threshold, as_tuple=False)
    if points.shape[0] < min_pixels:
        return None
    return points.float().mean(dim=0).cpu()


def correct_masks(images, masks, detect, track, *, query, empty_frames, interval, min_pixels,
                  threshold, max_distance, max_attempts, interrupt=lambda: None):
    if len(images) != len(masks) or tuple(images.shape[1:3]) != tuple(masks.shape[1:3]):
        raise ValueError("视频帧与 SAM 蒙版的帧数、宽高必须一致。")
    output = masks.clone()
    total = len(images)
    last_center = None
    index = 0
    attempts = 0
    log = []
    diagonal = (images.shape[1] ** 2 + images.shape[2] ** 2) ** 0.5
    while index < total:
        interrupt()
        center = _center(output[index], threshold, min_pixels)
        if center is not None:
            last_center = center
            index += 1
            continue
        start = index
        while index < total and _center(output[index], threshold, min_pixels) is None:
            index += 1
        end = index
        if end - start < empty_frames:
            continue
        if last_center is None:
            log.append(f"帧 {start}：之前没有有效目标，无法判断是否找回同一人。")
            continue
        restored = False
        for frame in range(start, end, interval):
            if attempts >= max_attempts:
                log.append(f"已达到 {max_attempts} 次识别上限，后续保留原蒙版。")
                return output, "\n".join(log)
            interrupt()
            attempts += 1
            candidates, count = detect(images[frame:frame + 1], query)
            if candidates.ndim != 3 or tuple(candidates.shape[1:]) != tuple(images.shape[1:3]):
                raise ValueError("WeVisOne 蒙版尺寸与视频不一致。")
            ranked = []
            for candidate in candidates:
                center = _center(candidate, threshold, min_pixels)
                if center is not None:
                    distance = float(torch.linalg.vector_norm(center - last_center)) / diagonal
                    if distance <= max_distance:
                        ranked.append((distance, candidate))
            ranked.sort(key=lambda item: item[0])
            if not ranked:
                log.append(f"帧 {frame}：{count} 个候选，没有符合位置和面积条件的目标。")
                continue
            if len(ranked) > 1 and ranked[1][0] - ranked[0][0] < 0.03:
                log.append(f"帧 {frame}：候选位置过于接近，跳过以避免跟错。")
                continue
            distance, selected = ranked[0]
            found_mask = selected.unsqueeze(0)
            log.append(f"帧 {frame}：从 {count} 个候选选择最近位置 {distance:.3f}，开始重新运行 SAM。")
            print("WeVisOne SAM 纠错：" + log[-1], flush=True)
            suffix = track(images[frame:], found_mask)
            if tuple(suffix.shape) != tuple(output[frame:].shape):
                raise ValueError("SAM 重新跟踪的输出尺寸与剩余片段不一致。")
            output[frame:] = suffix.to(device=output.device, dtype=output.dtype)
            output[frame] = found_mask[0].to(device=output.device, dtype=output.dtype)
            log.append(f"帧 {frame}：SAM 已重新跟踪 {len(suffix)} 帧；请预览核对身份。")
            index = frame
            restored = True
            break
        if not restored:
            log.append(f"帧 {start}–{end - 1}：未可靠找回，保留原蒙版。")
    return output, "\n".join(log) or "未检测到需要纠错的连续空蒙版。"


class WeVisOneSAMRecover:
    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {
            "images": ("IMAGE",), "masks": ("MASK",), "sam_model": ("MODEL",),
            "query": ("STRING", {"default": "person", "multiline": True}),
            "model_name": ("STRING", {"default": "wevisone/WeVisOne-VL-4B"}),
            "empty_frames": ("INT", {"default": 3, "min": 1, "max": 300}),
            "interval": ("INT", {"default": 24, "min": 1, "max": 300}),
            "min_pixels": ("INT", {"default": 64, "min": 1, "max": 1000000}),
            "threshold": ("FLOAT", {"default": 0.1, "min": 0.0, "max": 1.0, "step": 0.01}),
            "max_distance": ("FLOAT", {"default": 0.35, "min": 0.0, "max": 1.0, "step": 0.01}),
            "max_attempts": ("INT", {"default": 12, "min": 1, "max": 1000}),
        }, "optional": {"wevis_session": ("WEVISONE_SESSION",)}}

    RETURN_TYPES = ("MASK", "STRING")
    RETURN_NAMES = ("corrected_masks", "report")
    FUNCTION = "recover"
    CATEGORY = "WeVisOne"

    def recover(self, images, masks, sam_model, query, model_name, empty_frames, interval,
                min_pixels, threshold, max_distance, max_attempts, wevis_session=None):
        from comfy_extras.nodes_sam3 import SAM3_VideoTrack, SAM3_TrackToMask
        import comfy.model_management as mm

        session = wevis_session["session"] if wevis_session is not None else None
        if wevis_session is not None and model_name != wevis_session["model_name"]:
            raise ValueError("首帧与纠错节点的 WeVisOne 模型必须一致。")
        request = dict(wevis_session["request"], query=query, boxes=[[]], max_new_tokens=1024) if wevis_session else None

        def detect(frame, description):
            nonlocal session, request
            _flybird_node()
            backend = sys.modules["wevisone_flybird_correction.backend"]
            if session is None:
                paths = sys.modules["wevisone_flybird_correction.model_paths"]
                request = dict(kind="vl", model=str(paths.resolve_model(model_name)), task="segmentation", query=description,
                               boxes=[[]], device="auto", dtype="bfloat16", max_pixels=1024 * 1024,
                               max_new_tokens=1024, decoder_batch_size=1, temperature=0.0, seed=0)
                session = backend.create_vl_session(request)
            _, _, instances, records = backend.run_inference(request, frame, session=session)
            record = records[0]
            return instances[0], int(record["instance_count"])

        def track(frames, initial_mask):
            track_data = SAM3_VideoTrack.execute(frames, sam_model, initial_mask=initial_mask, max_objects=1)[0]
            return SAM3_TrackToMask.execute(track_data)[0]

        corrected, report = correct_masks(images, masks, detect, track, query=query, empty_frames=empty_frames,
                                          interval=interval, min_pixels=min_pixels, threshold=threshold,
                                          max_distance=max_distance, max_attempts=max_attempts,
                                          interrupt=mm.throw_exception_if_processing_interrupted)
        print("WeVisOne SAM 纠错：\n" + report, flush=True)
        return corrected, report


class WeVisOneInitialSession:
    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {
            "image": ("IMAGE",),
            "query": ("STRING", {"default": "person", "multiline": True}),
            "model_name": ("STRING", {"default": "wevisone/WeVisOne-VL-4B"}),
        }}

    RETURN_TYPES = ("MASK", "WEVISONE_SESSION", "IMAGE", "STRING")
    RETURN_NAMES = ("mask", "session", "preview", "report")
    FUNCTION = "segment"
    CATEGORY = "WeVisOne"

    def segment(self, image, query, model_name):
        if len(image) != 1:
            raise ValueError("首帧分割节点只接受一帧，请用首帧选择节点。")
        _flybird_node()
        backend = sys.modules["wevisone_flybird_correction.backend"]
        paths = sys.modules["wevisone_flybird_correction.model_paths"]
        request = dict(kind="vl", model=str(paths.resolve_model(model_name)), task="segmentation", query=query,
                       boxes=[[]], device="auto", dtype="bfloat16", max_pixels=1024 * 1024,
                       max_new_tokens=1024, decoder_batch_size=1, temperature=0.0, seed=0)
        session = backend.create_vl_session(request)
        preview, mask, instances, records = backend.run_inference(request, image, session=session)
        count = int(records[0]["instance_count"])
        if count != 1:
            raise ValueError(f"首帧识别到 {count} 个目标，请用更具体的描述，只选择需要替换的人物。")
        shared = {"session": session, "model_name": model_name, "request": request}
        return mask, shared, preview, f"首帧找到 {count} 个目标。"


class WeVisOneCLIPTextEncode:
    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {"clip": ("CLIP",), "text": ("STRING", {"multiline": True, "dynamicPrompts": True})}}

    RETURN_TYPES = ("CONDITIONING", "STRING")
    RETURN_NAMES = ("conditioning", "text")
    FUNCTION = "encode"
    CATEGORY = "WeVisOne"

    def encode(self, clip, text):
        from nodes import CLIPTextEncode
        conditioning = CLIPTextEncode().encode(clip, text)[0]
        return conditioning, text
