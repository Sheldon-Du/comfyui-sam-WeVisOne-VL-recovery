# Upstream provenance

The adapter uses upstream implementations rather than reimplementing their networks.

| Local path | Source | Revision | License |
| --- | --- | --- | --- |
| `vendor/wevisone_vl/` | Tencent/WeVisOne-VL main | `40f735b8daed437ece982db9718e9c9856f52a79` | Apache-2.0; `vendor/LICENSE-Tencent` |
| `vendor/mask2alpha/` | Tencent/WeVisOne-VL mask2alpha | `2dfe851ecdb8a6a72efd7e417ff51fbb442f15b4` | Repository license: Apache-2.0 |

The WeVisOne-VL files are unchanged copies from this revision (checkout line endings may differ). Mask2Alpha has two packaging-only changes: its `__init__.py` no longer prepends a bundled SAM2 to global `sys.path`; `model.py` no longer warns about that absent submodule. All model mathematics and checkpoint validation remain unchanged. The environment's existing official SAM2 package is reused; SAM2 is not vendored.

`vendor/provenance.json` records SHA256 hashes of the shipped files. No model weights are redistributed inside this plugin; download them from their official sources. Retain embedded third-party source notices, including DINO/Deformable DETR notices where present.

`backend.box_matting` adapts the public protocol in `evaluation/inference_matting.py`: teacher-forced `<ref>...<box>...<OBJ></box>` and the unrounded normalized box. The single-instance instruction is copied from `evaluation/utils/prompt_builder.py` under the Tencent repository license. `compat.ComfyWeVisOneVL` adapts the official engine constructor for older Transformers; inference methods remain inherited from upstream.

Paper: Liang et al., *WeVisOne-VL: Unified Visual Perception from Objects to Pixels*, arXiv:2610.31329 (2026).
