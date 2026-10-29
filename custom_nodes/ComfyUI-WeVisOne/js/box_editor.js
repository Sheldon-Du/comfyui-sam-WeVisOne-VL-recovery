import { app } from "../../scripts/app.js";
import { watchBoxPreviews } from "./box_preview.js";
import { currentMessages, localizeBoxButton } from "./i18n.js";

const EDITOR = "WeVisOneBoxEditor";
const TARGETS = new Set(["WeVisOnePerception", "WeVisOneMask2Alpha"]);

export function connectBoxEditor(target, appInstance, createNode) {
    const graph = target.graph;
    const imageLink = target.getInputLink(target.findInputSlot("images"));
    const source = imageLink && graph?.getNodeById(imageLink.origin_id);
    if (!source) throw new Error(currentMessages(appInstance).connectImage);
    const boxSlot = target.findInputSlot("bboxes");
    let editor = target.getInputNode(boxSlot);
    if (editor?.comfyClass !== EDITOR && editor?.type !== EDITOR) {
        editor = createNode(EDITOR);
        if (!editor) throw new Error(currentMessages(appInstance).missingEditor);
        const nearby = graph.nodes.filter(n => Math.abs(n.pos[0] - source.pos[0]) < 440);
        editor.pos = [source.pos[0], Math.max(...nearby.map(n => n.pos[1] + n.size[1]), source.pos[1]) + 60];
        graph.add(editor);
    }
    source.connect(imageLink.origin_slot, editor, editor.findInputSlot("background"));
    editor.connect(editor.findOutputSlot("bboxes"), target, boxSlot);
    appInstance.canvas.selectNode(editor);
    appInstance.canvas.centerOnNode(editor);
    graph.setDirtyCanvas(true, true);
    return editor;
}

app.registerExtension({
    name: "WeVisOne.BoxEditor",
    setup() {
        watchBoxPreviews();
    },
    nodeCreated(node) {
        const name = node.comfyClass ?? node.constructor.comfyClass;
        if (name === EDITOR) {
            node.properties.bboxGrid ??= false;
            node.setSize([Math.max(node.size[0], 480), Math.max(node.size[1], 640)]);
        }
        if (!TARGETS.has(name)) return;
        const widget = node.addWidget("button", "open_box_editor", null, () => {
            try {
                connectBoxEditor(node, app, type => window.LiteGraph.createNode(type));
            } catch (error) {
                app.extensionManager.toast.add({severity: "warn", summary: currentMessages(app).title, detail: error.message, life: 5000});
            }
        }, {serialize: false});
        localizeBoxButton(node, widget, app);
    },
});
