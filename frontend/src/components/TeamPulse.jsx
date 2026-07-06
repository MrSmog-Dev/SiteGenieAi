import { useEffect, useRef, useState, useCallback } from "react";
import { api } from "@/lib/api";
import { Activity, Newspaper, Hammer, Crosshair, MessageSquare, Users, Bell,
  Sparkles, Lightbulb, Mail, Radio } from "lucide-react";

// relative "time ago"
function ago(iso) {
  if (!iso) return "";
  const then = new Date(iso).getTime();
  const s = Math.max(0, Math.floor((Date.now() - then) / 1000));
  if (s < 60) return "just now";
  const m = Math.floor(s / 60);
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h ago`;
  const d = Math.floor(h / 24);
  return `${d}d ago`;
}

const KIND_META = {
  briefing: { icon: Radio, label: "Briefing", tint: "text-slate-300" },
  article: { icon: Newspaper, label: "Article", tint: "text-green-300" },
  social: { icon: Sparkles, label: "Social", tint: "text-red-300" },
  build: { icon: Hammer, label: "Build", tint: "text-amber-300" },
  demo: { icon: Hammer, label: "Demo", tint: "text-amber-300" },
  hunt: { icon: Crosshair, label: "Hunt", tint: "text-red-300" },
  nudge: { icon: Bell, label: "Nudge", tint: "text-red-300" },
  alert: { icon: Bell, label: "Alert", tint: "text-orange-300" },
  memo: { icon: MessageSquare, label: "Memo", tint: "text-blue-300" },
  meeting: { icon: Users, label: "War Room", tint: "text-brand" },
  digest: { icon: Mail, label: "Digest", tint: "text-pink-300" },
  pulse: { icon: Lightbulb, label: "Check-in", tint: "text-yellow-300" },
  feedback: { icon: MessageSquare, label: "Customer", tint: "text-sky-300" },
};

function ActivityRow({ act, agents, onOpen }) {
  const a = agents[act.agent_id] || {};
  const meta = KIND_META[act.kind] || { icon: Activity, label: act.kind, tint: "text-white/60" };
  const Icon = meta.icon;
  const external = act.link?.startsWith("/api/");
  return (
    <div
      data-testid={`activity-${act.activity_id}`}
      className="group flex gap-3 px-4 py-3.5 hover:bg-surface2/50 transition-colors duration-200 cursor-pointer"
      onClick={() => onOpen?.(act)}
    >
      <div className="relative shrink-0">
        <img src={`/agents/${act.agent_id}.png`} alt={a.name || act.agent_id}
          className="w-9 h-9 rounded-full object-cover mt-0.5" />
        <span className="absolute -bottom-0.5 -right-0.5 w-4 h-4 rounded-full bg-surface1 flex items-center justify-center">
          <Icon className={`w-2.5 h-2.5 ${meta.tint}`} />
        </span>
      </div>
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-sm font-semibold" style={{ color: a.color }}>{a.name || act.agent_id}</span>
          <span className={`text-[10px] font-mono uppercase tracking-wider px-1.5 py-0.5 bg-white/5 ${meta.tint}`}>{meta.label}</span>
          <span className="text-[11px] text-white/30 ml-auto">{ago(act.created_at)}</span>
        </div>
        <p className="text-sm text-white/80 mt-0.5 leading-snug">{act.summary}</p>
        {act.detail && <p className="text-xs text-white/40 mt-1 leading-snug line-clamp-2">{act.detail}</p>}
      </div>
    </div>
  );
}

/**
 * TeamPulse — the live feed of everything the AI team does autonomously.
 * compact=true renders the dashboard widget variant.
 */
export function TeamPulse({ compact = false, onOpenAgent, limit }) {
  const [feed, setFeed] = useState(null);
  const [agents, setAgents] = useState({});
  const [board, setBoard] = useState(null);
  const [filter, setFilter] = useState(null);
  const timerRef = useRef(null);

  const load = useCallback(async (silent = true) => {
    try {
      const [{ data: fd }, { data: st }] = await Promise.all([
        api.get(`/agents/activity`, { params: { limit: limit || (compact ? 6 : 40) } }),
        api.get(`/agents/status`),
      ]);
      setFeed(fd.activities);
      setAgents(fd.agents);
      setBoard(st);
    } catch {
      if (!silent) setFeed([]);
    }
  }, [compact, limit]);

  useEffect(() => {
    load(false);
    timerRef.current = setInterval(() => load(true), 10000);
    return () => clearInterval(timerRef.current);
  }, [load]);

  const openActivity = (act) => {
    if (act.link?.startsWith("/api/")) {
      window.open(act.link, "_blank", "noopener");
    } else if (onOpenAgent) {
      onOpenAgent(act.agent_id);
    }
  };

  const shown = filter ? (feed || []).filter((a) => a.agent_id === filter) : feed;
  const working = board?.statuses
    ? Object.entries(board.statuses).filter(([, s]) => s.status === "working")
    : [];

  // ---------------- compact dashboard widget ----------------
  if (compact) {
    return (
      <div className="border border-white/10 bg-surface1" data-testid="dashboard-team-pulse">
        <div className="flex items-center gap-2 px-5 py-4 border-b border-white/10">
          <span className="relative flex h-2.5 w-2.5">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
            <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-emerald-400" />
          </span>
          <h2 className="font-display font-bold">Team Pulse — live</h2>
          <span className="text-[11px] text-white/40 ml-auto font-mono">
            {board?.working_now ? `${board.working_now} working now` : `${board?.today_count ?? 0} today`}
          </span>
        </div>
        <div className="divide-y divide-white/5 max-h-[380px] overflow-y-auto">
          {feed === null ? (
            <div className="px-5 py-8 text-white/30 text-sm font-mono">Loading team activity…</div>
          ) : feed.length === 0 ? (
            <div className="px-5 py-8 text-white/40 text-sm text-center">
              Your AI team is warming up. Autonomous updates will appear here as they work.
            </div>
          ) : (
            feed.map((act) => <ActivityRow key={act.activity_id} act={act} agents={agents} onOpen={openActivity} />)
          )}
        </div>
        <a href="/team" className="block text-center text-sm text-brand hover:underline py-3 border-t border-white/10">
          Open the AI Team →
        </a>
      </div>
    );
  }

  // ---------------- full Team Pulse tab ----------------
  return (
    <div className="flex flex-col h-full" data-testid="team-pulse">
      {/* Working-now strip */}
      <div className="px-6 py-4 border-b border-white/10 bg-surface1">
        <div className="flex items-center gap-2 mb-3">
          <span className="relative flex h-2.5 w-2.5">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
            <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-emerald-400" />
          </span>
          <h2 className="font-display font-bold text-lg">Team Pulse</h2>
          <span className="text-[11px] text-white/40 font-mono ml-1">
            {board?.working_now ? `${board.working_now} working now` : "all idle · on standby"}
            {board ? ` · ${board.today_count} updates today` : ""}
          </span>
        </div>
        {working.length > 0 ? (
          <div className="flex gap-2 flex-wrap" data-testid="working-now">
            {working.map(([id, s]) => (
              <div key={id} className="flex items-center gap-2 border border-emerald-400/30 bg-emerald-400/5 px-2.5 py-1.5">
                <img src={`/agents/${id}.png`} alt={id} className="w-6 h-6 rounded-full object-cover" />
                <span className="text-xs">
                  <span className="font-semibold" style={{ color: agents[id]?.color }}>{agents[id]?.name || id}</span>
                  <span className="text-white/50"> — {s.current_task || "working"}…</span>
                </span>
                <span className="flex gap-0.5 ml-1">
                  <span className="w-1 h-1 bg-emerald-400 rounded-full animate-bounce" />
                  <span className="w-1 h-1 bg-emerald-400 rounded-full animate-bounce" style={{ animationDelay: "150ms" }} />
                  <span className="w-1 h-1 bg-emerald-400 rounded-full animate-bounce" style={{ animationDelay: "300ms" }} />
                </span>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-xs text-white/40">
            The team is on standby between scheduled duties. They check in on their own — updates land here automatically.
          </p>
        )}
      </div>

      {/* Filter chips */}
      <div className="flex gap-2 overflow-x-auto px-6 py-3 border-b border-white/10 bg-surface1/60">
        <button onClick={() => setFilter(null)}
          className={`shrink-0 text-xs px-3 py-1.5 border transition-colors duration-200 ${
            !filter ? "border-brand text-brand" : "border-white/10 text-white/50 hover:text-white"}`}>
          All activity
        </button>
        {Object.entries(agents).map(([id, a]) => (
          <button key={id} onClick={() => setFilter(id === filter ? null : id)}
            className={`shrink-0 flex items-center gap-1.5 text-xs px-3 py-1.5 border transition-colors duration-200 ${
              filter === id ? "border-brand text-brand" : "border-white/10 text-white/50 hover:text-white"}`}>
            <img src={`/agents/${id}.png`} alt="" className="w-4 h-4 rounded-full object-cover" /> {a.name}
          </button>
        ))}
      </div>

      {/* Feed */}
      <div className="flex-1 overflow-y-auto divide-y divide-white/5" data-testid="activity-feed">
        {feed === null ? (
          <div className="px-6 py-12 text-white/30 text-sm font-mono">Loading team activity…</div>
        ) : (shown || []).length === 0 ? (
          <div className="max-w-md mx-auto text-center mt-16">
            <Activity className="w-10 h-10 text-white/20 mx-auto" />
            <h3 className="font-display text-lg font-bold mt-4">No activity yet</h3>
            <p className="text-white/40 text-sm mt-2">
              Your AI team runs on a schedule — daily briefings, articles, weekly builds, lead hunts —
              and checks in proactively between duties. Everything they do autonomously shows up here.
            </p>
          </div>
        ) : (
          shown.map((act) => <ActivityRow key={act.activity_id} act={act} agents={agents} onOpen={openActivity} />)
        )}
      </div>
    </div>
  );
}
