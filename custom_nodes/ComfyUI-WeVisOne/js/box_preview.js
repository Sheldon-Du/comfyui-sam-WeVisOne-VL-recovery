// Keep ComfyUI's canvas interaction, but draw only the image, outlines and handles.
// All overrides belong to this canvas context, never to CanvasRenderingContext2D.prototype.
const SELECTOR = '[data-testid="bounding-boxes"][node-type="WeVisOneBoxEditor"] canvas';

export function outlineCanvas(canvas) {
    const ctx = canvas.getContext("2d");
    if (!ctx) return () => {};
    const names = ["fillRect", "fillText", "strokeRect", "save", "restore", "clearRect"];
    const original = Object.fromEntries(names.map(name => [name, ctx[name]]));
    const descriptors = Object.fromEntries(names.map(name => [name, Object.getOwnPropertyDescriptor(ctx, name)]));
    let depth = 0;

    ctx.fillRect = () => {};
    ctx.fillText = () => {};
    ctx.save = function () { depth++; return original.save.call(this); };
    ctx.restore = function () { depth = Math.max(0, depth - 1); return original.restore.call(this); };
    ctx.clearRect = function (...args) { depth = 0; return original.clearRect.apply(this, args); };
    ctx.strokeRect = function (x, y, width, height) {
        // The native editor clips its metadata tags inside save/restore; those aren't boxes.
        if (depth > 0 || width <= 0 || height <= 0) return;
        const inset = this.lineWidth / 2;
        const left = x - inset, top = y - inset;
        const right = x + width + inset, bottom = y + height + inset;
        original.save.call(this);
        this.strokeStyle = "#14232b";
        this.lineWidth = 3;
        original.strokeRect.call(this, x, y, width, height);
        this.strokeStyle = "#7ce7ff";
        this.lineWidth = 1.5;
        original.strokeRect.call(this, x, y, width, height);

        // Handle centres match the native corners/edge hit targets (8 logical px tolerance).
        const handles = [
            [left, top], [(left + right) / 2, top], [right, top],
            [right, (top + bottom) / 2], [right, bottom],
            [(left + right) / 2, bottom], [left, bottom], [left, (top + bottom) / 2],
        ];
        this.fillStyle = "#ffffff";
        this.strokeStyle = "#14232b";
        this.lineWidth = 1.25;
        for (const [hx, hy] of handles) {
            original.fillRect.call(this, hx - 4, hy - 4, 8, 8);
            original.strokeRect.call(this, hx - 4, hy - 4, 8, 8);
        }
        original.restore.call(this);
    };
    canvas.dataset.wevisonePreview = "outline";

    return () => {
        for (const name of names) {
            if (descriptors[name]) Object.defineProperty(ctx, name, descriptors[name]);
            else delete ctx[name];
        }
        delete canvas.dataset.wevisonePreview;
    };
}

export function watchBoxPreviews(root = document.body) {
    const attached = new Map();
    function scan() {
        for (const canvas of root.querySelectorAll(SELECTOR)) {
            if (!attached.has(canvas)) attached.set(canvas, outlineCanvas(canvas));
        }
        for (const [canvas, restore] of attached) {
            if (!root.contains(canvas) || !canvas.matches(SELECTOR)) {
                restore();
                attached.delete(canvas);
            }
        }
    }
    const observer = new MutationObserver(scan);
    observer.observe(root, {childList: true, subtree: true, attributes: true, attributeFilter: ["node-type"]});
    scan();
    const stop = () => {
        observer.disconnect();
        for (const restore of attached.values()) restore();
        attached.clear();
        window.removeEventListener("pagehide", onPageHide);
    };
    const onPageHide = event => { if (!event.persisted) stop(); };
    window.addEventListener("pagehide", onPageHide);
    return stop;
}
