import { useEffect, useState, useCallback } from "react";
import { api, formatApiError } from "@/lib/api";
import { toast } from "sonner";
import { X, Loader2, CalendarDays, Bot, Wrench, Link2, MessageSquare, Gauge,
  Sparkles, TrendingUp, CheckCircle2, AlertTriangle } from "lucide-react";

const TABS = [
  { key: "overview", label: "Overview", icon: Gauge },
  { key: "calendar", label: "Calendar", icon: CalendarDays },
  { key: "geo", label: "AI Visibility", icon: Bot },
  { key: "tech", label: "Site Audit", icon: Wrench },
  { key: "links", label: "Link Map", icon: Link2 },
  { key: "reddit", label: "Community", icon: MessageSquare },
];

const scoreColor = (s) => s == null ? "text-white/40" : s >= 80 ? "text-emerald-300" : s >= 60 ? "text-yellow-300" : "text-red-300";

export function SeoCenter({ onClose }) {
  const [tab, setTab] = useState("overview");

  return (
    <div className="border-b border-green-400/20 bg-green-400/5 px-6 py-4" data-testid="seo-center">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <TrendingUp className="w-4 h-4 text-green-300" />
          <p className="text-sm font-semibold text-green-100">Ivy&apos;s SEO Command Center</p>
          <span className="text-[10px] font-mono uppercase tracking-wider text-green-300/60">Google + AI search · autopilot</span>
        </div>
        <button onClick={onClose} className="text-white/40 hover:text-white p-1"><X className="w-4 h-4" /></button>
      </div>

      <div className="flex gap-2 mt-3 flex-wrap">
        {TABS.map((t) => {
          const Icon = t.icon;
          return (
            <button key={t.key} data-testid={`seo-tab-${t.key}`} onClick={() => setTab(t.key)}
              className={`flex items-center gap-1.5 text-xs px-3 py-1.5 border transition-colors duration-200 ${
                tab === t.key ? "border-green-400 text-green-200" : "border-white/10 text-white/50 hover:text-white"}`}>
              <Icon className="w-3.5 h-3.5" /> {t.label}
            </button>
          );
        })}
      </div>

      <div className="mt-4 max-h-[54vh] overflow-y-auto pr-1" data-testid="seo-panel-body">
        {tab === "overview" && <Overview />}
        {tab === "calendar" && <Calendar />}
        {tab === "geo" && <Geo />}
        {tab === "tech" && <Tech />}
        {tab === "links" && <Links />}
        {tab === "reddit" && <Reddit />}
      </div>
    </div>
  );
}

function Stat({ label, value, tint = "text-white" }) {
  return (
    <div className="border border-white/10 bg-surface2/50 p-3">
      <div className="text-[10px] font-mono uppercase text-white/40">{label}</div>
      <div className={`text-2xl font-bold mt-1 ${tint}`}>{value}</div>
    </div>
  );
}

function Overview() {
  const [data, setData] = useState(null);
  useEffect(() => { api.get("/agents/ivy/seo/overview").then(({ data }) => setData(data)).catch(() => setData({})); }, []);
  if (!data) return <Loading />;
  return (
    <div data-testid="seo-overview">
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
        <Stat label="Planned topics" value={data.calendar_planned ?? 0} tint="text-green-300" />
        <Stat label="Articles live" value={data.articles_published ?? 0} />
        <Stat label="Avg SEO score" value={data.avg_article_score != null ? `${data.avg_article_score}` : "—"} tint={scoreColor(data.avg_article_score)} />
        <Stat label="AI visibility" value={data.last_geo_visibility != null ? `${data.last_geo_visibility}` : "—"} tint={scoreColor(data.last_geo_visibility)} />
      </div>
      <p className="text-xs text-white/50 mt-3 leading-relaxed">
        Ivy runs SEO on autopilot: she plans keywords, publishes a scored article daily, and tracks how visible
        SiteGenie is on Google and AI assistants. Use the tabs above to plan, audit and grow.
      </p>
    </div>
  );
}

