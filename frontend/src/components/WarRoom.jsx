import { useEffect, useRef, useState, useCallback } from "react";
import { api } from "@/lib/api";
import { toast } from "sonner";
import { Send, Loader2, Users, Trash2, ListChecks } from "lucide-react";

const STATUS_STYLE = {
  queued: "text-white/50 border-white/20",
  running: "text-amber-300 border-amber-400/50 animate-pulse",
  done: "text-emerald-300 border-emerald-400/50",
  error: "text-red-300 border-red-400/50",
  assigned: "text-sky-300 border-sky-400/40",
};

export const WarRoom = ({ agents }) => {
  const [messages, setMessages] = useState(null);
  const [meeting, setMeeting] = useState(null);
  const [tasks, setTasks] = useState([]);
  const [topic, setTopic] = useState("");
  const [starting, setStarting] = useState(false);
  const scrollRef = useRef(null);
  const agentById = Object.fromEntries(agents.map((a) => [a.id, a]));

  const load = useCallback(async () => {
    try {
      const { data } = await api.get("/agents/war-room");
      setMessages(data.messages);
      setMeeting(data.meeting);
      setTasks(data.tasks || []);
    } catch {}
  }, []);

  useEffect(() => { load(); }, [load]);

  const meetingLive = meeting && ["starting", "running"].includes(meeting.status);
  const tasksLive = tasks.some((t) => ["queued", "running"].includes(t.status));

  useEffect(() => {
    if (!meetingLive && !tasksLive) return;
    const timer = setInterval(load, 4000);
    return () => clearInterval(timer);
  }, [meetingLive, tasksLive, load]);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages]);

  const start = async () => {
    const t = topic.trim();
    if (!t || starting || meetingLive) return;
    setStarting(true);
    try {
      await api.post("/agents/war-room", { topic: t });
      setTopic("");
      setMessages((m) => [...(m || []), { role: "owner", content: t }]);
      setMeeting({ status: "starting" });
      toast.info("Titan is convening the team — agents will weigh in one by one.");
    } catch (e) {
      toast.error(e.response?.data?.detail || "Couldn't start the meeting.");
    } finally { setStarting(false); }
  };

  const clear = async () => {
    if (!window.confirm("Clear the War Room transcript?")) return;
    await api.delete("/agents/war-room").catch(() => {});
    setMessages([]);
  };

  return (
    <>
      <div className="flex items-center gap-3 px-6 py-4 border-b border-white/10 bg-surface1" data-testid="war-room-header">
        <div className="w-11 h-11 rounded-full flex items-center justify-center bg-brand/20 border border-brand/40">
          <Users className="w-5 h-5 text-brand" />
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <h2 className="font-display font-bold">War Room</h2>
            <span className="text-[10px] font-mono uppercase tracking-wider px-2 py-0.5 bg-brand/20 text-brand">Team meeting</span>
            {meetingLive && (
              <span className="text-[10px] font-mono uppercase tracking-wider text-amber-300 animate-pulse" data-testid="war-room-live">● Meeting in progress</span>
            )}
          </div>
          <p className="text-white/40 text-xs truncate">Drop a topic — Titan chairs, the right agents weigh in, decisions become real tasks.</p>
        </div>
        <button data-testid="war-room-clear" onClick={clear} title="Clear transcript"
          className="p-2 text-white/40 hover:text-neon transition-colors duration-300">
          <Trash2 className="w-4 h-4" />
        </button>
      </div>

      {tasks.length > 0 && (
        <div className="border-b border-white/10 bg-surface1/60 px-6 py-3" data-testid="war-room-tasks">
          <div className="flex items-center gap-2 text-[10px] font-mono uppercase tracking-wider text-white/40 mb-2">
            <ListChecks className="w-3.5 h-3.5" /> Task board
          </div>
          <div className="flex gap-2 flex-wrap max-h-24 overflow-y-auto">
            {tasks.map((t) => (
              <div key={t.task_id} title={t.error || t.task}
                className={`flex items-center gap-2 border px-2.5 py-1 text-xs ${STATUS_STYLE[t.status] || "text-white/50 border-white/20"}`}>
                <img src={`/agents/${t.owner_agent}.png`} alt="" className="w-4 h-4 rounded-full object-cover" />
                <span className="max-w-[220px] truncate">{t.task || t.brief}</span>
                <span className="font-mono uppercase text-[9px] tracking-wider opacity-80">{t.status}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      <div ref={scrollRef} className="flex-1 overflow-y-auto px-6 py-6 space-y-4" data-testid="war-room-messages">
        {messages === null ? (
          <div className="font-mono text-white/30 text-sm">Loading the War Room…</div>
        ) : messages.length === 0 ? (
          <div className="max-w-lg mx-auto text-center mt-10">
            <div className="w-24 h-24 rounded-full mx-auto flex items-center justify-center bg-brand/15 border border-brand/30">
              <Users className="w-10 h-10 text-brand" />
            </div>
            <h3 className="font-display text-xl font-bold mt-4">The team is assembled</h3>
            <p className="text-white/50 text-sm mt-2">Drop a topic below and watch the agents actually discuss it together — then turn the decision into real work.</p>
            <p className="text-white/30 text-xs mt-4 font-mono uppercase tracking-wider">e.g. "Plan 3 new flagship templates for the Market"</p>
          </div>
        ) : (
          messages.map((m, i) => {
            const a = m.agent_id ? agentById[m.agent_id] : null;
            return m.role === "owner" ? (
              <div key={i} className="flex justify-end">
                <div className="max-w-[75%] px-4 py-3 text-sm whitespace-pre-wrap leading-relaxed bg-brand text-white">{m.content}</div>
              </div>
            ) : (
              <div key={i} className="flex gap-3">
                <img src={`/agents/${m.agent_id}.png`} alt="" className="w-8 h-8 rounded-full object-cover shrink-0 mt-1" />
                <div className="max-w-[75%]">
                  <div className="text-[11px] font-mono uppercase tracking-wider mb-1" style={{ color: a?.color || "#94A3B8" }}>
                    {a?.name || m.agent_id}
                  </div>
                  <div className="px-4 py-3 text-sm whitespace-pre-wrap leading-relaxed bg-surface2 text-white/90">{m.content}</div>
                </div>
              </div>
            );
          })
        )}
        {meetingLive && (
          <div className="flex gap-3" data-testid="war-room-typing">
            <div className="w-8 h-8 rounded-full shrink-0 mt-1 flex items-center justify-center bg-brand/20 border border-brand/40">
              <Users className="w-4 h-4 text-brand" />
            </div>
            <div className="bg-surface2 px-4 py-3 flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 bg-white/50 rounded-full animate-bounce" />
              <span className="w-1.5 h-1.5 bg-white/50 rounded-full animate-bounce" style={{ animationDelay: "150ms" }} />
              <span className="w-1.5 h-1.5 bg-white/50 rounded-full animate-bounce" style={{ animationDelay: "300ms" }} />
            </div>
          </div>
        )}
      </div>

      <div className="border-t border-white/10 bg-surface1 p-4">
        <div className="flex gap-2">
          <input data-testid="war-room-topic-input" value={topic} onChange={(e) => setTopic(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && start()}
            placeholder={meetingLive ? "Meeting in progress…" : 'Drop a topic for the team — e.g. "Plan 3 new flagships for the Market"'}
            disabled={meetingLive || starting}
            className="flex-1 bg-surface2 border border-white/10 focus:border-brand outline-none px-4 py-3 text-sm transition-colors duration-300 disabled:opacity-50" />
          <button data-testid="war-room-start-btn" onClick={start} disabled={meetingLive || starting || !topic.trim()}
            className="bg-brand hover:bg-brand-hover px-4 transition-colors duration-300 disabled:opacity-40">
            {starting || meetingLive ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
          </button>
        </div>
      </div>
    </>
  );
};
