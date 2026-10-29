from comfy_api.latest import ComfyExtension

from .nodes import WeVisOneMask2Alpha, WeVisOnePerception
from .box_editor import WeVisOneBoxEditor

WEB_DIRECTORY = "./js"


class WeVisOneExtension(ComfyExtension):
    async def get_node_list(self):
        return [WeVisOnePerception, WeVisOneMask2Alpha, WeVisOneBoxEditor]


async def comfy_entrypoint():
    return WeVisOneExtension()
