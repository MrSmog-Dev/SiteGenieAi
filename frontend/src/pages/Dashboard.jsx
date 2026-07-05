import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import DashboardLayout from "@/components/DashboardLayout";
import { api } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { Sparkles, LayoutTemplate, Zap, CreditCard, ArrowRight, Calendar, PartyPopper, CheckCircle2, Circle } from "lucide-react";

export default function Dashboard() {
  const { user } = useAuth();
  const [templates, setTemplates] = useState([]);
  const [milestones, setMilestones] = useState(null);

  useEffect(() => {
    api.get("/templates").then(({ data }) => setTemplates(data)).catch(() => {});
  }, []);

  useEffect(() => {
    if (user?.role === "owner") {
      api.get("/milestones").then(({ data }) => setMilestones(data.milestones)).catch(() => {});
    }
  }, [user?.role]);

  const planLabel = user?.plan_name || "Free";
  const expires = user?.plan_expires_at ? new Date(user.plan_expires_at).toLocaleDateString() : null;

  return (
    <DashboardLayout>
      <div className="p-6 md:p-10 max-w-6xl">
        <div className="mb-8">
          <div className="font-mono text-xs text-white/40 uppercase tracking-wider">Dashboard</div>
          <h1 className="font-display text-3xl md:text-4xl font-bold mt-1">Hi, {user?.name?.split(" ")[0] || "there"} 👋</h1>
        </div>

        {/* stat cards */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-6">
          <div className="border border-white/10 bg-surface1 p-6" data-testid="stat-credits">
            <div className="flex items-center justify-between">
              <span className="text-xs text-white/40 uppercase font-mono">Credits left</span>
              <Zap className="w-4 h-4 text-brand" />
            </div>
            <div className="font-mono text-4xl font-bold mt-3 text-brand">{user?.unlimited ? "∞" : (user?.credits ?? 0)}</div>
            {!user?.unlimited && (user?.credits ?? 0) <= 5 && <div className="text-neon text-xs mt-2">Running low — top up soon.</div>}
          </div>
          <div className="border border-white/10 bg-surface1 p-6" data-testid="stat-plan">
            <div className="flex items-center justify-between">
              <span className="text-xs text-white/40 uppercase font-mono">Plan</span>
              <CreditCard className="w-4 h-4 text-white/50" />
            </div>
            <div className="font-display text-2xl font-bold mt-3">{planLabel}</div>
            {expires && <div className="text-white/40 text-xs mt-2 flex items-center gap-1"><Calendar className="w-3 h-3" /> Renews {expires}</div>}
          </div>
          <div className="border border-white/10 bg-surface1 p-6" data-testid="stat-templates">
            <div className="flex items-center justify-between">
              <span className="text-xs text-white/40 uppercase font-mono">Websites made</span>
              <LayoutTemplate className="w-4 h-4 text-white/50" />
            </div>
            <div className="font-mono text-4xl font-bold mt-3">{templates.length}</div>
          </div>
        </div>

        {milestones && (
          <div className="border border-white/10 bg-surface1 p-6 mb-6" data-testid="milestone-tracker">
            <div className="flex items-center gap-2 mb-4">
              <PartyPopper className="w-4 h-4 text-amber-300" />
              <h2 className="font-display font-bold">Launch Day milestones</h2>
              <span className="text-[10px] font-mono uppercase tracking-wider text-white/40 ml-1">
                {milestones.filter((m) => m.achieved).length}/{milestones.length} unlocked
              </span>
            </div>
            <div className="grid sm:grid-cols-2 lg:grid-cols-5 gap-3">
              {milestones.map((m) => (
                <div key={m.id} data-testid={`milestone-${m.id}`}
                  className={`border p-3 ${m.achieved ? "border-emerald-400/40 bg-emerald-400/5" : "border-white/10 opacity-60"}`}>
                  {m.achieved
                    ? <CheckCircle2 className="w-4 h-4 text-emerald-300" />
                    : <Circle className="w-4 h-4 text-white/30" />}
                  <div className="text-sm font-semibold mt-2 leading-tight">{m.title}</div>
                  <div className={`text-[11px] mt-1 ${m.achieved ? "text-emerald-300/90" : "text-white/35"}`}>
                    {m.achieved ? `🎉 ${m.detail}${m.date ? ` · ${m.date}` : ""}` : m.hint}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* CTA row */}
        <div className="grid md:grid-cols-2 gap-4 mb-10">
          <Link to="/generate" data-testid="dashboard-generate-cta" className="group border border-brand bg-brand/10 hover:bg-brand/20 p-8 transition-colors duration-300">
            <Sparkles className="w-8 h-8 text-brand" />
            <h3 className="font-display text-xl font-bold mt-4">Generate a new website</h3>
            <p className="text-white/50 text-sm mt-1">Describe your business and let AI do the rest.</p>
            <span className="inline-flex items-center gap-2 mt-4 text-brand text-sm">Start <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform duration-300" /></span>
          </Link>
          <Link to="/pricing" data-testid="dashboard-buy-cta" className="group border border-white/10 hover:border-white/30 bg-surface1 p-8 transition-colors duration-300">
            <CreditCard className="w-8 h-8 text-white/70" />
            <h3 className="font-display text-xl font-bold mt-4">Upgrade or buy credits</h3>
            <p className="text-white/50 text-sm mt-1">Subscribe monthly, quarterly or annually — or top up.</p>
            <span className="inline-flex items-center gap-2 mt-4 text-white/70 text-sm">View plans <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform duration-300" /></span>
          </Link>
        </div>

        {/* recent */}
        <div className="flex items-center justify-between mb-4">
          <h2 className="font-display text-xl font-bold">Recent websites</h2>
          <Link to="/templates" className="text-sm text-brand hover:underline">View all</Link>
        </div>
        {templates.length === 0 ? (
          <div className="border border-dashed border-white/15 p-12 text-center text-white/40">
            No websites yet. <Link to="/generate" className="text-brand hover:underline">Generate your first one →</Link>
          </div>
        ) : (
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {templates.slice(0, 6).map((t) => (
              <Link key={t.template_id} to={`/templates/${t.template_id}`} data-testid={`recent-template-${t.template_id}`}
                className="border border-white/10 hover:border-white/30 bg-surface1 p-5 transition-colors duration-300">
                <div className="w-8 h-8 flex items-center justify-center" style={{ background: t.primary_color || "#0055FF" }}>
                  <LayoutTemplate className="w-4 h-4 text-white" />
                </div>
                <h3 className="font-display font-semibold mt-3 truncate">{t.business_name}</h3>
                <p className="text-white/40 text-xs mt-1">{t.industry}</p>
              </Link>
            ))}
          </div>
        )}
      </div>
    </DashboardLayout>
  );
}
