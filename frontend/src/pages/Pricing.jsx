import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api, formatApiError } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { toast } from "sonner";
import { Zap, Check, X, ArrowLeft, Loader2, Sparkles } from "lucide-react";

// SiteGenie-relevant feature bullets per plan (structure mirrors Emergent).
const PLAN_FEATURES = {
  free: [
    "15 credits to start",
    "AI website generation",
    "Visual click-to-edit builder",
    "Publish to a free SiteGenie link",
  ],
  standard: [
    "50 credits / month",
    "Everything in Free, plus:",
    "Custom domains",
    "ZIP export & download",
    "Per-site analytics",
    "Buy top-up credits anytime",
  ],
  pro: [
    "120 credits / month",
    "Everything in Standard, plus:",
    "Premium build tier (animations, galleries)",
    "Sell on the Template Market",
    "Priority AI builds",
    "Priority support",
  ],
  team: [
    "750 shared credits / month",
    "Everything in Pro, plus:",
    "Up to 5 team members",
    "Shared credit pool",
    "Collaborative workspace",
  ],
};

const COMPARISON = [
  { label: "Monthly credits", free: "15", standard: "50", pro: "120", team: "750" },
  { label: "Team members", free: "1", standard: "1", pro: "1", team: "5" },
  { label: "AI website generation", free: true, standard: true, pro: true, team: true },
  { label: "Visual editor", free: true, standard: true, pro: true, team: true },
  { label: "Custom domains", free: false, standard: true, pro: true, team: true },
  { label: "ZIP export", free: false, standard: true, pro: true, team: true },
  { label: "Analytics", free: false, standard: true, pro: true, team: true },
  { label: "Top-up credits", free: false, standard: true, pro: true, team: true },
  { label: "Premium build tier", free: false, standard: false, pro: true, team: true },
  { label: "Sell on Template Market", free: false, standard: false, pro: true, team: true },
  { label: "Priority support", free: false, standard: false, pro: true, team: true },
  { label: "Annual billing", free: false, standard: true, pro: true, team: true },
];

const PLAN_ORDER = ["free", "standard", "pro", "team"];

function Cell({ v }) {
  return typeof v === "boolean"
    ? (v ? <Check className="w-4 h-4 text-brand mx-auto" /> : <X className="w-4 h-4 text-white/20 mx-auto" />)
    : <span className="text-white/80">{v}</span>;
}

