const messages = {
    en: {
        button: "Add / locate image box editor",
        tooltip: "Create and connect an image box editor, or focus the connected editor.",
        title: "WeVisOne Image Box Editor",
        connectImage: "Connect the WeVisOne images input before adding a box editor.",
        missingEditor: "The image box editor is not loaded. Restart ComfyUI and refresh the page.",
    },
    zh: {
        button: "添加／定位图片框选",
        tooltip: "创建并连接图片框选节点，或定位已经连接的框选节点。",
        title: "WeVisOne 图片框选",
        connectImage: "请先连接 WeVisOne 的 images 输入，再添加框选节点。",
        missingEditor: "图片框选节点未加载，请重启 ComfyUI 并刷新页面。",
    },
};

export function messagesFor(locale) {
    return typeof locale === "string" && /^zh(?:[-_]|$)/i.test(locale) ? messages.zh : messages.en;
}

export function currentMessages(app) {
    return messagesFor(app.extensionManager.setting.get("Comfy.Locale"));
}

export function localizeBoxButton(node, widget, app) {
    const update = () => {
        const text = currentMessages(app);
        widget.label = text.button;
        widget.options.tooltip = text.tooltip;
        node.setDirtyCanvas(true, true);
    };
    // This is the settings EventTarget used by ComfyUI's native setting store.
    const settings = app.ui.settings;
    settings.addEventListener("Comfy.Locale.change", update);
    const onRemoved = node.onRemoved;
    node.onRemoved = function (...args) {
        settings.removeEventListener("Comfy.Locale.change", update);
        return onRemoved?.apply(this, args);
    };
    update();
}
