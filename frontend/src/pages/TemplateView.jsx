import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import DashboardLayout from "@/components/DashboardLayout";
import { api, pollGenerationJob } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { toast } from "sonner";
import { ArrowLeft, Download, Copy, Monitor, Smartphone, Code, RefreshCw, Wand2, Loader2, X } from "lucide-react";

export default function TemplateView() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { user, refreshUser } = useAuth();
  const [tpl, setTpl] = useState(null);
  const [view, setView] = useState("desktop");
  const [showCode, setShowCode] = useState(false);
  const [busy, setBusy] = useState(false);
  const [busyLabel, setBusyLabel] = useState("");
  const [editOpen, setEditOpen] = useState(false);
  const [instructions, setInstructions] = useState("");

  const load = () => api.get(`/templates/${id}`).then(({ data }) => setTpl(data)).catch(() => { toast.error("Not found"); navigate("/templates"); });
  useEffect(() => { load(); /* eslint-disable-next-line */ }, [id]);

  const runJob = async (promise, label) => {
    if ((user?.credits ?? 0) < 1) { toast.error("Not enough credits."); navigate("/pricing"); return; }
    setBusy(true); setBusyLabel(label);
    try {
      const { data } = await promise;
      const job = await pollGenerationJob(data.job_id);
      setTpl((t) => ({ ...t, html: job.template.html }));
      await refreshUser();
      toast.success(`${label} complete! 1 credit used.`);
    } catch (e) {
      const status = e.response?.status;
      if (status === 402) { toast.error("Not enough credits."); navigate("/pricing"); }
      else toast.error(e.message || "Failed. Please try again.");
    } finally { setBusy(false); setBusyLabel(""); }
  };

  const regenerate = () => runJob(api.post(`/templates/${id}/regenerate`), "Regenerate");
  const submitEdit = async () => {
    if (!instructions.trim()) { toast.error("Describe what to change."); return; }
    setEditOpen(false);
    await runJob(api.post(`/templates/${id}/edit`, { instructions }), "Edit");
    setInstructions("");
  };

  const download = () => {
    const blob = new Blob([tpl.html], { type: "text/html" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url; a.download = `${tpl.business_name.replace(/\s+/g, "-").toLowerCase()}.html`; a.click();
    URL.revokeObjectURL(url);
  };
  const copy = () => { navigator.clipboard.writeText(tpl.html); toast.success("HTML copied to clipboard"); };

  if (!tpl) return <DashboardLayout><div className="p-10 font-mono text-white/40">Loading…</div></DashboardLayout>;

  return (
    <DashboardLayout>
      <div className="flex flex-col h-screen">
        <div className="flex items-center justify-between p-4 border-b border-white/10 bg-surface1 gap-3 flex-wrap">
          <div className="flex items-center gap-3 min-w-0">
            <button onClick={() => navigate("/templates")} data-testid="back-btn" className="p-2 border border-white/15 hover:border-white/40 transition-colors duration-300"><ArrowLeft className="w-4 h-4" /></button>
            <div className="min-w-0">
              <h1 className="font-display font-bold truncate">{tpl.business_name}</h1>
              <p className="text-white/40 text-xs truncate">{tpl.industry}</p>
            </div>
          </div>
          <div className="flex items-center gap-2 flex-wrap">
            <button data-testid="regenerate-btn" onClick={regenerate} disabled={busy}
              className="flex items-center gap-2 text-sm border border-white/15 hover:border-brand hover:text-brand px-3 py-2 transition-colors duration-300 disabled:opacity-50">
              <RefreshCw className={`w-4 h-4 ${busy && busyLabel === "Regenerate" ? "animate-spin" : ""}`} /> Regenerate
            </button>
            <button data-testid="edit-btn" onClick={() => setEditOpen(true)} disabled={busy}
              className="flex items-center gap-2 text-sm border border-white/15 hover:border-neon hover:text-neon px-3 py-2 transition-colors duration-300 disabled:opacity-50">
              <Wand2 className="w-4 h-4" /> Edit with AI
            </button>
            <div className="hidden sm:flex border border-white/10">
              <button onClick={() => setView("desktop")} className={`p-2 ${view === "desktop" ? "bg-brand" : "hover:bg-surface2"} transition-colors duration-300`}><Monitor className="w-4 h-4" /></button>
              <button onClick={() => setView("mobile")} className={`p-2 ${view === "mobile" ? "bg-brand" : "hover:bg-surface2"} transition-colors duration-300`}><Smartphone className="w-4 h-4" /></button>
            </div>
            <button data-testid="view-code-btn" onClick={() => setShowCode((s) => !s)} className={`flex items-center gap-2 text-sm px-3 py-2 border transition-colors duration-300 ${showCode ? "border-brand text-brand" : "border-white/15 hover:border-white/40"}`}><Code className="w-4 h-4" /> Code</button>
            <button data-testid="copy-btn" onClick={copy} className="flex items-center gap-2 text-sm border border-white/15 hover:border-white/40 px-3 py-2 transition-colors duration-300"><Copy className="w-4 h-4" /></button>
            <button data-testid="download-btn" onClick={download} className="flex items-center gap-2 text-sm bg-brand hover:bg-brand-hover px-3 py-2 transition-colors duration-300"><Download className="w-4 h-4" /> Download</button>
          </div>
        </div>
        <div className="flex-1 overflow-auto bg-surface2 p-4 flex justify-center relative">
          {busy && (
            <div className="absolute inset-0 z-10 bg-base/80 backdrop-blur-sm flex flex-col items-center justify-center gap-3" data-testid="tpl-busy-overlay">
              <Loader2 className="w-10 h-10 text-brand animate-spin" />
              <div className="font-mono text-sm text-white/70">{busyLabel === "Edit" ? "Applying your changes…" : "Regenerating your site…"}</div>
            </div>
          )}
          {showCode ? (
            <pre className="w-full max-w-4xl bg-base border border-white/10 p-4 overflow-auto text-xs font-mono text-white/70">{tpl.html}</pre>
          ) : (
            <div className={`bg-white h-full ${view === "mobile" ? "w-[390px]" : "w-full max-w-6xl"} border border-white/10 transition-all duration-300`}>
              <iframe data-testid="template-iframe" title="site" sandbox="allow-scripts" srcDoc={tpl.html} className="w-full h-full" />
            </div>
          )}
        </div>
      </div>

      {editOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-6 bg-black/70 backdrop-blur-sm" onClick={() => setEditOpen(false)}>
          <div className="w-full max-w-lg bg-surface2 border border-white/10 p-6" onClick={(e) => e.stopPropagation()} data-testid="edit-dialog">
            <div className="flex items-center justify-between mb-4">
              <h2 className="font-display text-xl font-bold flex items-center gap-2"><Wand2 className="w-5 h-5 text-neon" /> Edit with AI</h2>
              <button onClick={() => setEditOpen(false)} className="text-white/50 hover:text-white"><X className="w-5 h-5" /></button>
            </div>
            <p className="text-white/50 text-sm mb-3">Describe the changes and AI will revise your site. Costs 1 credit.</p>
            <textarea data-testid="edit-instructions" rows={4} value={instructions} onChange={(e) => setInstructions(e.target.value)}
              className="w-full bg-surface1 border border-white/10 focus:border-neon px-4 py-3 outline-none transition-colors duration-300 text-white"
              placeholder="e.g. Make the hero darker, add a pricing section, change the tagline to..." />
            <div className="flex items-center justify-end gap-2 mt-4">
              <button onClick={() => setEditOpen(false)} className="px-4 py-2 text-sm border border-white/15 hover:border-white/40 transition-colors duration-300">Cancel</button>
              <button data-testid="submit-edit-btn" onClick={submitEdit} className="px-4 py-2 text-sm bg-neon hover:bg-neon-hover transition-colors duration-300 flex items-center gap-2">
                <Wand2 className="w-4 h-4" /> Apply changes
              </button>
            </div>
          </div>
        </div>
      )}
    </DashboardLayout>
  );
}
