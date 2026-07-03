import { useEffect, useRef, useState, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import DashboardLayout from "@/components/DashboardLayout";
import { api } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { toast } from "sonner";
import { Send, Loader2, Trash2, Hammer, Sparkles, X } from "lucide-react";

export default function AiTeam() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [agents, setAgents] = useState([]);
  const [activeId, setActiveId] = useState("titan");
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [thinking, setThinking] = useState(false);
  const [forgeJob, setForgeJob] = useState(null);
  const [showForge, setShowForge] = useState(false);
  const scrollRef = useRef(null);

  const isOwner = !!user && (user.role === "owner" || user.role === "admin");
  const active = agents.find((a) => a.id === activeId);

  useEffect(() => {
    if (user && !isOwner) navigate("/dashboard");
  }, [user, isOwner, navigate]);

  useEffect(() => {
    if (!isOwner) return;
    api.get("/agents").then(({ data }) => setAgents(data)).catch(() => {});
  }, [isOwner]);

  useEffect(() => {
    if (!isOwner || !activeId) return;
    setMessages(null);
    api.get(`/agents/${activeId}/chat`)
      .then(({ data }) => setMessages(data.messages))
      .catch(() => setMessages([]));
  }, [activeId, isOwner]);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, thinking]);

  const send = async (text) => {
    const message = (text || input).trim();
    if (!message || thinking) return;
    setInput("");
    setMessages((m) => [...(m || []), { role: "user", content: message }]);
    setThinking(true);
    try {
      const { data } = await api.post(`/agents/${activeId}/chat`, { message });
      setMessages((m) => [...m, { role: "agent", content: data.reply }]);
    } catch (e) {
      toast.error(e.response?.data?.detail || "The agent couldn't reply. Try again.");
      setMessages((m) => m.slice(0, -1));
      setInput(message);
    } finally { setThinking(false); }
  };

  const clearChat = async () => {
    if (!window.confirm(`Clear your conversation with ${active?.name}?`)) return;
    await api.delete(`/agents/${activeId}/chat`).catch(() => {});
    setMessages([]);
  };

  const pollForge = useCallback((jobId) => {
    const timer = setInterval(async () => {
      try {
        const { data } = await api.get(`/agents/jobs/${jobId}`);
        setForgeJob(data);
        if (data.status === "done") {
          clearInterval(timer);
          toast.success(`Forge listed "${data.result.title}" on the Market at $${data.result.price_usd} (${data.result.tier}).`);
        } else if (data.status === "error") {
          clearInterval(timer);
          toast.error(`Forge hit a problem: ${data.error}`);
        }
      } catch { clearInterval(timer); }
    }, 5000);
  }, []);

  if (!isOwner) return null;

  return (
    <DashboardLayout>
      <div className="flex h-[calc(100vh-0px)] md:h-screen">
        {/* Roster */}
        <aside className="w-72 shrink-0 hidden lg:flex flex-col border-r border-white/10 bg-surface1 overflow-y-auto" data-testid="agent-roster">
          <div className="p-5 border-b border-white/10">
            <h1 className="font-display font-bold text-lg">AI Team</h1>
            <p className="text-white/40 text-xs mt-1">Your autonomous staff of 12</p>
          </div>
          {agents.map((a) => (
            <button key={a.id} data-testid={`agent-item-${a.id}`} onClick={() => setActiveId(a.id)}
              className={`flex items-center gap-3 px-4 py-3 text-left transition-colors duration-300 border-l-2 ${
                a.id === activeId ? "bg-surface2 border-l-brand" : "border-l-transparent hover:bg-surface2/50"}`}>
              <img src={`/agents/${a.id}.png`} alt={a.name} className="w-10 h-10 rounded-full object-cover shrink-0"
                style={{ backgroundColor: `${a.color}22` }} />
              <div className="min-w-0">
                <div className="text-sm font-semibold">{a.name}</div>
                <div className="text-[11px] text-white/40 truncate">{a.role}</div>
              </div>
            </button>
          ))}
        </aside>

        {/* Chat area */}
        <div className="flex-1 flex flex-col min-w-0">
          {/* mobile roster strip */}
          <div className="lg:hidden flex gap-2 overflow-x-auto p-3 border-b border-white/10 bg-surface1">
            {agents.map((a) => (
              <button key={a.id} onClick={() => setActiveId(a.id)}
                className={`shrink-0 rounded-full p-0.5 ${a.id === activeId ? "ring-2 ring-brand" : ""}`}>
                <img src={`/agents/${a.id}.png`} alt={a.name} className="w-10 h-10 rounded-full object-cover" />
              </button>
            ))}
          </div>

          {active && (
            <div className="flex items-center gap-3 px-6 py-4 border-b border-white/10 bg-surface1" data-testid="agent-chat-header">
              <img src={`/agents/${active.id}.png`} alt={active.name} className="w-11 h-11 rounded-full object-cover" />
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2">
                  <h2 className="font-display font-bold">{active.name}</h2>
                  <span className="text-[10px] font-mono uppercase tracking-wider px-2 py-0.5" style={{ backgroundColor: `${active.color}33`, color: active.color }}>{active.role}</span>
                </div>
                <p className="text-white/40 text-xs truncate">{active.tagline}</p>
              </div>
              {active.id === "forge" && (
                <button data-testid="forge-build-toggle" onClick={() => setShowForge(!showForge)}
                  className="flex items-center gap-2 text-sm border border-amber-400/50 text-amber-300 hover:border-amber-300 px-3 py-2 transition-colors duration-300">
                  <Hammer className="w-4 h-4" /> Build & list template
                </button>
              )}
              <button data-testid="clear-chat-btn" onClick={clearChat} title="Clear conversation"
                className="p-2 text-white/40 hover:text-neon transition-colors duration-300">
                <Trash2 className="w-4 h-4" />
              </button>
            </div>
          )}

          {active?.id === "forge" && showForge && (
            <ForgePanel forgeJob={forgeJob} setForgeJob={setForgeJob} pollForge={pollForge} onClose={() => setShowForge(false)} navigate={navigate} />
          )}

          <div ref={scrollRef} className="flex-1 overflow-y-auto px-6 py-6 space-y-4" data-testid="agent-messages">
            {messages === null ? (
              <div className="font-mono text-white/30 text-sm">Loading conversation…</div>
            ) : messages.length === 0 && active ? (
              <div className="max-w-lg mx-auto text-center mt-10">
                <img src={`/agents/${active.id}.png`} alt={active.name} className="w-24 h-24 rounded-full object-cover mx-auto" />
                <h3 className="font-display text-xl font-bold mt-4">{active.name}</h3>
                <p className="text-white/50 text-sm mt-2">{active.tagline}</p>
                <p className="text-white/30 text-xs mt-4 font-mono uppercase tracking-wider">Try a quick action below, or just ask</p>
              </div>
            ) : (
              messages.map((m, i) => (
                <div key={i} className={`flex gap-3 ${m.role === "user" ? "justify-end" : ""}`}>
                  {m.role === "agent" && (
                    <img src={`/agents/${active?.id}.png`} alt="" className="w-8 h-8 rounded-full object-cover shrink-0 mt-1" />
                  )}
                  <div className={`max-w-[75%] px-4 py-3 text-sm whitespace-pre-wrap leading-relaxed ${
                    m.role === "user" ? "bg-brand text-white" : "bg-surface2 text-white/90"}`}>
                    {m.content}
                  </div>
                </div>
              ))
            )}
            {thinking && active && (
              <div className="flex gap-3" data-testid="agent-typing">
                <img src={`/agents/${active.id}.png`} alt="" className="w-8 h-8 rounded-full object-cover shrink-0 mt-1" />
                <div className="bg-surface2 px-4 py-3 flex items-center gap-1.5">
                  <span className="w-1.5 h-1.5 bg-white/50 rounded-full animate-bounce" />
                  <span className="w-1.5 h-1.5 bg-white/50 rounded-full animate-bounce" style={{ animationDelay: "150ms" }} />
                  <span className="w-1.5 h-1.5 bg-white/50 rounded-full animate-bounce" style={{ animationDelay: "300ms" }} />
                </div>
              </div>
            )}
          </div>

          {active && (
            <div className="border-t border-white/10 bg-surface1 p-4">
              <div className="flex gap-2 mb-3 flex-wrap">
                {active.quick_actions.map((qa, i) => (
                  <button key={i} data-testid={`quick-action-${active.id}-${i}`} onClick={() => send(qa.prompt)} disabled={thinking}
                    className="flex items-center gap-1.5 text-xs border border-white/15 hover:border-brand hover:text-brand px-3 py-1.5 transition-colors duration-300 disabled:opacity-40">
                    <Sparkles className="w-3 h-3" /> {qa.label}
                  </button>
                ))}
              </div>
              <div className="flex gap-2">
                <input data-testid="agent-chat-input" value={input} onChange={(e) => setInput(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && send()}
                  placeholder={`Ask ${active.name} anything…`} disabled={thinking}
                  className="flex-1 bg-surface2 border border-white/10 focus:border-brand outline-none px-4 py-3 text-sm transition-colors duration-300" />
                <button data-testid="agent-send-btn" onClick={() => send()} disabled={thinking || !input.trim()}
                  className="bg-brand hover:bg-brand-hover px-4 transition-colors duration-300 disabled:opacity-40">
                  {thinking ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </DashboardLayout>
  );
}

function ForgePanel({ forgeJob, setForgeJob, pollForge, onClose, navigate }) {
  const [brief, setBrief] = useState("");
  const building = forgeJob && ["queued", "designing", "building", "pricing"].includes(forgeJob.status);

  const start = async () => {
    if (!brief.trim()) return;
    try {
      const { data } = await api.post("/agents/forge/build", { brief });
      setForgeJob({ job_id: data.job_id, status: "queued" });
      pollForge(data.job_id);
      toast.info("Forge is on it — designing, building and pricing your template.");
    } catch (e) {
      toast.error(e.response?.data?.detail || "Could not start the build.");
    }
  };

  const statusLabel = { queued: "Queued…", designing: "Designing the brand…", building: "Building the website…", pricing: "AI pricing agent at work…" };

  return (
    <div className="border-b border-amber-400/20 bg-amber-400/5 px-6 py-4" data-testid="forge-panel">
      <div className="flex items-center justify-between">
        <p className="text-sm text-amber-200/90">Tell Forge a niche — he'll invent a brand, build the full website and list it on the Market, priced by the AI pricing agent.</p>
        <button onClick={onClose} className="text-white/40 hover:text-white p-1"><X className="w-4 h-4" /></button>
      </div>
      {building ? (
        <div className="mt-3 flex items-center gap-3 text-sm text-amber-300 font-mono" data-testid="forge-status">
          <Loader2 className="w-4 h-4 animate-spin" /> {statusLabel[forgeJob.status] || forgeJob.status}
          {forgeJob.title && <span className="text-white/50">— {forgeJob.title}</span>}
        </div>
      ) : forgeJob?.status === "done" ? (
        <div className="mt-3 flex items-center gap-3 text-sm" data-testid="forge-done">
          <span className="text-emerald-300">✓ "{forgeJob.result.title}" listed at ${forgeJob.result.price_usd} ({forgeJob.result.tier})</span>
          <button onClick={() => navigate("/market")} className="underline text-amber-300 hover:text-amber-200">View on Market</button>
          <button onClick={() => setForgeJob(null)} className="text-white/40 hover:text-white text-xs">Build another</button>
        </div>
      ) : (
        <div className="mt-3 flex gap-2">
          <input data-testid="forge-brief-input" value={brief} onChange={(e) => setBrief(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && start()}
            placeholder='e.g. "high-end barbershop" or "yoga studio for busy moms"'
            className="flex-1 bg-surface2 border border-white/10 focus:border-amber-300 outline-none px-4 py-2.5 text-sm transition-colors duration-300" />
          <button data-testid="forge-start-btn" onClick={start} disabled={!brief.trim()}
            className="flex items-center gap-2 bg-amber-400 text-black hover:bg-amber-300 px-4 py-2.5 text-sm font-semibold transition-colors duration-300 disabled:opacity-40">
            <Hammer className="w-4 h-4" /> Build
          </button>
        </div>
      )}
    </div>
  );
}
