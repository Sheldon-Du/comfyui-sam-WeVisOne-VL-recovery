# 示例工作流

[English](README.md) | 简体中文

把不带 `.api` 的 JSON 拖入 ComfyUI。`.api.json` 是 API 请求中的 prompt 对象，不能替代画布工作流文件。

| 文件 | 用途 |
| --- | --- |
| [01_text_matting.json](01_text_matting.json) | 文本抠图与透明 PNG |
| [02_detection_ocr_counting.json](02_detection_ocr_counting.json) | 检测、OCR、指点、计数；切换 task 和 query |
| [03_box_matting.json](03_box_matting.json) | 手填框提示，兼容已有工作流 |
| [04_mask2alpha.json](04_mask2alpha.json) | SAM2.1-B+ 与精修头的框提示抠图 |
| [05_draw_boxes.json](05_draw_boxes.json) | 推荐：在图片上画框，并预览黑白 MASK |

导入后先在 Load Image 选择图片，再选择已经下载的模型。示例中的 `wevisone_seabreeze_example.jpg` 是开发时的文件名；可上传本仓库的 [matting-input.jpg](../assets/screenshots/matting-input.jpg)，或从[官方示例](https://github.com/Tencent/WeVisOne-VL/tree/40f735b8daed437ece982db9718e9c9856f52a79/demo/examples/images)获取其他图片。

`03`、`04` 的预填坐标是为原始 1620×1080 示例准备的，换图后需要重新设框。`05` 可以直接清除预填框并拖拽重画，无需填写坐标。Mask2Alpha 的 bbox 模式每张图像只能保留一个框。

透明图沿用核心节点 `MASK → InvertMask → JoinImageWithAlpha → SaveImage`。MASK 白色为前景；中间取反用于匹配当前 JoinImageWithAlpha 的接口。