function Calendar() {
  const [cal, setCal] = useState(null);
  const [busy, setBusy] = useState(false);
  const load = useCallback(() => api.get("/agents/ivy/seo/calendar").then(({ data }) => setCal(data.calendar)).catch(() => setCal([])), []);
  useEffect(() => { load(); }, [load]);
  const build = async () => {
    setBusy(true);
    try {
      const { data } = await api.post("/agents/ivy/seo/calendar");
      toast.success(`Ivy planned ${data.created} new topics.`);
      await load();
    } catch (e) { toast.error(formatApiError(e.response?.data?.detail)); }
    finally { setBusy(false); }
  };
  if (cal === null) return <Loading />;
  return (
    <div data-testid="seo-calendar">
      <div className="flex items-center justify-between mb-3">
        <span className="text-xs text-white/50">{cal.length} topics planned</span>
        <button data-testid="seo-build-calendar" onClick={build} disabled={busy}
          className="flex items-center gap-1.5 text-xs bg-green-500/90 hover:bg-green-400 text-black font-semibold px-3 py-1.5 transition-colors duration-200 disabled:opacity-50">
          {busy ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Sparkles className="w-3.5 h-3.5" />} Plan 30 days
        </button>
      </div>
      {cal.length === 0 ? (
        <Empty text="No calendar yet. Click 'Plan 30 days' and Ivy will research keywords and schedule a month of content." />
      ) : (
        <div className="space-y-1.5">
          {cal.map((c) => (
            <div key={c.cal_id} className="border border-white/8 bg-surface2/40 px-3 py-2">
              <div className="flex items-center gap-2 flex-wrap">
                <span className="text-[10px] font-mono text-white/30">{c.scheduled_for}</span>
                <span className={`text-[9px] font-mono uppercase px-1.5 py-0.5 ${
                  c.status === "published" ? "bg-emerald-400/15 text-emerald-300" : c.status === "writing" ? "bg-yellow-400/15 text-yellow-300" : "bg-white/5 text-white/40"}`}>{c.status}</span>
                <span className="text-[9px] font-mono uppercase text-green-300/70">{c.intent}</span>
                {c.score ? <span className={`text-[10px] font-mono ml-auto ${scoreColor(c.score)}`}>{c.score}/100</span> : null}
              </div>
              <div className="text-sm text-white/90 mt-1">{c.title}</div>
              <div className="text-[11px] text-white/40 mt-0.5">🔑 {c.target_keyword}{c.ai_prompt ? ` · 🤖 "${c.ai_prompt}"` : ""}</div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function Geo() {
  const [q, setQ] = useState("");
  const [busy, setBusy] = useState(false);
  const [res, setRes] = useState(null);
  const run = async () => {
    if (!q.trim()) return;
    setBusy(true); setRes(null);
    try {
      const { data } = await api.post("/agents/ivy/seo/geo-audit", { query: q });
      setRes(data);
    } catch (e) { toast.error(formatApiError(e.response?.data?.detail)); }
    finally { setBusy(false); }
  };
  return (
    <div data-testid="seo-geo">
      <p className="text-xs text-white/50 mb-2">Check if AI assistants (ChatGPT/Perplexity/Gemini) would recommend SiteGenie for a buyer&apos;s question.</p>
      <div className="flex gap-2">
        <input data-testid="seo-geo-input" value={q} onChange={(e) => setQ(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && run()}
          placeholder='e.g. "best AI website builder for a barber shop"'
          className="flex-1 bg-surface2 border border-white/10 focus:border-green-300 outline-none px-3 py-2 text-sm transition-colors duration-200" />
        <button data-testid="seo-geo-run" onClick={run} disabled={busy || !q.trim()}
          className="flex items-center gap-1.5 bg-green-500/90 hover:bg-green-400 text-black font-semibold px-3 py-2 text-sm transition-colors duration-200 disabled:opacity-50">
          {busy ? <Loader2 className="w-4 h-4 animate-spin" /> : "Audit"}
        </button>
      </div>
      {res && (
        <div className="mt-3 border border-white/10 bg-surface2/50 p-3" data-testid="seo-geo-result">
          <div className="flex items-center gap-2">
            <span className={`text-2xl font-bold ${scoreColor(res.visibility)}`}>{res.visibility}<span className="text-sm text-white/40">/100</span></span>
            {res.sitegenie_cited
              ? <span className="flex items-center gap-1 text-xs text-emerald-300"><CheckCircle2 className="w-3.5 h-3.5" /> Cited by AI</span>
              : <span className="flex items-center gap-1 text-xs text-red-300"><AlertTriangle className="w-3.5 h-3.5" /> Not cited yet</span>}
          </div>
          <p className="text-sm text-white/80 mt-2">{res.answer}</p>
          <p className="text-xs text-white/40 mt-2">{res.why}</p>
          {res.content_gap && (
            <div className="mt-3 border-t border-white/10 pt-2">
              <div className="text-[10px] font-mono uppercase text-green-300/70">Content gap to win this</div>
              <div className="text-sm text-white/85 mt-0.5">{res.content_gap}</div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function Tech() {
  const [url, setUrl] = useState("");
  const [busy, setBusy] = useState(false);
  const [res, setRes] = useState(null);
  const run = async () => {
    if (!url.trim()) return;
    setBusy(true); setRes(null);
    try {
      const { data } = await api.post("/agents/ivy/seo/tech-audit", { url });
      setRes(data);
    } catch (e) { toast.error(formatApiError(e.response?.data?.detail)); }
    finally { setBusy(false); }
  };
  const P = { high: "text-red-300 border-red-400/30", medium: "text-yellow-300 border-yellow-400/30", low: "text-white/50 border-white/15" };
  return (
    <div data-testid="seo-tech">
      <p className="text-xs text-white/50 mb-2">Scan any URL for technical SEO + GEO gaps (schema, meta, headings, alt text, JSON-LD).</p>
      <div className="flex gap-2">
        <input data-testid="seo-tech-input" value={url} onChange={(e) => setUrl(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && run()} placeholder="https://yoursite.com"
          className="flex-1 bg-surface2 border border-white/10 focus:border-green-300 outline-none px-3 py-2 text-sm transition-colors duration-200" />
        <button data-testid="seo-tech-run" onClick={run} disabled={busy || !url.trim()}
          className="flex items-center gap-1.5 bg-green-500/90 hover:bg-green-400 text-black font-semibold px-3 py-2 text-sm transition-colors duration-200 disabled:opacity-50">
          {busy ? <Loader2 className="w-4 h-4 animate-spin" /> : "Audit"}
        </button>
      </div>
      {res && (
        <div className="mt-3" data-testid="seo-tech-result">
          <p className="text-sm text-white/80">{res.summary}</p>
          <div className="space-y-1.5 mt-3">
            {res.fixes.map((f, i) => (
              <div key={i} className={`border ${P[f.priority] || P.low} bg-surface2/40 px-3 py-2`}>
                <div className="flex items-center gap-2">
                  <span className={`text-[9px] font-mono uppercase ${P[f.priority] || P.low}`}>{f.priority}</span>
                  <span className="text-sm text-white/90">{f.issue}</span>
                </div>
                <p className="text-xs text-white/40 mt-0.5">{f.why}</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function Links() {
  const [data, setData] = useState(null);
  useEffect(() => { api.get("/agents/ivy/seo/link-map").then(({ data }) => setData(data)).catch(() => setData({ pillars: [], total_posts: 0 })); }, []);
  if (!data) return <Loading />;
  if (!data.total_posts) return <div data-testid="seo-links"><Empty text="No published articles yet to map. Once Ivy publishes a few, she'll build a pillar/cluster internal-link map here." /></div>;
  return (
    <div data-testid="seo-links">
      <div className="text-xs text-white/50 mb-3">{data.total_posts} articles · {data.posts_with_links} with internal links</div>
      <div className="space-y-2">
        {(data.pillars || []).map((p, i) => (
          <div key={i} className="border border-white/8 bg-surface2/40 px-3 py-2">
            <div className="text-sm font-semibold text-green-200">{p.name}</div>
            <div className="text-[11px] text-white/40 mt-0.5">{(p.slugs || []).length} article(s) in this pillar</div>
          </div>
        ))}
      </div>
      {(data.suggestions || []).length > 0 && (
        <div className="mt-4">
          <div className="text-[10px] font-mono uppercase text-white/40 mb-2">Suggested internal links</div>
          <div className="space-y-1">
            {data.suggestions.slice(0, 12).map((s, i) => (
              <div key={i} className="text-xs text-white/60"><span className="text-white/80">{s.from}</span> → {(s.link_to || []).join(", ")}</div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function Reddit() {
  const [opps, setOpps] = useState(null);
  const [busy, setBusy] = useState(false);
  const run = async () => {
    setBusy(true);
    try {
      const { data } = await api.post("/agents/ivy/seo/reddit");
      setOpps(data.opportunities);
    } catch (e) { toast.error(formatApiError(e.response?.data?.detail)); }
    finally { setBusy(false); }
  };
  return (
    <div data-testid="seo-reddit">
      <div className="flex items-center justify-between mb-3">
        <p className="text-xs text-white/50">High-intent community threads (AI assistants increasingly cite Reddit) + ready-to-post helpful replies.</p>
      </div>
      <button data-testid="seo-reddit-run" onClick={run} disabled={busy}
        className="flex items-center gap-1.5 text-xs bg-green-500/90 hover:bg-green-400 text-black font-semibold px-3 py-1.5 transition-colors duration-200 disabled:opacity-50">
        {busy ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Sparkles className="w-3.5 h-3.5" />} Find opportunities
      </button>
      {opps && (
        <div className="space-y-2 mt-3">
          {opps.length === 0 ? <Empty text="No opportunities found — try again." /> : opps.map((o, i) => (
            <div key={i} className="border border-white/8 bg-surface2/40 px-3 py-2">
              <div className="flex items-center gap-2">
                <span className="text-sm font-semibold text-orange-300">{o.subreddit}</span>
                <span className="text-[11px] text-white/40">{o.angle}</span>
              </div>
              <p className="text-xs text-white/50 mt-1">{o.why}</p>
              <div className="mt-2 border-t border-white/10 pt-2">
                <div className="text-[10px] font-mono uppercase text-white/30 mb-1">Reply draft</div>
                <p className="text-xs text-white/75 leading-relaxed">{o.reply_draft}</p>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function Loading() {
  return <div className="flex items-center gap-2 text-white/40 text-sm font-mono py-6"><Loader2 className="w-4 h-4 animate-spin" /> Loading…</div>;
}
function Empty({ text }) {
  return <div className="text-center text-white/40 text-sm py-8 border border-dashed border-white/10 px-4">{text}</div>;
}
