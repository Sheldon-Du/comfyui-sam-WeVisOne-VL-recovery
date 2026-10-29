# ComfyUI-WeVisOne

English | [简体中文](README_zh-CN.md)

An independent ComfyUI integration for Tencent [**WeVisOne-VL**](https://github.com/Tencent/WeVisOne-VL) and [**Mask2Alpha**](https://github.com/Tencent/WeVisOne-VL/tree/mask2alpha). Supports the official 2B and 4B models, reuses upstream models, pixel decoding and inference, and runs in the existing ComfyUI process without a separate service.

[Example workflows](examples/README.md) · [Test results](#test-results) · [Upstream provenance](THIRD_PARTY.md) · [Changelog (Chinese)](CHANGELOG.md)

## Features

| Node ID | Features |
| --- | --- |
| **WeVisOnePerception** | Detection, referring localization, pointing, box/point counting, OCR, text grounding, segmentation, continuous alpha matting, visual reference prompts, freeform prompts and box-prompted matting |
| **WeVisOneMask2Alpha** | Coarse-mask refinement, single-box matting and positive/negative point prompts using the official SAM2.1-B+ backbone and refinement head |
| **WeVisOneBoxEditor** | Draw, move and resize boxes on the image; preserve image brightness with outlines and eight resize handles |

The box editor reuses ComfyUI's native component. Image loading, mask previews, cropping and transparent-image saving use core nodes. Models are managed through ComfyUI's `ModelPatcher`, with support for interrupting generation.

## Test results

These examples use public images from Tencent's repository and were run on an RTX 5060 Ti with 16 GB VRAM. Screenshots and outputs come from actual inference; they do not replace a full benchmark evaluation. See [image sources and settings](assets/README.md).

**Box selection and MASK preview:** draw boxes directly in ComfyUI while preserving image brightness, then generate masks at the original resolution.

![ComfyUI box selection and MASK workflow](assets/screenshots/workflow-box-matting.jpg)

**4B text-prompted matting:** the query is `person`. The input image is on the left; the model's continuous alpha output is on the right.

| Input image | 4B alpha output |
| --- | --- |
| ![Matting input](assets/screenshots/matting-input.jpg) | ![4B alpha output](assets/screenshots/matting-alpha-4b.png) |

**2B detection:** queries are `sofa`, `pillow` and `lamp`.

![Actual 2B detection result](assets/screenshots/detection-2b.png)

**2B OCR:** actual text regions and labels, including recognition or font-rendering limitations in the original output.

![Actual 2B OCR result](assets/screenshots/ocr-2b.png)

## Requirements

- Current ComfyUI with the V3 API and core components such as `BOUNDING_BOXES` and `JoinImageWithAlpha`.
- Python ≥3.10, using the environment that runs ComfyUI.
- Transformers with Qwen3-VL support. **4.57.6** has been tested. The compatibility layer adapts newer checkpoint configurations without requiring Transformers 5. Versions before 4.57 that lack Qwen3-VL classes are outside the supported range.
- A working Torch/Torchvision installation. Full-model GPU inference was tested on an RTX 5060 Ti with 16 GB VRAM; other devices and the CPU path have not received the same validation.
- The official `sam2` package is additionally required for Mask2Alpha. Standard VLM tasks do not use SAM2.

## Installation

Clone this repository inside `ComfyUI/custom_nodes`, or extract the Release ZIP there:

```sh
git clone https://github.com/flybirdxx/ComfyUI-WeVisOne.git
```

Install additional dependencies using **ComfyUI's Python environment**. For Windows portable installations with `uv` available, run from the portable root directory:

```powershell
.\python_embeded\Scripts\uv.exe pip install --python .\python_embeded\python.exe --dry-run -r ComfyUI\custom_nodes\ComfyUI-WeVisOne\requirements.txt
.\python_embeded\Scripts\uv.exe pip install --python .\python_embeded\python.exe -r ComfyUI\custom_nodes\ComfyUI-WeVisOne\requirements.txt
```

Review the dry-run output before installing. The requirements file does not request Torch, CUDA or Transformers upgrades. If dependencies are already satisfied, no additional installation is needed. Do not install the upstream repository's entire pinned requirements file into ComfyUI.

For Mask2Alpha, install `sam2` using the [official SAM2 instructions](https://github.com/facebookresearch/sam2#installation) if it is missing. The corresponding upstream submodule revision is `2b90b9f5ceec907a1c18123530e92e794ad901a4`. On Windows, `SAM2_BUILD_CUDA=0` can disable the optional CUDA extension while retaining your existing Torch build.

Restart ComfyUI and refresh the browser after initial installation or after adding/updating locale files.

### Interface language

Node names, parameter labels/tooltips, output labels and the box-editor button follow **ComfyUI Settings → Comfy → Locale**. English is the default/fallback language; selecting Chinese switches the interface to Simplified Chinese. Existing box-editor buttons update when the language changes. Node IDs, input keys and task values remain unchanged, so saved workflows stay compatible.

## Model downloads

Nodes load local models only and do not download weights automatically. This repository contains no model weights. Download the complete [2B model](https://huggingface.co/tencent/WeVisOne-VL-2B/tree/main) or [4B model](https://huggingface.co/tencent/WeVisOne-VL-4B/tree/main), including the tokenizer, processor configuration and `mask_decoder.pt`. You can also use the Hugging Face CLI already installed in your environment:

```powershell
.\python_embeded\Scripts\hf.exe download tencent/WeVisOne-VL-2B --local-dir ComfyUI\models\wevisone\WeVisOne-VL-2B
.\python_embeded\Scripts\hf.exe download tencent/WeVisOne-VL-4B --local-dir ComfyUI\models\wevisone\WeVisOne-VL-4B
```

Mask2Alpha needs the [official SAM2.1-B+ checkpoint](https://dl.fbaipublicfiles.com/segment_anything_2/092824/sam2.1_hiera_base_plus.pt) and [official refinement head](https://github.com/Tencent/WeVisOne-VL/raw/2dfe851ecdb8a6a72efd7e417ff51fbb442f15b4/weights/mask2alpha_sam2_bplus.pt). Use these filenames and directories:

```text
ComfyUI/models/wevisone/
├── WeVisOne-VL-2B/    Complete Hugging Face model directory, including mask_decoder.pt
├── WeVisOne-VL-4B/    Same layout as above
└── Mask2Alpha/
    ├── sam2.1_hiera_base_plus.pt
    └── mask2alpha_sam2_bplus.pt
```

The official large weight files are F32: approximately 9.77 GB for 2B and 19.32 GB for 4B. The default inference dtype is BF16. The SAM2 backbone is approximately 324 MB and the refinement head is approximately 16 MB. VRAM usage also depends on resolution, output length and instance count.

Model discovery also checks `wevisone` and `LLM` directories configured in `extra_model_paths.yaml`, plus the local Hugging Face cache for the official models. Mask2Alpha can reuse the official SAM2.1-B+ `.pt` in a `sam2` model directory; its SHA256 is checked against the upstream value.

## Quick start

Import [05_draw_boxes.json](examples/05_draw_boxes.json), select an image in Load Image, choose a model, and redraw the selection on the box-editor canvas. Upload the included [matting-input.jpg](assets/screenshots/matting-input.jpg) or use your own image. Select the image again after importing a workflow.

In an existing workflow, click **Add / locate image box editor** to connect the image and `bboxes` automatically. Drag inside a box to move it, drag an edge or handle to resize it, and press Delete to remove the selected box. Multiple boxes are supported; Mask2Alpha's `bbox` mode requires exactly one box per image.

The canvas displays the first image of a batch, and the same boxes apply to every image in that batch. Coordinates are saved with the workflow and mapped back to the original dimensions. If the connected processing node has not run and has no preview, execute the box-editor node by itself first to obtain its background image.

| Task | Query / input |
| --- | --- |
| `detection`, `point` | One category per line, such as `person` followed by `car` on the next line |
| `referring` | A complete referring expression; commas are preserved |
| `count_box`, `count_point` | The category or objects to count |
| `ocr`, `ocr_grounding` | Recognize all text / locate the requested text |
| `segmentation`, `matting` | An object description; binary MASKs / continuous alpha |
| `box_matting` | Connect `bboxes`; each box uses the official box-prompted evaluation protocol |
| `visual_prompt` | Connect reference boxes to find similar objects |
| `freeform` | Uses the query as the prompt; generated `<OBJ>` tokens still use the official pixel decoder |

English categories and descriptions follow the official examples. Evaluate Chinese prompts against their actual outputs.

## Outputs and connections

- `preview`: visualized categories, OCR text, boxes, points and masks.
- `mask`: one merged MASK per input image, with white foreground. `matting` preserves continuous alpha; `segmentation` uses a 0.5 threshold. Detection/OCR without pixel segmentation returns a zero mask.
- `bboxes`: native pixel-space boxes `{x,y,width,height,label}`, grouped by image and compatible with core cropping nodes. Confidence scores are not fabricated.
- `response`, `result_json`: one string per image using standard ComfyUI list mapping. JSON preserves the raw response, prompt, spatial coordinates, counts and instance count.
- `instance_masks`: one `[N,H,W]` MASK batch per input image. When no target is found, `N=0`; handle this branch using `instance_count`. The merged `mask` still contains one all-black MASK.

To view a grayscale mask: `mask → Convert Mask to Image → Preview Image`.

To save a transparent PNG: connect `mask → InvertMask → JoinImageWithAlpha.alpha`, connect the original image to `JoinImageWithAlpha.image`, then connect its output to `SaveImage`. The inversion matches the current core JoinImageWithAlpha interface; the examples already include it.

Mask2Alpha point coordinates use `[{"x":100,"y":200}]`, with positive and negative points supplied separately. Coarse MASK inputs use white foreground; empty foreground masks produce an error.

## Limitations and validation

A model is loaded once per node execution, images are processed sequentially, and the model is unloaded on completion, failure or cancellation. Models are loaded in full; this is not layer-by-layer CPU offloading. Missing targets retain the official empty result instead of an artificial full-image mask.

Validation covered 2B/4B matting, the complete 2B task examples, all three Mask2Alpha prompt modes, node registration and frontend box selection. The tested environment was Windows, Python 3.11, Torch 2.11.0+cu130, Transformers 4.57.6, supervision 0.6.0 and ComfyUI frontend 1.55.17. The full paper benchmarks were not rerun, so these checks do not establish reproduction of the reported accuracy. Warnings about ignored sampling parameters in greedy mode do not affect that decoding mode.

GitHub CI checks source syntax, upstream file hashes and example JSON. It does not run GPU inference.

## License and acknowledgments

The plugin uses [Apache-2.0](LICENSE). See [THIRD_PARTY.md](THIRD_PARTY.md) and [NOTICE](NOTICE) for upstream code, pinned revisions and modifications. This is an independent integration, not an official Tencent repository.

Thanks to Tencent's WeChat Vision team, ComfyUI, Hugging Face Transformers, SAM2 and supervision. Paper: [WeVisOne-VL: Unified Visual Perception from Objects to Pixels](https://arxiv.org/html/2610.31329v1).
