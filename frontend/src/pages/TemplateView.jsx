import { useEffect, useState } from "react";
import { useParams, useNavigate, useSearchParams } from "react-router-dom";
import DashboardLayout from "@/components/DashboardLayout";
import { OwnershipOnboarding, OwnershipCertificate } from "@/components/OwnershipOnboarding";
import { VisualEditor } from "@/components/VisualEditor";
import { api, formatApiError, pollGenerationJob } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { toast } from "sonner";
import { ArrowLeft, Download, Copy, Monitor, Smartphone, Code, RefreshCw, Wand2, Loader2, X, Globe, Share2, Check, ExternalLink, ChevronDown, FileArchive, FileCode, BarChart2, ShieldCheck, Clock, Store, Gem, PencilRuler } from "lucide-react";

export default function TemplateView() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const { user, refreshUser } = useAuth();
  const [tpl, setTpl] = useState(null);
  const [onboardOpen, setOnboardOpen] = useState(false);
  const [certOpen, setCertOpen] = useState(false);
  const [editorOpen, setEditorOpen] = useState(false);
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
  const [stats, setStats] = useState(null);
  const [domainDraft, setDomainDraft] = useState("");
  const [savingDomain, setSavingDomain] = useState(false);
  const [verifying, setVerifying] = useState(false);
  const [domainInfo, setDomainInfo] = useState(null);
  const [listing, setListing] = useState(null);
  const [listingBusy, setListingBusy] = useState(false);

  const isOwnerUser = !!user && (user.role === "owner" || user.role === "admin");

  const publicUrl = tpl?.slug ? `${window.location.origin}/api/p/${tpl.slug}` : "";
  const appHost = window.location.hostname;

  const loadStats = () => api.get(`/templates/${id}/stats`).then(({ data }) => setStats(data)).catch(() => {});
  const load = () => api.get(`/templates/${id}`).then(({ data }) => {
    setTpl(data);
    setDomainDraft(data.custom_domain || "");
    if (data.published) loadStats();
    // Post-purchase: open the "Make it yours" flow (once) for freshly-transferred sites.
    if (data.purchased && !data.onboarded && searchParams.get("onboard") === "1") {
      setOnboardOpen(true);
    }
  }).catch(() => { toast.error("Not found"); navigate("/templates"); });
  useEffect(() => { load(); /* eslint-disable-next-line */ }, [id]);

  useEffect(() => {
    if (!isOwnerUser) return;
    api.get("/market/mine")
      .then(({ data }) => setListing(data.find((l) => l.source_template_id === id) || null))
      .catch(() => {});
  }, [id, isOwnerUser]);

  const sellOnMarket = async () => {
    setListingBusy(true);
    try {
      const { data } = await api.post("/market/list", { template_id: id });
      setListing(data);
      toast.success(`Listed on the Market at $${data.price_usd} — priced by the AI pricing agent (${data.tier}).`);
    } catch (e) {
      if (e.response?.status === 409) toast.error("This template is already listed on the Market.");
      else toast.error(formatApiError(e.response?.data?.detail));
    } finally { setListingBusy(false); }
  };
  const delistFromMarket = async () => {
    if (!window.confirm("Remove this template from the Market?")) return;
    try {
      await api.delete(`/market/${listing.market_id}`);
      setListing(null);
      toast.success("Removed from the Market.");
    } catch (e) { toast.error("Could not remove listing."); }
  };

  const runJob = async (promise, label) => {
    if (!tpl?.purchased && (user?.credits ?? 0) < 1 && !user?.unlimited) { toast.error("You're out of credits. Purchase a credit pack to continue."); navigate("/pricing"); return false; }
    setBusy(true); setBusyLabel(label);
    try {
      const { data } = await promise;
      const job = await pollGenerationJob(data.job_id);
      setTpl((t) => ({ ...t, html: job.template.html }));
      await refreshUser();
      toast.success(job.unlimited || !job.cost ? `${label} complete!` : `${label} complete! ${job.cost} credits used.`);
      return true;
    } catch (e) {
      const status = e.response?.status;
      if (status === 402) { toast.error("Not enough credits."); navigate("/pricing"); }
      else toast.error(e.message || "Failed. Please try again.");
      return false;
    } finally { setBusy(false); setBusyLabel(""); }
  };

  const regenerate = () => runJob(api.post(`/templates/${id}/regenerate`), "Regenerate");
  const upgradeToPremium = async () => {
    if (!window.confirm("Upgrade this site to Premium tier? AI adds scroll animations, a gallery/slider, animated stats, an FAQ accordion and a richer contact form." + (tpl.purchased || user?.unlimited ? "" : " Credits are spent based on the work done."))) return;
    const ok = await runJob(api.post(`/templates/${id}/upgrade`), "Premium upgrade");
    if (ok) setTpl((t) => ({ ...t, quality: "premium" }));
  };
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
  const openShare = () => { setSlugDraft(tpl?.slug || ""); if (tpl?.published) loadStats(); setShareOpen(true); };

  const saveDomain = async () => {
    setSavingDomain(true);
    try {
      const { data } = await api.put(`/templates/${id}/domain`, { domain: domainDraft });
      setTpl((t) => ({ ...t, custom_domain: data.custom_domain, domain_verified: false }));
      setDomainDraft(data.custom_domain);
      setDomainInfo(null);
      toast.success("Domain connected — now point your DNS, then verify.");
    } catch (e) { toast.error(formatApiError(e.response?.data?.detail)); }
    finally { setSavingDomain(false); }
  };
  const verifyDomain = async () => {
    setVerifying(true);
    try {
      const { data } = await api.post(`/templates/${id}/domain/verify`);
      setDomainInfo(data);
      setTpl((t) => ({ ...t, domain_verified: data.domain_verified }));
      if (data.domain_verified) toast.success("Domain verified! Your site is reachable on your domain.");
      else toast.error("DNS isn't pointing here yet — records can take up to 24h to propagate.");
    } catch (e) { toast.error(formatApiError(e.response?.data?.detail)); }
    finally { setVerifying(false); }
  };
  const removeDomain = async () => {
    try {
      await api.delete(`/templates/${id}/domain`);
      setTpl((t) => ({ ...t, custom_domain: null, domain_verified: false }));
      setDomainDraft(""); setDomainInfo(null);
      toast.success("Domain removed.");
    } catch (e) { toast.error("Could not remove domain."); }
  };

  if (!tpl) return <DashboardLayout><div className="p-10 font-mono text-white/40">Loading…</div></DashboardLayout>;

  return (
    <DashboardLayout>
      <div className="flex flex-col h-screen">
        <div className="flex items-center justify-between p-4 border-b border-white/10 bg-surface1 gap-3 flex-wrap">
          <div className="flex items-center gap-3 min-w-0">
            <button onClick={() => navigate("/templates")} data-testid="back-btn" className="p-2 border border-white/15 hover:border-white/40 transition-colors duration-300"><ArrowLeft className="w-4 h-4" /></button>
            <div className="min-w-0">
              <div className="flex items-center gap-2 min-w-0">
                <h1 className="font-display font-bold truncate">{tpl.business_name}</h1>
                {tpl.purchased && (
                  <span data-testid="owned-free-edits-badge" className="shrink-0 text-[10px] font-mono uppercase tracking-wider bg-amber-400 text-black px-2 py-0.5">Owned · Free edits</span>
                )}
              </div>
              <p className="text-white/40 text-xs truncate">{tpl.industry}</p>
            </div>
          </div>
          <div className="flex items-center gap-2 flex-wrap">
            {tpl.purchased && (
              <>
                <button data-testid="make-it-yours-btn" onClick={() => setOnboardOpen(true)}
                  className="flex items-center gap-2 text-sm border border-emerald-400/50 text-emerald-300 hover:border-emerald-300 px-3 py-2 transition-colors duration-300">
                  <ShieldCheck className="w-4 h-4" /> Make it yours
                </button>
                <button data-testid="ownership-cert-btn" onClick={() => setCertOpen(true)}
                  className="flex items-center gap-2 text-sm border border-amber-400/40 text-amber-300 hover:border-amber-300 px-3 py-2 transition-colors duration-300">
                  <Store className="w-4 h-4" /> Ownership
                </button>
              </>
            )}
            {isOwnerUser && !tpl.purchased && (listing ? (
              <button data-testid="delist-market-btn" onClick={delistFromMarket}
                className="flex items-center gap-2 text-sm border border-amber-400/50 text-amber-300 hover:border-amber-300 px-3 py-2 transition-colors duration-300">
                <Store className="w-4 h-4" /> On Market · ${listing.price_usd}
              </button>
            ) : (
              <button data-testid="sell-market-btn" onClick={sellOnMarket} disabled={listingBusy || busy}
                className="flex items-center gap-2 text-sm border border-white/15 hover:border-amber-300 hover:text-amber-300 px-3 py-2 transition-colors duration-300 disabled:opacity-50">
                {listingBusy ? <Loader2 className="w-4 h-4 animate-spin" /> : <Store className="w-4 h-4" />} Sell on Market
              </button>
            ))}
            {tpl.quality === "premium" ? (
              <span data-testid="premium-badge" className="flex items-center gap-1.5 text-[10px] font-mono uppercase tracking-wider bg-amber-400/15 text-amber-300 border border-amber-400/40 px-2.5 py-2">
                <Gem className="w-3.5 h-3.5" /> Premium
              </span>
            ) : (
              <button data-testid="upgrade-premium-btn" onClick={upgradeToPremium} disabled={busy}
                className="flex items-center gap-2 text-sm border border-amber-400/50 text-amber-300 hover:border-amber-300 px-3 py-2 transition-colors duration-300 disabled:opacity-50">
                <Gem className="w-4 h-4" /> Upgrade to Premium
              </button>
            )}
            <button data-testid="regenerate-btn" onClick={regenerate} disabled={busy}
              className="flex items-center gap-2 text-sm border border-white/15 hover:border-brand hover:text-brand px-3 py-2 transition-colors duration-300 disabled:opacity-50">
              <RefreshCw className={`w-4 h-4 ${busy && busyLabel === "Regenerate" ? "animate-spin" : ""}`} /> Regenerate
            </button>
            <button data-testid="visual-edit-btn" onClick={() => setEditorOpen(true)} disabled={busy}
              className="flex items-center gap-2 text-sm bg-brand/15 border border-brand/50 text-brand hover:bg-brand/25 px-3 py-2 transition-colors duration-300 disabled:opacity-50">
              <PencilRuler className="w-4 h-4" /> Edit
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
            {tpl.published && stats && (
              <div data-testid="views-chip" className="hidden md:flex items-center gap-1.5 text-sm border border-white/10 bg-surface2 px-3 py-2 font-mono text-white/60">
                <BarChart2 className="w-4 h-4 text-brand" /> {stats.views_total}
              </div>
            )}
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
              <div className="font-mono text-sm text-white/70">{busyLabel === "Edit" ? "Applying your changes…" : busyLabel === "Premium upgrade" ? "Upgrading to Premium — animations, gallery, FAQ, richer forms…" : "Regenerating your site…"}</div>
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
            <p className="text-white/50 text-sm mb-3">{tpl.purchased ? "You own this template — AI edits are free and unlimited." : "Describe the changes and AI will revise your site. Credits are spent based on the work done."}</p>
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
          <div className="w-full max-w-lg bg-surface2 border border-white/10 p-6 max-h-[88vh] overflow-y-auto" onClick={(e) => e.stopPropagation()} data-testid="share-dialog">
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

                {stats && (
                  <div className="mt-5 border-t border-white/10 pt-4">
                    <div className="flex items-center justify-between mb-2">
                      <div className="text-xs text-white/40 font-mono uppercase">Traffic · last 14 days</div>
                      <div className="text-sm font-mono text-white/70" data-testid="views-total">
                        <span className="text-brand font-bold">{stats.views_total}</span> total views
                      </div>
                    </div>
                    <div className="flex items-end gap-1 h-12" data-testid="views-sparkline">
                      {stats.daily.map((d) => {
                        const max = Math.max(...stats.daily.map((x) => x.views), 1);
                        return (
                          <div key={d.date} title={`${d.date}: ${d.views} views`}
                            className="flex-1 bg-brand/30 hover:bg-brand transition-colors duration-300"
                            style={{ height: `${Math.max((d.views / max) * 100, 5)}%` }} />
                        );
                      })}
                    </div>
                  </div>
                )}

                <div className="mt-5 border-t border-white/10 pt-4">
                  <div className="text-xs text-white/40 font-mono uppercase mb-2">Custom domain</div>
                  {tpl.custom_domain ? (
                    <>
                      <div className="flex items-center justify-between gap-2 flex-wrap">
                        <div className="flex items-center gap-2 min-w-0">
                          <Globe className="w-4 h-4 text-brand shrink-0" />
                          <span data-testid="connected-domain" className="font-mono text-sm truncate">{tpl.custom_domain}</span>
                          {tpl.domain_verified ? (
                            <span data-testid="domain-verified-badge" className="flex items-center gap-1 text-[10px] font-mono uppercase bg-emerald-500/15 text-emerald-400 px-2 py-0.5">
                              <ShieldCheck className="w-3 h-3" /> Verified
                            </span>
                          ) : (
                            <span data-testid="domain-pending-badge" className="flex items-center gap-1 text-[10px] font-mono uppercase bg-white/10 text-white/50 px-2 py-0.5">
                              <Clock className="w-3 h-3" /> Pending DNS
                            </span>
                          )}
                        </div>
                        <div className="flex items-center gap-2">
                          <button data-testid="verify-domain-btn" onClick={verifyDomain} disabled={verifying}
                            className="flex items-center gap-1.5 text-xs border border-white/15 hover:border-brand hover:text-brand px-2.5 py-1.5 transition-colors duration-300 disabled:opacity-50">
                            {verifying ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <ShieldCheck className="w-3.5 h-3.5" />} Verify DNS
                          </button>
                          <button data-testid="remove-domain-btn" onClick={removeDomain}
                            className="text-xs text-white/40 hover:text-neon px-1 py-1.5 transition-colors duration-300">Remove</button>
                        </div>
                      </div>
                      {!tpl.domain_verified && (
                        <div data-testid="dns-instructions" className="mt-3 bg-surface1 border border-white/10 p-3 text-xs text-white/50 space-y-1.5">
                          <div className="text-white/70 font-medium">Point your DNS to SiteGenie, then click Verify:</div>
                          <div className="font-mono">CNAME &nbsp;{tpl.custom_domain} &nbsp;→&nbsp; {appHost}</div>
                          <div>Apex domain (no www)? Use an ALIAS/ANAME record to <span className="font-mono">{appHost}</span>, or an A record to its IP.</div>
                          <div className="text-white/30">DNS changes can take up to 24 hours to propagate.</div>
                          {domainInfo && !domainInfo.domain_verified && (
                            <div className="text-neon/80 pt-1">
                              {domainInfo.domain_ips?.length
                                ? `Your domain currently resolves to ${domainInfo.domain_ips.join(", ")} — expected ${domainInfo.expected_ips?.join(", ") || appHost}.`
                                : "Your domain doesn't resolve yet — check that the DNS record was saved."}
                            </div>
                          )}
                        </div>
                      )}
                    </>
                  ) : (
                    <>
                      <div className="flex items-stretch gap-2">
                        <input data-testid="domain-input" value={domainDraft}
                          onChange={(e) => setDomainDraft(e.target.value)}
                          className="flex-1 bg-surface1 border border-white/10 px-3 py-2 text-sm font-mono text-white outline-none focus:border-brand"
                          placeholder="www.mybusiness.com" />
                        <button data-testid="connect-domain-btn" onClick={saveDomain} disabled={savingDomain || !domainDraft.trim()}
                          className="flex items-center gap-2 text-sm border border-white/15 hover:border-brand hover:text-brand px-3 py-2 transition-colors duration-300 disabled:opacity-40">
                          {savingDomain ? <Loader2 className="w-4 h-4 animate-spin" /> : "Connect"}
                        </button>
                      </div>
                      <p className="text-white/30 text-xs mt-2">Use your own domain instead of the SiteGenie link. You'll get DNS instructions after connecting.</p>
                    </>
                  )}
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
      {onboardOpen && tpl && (
        <OwnershipOnboarding
          tpl={tpl}
          onClose={() => { setOnboardOpen(false); if (searchParams.get("onboard")) setSearchParams({}, { replace: true }); }}
          onUpdated={(patch) => setTpl((t) => ({ ...t, ...patch }))}
        />
      )}
      {certOpen && (
        <OwnershipCertificate templateId={id} onClose={() => setCertOpen(false)} />
      )}
      {editorOpen && tpl && (
        <VisualEditor
          templateId={id}
          initialHtml={tpl.html}
          onClose={() => setEditorOpen(false)}
          onSaved={(html) => setTpl((t) => ({ ...t, html }))}
        />
      )}
    </DashboardLayout>
  );
}
