# Test image provenance

English | [简体中文](README_zh-CN.md)

These are actual inference outputs and ComfyUI screenshots, not illustrative mockups. The examples do not represent full benchmark performance.

| File | Source and settings |
| --- | --- |
| screenshots/workflow-box-matting.jpg | Actual ComfyUI workflow screenshot: 2B, BF16, SDPA, box_matting, query=person, max_pixels=1048576. The canvas layout was adjusted for presentation; inference results are unchanged. |
| screenshots/matting-input.jpg | The official Tencent seabreeze.jpg input image, 1620×1080. |
| screenshots/matting-alpha-4b.png | Continuous alpha from local 4B matting: query=person, BF16, SDPA, max_pixels=1048576, max_new_tokens=512. Saved as an 8-bit PNG for viewing. |
| screenshots/detection-2b.png | Local 2B detection preview for livingroom.jpg; categories sofa, pillow and lamp; max_pixels=262144. |
| screenshots/ocr-2b.png | Local 2B OCR preview for coffee_sign.jpg; max_pixels=262144. Recognition and font-rendering results are preserved as produced. |

Input images come from [Tencent/WeVisOne-VL's official examples](https://github.com/Tencent/WeVisOne-VL/tree/40f735b8daed437ece982db9718e9c9856f52a79/demo/examples/images); upstream rights and notices apply. Screenshots use only these public examples and exclude personal test images and unrelated chat or workflow tabs.