export default function Pricing() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [plans, setPlans] = useState({ subscriptions: {}, credit_packs: {} });
  const [busy, setBusy] = useState("");
  const [billing, setBilling] = useState("monthly"); // monthly | annual

  useEffect(() => { api.get("/plans").then(({ data }) => setPlans(data)).catch(() => {}); }, []);

  const subscribe = async (plan_id) => {
    if (!user) { navigate("/register"); return; }
    setBusy(`sub-${plan_id}`);
    try {
      const { data } = await api.post("/subscription/checkout", { plan_id, billing, origin_url: window.location.origin });
      window.location.href = data.url;
    } catch (e) {
      toast.error(formatApiError(e.response?.data?.detail) || e.message);
      setBusy("");
    }
  };

  const buyPack = async (plan_id) => {
    if (!user) { navigate("/register"); return; }
    setBusy(`pack-${plan_id}`);
    try {
      const { data } = await api.post("/checkout/session", { kind: "credits", plan_id, origin_url: window.location.origin });
      window.location.href = data.url;
    } catch (e) {
      toast.error(formatApiError(e.response?.data?.detail) || e.message);
      setBusy("");
    }
  };

  const subs = plans.subscriptions || {};
  const packs = Object.entries(plans.credit_packs || {});
  const highlight = "pro";
  const activePlan = user?.plan;

  const priceFor = (id, p) => {
    if (id === "free") return { big: "$0", sub: "forever" };
    if (billing === "annual" && p.annual_available) return { big: `$${p.annual_amount}`, sub: "/mo · billed yearly" };
    return { big: `$${p.amount}`, sub: "/mo" };
  };

  return (
    <div className="min-h-screen bg-base text-white">
      <header className="border-b border-white/10 bg-surface1 sticky top-0 z-20">
        <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
          <Link to={user ? "/dashboard" : "/"} className="flex items-center gap-2 text-white/70 hover:text-white transition-colors duration-300">
            <ArrowLeft className="w-4 h-4" /> {user ? "Dashboard" : "Home"}
          </Link>
          {user && (
            <div className="flex items-center gap-2 border border-white/10 px-3 py-1.5">
              <Zap className="w-4 h-4 text-brand" /><span className="font-mono text-sm" data-testid="pricing-credits">{user.unlimited ? "∞" : user.credits} credits</span>
            </div>
          )}
        </div>
      </header>

      <div className="max-w-6xl mx-auto px-6 py-14">
        <div className="text-center mb-8">
          <h1 className="font-display text-4xl md:text-5xl font-bold">Plans &amp; Credits</h1>
          <p className="mt-4 text-white/50 max-w-xl mx-auto">Credits power everything — generating, editing and publishing sites.
            <span className="text-white/70"> Pick a plan, top up anytime.</span></p>
        </div>

        {/* Billing toggle */}
        <div className="flex justify-center mb-10">
          <div className="inline-flex items-center border border-white/12 bg-surface1 p-1 rounded-lg" data-testid="billing-toggle">
            <button data-testid="billing-monthly" onClick={() => setBilling("monthly")}
              className={`px-5 py-2 text-sm rounded-md transition-colors duration-200 ${billing === "monthly" ? "bg-brand text-white" : "text-white/60 hover:text-white"}`}>
              Monthly
            </button>
            <button data-testid="billing-annual" onClick={() => setBilling("annual")}
              className={`px-5 py-2 text-sm rounded-md transition-colors duration-200 flex items-center gap-2 ${billing === "annual" ? "bg-brand text-white" : "text-white/60 hover:text-white"}`}>
              Annual <span className="text-[10px] font-mono bg-emerald-400/20 text-emerald-300 px-1.5 py-0.5 rounded">Save ~15%</span>
            </button>
          </div>
        </div>

        {/* Plan cards */}
        <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-4" data-testid="plan-cards">
          {PLAN_ORDER.map((id) => {
            const p = subs[id]; if (!p) return null;
            const price = priceFor(id, p);
            const isActive = activePlan === id;
            return (
              <div key={id} data-testid={`plan-${id}`}
                className={`relative border p-6 bg-surface1 flex flex-col transition-all duration-300 ${id === highlight ? "border-brand shadow-[0_0_30px_rgba(0,85,255,0.15)]" : "border-white/10 hover:border-white/30"}`}>
                {id === highlight && <div className="absolute -top-3 left-6 bg-brand text-[11px] font-mono px-3 py-1 rounded">MOST POPULAR</div>}
                <div className="font-display text-lg font-semibold">{p.name}</div>
                <p className="text-white/40 text-xs mt-1 min-h-[32px]">{p.tagline}</p>
                <div className="mt-3 flex items-end gap-1.5">
                  <span className="font-display text-4xl font-bold">{price.big}</span>
                  <span className="text-white/40 text-sm mb-1.5">{price.sub}</span>
                </div>
                <div className="mt-3 font-mono text-brand text-sm font-bold">{p.monthly_credits} credits{id === "team" ? " shared" : ""}/mo</div>
                <ul className="mt-4 space-y-2.5 text-sm text-white/60 flex-1">
                  {PLAN_FEATURES[id].map((f, i) => (
                    <li key={i} className={`flex gap-2 ${f.endsWith("plus:") ? "text-white/40 text-xs font-mono uppercase tracking-wide mt-1" : ""}`}>
                      {!f.endsWith("plus:") && <Check className="w-4 h-4 text-brand shrink-0 mt-0.5" />} {f}
                    </li>
                  ))}
                </ul>
                {id === "free" ? (
                  <button disabled className="mt-6 w-full py-2.5 text-sm border border-white/10 text-white/40 cursor-default">
                    {isActive || !user ? "Included" : "Free forever"}
                  </button>
                ) : isActive ? (
                  <button disabled data-testid={`plan-current-${id}`} className="mt-6 w-full py-2.5 text-sm border border-emerald-400/40 text-emerald-300 cursor-default">
                    Current plan
                  </button>
                ) : (
                  <button data-testid={`subscribe-${id}`} disabled={busy === `sub-${id}`} onClick={() => subscribe(id)}
                    className={`mt-6 w-full flex items-center justify-center gap-2 py-2.5 text-sm font-medium transition-colors duration-300 disabled:opacity-60 ${id === highlight ? "bg-brand hover:bg-brand-hover" : "border border-white/15 hover:border-white/40"}`}>
                    {busy === `sub-${id}` ? <Loader2 className="w-4 h-4 animate-spin" /> : null}
                    Choose {p.name}
                  </button>
                )}
              </div>
            );
          })}
        </div>

        {/* Comparison table */}
        <div className="mt-16">
          <h2 className="font-display text-2xl font-bold text-center mb-6">Compare plans</h2>
          <div className="overflow-x-auto border border-white/10">
            <table className="w-full text-sm" data-testid="comparison-table">
              <thead>
                <tr className="border-b border-white/10 bg-surface1">
                  <th className="text-left font-mono text-white/40 uppercase text-xs px-4 py-3 font-medium">Feature</th>
                  {PLAN_ORDER.map((id) => (
                    <th key={id} className={`px-4 py-3 text-center font-display font-semibold ${id === highlight ? "text-brand" : ""}`}>{subs[id]?.name}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                <tr className="border-b border-white/5">
                  <td className="px-4 py-3 text-white/60">Price</td>
                  {PLAN_ORDER.map((id) => {
                    const p = subs[id]; const price = p ? priceFor(id, p) : { big: "" };
                    return <td key={id} className="px-4 py-3 text-center font-semibold">{price.big}<span className="text-white/30 text-xs">{id !== "free" ? "/mo" : ""}</span></td>;
                  })}
                </tr>
                {COMPARISON.map((row, i) => (
                  <tr key={i} className="border-b border-white/5 hover:bg-surface1/50">
                    <td className="px-4 py-3 text-white/60">{row.label}</td>
                    <td className="px-4 py-3 text-center"><Cell v={row.free} /></td>
                    <td className="px-4 py-3 text-center"><Cell v={row.standard} /></td>
                    <td className="px-4 py-3 text-center"><Cell v={row.pro} /></td>
                    <td className="px-4 py-3 text-center"><Cell v={row.team} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Top-ups */}
        <div className="mt-20" data-testid="topup-section">
          <div className="text-center mb-3">
            <h2 className="font-display text-3xl font-bold">Top up anytime</h2>
            <p className="mt-3 text-white/50">One-time credit packs that <span className="text-white/70">never expire</span>. Used after your monthly credits run out.</p>
          </div>
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4 mt-8">
            {packs.map(([id, p]) => {
              const popular = p.note === "Most popular";
              const value = p.note && p.note !== "Most popular";
              return (
                <div key={id} data-testid={`pack-${id}`}
                  className={`relative border bg-surface1 p-6 text-center transition-colors duration-300 ${popular ? "border-brand" : value ? "border-amber-400/40" : "border-white/10 hover:border-white/30"}`}>
                  {p.note && (
                    <div className={`absolute -top-3 left-1/2 -translate-x-1/2 text-[10px] font-mono px-2.5 py-1 rounded whitespace-nowrap ${popular ? "bg-brand" : "bg-amber-400 text-black"}`}>
                      {p.note.toUpperCase()}
                    </div>
                  )}
                  <div className="font-mono text-brand text-4xl font-bold">+{p.credits.toLocaleString()}</div>
                  <div className="text-white/40 text-xs mt-1 uppercase font-mono tracking-wide">credits</div>
                  <div className="font-display text-2xl font-bold mt-4">${p.amount.toLocaleString()}</div>
                  <div className="text-white/30 text-[11px] mt-1">${(p.amount / p.credits).toFixed(2)}/credit</div>
                  <button data-testid={`buy-${id}`} disabled={busy === `pack-${id}`} onClick={() => buyPack(id)}
                    className={`mt-5 w-full flex items-center justify-center gap-2 py-2.5 text-sm transition-colors duration-300 disabled:opacity-60 ${popular ? "bg-brand hover:bg-brand-hover" : "border border-white/15 hover:border-brand hover:text-brand"}`}>
                    {busy === `pack-${id}` ? <Loader2 className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />}
                    Buy credits
                  </button>
                </div>
              );
            })}
          </div>
          <p className="text-center text-white/30 text-xs mt-6">Usage priority: monthly plan credits are used first, then top-ups. Top-ups never expire.</p>
        </div>
      </div>
    </div>
  );
}
