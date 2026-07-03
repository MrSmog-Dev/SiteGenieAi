import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import DashboardLayout from "@/components/DashboardLayout";
import { api, pollGenerationJob } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { toast } from "sonner";
import { ArrowLeft, Download, Copy, Monitor, Smartphone, Code, RefreshCw, Wand2, Loader2, X, Globe, Share2, Check, ExternalLink, ChevronDown, FileArchive, FileCode } from "lucide-react";

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
  const [shareOpen, setShareOpen] = useState(false);
  const [publishing, setPublishing] = useState(false);
  const [copied, setCopied] = useState(false);
  const [downloadOpen, setDownloadOpen] = useState(false);
  const [slugDraft, setSlugDraft] = useState("");
  const [savingSlug, setSavingSlug] = useState(false);

  const publicUrl = tpl?.slug ? `${window.location.origin}/api/p/${tpl.slug}` : "";

  const load = () => api.get(`/templates/${id}`).then(({ data }) => setTpl(data)).catch(() => { toast.error("Not found"); navigate("/templates"); });
  useEffect(() => { load(); /* eslint-disable-next-line */ }, [id]);

  const runJob = async (promise, label) => {
    if ((user?.credits ?? 0) < 1 && !user?.unlimited) { toast.error("You're out of credits. Purchase a credit pack to continue."); navigate("/pricing"); return; }
    setBusy(true); setBusyLabel(label);
    try {
      const { data } = await promise;
      const job = await pollGenerationJob(data.job_id);
      setTpl((t) => ({ ...t, html: job.template.html }));
      await refreshUser();
      toast.success(job.unlimited ? `${label} complete!` : `${label} complete! ${job.cost} credits used.`);
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
    setDownloadOpen(false);
  };
  const downloadZip = async () => {
    setDownloadOpen(false);
    try {
      const res = await api.get(`/templates/${id}/download-zip`, { responseType: "blob" });
      const url = URL.createObjectURL(res.data);
      const a = document.createElement("a");
      a.href = url; a.download = `${tpl.business_name.replace(/\s+/g, "-").toLowerCase()}.zip`; a.click();
      URL.revokeObjectURL(url);
      toast.success("ZIP downloaded");
    } catch (e) { toast.error("Could not build ZIP. Please try again."); }
  };
  const copy = () => { navigator.clipboard.writeText(tpl.html); toast.success("HTML copied to clipboard"); };

  const publish = async () => {
    setPublishing(true);
    try {
      const { data } = await api.post(`/templates/${id}/publish`);
      setTpl((t) => ({ ...t, published: true, slug: data.slug }));
      setSlugDraft(data.slug);
      toast.success("Your site is live!");
    } catch (e) { toast.error("Could not publish. Please try again."); }
    finally { setPublishing(false); }
  };
  const unpublish = async () => {
    setPublishing(true);
    try {
      await api.post(`/templates/${id}/unpublish`);
      setTpl((t) => ({ ...t, published: false }));
      toast.success("Site unpublished.");
    } catch (e) { toast.error("Could not unpublish. Please try again."); }
    finally { setPublishing(false); }
  };
  const copyLink = () => {
    navigator.clipboard.writeText(publicUrl);
    setCopied(true); setTimeout(() => setCopied(false), 1800);
    toast.success("Public link copied");
  };
  const saveSlug = async () => {
    const next = slugDraft.trim();
    if (next === tpl.slug) return;
    setSavingSlug(true);
    try {
      const { data } = await api.put(`/templates/${id}/slug`, { slug: next });
      setTpl((t) => ({ ...t, slug: data.slug }));
      setSlugDraft(data.slug);
      toast.success("Link updated");
    } catch (e) {
      const status = e.response?.status;
      if (status === 409) toast.error("That link is already taken. Try another.");
      else if (status === 400) toast.error("Link must be at least 3 characters (letters, numbers, hyphens).");
      else toast.error("Could not update link. Please try again.");
    } finally { setSavingSlug(false); }
  };
  const openShare = () => { setSlugDraft(tpl?.slug || ""); setShareOpen(true); };

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
            <button data-testid="publish-btn" onClick={openShare}
              className={`flex items-center gap-2 text-sm px-3 py-2 border transition-colors duration-300 ${tpl.published ? "border-neon text-neon" : "border-white/15 hover:border-white/40"}`}>
              {tpl.published ? <><span className="w-2 h-2 rounded-full bg-neon animate-pulse" /> Live</> : <><Globe className="w-4 h-4" /> Publish</>}
            </button>
            <div className="relative">
              <button data-testid="download-btn" onClick={() => setDownloadOpen((o) => !o)}
                className="flex items-center gap-2 text-sm bg-brand hover:bg-brand-hover px-3 py-2 transition-colors duration-300">
                <Download className="w-4 h-4" /> Download <ChevronDown className="w-3.5 h-3.5" />
              </button>
              {downloadOpen && (
                <>
                  <div className="fixed inset-0 z-40" onClick={() => setDownloadOpen(false)} />
                  <div data-testid="download-menu" className="absolute right-0 mt-1 z-50 w-52 bg-surface2 border border-white/10 shadow-xl">
                    <button data-testid="download-html-btn" onClick={download}
                      className="w-full flex items-center gap-3 px-4 py-3 text-sm text-left hover:bg-surface1 transition-colors duration-300">
                      <FileCode className="w-4 h-4 text-brand" /> HTML file
                    </button>
                    <button data-testid="download-zip-btn" onClick={downloadZip}
                      className="w-full flex items-center gap-3 px-4 py-3 text-sm text-left hover:bg-surface1 transition-colors duration-300 border-t border-white/5">
                      <FileArchive className="w-4 h-4 text-neon" /> ZIP (HTML + README)
                    </button>
                  </div>
                </>
              )}
            </div>
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
            <p className="text-white/50 text-sm mb-3">Describe the changes and AI will revise your site. Credits are spent based on the work done.</p>
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

      {shareOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-6 bg-black/70 backdrop-blur-sm" onClick={() => setShareOpen(false)}>
          <div className="w-full max-w-lg bg-surface2 border border-white/10 p-6" onClick={(e) => e.stopPropagation()} data-testid="share-dialog">
            <div className="flex items-center justify-between mb-4">
              <h2 className="font-display text-xl font-bold flex items-center gap-2"><Share2 className="w-5 h-5 text-neon" /> Share your website</h2>
              <button onClick={() => setShareOpen(false)} className="text-white/50 hover:text-white"><X className="w-5 h-5" /></button>
            </div>

            {tpl.published ? (
              <>
                <div className="flex items-center gap-2 text-sm text-neon mb-3">
                  <span className="w-2 h-2 rounded-full bg-neon animate-pulse" /> Your site is live
                </div>
                <p className="text-white/50 text-sm mb-3">Anyone with this link can view your site. Edits and regenerations go live automatically.</p>
                <div className="flex items-stretch gap-2">
                  <input data-testid="public-url-input" readOnly value={publicUrl}
                    className="flex-1 bg-surface1 border border-white/10 px-3 py-2 text-sm font-mono text-white/80 outline-none truncate" />
                  <button data-testid="copy-link-btn" onClick={copyLink}
                    className="flex items-center gap-2 text-sm bg-brand hover:bg-brand-hover px-3 py-2 transition-colors duration-300">
                    {copied ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />} {copied ? "Copied" : "Copy"}
                  </button>
                </div>
                <div className="mt-4">
                  <div className="text-xs text-white/40 font-mono uppercase mb-2">Customize your link</div>
                  <div className="flex items-stretch gap-2">
                    <div className="flex items-center bg-surface1 border border-white/10 border-r-0 pl-3 pr-1 text-xs text-white/40 font-mono select-none">/api/p/</div>
                    <input data-testid="slug-input" value={slugDraft}
                      onChange={(e) => setSlugDraft(e.target.value)}
                      className="flex-1 bg-surface1 border border-white/10 border-l-0 px-1 py-2 text-sm font-mono text-white outline-none focus:border-neon"
                      placeholder="your-business" />
                    <button data-testid="save-slug-btn" onClick={saveSlug} disabled={savingSlug || !slugDraft.trim() || slugDraft.trim() === tpl.slug}
                      className="flex items-center gap-2 text-sm border border-white/15 hover:border-neon hover:text-neon px-3 py-2 transition-colors duration-300 disabled:opacity-40">
                      {savingSlug ? <Loader2 className="w-4 h-4 animate-spin" /> : "Save"}
                    </button>
                  </div>
                  <p className="text-white/30 text-xs mt-2">Letters, numbers and hyphens. Changing it updates your live link.</p>
                </div>
                <div className="flex items-center justify-between mt-5">
                  <button data-testid="unpublish-btn" onClick={unpublish} disabled={publishing}
                    className="text-sm text-white/50 hover:text-neon transition-colors duration-300 disabled:opacity-50">
                    {publishing ? "Working…" : "Unpublish"}
                  </button>
                  <a data-testid="open-public-btn" href={publicUrl} target="_blank" rel="noopener noreferrer"
                    className="flex items-center gap-2 text-sm border border-white/15 hover:border-white/40 px-4 py-2 transition-colors duration-300">
                    <ExternalLink className="w-4 h-4" /> Open site
                  </a>
                </div>
              </>
            ) : (
              <>
                <p className="text-white/50 text-sm mb-5">Publish your site to get a shareable public link. No download needed — send it to anyone and they'll see your live website instantly.</p>
                <button data-testid="publish-confirm-btn" onClick={publish} disabled={publishing}
                  className="w-full flex items-center justify-center gap-2 bg-neon hover:bg-neon-hover px-4 py-3 transition-colors duration-300 disabled:opacity-50">
                  {publishing ? <Loader2 className="w-4 h-4 animate-spin" /> : <Globe className="w-4 h-4" />} Publish site
                </button>
              </>
            )}
          </div>
        </div>
      )}
    </DashboardLayout>
  );
}
