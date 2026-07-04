import { useState, useEffect, useRef, useMemo } from "react";
import { useNavigate } from "react-router-dom";
import DashboardLayout from "@/components/DashboardLayout";
import { api, formatApiError, pollGenerationJob } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { toast } from "sonner";
import {
  Sparkles, Loader2, Eye, Download, Save, Zap, Gauge, Gem, Crown,
  ArrowUp, RotateCcw, Settings2, Palette, ChevronDown, Bot, Check,
} from "lucide-react";

const STYLES = ["modern", "minimal", "bold", "elegant", "playful", "corporate"];

const VIBES = [
  { label: "Warm & cozy", keywords: "warm, cozy, welcoming", style: "modern" },
  { label: "Premium & elegant", keywords: "premium, elegant, refined", style: "elegant" },
  { label: "Playful & bold", keywords: "playful, bold, vibrant", style: "playful" },
  { label: "Clean & minimal", keywords: "clean, minimal, airy", style: "minimal" },
  { label: "Modern & techy", keywords: "modern, sleek, innovative", style: "modern" },
  { label: "Classic & trustworthy", keywords: "classic, trustworthy, established", style: "corporate" },
];

const MODELS = [
  { id: "claude-sonnet-4-6", name: "Sonnet 4.6", desc: "Deepest reasoning · slower" },
  { id: "claude-haiku-4-5", name: "Haiku 4.5", desc: "Fast & efficient" },
];

const TIERS = [
  { id: "economy", name: "Economy", cost: "~2 credits", icon: Gauge, color: "neon",
    desc: "Single fast pass. Solid starter draft." },
  { id: "quality", name: "Quality", cost: "~5 credits", icon: Gem, color: "brand",
    desc: "Strategist + builder 2-pass. Polished." },
  { id: "premium", name: "Premium", cost: "~8 credits", icon: Crown, color: "amber",
    desc: "Adds gallery, counters, animations, richer form." },
];

const DEFAULT_FORM = {
  business_name: "", industry: "", description: "",
  style: "modern", primary_color: "#0055FF", contact_email: "", phone: "",
  target_audience: "", key_services: "", brand_keywords: "", pages: "",
  quality: "quality", model: "claude-sonnet-4-6",
};

