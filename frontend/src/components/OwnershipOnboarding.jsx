import { useState, useEffect } from "react";
import { api, formatApiError } from "@/lib/api";
import { toast } from "sonner";
import { X, Loader2, Wand2, Globe, FileArchive, CheckCircle2, ShieldCheck, Sparkles, ArrowRight } from "lucide-react";

/**
 * "Make it yours" — post-purchase onboarding for an exclusively-owned site.
 * Steps: 1) set your details  2) publish  3) done (with certificate + ZIP).
 */
export function OwnershipOnboarding({ tpl, onClose, onUpdated }) {
  const [step, setStep] = useState(1);
  const [busy, setBusy] = useState(false);
  const [form, setForm] = useState({
    business_name: tpl.business_name || "",
    contact_email: tpl.contact_email || "",
    phone: tpl.phone || "",
    primary_color: tpl.primary_color || "#0055FF",
  });
  const [publishedUrl, setPublishedUrl] = useState(tpl.slug ? `${window.location.origin}/api/p/${tpl.slug}` : "");

  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }));

  const saveDetails = async () => {
    setBusy(true);
    try {
      const { data } = await api.put(`/templates/${tpl.template_id}/details`, form);
      onUpdated?.(data);
      toast.success("Your details are in — the site now reflects them.");
      setStep(2);
    } catch (e) {
      toast.error(formatApiError(e.response?.data?.detail) || "Couldn't save details.");
    } finally { setBusy(false); }
  };

  const publish = async () => {
    setBusy(true);
    try {
      const { data } = await api.post(`/templates/${tpl.template_id}/publish`);
      const url = `${window.location.origin}/api/p/${data.slug}`;
      setPublishedUrl(url);
      onUpdated?.({ published: true, slug: data.slug });
      toast.success("Your site is live!");
      setStep(3);
    } catch (e) {
      toast.error("Couldn't publish. You can publish anytime from the Publish button.");
    } finally { setBusy(false); }
  };

  const finish = async () => {
    await api.post(`/templates/${tpl.template_id}/onboarded`).catch(() => {});
    onUpdated?.({ onboarded: true });
    onClose();
  };

  const downloadZip = async () => {
    try {
      const res = await api.get(`/templates/${tpl.template_id}/download-zip`, { responseType: "blob" });
      const url = URL.createObjectURL(res.data);
      const a = document.createElement("a");
      a.href = url; a.download = `${(form.business_name || "website").replace(/\s+/g, "-").toLowerCase()}.zip`; a.click();
      URL.revokeObjectURL(url);
      toast.success("ZIP downloaded");
    } catch { toast.error("Could not build ZIP."); }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-6 bg-black/75 backdrop-blur-sm" data-testid="onboarding-modal">
      <div className="w-full max-w-lg bg-surface2 border border-white/10 p-6 max-h-[90vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between mb-1">
          <div className="flex items-center gap-2">
            <ShieldCheck className="w-5 h-5 text-emerald-400" />
            <h2 className="font-display text-xl font-bold">Make it yours</h2>
          </div>
          <button onClick={onClose} className="text-white/50 hover:text-white"><X className="w-5 h-5" /></button>
        </div>
        {/* step dots */}
        <div className="flex items-center gap-2 mb-5 mt-2">
          {[1, 2, 3].map((s) => (
            <div key={s} className={`h-1.5 flex-1 rounded-full transition-colors duration-300 ${
              s <= step ? "bg-brand" : "bg-white/10"}`} />
          ))}
        </div>

        {step === 1 && (
          <div data-testid="onboard-step-details">
            <p className="text-white/50 text-sm mb-4">This site is now exclusively yours. Set your business details — we'll drop them straight into the site. You can change anything else with AI edits.</p>
            <div className="space-y-3">
              <div>
                <label className="text-xs text-white/40 font-mono uppercase">Business name</label>
                <input data-testid="onboard-name" value={form.business_name} onChange={set("business_name")}
                  className="mt-1 w-full bg-surface1 border border-white/10 focus:border-brand px-3 py-2.5 text-sm outline-none transition-colors duration-300" />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs text-white/40 font-mono uppercase">Contact email</label>
                  <input data-testid="onboard-email" value={form.contact_email} onChange={set("contact_email")}
                    placeholder="you@business.com"
                    className="mt-1 w-full bg-surface1 border border-white/10 focus:border-brand px-3 py-2.5 text-sm outline-none transition-colors duration-300" />
                </div>
                <div>
                  <label className="text-xs text-white/40 font-mono uppercase">Phone</label>
                  <input data-testid="onboard-phone" value={form.phone} onChange={set("phone")}
                    placeholder="+1 555 000 0000"
                    className="mt-1 w-full bg-surface1 border border-white/10 focus:border-brand px-3 py-2.5 text-sm outline-none transition-colors duration-300" />
                </div>
              </div>
              <div className="flex items-center gap-3">
                <div>
                  <label className="text-xs text-white/40 font-mono uppercase">Brand color</label>
                  <input data-testid="onboard-color" type="color" value={form.primary_color} onChange={set("primary_color")}
                    className="mt-1 block h-10 w-16 bg-surface1 border border-white/10 cursor-pointer" />
                </div>
                <p className="text-white/30 text-xs mt-4 flex items-center gap-1.5">
                  <Wand2 className="w-3.5 h-3.5" /> Want deeper changes? Use “Edit with AI” for copy, sections & layout.
                </p>
              </div>
            </div>
            <div className="flex items-center justify-between mt-6">
              <button onClick={() => setStep(2)} className="text-sm text-white/40 hover:text-white transition-colors duration-300">Skip for now</button>
              <button data-testid="onboard-save-details" onClick={saveDetails} disabled={busy}
                className="flex items-center gap-2 bg-brand hover:bg-brand-hover px-5 py-2.5 text-sm transition-colors duration-300 disabled:opacity-50">
                {busy ? <Loader2 className="w-4 h-4 animate-spin" /> : <>Save & continue <ArrowRight className="w-4 h-4" /></>}
              </button>
            </div>
          </div>
        )}

        {step === 2 && (
          <div data-testid="onboard-step-publish" className="text-center py-2">
            <Globe className="w-10 h-10 text-brand mx-auto" />
            <h3 className="font-display text-lg font-bold mt-4">Take it live</h3>
            <p className="text-white/50 text-sm mt-2">Publish now to get a shareable public link. You can connect a custom domain and view analytics right after.</p>
            <button data-testid="onboard-publish" onClick={publish} disabled={busy}
              className="mt-5 w-full flex items-center justify-center gap-2 bg-neon hover:bg-neon-hover py-3 text-sm transition-colors duration-300 disabled:opacity-50">
              {busy ? <Loader2 className="w-4 h-4 animate-spin" /> : <Globe className="w-4 h-4" />} Publish my site
            </button>
            <button onClick={() => setStep(3)} className="mt-3 text-sm text-white/40 hover:text-white transition-colors duration-300">I'll publish later</button>
          </div>
        )}

        {step === 3 && (
          <div data-testid="onboard-step-done" className="text-center py-2">
            <CheckCircle2 className="w-12 h-12 text-emerald-400 mx-auto" />
            <h3 className="font-display text-xl font-bold mt-4">You're all set 🎉</h3>
            <p className="text-white/50 text-sm mt-2">
              {publishedUrl ? "Your website is live and fully yours." : "Your website is ready and fully yours."} Edit it anytime with AI, connect a domain, or download the source.
            </p>
            {publishedUrl && (
              <a href={publishedUrl} target="_blank" rel="noopener noreferrer"
                className="mt-4 inline-block text-sm font-mono text-brand hover:underline break-all">{publishedUrl}</a>
            )}
            <div className="grid grid-cols-2 gap-2 mt-5">
              <button data-testid="onboard-download-zip" onClick={downloadZip}
                className="flex items-center justify-center gap-2 border border-white/15 hover:border-white/40 py-2.5 text-sm transition-colors duration-300">
                <FileArchive className="w-4 h-4 text-neon" /> Download ZIP
              </button>
              <button data-testid="onboard-finish" onClick={finish}
                className="flex items-center justify-center gap-2 bg-brand hover:bg-brand-hover py-2.5 text-sm transition-colors duration-300">
                <Sparkles className="w-4 h-4" /> Start editing
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

/** Compact ownership certificate shown on owned sites. */
export function OwnershipCertificate({ templateId, onClose }) {
  const [cert, setCert] = useState(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    api.get(`/templates/${templateId}/certificate`)
      .then(({ data }) => setCert(data))
      .catch(() => setError(true));
  }, [templateId]);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-6 bg-black/75 backdrop-blur-sm" onClick={onClose} data-testid="certificate-modal">
      <div className="w-full max-w-md bg-surface2 border border-amber-400/30 p-8 text-center relative" onClick={(e) => e.stopPropagation()}>
        <button onClick={onClose} className="absolute top-4 right-4 text-white/40 hover:text-white"><X className="w-5 h-5" /></button>
        <ShieldCheck className="w-12 h-12 text-amber-400 mx-auto" />
        <div className="text-[10px] font-mono uppercase tracking-[0.2em] text-amber-300/70 mt-4">Certificate of Ownership</div>
        {error ? (
          <p className="text-white/50 text-sm mt-4">No ownership certificate found for this site.</p>
        ) : !cert ? (
          <Loader2 className="w-5 h-5 animate-spin text-white/40 mx-auto mt-6" />
        ) : (
          <>
            <h3 className="font-display text-2xl font-bold mt-3">{cert.title}</h3>
            <p className="text-white/50 text-sm mt-1">has been exclusively transferred to</p>
            <p className="font-display text-lg font-semibold mt-1">{cert.owner_name}</p>
            <div className="border-t border-white/10 mt-6 pt-4 grid grid-cols-2 gap-3 text-left">
              <div>
                <div className="text-[10px] font-mono uppercase text-white/30">Transferred</div>
                <div className="text-sm mt-0.5">{new Date(cert.transferred_at).toLocaleDateString()}</div>
              </div>
              <div>
                <div className="text-[10px] font-mono uppercase text-white/30">Price</div>
                <div className="text-sm mt-0.5">${cert.price_usd}</div>
              </div>
              <div className="col-span-2">
                <div className="text-[10px] font-mono uppercase text-white/30">Certificate ID</div>
                <div className="text-xs font-mono mt-0.5 text-white/60 break-all">{cert.cert_id}</div>
              </div>
            </div>
            <p className="text-white/30 text-[11px] mt-5">This site is one-of-one and no longer sold on the Market. You own it in full with free unlimited AI edits.</p>
          </>
        )}
      </div>
    </div>
  );
}
