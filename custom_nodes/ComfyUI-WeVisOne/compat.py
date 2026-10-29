"""Checkpoint/API adapters for Transformers 4.57; no global monkey patches."""

import copy
import json
from pathlib import Path

from packaging.version import Version
import torch
import transformers
from transformers import (
    AutoTokenizer, Qwen2VLImageProcessor, Qwen3VLConfig,
    Qwen3VLForConditionalGeneration, Qwen3VLProcessor, Qwen3VLVideoProcessor,
    StoppingCriteria, StoppingCriteriaList,
)

import comfy.model_management as mm

from .vendor.wevisone_vl.config import Qwen3VLSegConfig
from .vendor.wevisone_vl.decoder import build_mask_decoder_from_qwen
from .vendor.wevisone_vl.engine import WeVisOneVL


def legacy_config(config):
    config = copy.deepcopy(config)
    text = config["text_config"]
    if "rope_parameters" in text:
        rope = text.pop("rope_parameters")
        text["rope_theta"] = rope.pop("rope_theta", 5000000.0)
        text["rope_scaling"] = rope
    return config


def load_processor(path, min_pixels, max_pixels):
    config = json.loads((path / "processor_config.json").read_text(encoding="utf-8"))
    token_config = json.loads((path / "tokenizer_config.json").read_text(encoding="utf-8"))
    kwargs = {}
    extra = token_config.get("extra_special_tokens")
    if Version(transformers.__version__).major < 5 and isinstance(extra, list):
        kwargs.update(extra_special_tokens={}, additional_special_tokens=extra)
    tokenizer = AutoTokenizer.from_pretrained(str(path), local_files_only=True, **kwargs)
    image_config = config["image_processor"] | {"min_pixels": min_pixels, "max_pixels": max_pixels}
    image_processor = Qwen2VLImageProcessor(**image_config)
    video_processor = Qwen3VLVideoProcessor(**config["video_processor"])
    return Qwen3VLProcessor(image_processor, tokenizer, video_processor,
                           chat_template=(path / "chat_template.jinja").read_text(encoding="utf-8"))


class ComfyInterrupt(StoppingCriteria):
    def __call__(self, input_ids, scores, **kwargs):
        mm.throw_exception_if_processing_interrupted()
        return False


class InterruptibleQwen3VL(Qwen3VLForConditionalGeneration):
    def generate(self, *args, **kwargs):
        criteria = list(kwargs.pop("stopping_criteria", []))
        return super().generate(*args, stopping_criteria=StoppingCriteriaList(criteria + [ComfyInterrupt()]), **kwargs)


class ComfyWeVisOneVL(WeVisOneVL):
    """Reuse all official inference methods, adapt only checkpoint construction."""

    def __init__(self, path, dtype, max_pixels, decoder_batch_size):
        path = Path(path)
        self.model_name_or_path = str(path)
        self.backend = "transformers"
        self.device = torch.device("cpu")
        self.dtype = dtype
        self.min_pixels = 16 * 32 * 32
        self.max_pixels = max_pixels
        self.decoder_batch_size = decoder_batch_size
        self.vllm = None
        self._sampling_params_cls = None
        sidecar = torch.load(path / "mask_decoder.pt", map_location="cpu", weights_only=True)
        self.cfg = Qwen3VLSegConfig.from_dict(sidecar.get("cfg"))
        self.processor = load_processor(path, self.min_pixels, self.max_pixels)
        self.tokenizer = self.processor.tokenizer
        if self.tokenizer.pad_token_id is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token
        if "<OBJ>" not in self.tokenizer.get_vocab():
            raise ValueError("The official tokenizer is missing the <OBJ> token.")
        self.seg_token_id = self.tokenizer.convert_tokens_to_ids("<OBJ>")
        if sidecar.get("seg_token_id", self.seg_token_id) != self.seg_token_id:
            raise ValueError("The tokenizer and mask_decoder.pt have different <OBJ> token IDs.")
        config_data = json.loads((path / "config.json").read_text(encoding="utf-8"))
        if Version(transformers.__version__).major < 5:
            config_data = legacy_config(config_data)
        config = Qwen3VLConfig.from_dict(config_data)
        self.model, loading = InterruptibleQwen3VL.from_pretrained(
            str(path), config=config, dtype=dtype, attn_implementation="sdpa",
            local_files_only=True, low_cpu_mem_usage=True, output_loading_info=True,
        )
        if any(loading.get(key) for key in ("missing_keys", "unexpected_keys", "mismatched_keys", "error_msgs")):
            raise RuntimeError(f"Model weight structure mismatch: {loading}")
        self.mask_decoder = build_mask_decoder_from_qwen(self.model, self.cfg)
        self.mask_decoder.load_state_dict(sidecar["state_dict"], strict=True)
        self.mask_decoder.to(dtype=dtype).eval()
        self.model.eval()
        self.spatial_merge_size = int(sidecar.get("spatial_merge_size") or config.vision_config.spatial_merge_size)
        self.cnn_size = self.cfg.cnn_image_size