export default function Generator() {
  const { user, refreshUser } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState(DEFAULT_FORM);
  const [messages, setMessages] = useState([]);
  const [stage, setStage] = useState("idea");
  const [input, setInput] = useState("");
  const [typing, setTyping] = useState(false);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [advOpen, setAdvOpen] = useState(false);
  const endRef = useRef(null);
  const inputRef = useRef(null);
  const seededRef = useRef(false);

  const setField = (k, v) => setForm((f) => ({ ...f, [k]: v }));

  const pushAi = (text, delay = 700) => new Promise((resolve) => {
    setTyping(true);
    setTimeout(() => {
      setMessages((m) => [...m, { role: "ai", text }]);
      setTyping(false);
      resolve();
    }, delay);
  });
  const pushUser = (text) => setMessages((m) => [...m, { role: "user", text }]);

  // Auto-scroll
  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }, [messages, typing, result]);

  // Seed brief from Landing (once)
  useEffect(() => {
    if (seededRef.current) return;
    seededRef.current = true;
    const raw = sessionStorage.getItem("sg_pending_brief");
    if (raw) {
      sessionStorage.removeItem("sg_pending_brief");
      try {
        const b = JSON.parse(raw);
        const next = {
          ...DEFAULT_FORM,
          description: b.description || "",
          business_name: b.business_name || "",
          industry: b.industry || "",
          brand_keywords: b.brand_keywords || "",
          style: b.style || DEFAULT_FORM.style,
        };
        setForm(next);
        const missing = [];
        if (!next.business_name) missing.push("name");
        if (!next.industry) missing.push("industry");
        if (missing.length === 0) {
          setStage("ready");
          setMessages([
            { role: "ai", text: `Loaded your brief for ${next.business_name}. Pick a quality tier and hit Generate — or refine the brief on the right.` },
          ]);
        } else {
          setStage(missing[0] === "name" ? "name" : "industry");
          setMessages([
            { role: "ai", text: `Got your idea: "${next.description.slice(0, 120)}${next.description.length > 120 ? "…" : ""}"` },
            { role: "ai", text: missing[0] === "name"
                ? "What's the business called?"
                : "What industry or type of business is it?" },
          ]);
        }
        return;
      } catch (_) { /* ignore bad JSON */ }
    }
    setMessages([
      { role: "ai", text: user?.name
          ? `Hey ${user.name.split(" ")[0]} — I'm your build assistant. Tell me about the business we're creating today.`
          : "Hi! I'm your build assistant. Tell me about the business we're creating today." },
    ]);
  }, []);

  const advanceAfterVibe = async () => {
    setStage("ready");
    await pushAi("Perfect — I've got everything I need. Pick a model + tier below, then hit Generate. You can still tweak advanced fields in the brief panel.");
  };

  const send = async (raw) => {
    const text = (raw ?? input).trim();
    if (!text || typing || stage === "ready") return;
    pushUser(text);
    setInput("");

    if (stage === "idea") {
      setField("description", text);
      if (!form.business_name) {
        setStage("name");
        await pushAi("Love it. What's the business called?");
      } else if (!form.industry) {
        setStage("industry");
        await pushAi("Got it. What industry is it — florist, coffee shop, law firm, gym…?");
      } else {
        setStage("vibe");
        await pushAi("Nice. Pick a brand vibe below, or describe one.");
      }
    } else if (stage === "name") {
      setField("business_name", text);
      if (!form.industry) {
        setStage("industry");
        await pushAi(`${text} — got it. What industry is it — florist, coffee shop, law firm, gym…?`);
      } else {
        setStage("vibe");
        await pushAi("Great. Pick a brand vibe below, or describe one.");
      }
    } else if (stage === "industry") {
      setField("industry", text);
      setStage("vibe");
      await pushAi("Pick a brand vibe below, or describe one in your own words.");
    } else if (stage === "vibe") {
      setField("brand_keywords", text);
      await advanceAfterVibe();
    }
  };

  const pickVibe = async (v) => {
    if (typing) return;
    pushUser(v.label);
    setField("brand_keywords", v.keywords);
    setField("style", v.style);
    await advanceAfterVibe();
  };

  const restart = () => {
    setMessages([]);
    setForm(DEFAULT_FORM);
    setStage("idea");
    setInput("");
    setResult(null);
    setTimeout(() => {
      setMessages([{ role: "ai", text: "Fresh start. Tell me about the business we're creating." }]);
      inputRef.current?.focus();
    }, 100);
  };

  const generate = async () => {
    if ((user?.credits ?? 0) < 1 && !user?.unlimited) {
      toast.error("You're out of credits. Purchase a credit pack to continue.");
      navigate("/pricing");
      return;
    }
    if (!form.business_name || !form.industry || !form.description) {
      toast.error("I still need a business name, industry and short description.");
      return;
    }
    setLoading(true);
    setResult(null);
    pushUser("Generate the website");
    setTyping(true);
    setMessages((m) => [...m, { role: "ai", text: `Building your ${form.quality} tier site${form.quality === "premium" ? " (this includes a polish pass)" : ""} — hang tight.` }]);
    setTyping(false);
    try {
      const { data } = await api.post("/templates/generate", form);
      const job = await pollGenerationJob(data.job_id);
      setResult(job.template);
      await refreshUser();
      setLoading(false);
      await pushAi(job.unlimited ? "Done — your website is live in the preview." : `Done — used ${job.cost} credits. Preview is on the right.`, 300);
      toast.success("Website generated!");
    } catch (e) {
      setLoading(false);
      const status = e.response?.status;
      if (status === 402) { toast.error("Not enough credits."); navigate("/pricing"); }
      else {
        const msg = e.message || formatApiError(e.response?.data?.detail);
        await pushAi(`Something went sideways: ${msg}. Try Economy tier for a faster build.`, 300);
        toast.error(msg);
      }
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

  const briefReady = form.business_name && form.industry && form.description;
  const placeholder = useMemo(() => {
    if (stage === "idea") return "A cozy neighborhood florist making seasonal bouquets…";
    if (stage === "name") return "e.g. Bloom & Co.";
    if (stage === "industry") return "e.g. Florist, coffee shop, law firm…";
    if (stage === "vibe") return "e.g. warm and welcoming with earthy tones";
    return loading ? "Building…" : "Refine the brief or say Generate";
  }, [stage, loading]);

  return (
    <DashboardLayout>
      <div className="grid lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)] min-h-[calc(100vh-0px)]">
        {/* LEFT: Chat + brief + controls */}
        <div className="flex flex-col border-r border-white/10">
          {/* Header */}
          <div className="flex items-center justify-between px-6 md:px-10 py-5 border-b border-white/10 bg-base">
            <div className="flex items-center gap-3">
              <div className="relative w-10 h-10 bg-brand flex items-center justify-center">
                <Bot className="w-5 h-5" />
                <span className="absolute -bottom-0.5 -right-0.5 w-2.5 h-2.5 rounded-full bg-emerald-400 border-2 border-base" />
              </div>
              <div>
                <div className="font-mono text-xs text-white/40 uppercase tracking-wider">AI Generator</div>
                <div className="font-display font-semibold text-sm">Chat with your build assistant</div>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <button data-testid="chat-restart-btn" onClick={restart}
                className="flex items-center gap-1.5 text-xs font-mono text-white/45 hover:text-white border border-white/10 hover:border-white/25 px-2.5 py-2 transition-colors duration-300">
                <RotateCcw className="w-3.5 h-3.5" /> Restart
              </button>
              <div className="flex items-center gap-2 border border-white/10 px-3 py-2 bg-surface1">
                <Zap className="w-4 h-4 text-brand" />
                <span className="font-mono text-sm" data-testid="generator-credits">{user?.unlimited ? "∞" : (user?.credits ?? 0)}</span>
              </div>
            </div>
          </div>

          {/* Chat thread */}
          <div className="flex-1 overflow-y-auto px-6 md:px-10 py-6 space-y-3" data-testid="chat-thread">
            {messages.map((m, i) => m.role === "ai" ? (
              <div key={i} className="flex items-start gap-2.5" data-testid={`gen-chat-ai-${i}`}>
                <div className="w-7 h-7 bg-brand flex items-center justify-center shrink-0 mt-0.5"><Bot className="w-4 h-4" /></div>
                <div className="rounded-2xl rounded-tl-sm bg-surface1 border border-white/10 px-4 py-3 text-sm text-white/85 max-w-[85%] whitespace-pre-line">{m.text}</div>
              </div>
            ) : (
              <div key={i} className="flex justify-end" data-testid={`gen-chat-user-${i}`}>
                <div className="rounded-2xl rounded-tr-sm bg-brand px-4 py-3 text-sm max-w-[85%]">{m.text}</div>
              </div>
            ))}
            {typing && (
              <div className="flex items-start gap-2.5" data-testid="gen-chat-typing">
                <div className="w-7 h-7 bg-brand flex items-center justify-center shrink-0 mt-0.5"><Bot className="w-4 h-4" /></div>
                <div className="rounded-2xl rounded-tl-sm bg-surface1 border border-white/10 px-4 py-3.5 flex gap-1.5 items-center">
                  <span className="w-1.5 h-1.5 rounded-full bg-white/50 animate-bounce" />
                  <span className="w-1.5 h-1.5 rounded-full bg-white/50 animate-bounce [animation-delay:0.15s]" />
                  <span className="w-1.5 h-1.5 rounded-full bg-white/50 animate-bounce [animation-delay:0.3s]" />
                </div>
              </div>
            )}

            {/* Vibe chips inline */}
            {stage === "vibe" && !typing && (
              <div className="pl-9 flex flex-wrap gap-2 pt-1" data-testid="gen-vibe-chips">
                {VIBES.map((v, i) => (
                  <button key={v.label} data-testid={`gen-vibe-${i}`} onClick={() => pickVibe(v)}
                    className="rounded-full border border-white/12 bg-surface1/70 px-3.5 py-1.5 text-xs text-white/60 hover:text-white hover:border-brand/60 transition-colors duration-300">
                    {v.label}
                  </button>
                ))}
              </div>
            )}
            <div ref={endRef} />
          </div>

          {/* Brief summary + advanced (collapsible) */}
          <div className="border-t border-white/10 bg-surface1/40 px-6 md:px-10 py-4">
            <button data-testid="brief-toggle" onClick={() => setAdvOpen(!advOpen)}
              className="w-full flex items-center justify-between text-left group">
              <div className="flex items-center gap-2 min-w-0">
                <Settings2 className="w-4 h-4 text-brand shrink-0" />
                <div className="text-xs font-mono uppercase tracking-wider text-white/50 shrink-0">Brief</div>
                <div className="text-sm text-white/70 truncate ml-2">
                  {briefReady ? `${form.business_name} · ${form.industry}` : "Fill via chat or expand to edit"}
                </div>
              </div>
              <ChevronDown className={`w-4 h-4 text-white/50 transition-transform duration-300 shrink-0 ${advOpen ? "rotate-180" : ""}`} />
            </button>
            {advOpen && (
              <div className="mt-4 grid grid-cols-2 gap-3" data-testid="brief-fields">
                <Field label="Business name">
                  <input data-testid="gen-business-name" value={form.business_name} onChange={(e) => setField("business_name", e.target.value)} className={inputCls} placeholder="Bloom & Co." />
                </Field>
                <Field label="Industry">
                  <input data-testid="gen-industry" value={form.industry} onChange={(e) => setField("industry", e.target.value)} className={inputCls} placeholder="Florist" />
                </Field>
                <div className="col-span-2">
                  <Field label="Description">
                    <textarea data-testid="gen-description" rows={3} value={form.description} onChange={(e) => setField("description", e.target.value)} className={inputCls} placeholder="What do you offer? Who are your customers?" />
                  </Field>
                </div>
                <Field label="Target audience">
                  <input data-testid="gen-audience" value={form.target_audience} onChange={(e) => setField("target_audience", e.target.value)} className={inputCls} placeholder="busy professionals" />
                </Field>
                <Field label="Key services">
                  <input data-testid="gen-services" value={form.key_services} onChange={(e) => setField("key_services", e.target.value)} className={inputCls} placeholder="weddings, subscriptions" />
                </Field>
                <Field label="Brand keywords">
                  <input data-testid="gen-keywords" value={form.brand_keywords} onChange={(e) => setField("brand_keywords", e.target.value)} className={inputCls} placeholder="warm, earthy, premium" />
                </Field>
                <Field label="Sections wanted">
                  <input data-testid="gen-pages" value={form.pages} onChange={(e) => setField("pages", e.target.value)} className={inputCls} placeholder="hero, gallery, FAQ" />
                </Field>
                <Field label="Style">
                  <select data-testid="gen-style" value={form.style} onChange={(e) => setField("style", e.target.value)} className={inputCls}>
                    {STYLES.map((s) => <option key={s} value={s}>{s}</option>)}
                  </select>
                </Field>
                <Field label="Brand color">
                  <div className="flex items-center gap-2 mt-1">
                    <input data-testid="gen-color" type="color" value={form.primary_color} onChange={(e) => setField("primary_color", e.target.value)} className="w-11 h-10 bg-surface2 border border-white/10 cursor-pointer" />
                    <input value={form.primary_color} onChange={(e) => setField("primary_color", e.target.value)} className={`${inputCls} font-mono`} />
                  </div>
                </Field>
                <Field label="Contact email">
                  <input data-testid="gen-email" value={form.contact_email} onChange={(e) => setField("contact_email", e.target.value)} className={inputCls} placeholder="hello@business.com" />
                </Field>
                <Field label="Phone">
                  <input data-testid="gen-phone" value={form.phone} onChange={(e) => setField("phone", e.target.value)} className={inputCls} placeholder="+1 555 000 0000" />
                </Field>
              </div>
            )}
          </div>

          {/* Model + Tier selectors */}
          <div className="border-t border-white/10 px-6 md:px-10 py-4 bg-surface1/60">
            <div className="grid md:grid-cols-2 gap-4">
              <div>
                <div className="text-[10px] font-mono uppercase tracking-wider text-white/40 mb-2 flex items-center gap-1.5"><Bot className="w-3.5 h-3.5 text-brand" /> AI Model</div>
                <div className="grid grid-cols-2 gap-2" data-testid="model-selector">
                  {MODELS.map((m) => (
                    <button key={m.id} data-testid={`model-${m.id}`} type="button" onClick={() => setField("model", m.id)}
                      className={`text-left p-2.5 border transition-colors duration-300 ${form.model === m.id ? "border-brand bg-brand/10" : "border-white/10 hover:border-white/25"}`}>
                      <div className="flex items-center justify-between">
                        <div className="text-sm font-medium">{m.name}</div>
                        {form.model === m.id && <Check className="w-3.5 h-3.5 text-brand" />}
                      </div>
                      <div className="text-[10px] text-white/40 mt-0.5 font-mono">{m.desc}</div>
                    </button>
                  ))}
                </div>
              </div>
              <div>
                <div className="text-[10px] font-mono uppercase tracking-wider text-white/40 mb-2 flex items-center gap-1.5"><Sparkles className="w-3.5 h-3.5 text-brand" /> Quality tier</div>
                <div className="grid grid-cols-3 gap-2" data-testid="tier-selector">
                  {TIERS.map((t) => {
                    const Icon = t.icon;
                    const active = form.quality === t.id;
                    const activeColor = t.color === "brand" ? "border-brand bg-brand/10 text-brand"
                      : t.color === "neon" ? "border-neon bg-neon/10 text-neon"
                      : "border-amber-300 bg-amber-300/10 text-amber-300";
                    return (
                      <button key={t.id} data-testid={`tier-${t.id}`} type="button" onClick={() => setField("quality", t.id)}
                        title={t.desc}
                        className={`text-left p-2.5 border transition-colors duration-300 ${active ? activeColor : "border-white/10 hover:border-white/25 text-white/80"}`}>
                        <div className="flex items-center gap-1.5"><Icon className="w-3.5 h-3.5" /> <span className="text-xs font-semibold">{t.name}</span></div>
                        <div className="text-[10px] text-white/40 mt-0.5 font-mono">{t.cost}</div>
                      </button>
                    );
                  })}
                </div>
              </div>
            </div>
            <div className="text-[11px] text-white/40 mt-2.5 font-mono">
              {TIERS.find((t) => t.id === form.quality)?.desc}
            </div>
          </div>

          {/* Input row */}
          <div className="border-t border-white/10 px-6 md:px-10 py-4 bg-base">
            {stage !== "ready" ? (
              <div className="flex items-end gap-2">
                <div className="flex-1 border border-white/15 focus-within:border-brand/70 bg-surface2 transition-colors duration-300">
                  <textarea
                    ref={inputRef}
                    data-testid="gen-chat-input"
                    rows={2}
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); } }}
                    placeholder={placeholder}
                    className="w-full resize-none bg-transparent px-4 py-3 text-sm text-white placeholder:text-white/30 outline-none"
                  />
                </div>
                <button data-testid="gen-chat-send" onClick={() => send()} disabled={!input.trim() || typing}
                  className={`h-[68px] w-12 flex items-center justify-center transition-colors duration-300 ${input.trim() ? "bg-brand hover:bg-brand-hover" : "bg-white/10 text-white/40"} disabled:opacity-50`}>
                  <ArrowUp className="w-5 h-5" />
                </button>
              </div>
            ) : (
              <button data-testid="generate-btn" onClick={generate} disabled={loading || !briefReady}
                className="w-full flex items-center justify-center gap-2 bg-brand hover:bg-brand-hover py-4 font-medium transition-colors duration-300 disabled:opacity-60">
                {loading ? <><Loader2 className="w-5 h-5 animate-spin" /> Crafting your website…</> : <><Sparkles className="w-5 h-5" /> Generate website</>}
              </button>
            )}
          </div>
        </div>

        {/* RIGHT: Preview */}
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
                <div className="text-xs text-white/30">
                  {form.quality === "economy" ? "Fast single-pass build. ~30–60 sec."
                    : form.quality === "premium" ? "Strategist → builder → polish. ~2–3 min."
                    : "Strategist writes a brief, then builds. ~1–2 min."}
                </div>
              </div>
            ) : result ? (
              <iframe data-testid="preview-iframe" title="preview" sandbox="allow-scripts" srcDoc={result.html} className="w-full h-full" style={{ minHeight: 500 }} />
            ) : (
              <div className="h-full flex flex-col items-center justify-center gap-3 bg-surface2 text-white/40 p-8 text-center">
                <Palette className="w-10 h-10" />
                <div className="font-mono text-sm">Your generated website will appear here.</div>
                <div className="text-xs text-white/30 max-w-xs">Chat with the assistant on the left, then click Generate.</div>
              </div>
            )}
          </div>
        </div>
      </div>
    </DashboardLayout>
  );
}

const inputCls = "mt-1 w-full bg-surface2 border border-white/10 focus:border-brand px-3 py-2 outline-none transition-colors duration-300 text-white text-sm";
function Field({ label, children }) {
  return (
    <label className="block">
      <span className="text-[10px] text-white/50 font-mono uppercase tracking-wider">{label}</span>
      {children}
    </label>
  );
}
