import { useEffect, useRef, useState, useCallback } from "react";
import { api } from "@/lib/api";
import { toast } from "sonner";
import { EDITOR_RUNTIME } from "@/lib/editorRuntime";
import { X, Save, Loader2, Monitor, Smartphone, Undo2, Type, Heading, MousePointerClick,
  Image, List, Link2, Minus, MoveVertical, Plus, Check } from "lucide-react";

const ADD_BLOCKS = [
  { kind: "subheadline", label: "Sub-headline", icon: Heading },
  { kind: "text", label: "Text paragraph", icon: Type },
  { kind: "button", label: "Button", icon: MousePointerClick },
  { kind: "image", label: "Image", icon: Image },
  { kind: "list", label: "Bullet list", icon: List },
  { kind: "quicklinks", label: "Quick links", icon: Link2 },
  { kind: "divider", label: "Divider", icon: Minus },
  { kind: "spacer", label: "Spacer", icon: MoveVertical },
];

function injectRuntime(html) {
  if (html.includes("</body>")) return html.replace("</body>", `${EDITOR_RUNTIME}</body>`);
  return html + EDITOR_RUNTIME;
}

export function VisualEditor({ templateId, initialHtml, onClose, onSaved }) {
  const [view, setView] = useState("desktop");
  const [dirty, setDirty] = useState(false);
  const [saving, setSaving] = useState(false);
  const [addOpen, setAddOpen] = useState(false);
  const [addSectionId, setAddSectionId] = useState(null);
  const [ready, setReady] = useState(false);
  const iframeRef = useRef(null);
  const srcDoc = useRef(injectRuntime(initialHtml || ""));

  const post = useCallback((msg) => {
    iframeRef.current?.contentWindow?.postMessage({ sg: true, ...msg }, "*");
  }, []);

  // Listen to messages from the iframe editor runtime.
  useEffect(() => {
    const pendingResolve = { current: null };
    const onMsg = (e) => {
      const d = e.data || {};
      if (!d.sg) return;
      if (d.type === "ready") setReady(true);
      if (d.type === "dirty") setDirty(true);
      if (d.type === "open-add") { setAddSectionId(d.sectionId); setAddOpen(true); }
      if (d.type === "html" && window.__sgHtmlResolve) { window.__sgHtmlResolve(d.html); window.__sgHtmlResolve = null; }
    };
    window.addEventListener("message", onMsg);
    return () => window.removeEventListener("message", onMsg);
  }, []);

  const addBlock = (kind) => {
    if (!addSectionId) return;
    post({ type: "add-block", sectionId: addSectionId, kind });
    setAddOpen(false);
    setDirty(true);
  };

  const requestHtml = () => new Promise((resolve) => {
    window.__sgHtmlResolve = resolve;
    post({ type: "request-html" });
    setTimeout(() => { if (window.__sgHtmlResolve) { window.__sgHtmlResolve(null); window.__sgHtmlResolve = null; } }, 4000);
  });

  const save = async () => {
    setSaving(true);
    try {
      const html = await requestHtml();
      if (!html) throw new Error("Could not read the page.");
      await api.put(`/templates/${templateId}/html`, { html });
      setDirty(false);
      toast.success("Saved. Publish to push it live.");
      onSaved?.(html);
    } catch (e) {
      toast.error(e.response?.data?.detail || e.message || "Couldn't save. Try again.");
    } finally { setSaving(false); }
  };

  const closeGuarded = () => {
    if (dirty && !window.confirm("Discard unsaved edits?")) return;
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex flex-col bg-base" data-testid="visual-editor">
      {/* top bar */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-white/10 bg-surface1 shrink-0">
        <div className="flex items-center gap-3">
          <button data-testid="editor-close" onClick={closeGuarded} className="p-2 border border-white/15 hover:border-white/40 transition-colors duration-200"><X className="w-4 h-4" /></button>
          <div>
            <div className="font-display font-bold text-sm flex items-center gap-2">Visual Editor
              {ready && <span className="text-[10px] font-mono uppercase tracking-wider text-emerald-300/80">live</span>}
            </div>
            <div className="text-[11px] text-white/40">Click any text to edit · hover a section for controls</div>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <div className="hidden sm:flex border border-white/10">
            <button onClick={() => setView("desktop")} className={`p-2 ${view === "desktop" ? "bg-brand" : "hover:bg-surface2"} transition-colors`}><Monitor className="w-4 h-4" /></button>
            <button onClick={() => setView("mobile")} className={`p-2 ${view === "mobile" ? "bg-brand" : "hover:bg-surface2"} transition-colors`}><Smartphone className="w-4 h-4" /></button>
          </div>
          <button data-testid="editor-save" onClick={save} disabled={saving || !dirty}
            className="flex items-center gap-2 text-sm bg-brand hover:bg-brand-hover px-4 py-2 transition-colors duration-200 disabled:opacity-40">
            {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : dirty ? <Save className="w-4 h-4" /> : <Check className="w-4 h-4" />}
            {saving ? "Saving…" : dirty ? "Save changes" : "Saved"}
          </button>
        </div>
      </div>

      {/* canvas */}
      <div className="flex-1 overflow-auto bg-surface2 p-4 flex justify-center relative">
        {!ready && (
          <div className="absolute inset-0 flex items-center justify-center text-white/40 font-mono text-sm z-10">
            <Loader2 className="w-5 h-5 animate-spin mr-2" /> Preparing the editor…
          </div>
        )}
        <div className={`bg-white h-full ${view === "mobile" ? "w-[390px]" : "w-full max-w-6xl"} border border-white/10 transition-all duration-300`}>
          <iframe ref={iframeRef} data-testid="editor-iframe" title="editor"
            sandbox="allow-scripts allow-same-origin" srcDoc={srcDoc.current} className="w-full h-full" />
        </div>
      </div>

      {/* Add-block dropdown (opens when a section's + Add is clicked) */}
      {addOpen && (
        <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/50" onClick={() => setAddOpen(false)} data-testid="add-block-menu">
          <div className="w-full max-w-sm bg-surface1 border border-white/12 rounded-xl overflow-hidden" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between px-4 py-3 border-b border-white/10">
              <span className="font-display font-bold text-sm flex items-center gap-2"><Plus className="w-4 h-4 text-brand" /> Add a block</span>
              <button onClick={() => setAddOpen(false)} className="text-white/40 hover:text-white"><X className="w-4 h-4" /></button>
            </div>
            <div className="grid grid-cols-2 gap-1 p-2">
              {ADD_BLOCKS.map((b) => {
                const Icon = b.icon;
                return (
                  <button key={b.kind} data-testid={`add-block-${b.kind}`} onClick={() => addBlock(b.kind)}
                    className="flex items-center gap-2.5 px-3 py-3 text-sm text-left hover:bg-surface2 rounded-lg transition-colors duration-150">
                    <Icon className="w-4 h-4 text-brand shrink-0" /> {b.label}
                  </button>
                );
              })}
            </div>
            <p className="text-[11px] text-white/40 px-4 pb-3">The block is added to the section — then click it to edit the text inline.</p>
          </div>
        </div>
      )}
    </div>
  );
}
