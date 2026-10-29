# ComfyUI SAM + WeVisOne-VL Recovery

[中文](README.md) | **English**

**Automatically recover a lost target in ComfyUI: WeVisOne-VL 4B finds the target and SAM3 resumes tracking.**

This community workflow uses WeVisOne-VL to identify a target and SAM3 to generate video masks. When masks remain empty, it attempts to find the target again and restarts SAM3 from the recovered frame. The example workflow uses the result for MiniMax H3 character replacement.

It includes an adapted version of [flybirdxx/ComfyUI-WeVisOne](https://github.com/flybirdxx/ComfyUI-WeVisOne), plus recovery, shared-model and shared-description nodes. It is not an official Tencent or ComfyUI project.

## Demo: recovering a person in a crowd

![Original SAM3 tracking and recovered mask](examples/sam3-recovery-demo.gif)

The left window shows SAM3 tracking; the right shows the corrected mask preview. The windows may not play in sync, so this is an illustration rather than a frame-accurate comparison.

### Mask and crop preview in a crowd

![Crowd tracking and mask preview](examples/sam3-recovery-crowd.gif)

The left window shows SAM3 tracking and the right shows a cropped mask preview. The windows may not be synchronized; inspect individual frames to evaluate results.

## Credits and roles

- [Tencent/WeVisOne-VL](https://github.com/Tencent/WeVisOne-VL): vision-language model used to locate and segment the described target; this project uses the 4B model.
- [flybirdxx/ComfyUI-WeVisOne](https://github.com/flybirdxx/ComfyUI-WeVisOne): the ComfyUI implementation adapted here. Its backend is modified to share a model session.
- [SAM3](https://github.com/facebookresearch/sam3): video object tracking using the target mask, called through ComfyUI's SAM3 node interface.
- This project adds initial segmentation, empty-mask detection, periodic re-detection, SAM3 tracking restart, and a MiniMax H3 example workflow.

This is an independent community integration. Source code, models, and dependencies remain subject to their respective licenses.

## How it works

1. WeVisOne 4B segments the target in the first video frame using the person description.
2. SAM3 tracks the clip, and the recovery node checks each output mask.
3. After enough consecutive empty masks, WeVisOne is called at the configured frame interval.
4. Candidates are ranked by distance from the last valid mask. Ambiguous nearby candidates are skipped. When a target is found, its mask seeds SAM3 tracking for the remaining frames.
5. The resulting masks are joined and used for preview, subject cropping, and H3.

The **example workflow** triggers after **3 empty frames**, tries every **12 frames**, and allows up to **120 attempts**. Intervals are measured in frames, not seconds. The initial and recovery nodes share a WeVisOne session during a workflow run; ComfyUI may unload and reload models under memory pressure.

## Changes in this project

- Extend the flybirdxx backend to share a WeVisOne session between initial segmentation and recovery.
- Add initial segmentation, automatic recovery, and a shared person-description node. Initial segmentation requires exactly one detected target.
- Check every SAM mask and periodically retry detection after consecutive empty frames.
- Filter candidates by their distance from the last valid position, skip ambiguous matches, and restart SAM3 after recovery.
- Feed recovered masks into the character-replacement workflow, with mask preview and reference-video dimensions.

## What is passed to SAM3?

The SAM3 prompt in this workflow is a **person mask**; the person description is not repeatedly sent as SAM3 text conditioning.

1. Enter a distinguishing description in the shared CLIP text node, for example `the man wearing a white shirt in the foreground`. WeVisOne uses this same description for initial segmentation and recovery.
2. WeVisOne's unique first-frame mask is passed as `initial_mask` to SAM3 VideoTrack, together with the frames and SAM3 model. The example leaves SAM3's `conditioning` input unconnected.
3. After tracking is lost, a position-matched WeVisOne mask is passed as a new `initial_mask`, along with the remaining frames, to restart SAM3. Recovery is limited to one object.
4. Empty frames before recovery may remain empty. If WeVisOne chooses a bystander, SAM3 may continue tracking the wrong person. Review identity and occlusion manually.

The values 3, 12, and 120 are configured in the **example workflow**. Newly added recovery nodes may have different defaults; check the actual node settings.

## Limitations

- The trigger detects empty masks; it **cannot reliably detect tracking the wrong person**. The closest candidate is not necessarily the same person, especially in crowds or similar clothing.
- A fully occluded or unrecognizable target cannot be recovered reliably. One or two empty frames do not trigger the example settings. Single-frame flicker and transition edges are not guaranteed to be fixed.
- The first frame must contain exactly one matching detection. Use a precise description; difficult occlusions may require another frame or manual mask editing.
- Repeated 4B inference costs time and GPU memory. Adjust the interval and attempt limit for your hardware.
- SAM3 reprocesses the remaining clip after recovery. This solution does not perform appearance-based identity verification or automatic quality assessment.
- Connections, candidate filtering, and SAM restarts were checked with simulations in the development environment; broad end-to-end testing across devices, ComfyUI versions, and videos remains outstanding.

## Requirements

- A ComfyUI version with SAM3 video tracking and the V3 node API.
- Python 3.10 or later. Development environment: Windows and an RTX 3090 with 24 GB VRAM.
- Both included directories: `custom_nodes/ComfyUI-WeVisOne` and `custom_nodes/ComfyUI-WeVisOne-Recovery`.
- The H3 example also requires [ComfyUI-KJNodes](https://github.com/kijai/ComfyUI-KJNodes), [ComfyUI-VideoHelperSuite](https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite), [MaskVidExperiments](https://github.com/drozbay/MaskVidExperiments), and other nodes used in the workflow. Use ComfyUI Manager to identify missing nodes.
- Models: [WeVisOne-VL 4B](https://huggingface.co/tencent/WeVisOne-VL-4B), SAM3.1 Multiplex, and the compatible MiniMax H3 model, video and audio VAEs, and text encoder. Model weights are not included.

## Installation

1. Copy both included `custom_nodes` directories into your ComfyUI `custom_nodes/` folder. Back up an existing flybirdxx installation first: model sharing depends on this project's backend changes.
2. Review `custom_nodes/ComfyUI-WeVisOne/requirements.txt` and check dependencies in the ComfyUI Python environment, for example with `pip install --dry-run -r <requirements-path>`. Review potential Torch, CUDA, Transformers, and OpenCV changes before installation.
3. Download the complete WeVisOne-VL 4B directory, including `model.safetensors`, `mask_decoder.pt`, `config.json`, tokenizer, processor configuration, and templates, to `ComfyUI/models/wevisone/WeVisOne-VL-4B/`.
4. Install SAM3.1 and H3 models according to their respective instructions and workflow nodes.
5. Restart ComfyUI completely, import `workflows/minimax_h3_wevisone_sam_recovery.json`, and select your own reference video and person image.

## Usage

Describe the person to replace in the shared person-description CLIP text node. Initial detection and recovery use that description; the H3 generation prompt remains in its separate prompt node.

- `interval`: frames between recovery attempts.
- `empty_frames`: consecutive empty masks needed to trigger recovery.
- `min_pixels` and `threshold`: determine whether a mask is valid.
- `max_distance`: maximum distance from the last valid position, normalized by the frame diagonal.
- `max_attempts`: maximum recovery attempts.

Review the corrected mask preview and console report. Before exporting, inspect occlusions, wrong-person selection, flicker, and recovery transitions.

## License and acknowledgments

This project is released under the Apache License 2.0. `custom_nodes/ComfyUI-WeVisOne` retains its upstream LICENSE, NOTICE, THIRD_PARTY information, and attribution. WeVisOne source code, weights, and other dependencies have their own licenses; consult [Tencent/WeVisOne-VL](https://github.com/Tencent/WeVisOne-VL), [flybirdxx/ComfyUI-WeVisOne](https://github.com/flybirdxx/ComfyUI-WeVisOne), and [SAM3](https://github.com/facebookresearch/sam3).
