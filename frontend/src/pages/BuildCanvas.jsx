import { useState, useEffect, useRef, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import DashboardLayout from "@/components/DashboardLayout";
import { api, formatApiError } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { toast } from "sonner";
import { Send, Loader2, Sparkles, Monitor, Smartphone, ExternalLink, Wand2,
  ArrowUp, RotateCcw, Gauge, Gem, Crown, ChevronDown, Bot } from "lucide-react";

const STAGE_LABEL = {
  designing: "Designing the brand & layout…",
  building: "Building your website…",
  polishing: "Adding premium polish…",
  refining: "Applying your changes…",
  pending: "Thinking…",
};

const STARTERS = [
  "A cozy neighborhood coffee shop with specialty espresso",
  "A luxury med spa offering botox and facials",
  "A modern barbershop for busy professionals",
  "A boutique fitness studio with small-group classes",
];

const MODELS = [
  { id: "claude-sonnet-4-6", name: "Sonnet 4.6", desc: "Deepest reasoning" },
  { id: "claude-haiku-4-5", name: "Haiku 4.5", desc: "Fast" },
];
const TIERS = [
  { id: "economy", name: "Economy", icon: Gauge },
  { id: "quality", name: "Quality", icon: Gem },
  { id: "premium", name: "Premium", icon: Crown },
];

export default function BuildCanvas() {
  const { user, refreshUser } = useAuth();
  const navigate = useNavigate();
  const [sessionId, setSessionId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [stage, setStage] = useState(null);
  const [html, setHtml] = useState("");
  const [templateId, setTemplateId] = useState(null);
  const [view, setView] = useState("desktop");
  const [model, setModel] = useState("claude-haiku-4-5");
  const [quality, setQuality] = useState("economy");
  const [showSettings, setShowSettings] = useState(false);
  const scrollRef = useRef(null);
  const pollRef = useRef(null);

  // Start a build session on mount.
  useEffect(() => {
    api.post("/build/session").then(({ data }) => setSessionId(data.session_id)).catch(() => {});
    return () => clearInterval(pollRef.current);
  }, []);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, busy, stage]);

  const pollJob = useCallback((jobId, isBuild) => new Promise((resolve, reject) => {
    clearInterval(pollRef.current);
    let n = 0;
    pollRef.current = setInterval(async () => {
      n += 1;
      if (n > 150) { clearInterval(pollRef.current); return reject(new Error("Timed out. Please try again.")); }
      try {
        const { data } = await api.get(`/templates/job/${jobId}`);
        if (data.stage) setStage(data.stage);
        if (data.status === "done" && data.template) {
          clearInterval(pollRef.current);
          return resolve(data);
        }
        if (data.status === "error") { clearInterval(pollRef.current); return reject(new Error(data.error || "Failed.")); }
      } catch { /* keep polling */ }
    }, 2500);
  }), []);

  const send = async (text) => {
    const msg = (text || input).trim();
    if (!msg || busy || !sessionId) return;
    setInput("");
    setMessages((m) => [...m, { role: "user", content: msg }]);
    setBusy(true); setStage("pending");
    try {
      const { data } = await api.post(`/build/${sessionId}/message`, { message: msg, model, quality });
      setMessages((m) => [...m, { role: "assistant", content: data.reply }]);
      if (data.kind === "chat" || !data.job_id) { setBusy(false); setStage(null); return; }
      const job = await pollJob(data.job_id, data.kind === "build");
      setHtml(job.template.html);
      if (!templateId) {
        setTemplateId(job.template.template_id);
        api.post(`/build/${sessionId}/attach/${job.template.template_id}`).catch(() => {});
      }
      await refreshUser();
      if (job.cost) toast.success(`Done · ${job.cost} credit${job.cost > 1 ? "s" : ""} used.`);
    } catch (e) {
      const detail = e.response?.data?.detail;
      if (e.response?.status === 402) { toast.error("Out of credits."); navigate("/pricing"); }
      else toast.error(detail ? formatApiError(detail) : (e.message || "Something went wrong."));
      setMessages((m) => [...m, { role: "assistant", content: "I hit a snag with that — mind trying again or rephrasing?" }]);
    } finally { setBusy(false); setStage(null); }
  };

  const openFull = () => templateId && navigate(`/templates/${templateId}`);
  const restart = async () => {
    clearInterval(pollRef.current);
    const { data } = await api.post("/build/session").catch(() => ({ data: {} }));
    setSessionId(data.session_id || null);
    setMessages([]); setHtml(""); setTemplateId(null); setStage(null); setBusy(false);
  };

  const hasSite = !!html;

  return (
    <DashboardLayout>
      <div className="flex h-[calc(100vh-0px)] md:h-screen" data-testid="build-canvas">
        {/* Chat side */}
        <div className="w-full lg:w-[42%] xl:w-[38%] shrink-0 flex flex-col border-r border-white/10 bg-surface1">
          <div className="flex items-center justify-between px-5 py-4 border-b border-white/10">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-full bg-brand/20 border border-brand/40 flex items-center justify-center">
                <Sparkles className="w-4 h-4 text-brand" />
              </div>
              <div>
                <div className="font-display font-bold text-sm">Build with SiteGenie</div>
                <div className="text-[11px] text-white/40">Describe it. Refine it. Live.</div>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <button data-testid="build-settings-toggle" onClick={() => setShowSettings((s) => !s)}
                className="text-xs border border-white/15 hover:border-white/40 px-2.5 py-1.5 flex items-center gap-1.5 transition-colors duration-200">
                <Bot className="w-3.5 h-3.5" /> {MODELS.find((m) => m.id === model)?.name} <ChevronDown className="w-3 h-3" />
              </button>
              {hasSite && (
                <button data-testid="build-restart" onClick={restart} title="Start over"
                  className="text-xs border border-white/15 hover:border-neon hover:text-neon px-2.5 py-1.5 transition-colors duration-200">
                  <RotateCcw className="w-3.5 h-3.5" />
                </button>
              )}
            </div>
          </div>

          {showSettings && (
            <div className="px-5 py-3 border-b border-white/10 bg-surface2/50" data-testid="build-settings">
              <div className="text-[10px] font-mono uppercase text-white/40 mb-1.5">AI model</div>
              <div className="flex gap-2 mb-3">
                {MODELS.map((m) => (
                  <button key={m.id} onClick={() => setModel(m.id)}
                    className={`text-xs px-3 py-1.5 border transition-colors duration-200 ${model === m.id ? "border-brand text-brand" : "border-white/10 text-white/50"}`}>
                    {m.name}<span className="text-white/30 ml-1">· {m.desc}</span>
                  </button>
                ))}
              </div>
              <div className="text-[10px] font-mono uppercase text-white/40 mb-1.5">Quality (first build)</div>
              <div className="flex gap-2">
                {TIERS.map((t) => {
                  const Icon = t.icon;
                  return (
                    <button key={t.id} onClick={() => setQuality(t.id)}
                      className={`flex items-center gap-1.5 text-xs px-3 py-1.5 border transition-colors duration-200 ${quality === t.id ? "border-brand text-brand" : "border-white/10 text-white/50"}`}>
                      <Icon className="w-3.5 h-3.5" /> {t.name}
                    </button>
                  );
                })}
              </div>
            </div>
          )}

          {/* messages */}
          <div ref={scrollRef} className="flex-1 overflow-y-auto px-5 py-5 space-y-4" data-testid="build-messages">
            {messages.length === 0 && (
              <div className="mt-4">
                <h2 className="font-display text-2xl font-bold leading-tight">Tell me about your business.<br /><span className="text-brand">I'll build the website.</span></h2>
                <p className="text-white/50 text-sm mt-2">Describe what you do — then just talk to refine it. Try:</p>
                <div className="mt-4 space-y-2">
                  {STARTERS.map((s) => (
                    <button key={s} data-testid="build-starter" onClick={() => send(s)}
                      className="w-full text-left text-sm border border-white/10 hover:border-brand hover:text-brand px-3.5 py-2.5 transition-colors duration-200">
                      {s}
                    </button>
                  ))}
                </div>
              </div>
            )}
            {messages.map((m, i) => (
              <div key={i} className={`flex ${m.role === "user" ? "justify-end" : ""}`}>
                <div className={`max-w-[85%] px-4 py-2.5 text-sm whitespace-pre-wrap leading-relaxed rounded-2xl ${
                  m.role === "user" ? "bg-brand text-white rounded-br-sm" : "bg-surface2 text-white/90 rounded-bl-sm"}`}>
                  {m.content}
                </div>
              </div>
            ))}
            {busy && (
              <div className="flex" data-testid="build-status">
                <div className="bg-surface2 px-4 py-3 rounded-2xl rounded-bl-sm flex items-center gap-2.5">
                  <Loader2 className="w-4 h-4 animate-spin text-brand" />
                  <span className="text-sm text-white/70">{STAGE_LABEL[stage] || "Working…"}</span>
                </div>
              </div>
            )}
          </div>

          {/* input */}
          <div className="border-t border-white/10 p-4">
            <div className="flex gap-2 items-end">
              <textarea data-testid="build-input" value={input} rows={1}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); } }}
                placeholder={hasSite ? "Refine it… e.g. 'make the hero darker, add a pricing section'" : "Describe your business…"}
                disabled={busy}
                className="flex-1 resize-none bg-surface2 border border-white/10 focus:border-brand outline-none px-4 py-3 text-sm rounded-lg transition-colors duration-200 max-h-32" />
              <button data-testid="build-send" onClick={() => send()} disabled={busy || !input.trim()}
                className="bg-brand hover:bg-brand-hover p-3 rounded-lg transition-colors duration-200 disabled:opacity-40">
                {busy ? <Loader2 className="w-5 h-5 animate-spin" /> : <ArrowUp className="w-5 h-5" />}
              </button>
            </div>
            <div className="text-[10px] text-white/30 text-center mt-2 font-mono">
              {hasSite ? "Small tweaks are half-price · Enter to send" : "Powered by Claude + UI-UX-Pro-Max · Enter to send"}
            </div>
          </div>
        </div>

        {/* Live preview side */}
        <div className="hidden lg:flex flex-1 flex-col bg-surface2 min-w-0">
          <div className="flex items-center justify-between px-4 py-3 border-b border-white/10 bg-surface1">
            <div className="flex items-center gap-2 text-sm text-white/50">
              <span className={`w-2 h-2 rounded-full ${hasSite ? "bg-neon" : "bg-white/20"} ${busy ? "animate-pulse" : ""}`} />
              {busy ? (STAGE_LABEL[stage] || "Working…") : hasSite ? "Live preview" : "Your website appears here"}
            </div>
            <div className="flex items-center gap-2">
              <div className="flex border border-white/10">
                <button onClick={() => setView("desktop")} className={`p-1.5 ${view === "desktop" ? "bg-brand" : "hover:bg-surface2"} transition-colors`}><Monitor className="w-4 h-4" /></button>
                <button onClick={() => setView("mobile")} className={`p-1.5 ${view === "mobile" ? "bg-brand" : "hover:bg-surface2"} transition-colors`}><Smartphone className="w-4 h-4" /></button>
              </div>
              {templateId && (
                <button data-testid="build-open-full" onClick={openFull}
                  className="flex items-center gap-1.5 text-xs bg-brand hover:bg-brand-hover px-3 py-2 transition-colors duration-200">
                  <ExternalLink className="w-3.5 h-3.5" /> Open & publish
                </button>
              )}
            </div>
          </div>
          <div className="flex-1 overflow-auto p-4 flex justify-center relative">
            {busy && !hasSite && (
              <div className="absolute inset-0 flex flex-col items-center justify-center gap-3 text-white/50">
                <Loader2 className="w-10 h-10 animate-spin text-brand" />
                <div className="font-mono text-sm">{STAGE_LABEL[stage] || "Building…"}</div>
              </div>
            )}
            {hasSite ? (
              <div className={`bg-white h-full ${view === "mobile" ? "w-[390px]" : "w-full max-w-6xl"} border border-white/10 transition-all duration-300 relative`}>
                {busy && <div className="absolute inset-0 bg-base/50 backdrop-blur-[1px] z-10 flex items-center justify-center"><Loader2 className="w-8 h-8 animate-spin text-brand" /></div>}
                <iframe data-testid="build-iframe" title="preview" sandbox="allow-scripts" srcDoc={html} className="w-full h-full" />
              </div>
            ) : !busy && (
              <div className="flex flex-col items-center justify-center text-center max-w-sm">
                <Wand2 className="w-12 h-12 text-white/15" />
                <p className="text-white/40 text-sm mt-4">Describe your business in the chat and your website will build here — then just talk to refine it, live.</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </DashboardLayout>
  );
}
