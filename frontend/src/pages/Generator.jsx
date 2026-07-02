import { useState } from "react";
import { useNavigate } from "react-router-dom";
import DashboardLayout from "@/components/DashboardLayout";
import { api, formatApiError } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { toast } from "sonner";
import { Sparkles, Loader2, Eye, Download, Save, Zap } from "lucide-react";

const STYLES = ["modern", "minimal", "bold", "elegant", "playful", "corporate"];

export default function Generator() {
  const { user, refreshUser } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState({
    business_name: "", industry: "", description: "",
    style: "modern", primary_color: "#0055FF", contact_email: "", phone: "",
  });
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);

  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }));

  const generate = async (e) => {
    e.preventDefault();
    if ((user?.credits ?? 0) < 1) {
      toast.error("You're out of credits. Please buy more.");
      navigate("/pricing");
      return;
    }
    setLoading(true); setResult(null);
    try {
      const { data } = await api.post("/templates/generate", form);
      const jobId = data.job_id;
      // poll for completion (generation takes ~1-2 min)
      let attempts = 0;
      const poll = async () => {
        attempts += 1;
        if (attempts > 80) { setLoading(false); toast.error("Generation timed out. Please try again."); return; }
        try {
          const { data: s } = await api.get(`/templates/job/${jobId}`);
          if (s.status === "done" && s.template) {
            setResult(s.template);
            await refreshUser();
            setLoading(false);
            toast.success("Website generated! 1 credit used.");
            return;
          }
          if (s.status === "error") {
            setLoading(false);
            toast.error(s.error || "Generation failed.");
            return;
          }
          setTimeout(poll, 2500);
        } catch (err) {
          setTimeout(poll, 2500);
        }
      };
      setTimeout(poll, 3000);
    } catch (e) {
      setLoading(false);
      const status = e.response?.status;
      if (status === 402) { toast.error("Not enough credits."); navigate("/pricing"); }
      else toast.error(formatApiError(e.response?.data?.detail) || e.message);
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
              <span className="font-mono text-sm" data-testid="generator-credits">{user?.credits ?? 0}</span>
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
            <button data-testid="generate-btn" disabled={loading}
              className="w-full flex items-center justify-center gap-2 bg-brand hover:bg-brand-hover py-4 font-medium transition-colors duration-300 disabled:opacity-60">
              {loading ? <><Loader2 className="w-5 h-5 animate-spin" /> Generating your website…</> : <><Sparkles className="w-5 h-5" /> Generate website (1 credit)</>}
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
              <div className="h-full flex flex-col items-center justify-center gap-4 bg-surface2 text-white/50">
                <Loader2 className="w-10 h-10 animate-spin text-brand" />
                <div className="font-mono text-sm">Designing your site…</div>
              </div>
            ) : result ? (
              <iframe data-testid="preview-iframe" title="preview" srcDoc={result.html} className="w-full h-full" style={{ minHeight: 500 }} />
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
