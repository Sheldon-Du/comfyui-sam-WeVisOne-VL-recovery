# 测试图片来源

[English](README.md) | 简体中文

这些是实际运行结果及 ComfyUI 页面截图，不是效果示意图。示例图不代表完整 benchmark 表现。

| 文件 | 来源与参数 |
| --- | --- |
| screenshots/workflow-box-matting.jpg | 当前插件在 ComfyUI 的真实工作流截图；2B、BF16、SDPA、box_matting、query=person、max_pixels=1048576。画布布局为便于展示而调整，保留实际推理结果。 |
| screenshots/matting-input.jpg | 腾讯官方 seabreeze.jpg 示例原图，1620×1080。 |
| screenshots/matting-alpha-4b.png | 本地 4B matting 输出的连续 alpha；query=person、BF16、SDPA、max_pixels=1048576、max_new_tokens=512。保存为 8-bit PNG 供查看。 |
| screenshots/detection-2b.png | 本地 2B 对 livingroom.jpg 的检测预览，类别 sofa、pillow、lamp；max_pixels=262144。 |
| screenshots/ocr-2b.png | 本地 2B 对 coffee_sign.jpg 的 OCR 预览；max_pixels=262144。保留实际识别／字体显示结果。 |

原始图片来自 [Tencent/WeVisOne-VL 官方示例](https://github.com/Tencent/WeVisOne-VL/tree/40f735b8daed437ece982db9718e9c9856f52a79/demo/examples/images)，相关权利声明遵循上游。截图只使用这些公开示例，未包含本机个人测试图片或其他聊天／工作流标签页。
