import { useEffect, useState, useCallback } from "react";
import { api } from "@/lib/api";
import { toast } from "sonner";
import { X, Loader2, Brain, Trash2, Plus, Target, Star, Bookmark, ListTodo } from "lucide-react";

const KIND_META = {
  fact: { icon: Bookmark, tint: "text-white/60", label: "Fact" },
  preference: { icon: Star, tint: "text-yellow-300", label: "Preference" },
  goal: { icon: Target, tint: "text-emerald-300", label: "Goal" },
  context: { icon: Brain, tint: "text-sky-300", label: "Context" },
};

export function AgentMemory({ agentId, agentName, onClose, shared = false }) {
  const [data, setData] = useState(null);
  const [adding, setAdding] = useState(false);
  const [newText, setNewText] = useState("");
  const [busy, setBusy] = useState(null);

  const base = shared ? "/agents/team-memory" : `/agents/${agentId}/memory`;
  const label = shared ? "the team" : agentName;

  const load = useCallback(() => {
    api.get(base)
      .then(({ data }) => setData(data))
      .catch(() => setData({ facts: [], open_threads: [], rolling_summary: "" }));
  }, [base]);

  useEffect(() => { setData(null); load(); }, [load]);

  const addMemory = async () => {
    const text = newText.trim();
    if (!text) return;
    setBusy("add");
    try {
      const { data } = await api.post(base, { text, kind: "fact" });
      setData((d) => ({ ...d, facts: data.facts, open_threads: (data.open_threads || []).filter((t) => t.status !== "done"), rolling_summary: data.rolling_summary }));
      setNewText(""); setAdding(false);
      toast.success(shared ? "The whole team will remember that." : `${agentName} will remember that.`);
    } catch (e) {
      toast.error(e.response?.data?.detail || "Couldn't save that memory.");
    } finally { setBusy(null); }
  };

  const removeItem = async (memId) => {
    setBusy(memId);
    try {
      await api.delete(`${base}/${memId}`);
      setData((d) => ({
        ...d,
        facts: (d.facts || []).filter((f) => f.mem_id !== memId),
        open_threads: (d.open_threads || []).filter((t) => t.mem_id !== memId),
      }));
      toast.success("Forgotten.");
    } catch {
      toast.error("Couldn't remove that.");
    } finally { setBusy(null); }
  };

  const facts = data?.facts || [];
  const threads = data?.open_threads || [];

  return (
    <div className={shared
      ? "flex-1 overflow-y-auto px-6 py-5 bg-violet-400/5"
      : "border-b border-violet-400/20 bg-violet-400/5 px-6 py-4"} data-testid={shared ? "team-brain" : "agent-memory"}>
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Brain className="w-4 h-4 text-violet-300" />
          <p className="text-sm font-semibold text-violet-100">{shared ? "Team Shared Brain" : `${agentName}'s Memory`}</p>
          <span className="text-[10px] font-mono uppercase tracking-wider text-violet-300/60">
            {shared ? "every agent sees this · survives resets" : "persistent · survives resets"}
          </span>
        </div>
        <div className="flex items-center gap-2">
          <button data-testid="memory-add-toggle" onClick={() => setAdding((a) => !a)}
            className="flex items-center gap-1.5 text-xs border border-violet-400/40 text-violet-200 hover:border-violet-300 px-2.5 py-1.5 transition-colors duration-200">
            <Plus className="w-3.5 h-3.5" /> Remember something
          </button>
          {!shared && <button onClick={onClose} className="text-white/40 hover:text-white p-1"><X className="w-4 h-4" /></button>}
        </div>
      </div>

      {shared && (
        <p className="text-xs text-white/40 mt-2 max-w-2xl">
          Facts here are shared with all 12 agents — brand standards, key decisions, company context.
          War Room decisions land here automatically so the whole team stays aligned, even after a data reset.
        </p>
      )}

      {adding && (
        <div className="mt-3 flex gap-2">
          <input data-testid="memory-add-input" value={newText} onChange={(e) => setNewText(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && addMemory()} autoFocus
            placeholder={shared ? "A fact the whole team should always know…" : `Tell ${agentName} something to always remember…`}
            className="flex-1 bg-surface2 border border-white/10 focus:border-violet-300 outline-none px-3 py-2 text-sm transition-colors duration-300" />
          <button data-testid="memory-add-save" onClick={addMemory} disabled={busy === "add" || !newText.trim()}
            className="flex items-center gap-1.5 bg-violet-500 hover:bg-violet-400 px-3 py-2 text-sm transition-colors duration-300 disabled:opacity-40">
            {busy === "add" ? <Loader2 className="w-4 h-4 animate-spin" /> : "Save"}
          </button>
        </div>
      )}

      <div className={shared ? "mt-4 space-y-4" : "mt-4 max-h-[52vh] overflow-y-auto pr-1 space-y-4"} data-testid="memory-body">
        {data === null ? (
          <div className="flex items-center gap-2 text-white/40 text-sm font-mono py-6">
            <Loader2 className="w-4 h-4 animate-spin" /> Loading memory…
          </div>
        ) : (
          <>
            {data.rolling_summary && (
              <div className="border border-white/10 bg-surface2/60 p-3">
                <div className="text-[10px] font-mono uppercase text-white/30 mb-1">Where we left off</div>
                <p className="text-sm text-white/80 leading-relaxed">{data.rolling_summary}</p>
              </div>
            )}

            <div>
              <div className="text-[10px] font-mono uppercase text-white/30 mb-2">{shared ? "Shared team facts" : "What they remember"} ({facts.length})</div>
              {facts.length === 0 ? (
                <p className="text-xs text-white/40">{shared
                  ? "Nothing shared yet — add a company-wide fact, or run a War Room and the decision lands here automatically."
                  : `Nothing yet — chat with ${agentName} or add a memory. Durable facts, preferences and goals are learned automatically.`}</p>
              ) : (
                <div className="space-y-1.5">
                  {facts.map((f) => {
                    const meta = KIND_META[f.kind] || KIND_META.fact;
                    const Icon = meta.icon;
                    return (
                      <div key={f.mem_id} data-testid={`memory-fact-${f.mem_id}`}
                        className="group flex items-start gap-2.5 border border-white/8 bg-surface2/40 px-3 py-2">
                        <Icon className={`w-3.5 h-3.5 mt-0.5 shrink-0 ${meta.tint}`} />
                        <span className="text-sm text-white/85 flex-1 leading-snug">{f.text}</span>
                        {f.source === "manual" && <span className="text-[9px] font-mono uppercase text-violet-300/70 mt-1">you</span>}
                        <button data-testid={`memory-delete-${f.mem_id}`} onClick={() => removeItem(f.mem_id)} disabled={busy === f.mem_id}
                          className="opacity-0 group-hover:opacity-100 text-white/30 hover:text-red-300 transition-all duration-200 disabled:opacity-40">
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>

            {threads.length > 0 && (
              <div>
                <div className="text-[10px] font-mono uppercase text-white/30 mb-2 flex items-center gap-1.5">
                  <ListTodo className="w-3 h-3" /> Open threads ({threads.length})
                </div>
                <div className="space-y-1.5">
                  {threads.map((t) => (
                    <div key={t.mem_id} data-testid={`memory-thread-${t.mem_id}`}
                      className="group flex items-start gap-2.5 border border-emerald-400/20 bg-emerald-400/5 px-3 py-2">
                      <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 mt-1.5 shrink-0" />
                      <span className="text-sm text-white/85 flex-1 leading-snug">{t.text}</span>
                      <button onClick={() => removeItem(t.mem_id)} disabled={busy === t.mem_id}
                        className="opacity-0 group-hover:opacity-100 text-white/30 hover:text-red-300 transition-all duration-200">
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
