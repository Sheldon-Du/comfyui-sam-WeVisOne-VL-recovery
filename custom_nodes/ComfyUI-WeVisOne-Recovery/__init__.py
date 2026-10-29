from .correction import WeVisOneSAMRecover, WeVisOneInitialSession, WeVisOneCLIPTextEncode

NODE_CLASS_MAPPINGS = {"WeVisOneSAMRecover": WeVisOneSAMRecover, "WeVisOneInitialSession": WeVisOneInitialSession, "WeVisOneCLIPTextEncode": WeVisOneCLIPTextEncode}
NODE_DISPLAY_NAME_MAPPINGS = {"WeVisOneSAMRecover": "WeVisOne SAM 自动纠错", "WeVisOneInitialSession": "WeVisOne 首帧分割及共享模型", "WeVisOneCLIPTextEncode": "CLIP文本编码（共享人物描述）"}
