import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import DashboardLayout from "@/components/DashboardLayout";
import { api, formatApiError, pollGenerationJob } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { toast } from "sonner";
import { Sparkles, Loader2, Eye, Download, Save, Zap, Gauge, Gem } from "lucide-react";

const STYLES = ["modern", "minimal", "bold", "elegant", "playful", "corporate"];

export default function Generator() {
  const { user, refreshUser } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState({
    business_name: "", industry: "", description: "",
    style: "modern", primary_color: "#0055FF", contact_email: "", phone: "",
    target_audience: "", key_services: "", brand_keywords: "", pages: "", quality: "quality",
  });
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);

  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }));

  useEffect(() => {
    const raw = sessionStorage.getItem("sg_pending_brief");
    if (!raw) return;
    sessionStorage.removeItem("sg_pending_brief");
    try {
      const b = JSON.parse(raw);
      setForm((f) => ({
        ...f,
        description: b.description || f.description,
        business_name: b.business_name || f.business_name,
        industry: b.industry || f.industry,
        brand_keywords: b.brand_keywords || f.brand_keywords,
        style: b.style || f.style,
      }));
      toast.info(b.business_name ? `Brief loaded for ${b.business_name} — review & generate.` : "Your idea is loaded — add a business name & industry, then generate.");
    } catch (e) {}
  }, []);

  const generate = async (e) => {
    e.preventDefault();
    if ((user?.credits ?? 0) < 1 && !user?.unlimited) {
      toast.error("You're out of credits. Purchase a credit pack to continue.");
      navigate("/pricing");
      return;
    }
    setLoading(true); setResult(null);
    try {
      const { data } = await api.post("/templates/generate", form);
      const job = await pollGenerationJob(data.job_id);
      setResult(job.template);
      await refreshUser();
      setLoading(false);
      toast.success(job.unlimited ? "Website generated!" : `Website generated! ${job.cost} credits used.`);
    } catch (e) {
      setLoading(false);
      const status = e.response?.status;
      if (status === 402) { toast.error("Not enough credits."); navigate("/pricing"); }
      else toast.error(e.message || formatApiError(e.response?.data?.detail));
    }
  };

  const download = () => {
    if (!result) return;
    const blob = new Blob([result.html], { type: "text/html" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${form.business_name.replace(/\s+/g, "-").toLowerCase() || "website"}.html`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <DashboardLayout>
      <div className="grid lg:grid-cols-2 min-h-[calc(100vh-0px)]">
        {/* left: prompt */}
        <div className="p-6 md:p-10 border-r border-white/10">
          <div className="flex items-center justify-between mb-6">
            <div>
              <div className="font-mono text-xs text-white/40 uppercase tracking-wider">AI Generator</div>
              <h1 className="font-display text-3xl font-bold mt-1">Describe your business</h1>
            </div>
            <div className="flex items-center gap-2 border border-white/10 px-3 py-2 bg-surface1">
              <Zap className="w-4 h-4 text-brand" />
              <span className="font-mono text-sm" data-testid="generator-credits">{user?.unlimited ? "∞" : (user?.credits ?? 0)}</span>
            </div>
          </div>

          <form onSubmit={generate} className="space-y-5">
            <Field label="Business name">
              <input data-testid="gen-business-name" required value={form.business_name} onChange={set("business_name")} className={inputCls} placeholder="Bloom & Co. Florist" />
            </Field>
            <Field label="Industry / type">
              <input data-testid="gen-industry" required value={form.industry} onChange={set("industry")} className={inputCls} placeholder="Florist, Restaurant, Gym, Law firm…" />
            </Field>
            <Field label="Description">
              <textarea data-testid="gen-description" required rows={4} value={form.description} onChange={set("description")} className={inputCls} placeholder="What do you offer? Who are your customers? What makes you special?" />
            </Field>
            <div className="border-t border-white/10 pt-4">
              <div className="text-xs text-brand font-mono uppercase mb-3 flex items-center gap-2"><Sparkles className="w-3.5 h-3.5" /> Help the AI go deeper (optional)</div>
              <div className="space-y-4">
                <Field label="Target audience">
                  <input data-testid="gen-audience" value={form.target_audience} onChange={set("target_audience")} className={inputCls} placeholder="e.g. busy professionals, brides-to-be, local families" />
                </Field>
                <Field label="Key services / products">
                  <input data-testid="gen-services" value={form.key_services} onChange={set("key_services")} className={inputCls} placeholder="e.g. wedding flowers, weekly subscriptions, workshops" />
                </Field>
                <div className="grid grid-cols-2 gap-4">
                  <Field label="Brand vibe / keywords">
                    <input data-testid="gen-keywords" value={form.brand_keywords} onChange={set("brand_keywords")} className={inputCls} placeholder="e.g. warm, earthy, premium" />
                  </Field>
                  <Field label="Sections wanted">
                    <input data-testid="gen-pages" value={form.pages} onChange={set("pages")} className={inputCls} placeholder="e.g. hero, services, gallery, FAQ" />
                  </Field>
                </div>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <Field label="Style">
                <select data-testid="gen-style" value={form.style} onChange={set("style")} className={inputCls}>
                  {STYLES.map((s) => <option key={s} value={s}>{s}</option>)}
                </select>
              </Field>
              <Field label="Brand color">
                <div className="flex items-center gap-2 mt-1">
                  <input data-testid="gen-color" type="color" value={form.primary_color} onChange={set("primary_color")} className="w-12 h-11 bg-surface1 border border-white/10 cursor-pointer" />
                  <input value={form.primary_color} onChange={set("primary_color")} className={`${inputCls} font-mono`} />
                </div>
              </Field>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <Field label="Contact email (optional)">
                <input data-testid="gen-email" value={form.contact_email} onChange={set("contact_email")} className={inputCls} placeholder="hello@business.com" />
              </Field>
              <Field label="Phone (optional)">
                <input data-testid="gen-phone" value={form.phone} onChange={set("phone")} className={inputCls} placeholder="+1 555 000 0000" />
              </Field>
            </div>
            <div className="border-t border-white/10 pt-4">
              <div className="text-xs text-white/50 font-mono uppercase mb-3">Generation mode</div>
              <div className="grid grid-cols-2 gap-3" data-testid="quality-toggle">
                <button type="button" data-testid="mode-quality" onClick={() => setForm((f) => ({ ...f, quality: "quality" }))}
                  className={`text-left p-4 border transition-colors duration-300 ${form.quality === "quality" ? "border-brand bg-brand/10" : "border-white/10 hover:border-white/30"}`}>
                  <div className="flex items-center gap-2 font-medium"><Gem className={`w-4 h-4 ${form.quality === "quality" ? "text-brand" : "text-white/50"}`} /> Quality</div>
                  <p className="text-xs text-white/40 mt-1">2-pass AI (strategist + builder). Deepest, most polished. ~1–2 min.</p>
                </button>
                <button type="button" data-testid="mode-economy" onClick={() => setForm((f) => ({ ...f, quality: "economy" }))}
                  className={`text-left p-4 border transition-colors duration-300 ${form.quality === "economy" ? "border-neon bg-neon/10" : "border-white/10 hover:border-white/30"}`}>
                  <div className="flex items-center gap-2 font-medium"><Gauge className={`w-4 h-4 ${form.quality === "economy" ? "text-neon" : "text-white/50"}`} /> Economy</div>
                  <p className="text-xs text-white/40 mt-1">Fast single-pass draft. Uses fewer credits. Great for quick concepts.</p>
                </button>
              </div>
            </div>
            <button data-testid="generate-btn" disabled={loading}
              className="w-full flex items-center justify-center gap-2 bg-brand hover:bg-brand-hover py-4 font-medium transition-colors duration-300 disabled:opacity-60">
              {loading ? <><Loader2 className="w-5 h-5 animate-spin" /> Crafting your website…</> : <><Sparkles className="w-5 h-5" /> Generate website</>}
            </button>
          </form>
        </div>

        {/* right: preview */}
        <div className="bg-surface1 p-6 md:p-10 flex flex-col">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-display text-lg font-bold flex items-center gap-2"><Eye className="w-5 h-5 text-white/60" /> Live Preview</h2>
            {result && (
              <div className="flex items-center gap-2">
                <button data-testid="preview-download" onClick={download} className="flex items-center gap-2 text-sm border border-white/15 hover:border-white/40 px-3 py-2 transition-colors duration-300"><Download className="w-4 h-4" /> HTML</button>
                <button data-testid="preview-open" onClick={() => navigate(`/templates/${result.template_id}`)} className="flex items-center gap-2 text-sm bg-brand hover:bg-brand-hover px-3 py-2 transition-colors duration-300"><Save className="w-4 h-4" /> Open</button>
              </div>
            )}
          </div>
          <div className="flex-1 border border-white/10 bg-white overflow-hidden min-h-[500px]">
            {loading ? (
              <div className="h-full flex flex-col items-center justify-center gap-4 bg-surface2 text-white/50 p-8 text-center">
                <Loader2 className="w-10 h-10 animate-spin text-brand" />
                <div className="font-mono text-sm">Researching your brand & crafting your site…</div>
                <div className="text-xs text-white/30">{form.quality === "economy" ? "Fast single-pass build. ~30–60 sec." : "Our AI strategist writes a brief, then builds. ~1–2 min."}</div>
              </div>
            ) : result ? (
              <iframe data-testid="preview-iframe" title="preview" sandbox="allow-scripts" srcDoc={result.html} className="w-full h-full" style={{ minHeight: 500 }} />
            ) : (
              <div className="h-full flex flex-col items-center justify-center gap-3 bg-surface2 text-white/40 p-8 text-center">
                <Sparkles className="w-10 h-10" />
                <div className="font-mono text-sm">Your generated website will appear here.</div>
              </div>
            )}
          </div>
        </div>
      </div>
    </DashboardLayout>
  );
}

const inputCls = "mt-1 w-full bg-surface2 border border-white/10 focus:border-brand px-4 py-3 outline-none transition-colors duration-300 text-white";
function Field({ label, children }) {
  return (
    <label className="block">
      <span className="text-xs text-white/50 font-mono uppercase">{label}</span>
      {children}
    </label>
  );
}
