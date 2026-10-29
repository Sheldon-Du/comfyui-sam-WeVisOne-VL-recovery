"""Discover and validate local model paths through ComfyUI folders."""

import json
import os
from pathlib import Path


import folder_paths


ROOT = Path(__file__).resolve().parent
MODEL_ROOT = Path(folder_paths.models_dir) / "wevisone"
folder_paths.add_model_folder_path("wevisone", str(MODEL_ROOT))


def discover_models():
    models = {}
    for category in ("wevisone", "LLM"):
        if category not in folder_paths.folder_names_and_paths:
            continue
        for root_string in folder_paths.get_folder_paths(category):
            root = Path(root_string)
            if not root.is_dir():
                continue
            configs = [root / "config.json", *root.glob("*/config.json"), *root.glob("*/*/config.json")]
            for config in configs:
                if config.is_file() and (config.parent / "mask_decoder.pt").is_file():
                    name = config.parent.relative_to(root).as_posix()
                    models.setdefault(f"{category}/{name}", config.parent.resolve())
    cache = Path(os.environ.get("HF_HUB_CACHE", Path(os.environ.get("HF_HOME", Path.home() / ".cache/huggingface")) / "hub"))
    for size in ("2B", "4B"):
        snapshots = cache / f"models--tencent--WeVisOne-VL-{size}" / "snapshots"
        if snapshots.is_dir():
            for path in sorted(snapshots.iterdir()):
                if (path / "config.json").is_file() and (path / "mask_decoder.pt").is_file():
                    models[f"HF/WeVisOne-VL-{size}/{path.name}"] = path.resolve()
    return models


def resolve_model(name):
    path = discover_models().get(name)
    if path is None:
        raise FileNotFoundError("Model not found. Follow README to place the complete official model in models/wevisone, then refresh the node.")
    config = json.loads((path / "config.json").read_text(encoding="utf-8"))
    if config.get("model_type") != "qwen3_vl":
        raise ValueError("Select an official WeVisOne-VL model directory.")
    weights = list(path.glob("*.safetensors"))
    if not weights:
        raise FileNotFoundError(f"Missing model weights: {path}")
    index = path / "model.safetensors.index.json"
    if index.is_file():
        for shard in set(json.loads(index.read_text(encoding="utf-8"))["weight_map"].values()):
            target = (path / shard).resolve()
            if not target.is_relative_to(path) or not target.is_file():
                raise FileNotFoundError(f"Model shard is missing or outside the model directory: {shard}")
    return path


def sam2_models():
    paths = {}
    roots = list(folder_paths.get_folder_paths("wevisone"))
    if "sam2" in folder_paths.folder_names_and_paths:
        roots.extend(folder_paths.get_folder_paths("sam2"))
    roots.append(str(Path(folder_paths.models_dir) / "sam2"))
    for root in map(Path, roots):
        for path in (root / "sam2.1_hiera_base_plus.pt", root / "Mask2Alpha/sam2.1_hiera_base_plus.pt"):
            if path.is_file():
                paths.setdefault(f"{root.name}/{path.relative_to(root).as_posix()}", path.resolve())
    return paths
