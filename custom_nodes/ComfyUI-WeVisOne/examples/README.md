# Example workflows

English | [简体中文](README_zh-CN.md)

Drag a JSON file without `.api` in its name into ComfyUI. Files ending in `.api.json` are prompt objects for API requests, not canvas workflow files.

| File | Purpose |
| --- | --- |
| [01_text_matting.json](01_text_matting.json) | Text-prompted matting and transparent PNG output |
| [02_detection_ocr_counting.json](02_detection_ocr_counting.json) | Detection, OCR, pointing and counting; change the task and query |
| [03_box_matting.json](03_box_matting.json) | Manually entered box prompts for existing workflows |
| [04_mask2alpha.json](04_mask2alpha.json) | Box-prompted matting with SAM2.1-B+ and the refinement head |
| [05_draw_boxes.json](05_draw_boxes.json) | Recommended: draw boxes on the image and preview grayscale MASKs |

After importing, select an image in Load Image and choose a downloaded model. `wevisone_seabreeze_example.jpg` is the development filename. Upload the included [matting-input.jpg](../assets/screenshots/matting-input.jpg), or obtain other images from the [official examples](https://github.com/Tencent/WeVisOne-VL/tree/40f735b8daed437ece982db9718e9c9856f52a79/demo/examples/images).

Preset coordinates in `03` and `04` are for the original 1620×1080 image. Set new boxes when changing the input image. In `05`, clear the preset box and draw a new one without entering coordinates. Mask2Alpha's `bbox` mode requires exactly one box per image.

Transparent output uses the core chain `MASK → InvertMask → JoinImageWithAlpha → SaveImage`. White indicates foreground in the MASK; the intermediate inversion matches the current JoinImageWithAlpha interface.
