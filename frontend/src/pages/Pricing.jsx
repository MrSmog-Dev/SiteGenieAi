import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api, formatApiError } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { toast } from "sonner";
import { Zap, Check, ArrowLeft, Loader2 } from "lucide-react";

export default function Pricing() {
  const { user, loading: authLoading } = useAuth();
  const navigate = useNavigate();
  const [plans, setPlans] = useState({ subscriptions: {}, credit_packs: {} });
  const [busy, setBusy] = useState("");

  useEffect(() => { api.get("/plans").then(({ data }) => setPlans(data)).catch(() => {}); }, []);

  const checkout = async (kind, plan_id) => {
    if (!user) { navigate("/register"); return; }
    setBusy(`${kind}-${plan_id}`);
    try {
      const endpoint = kind === "subscription" ? "/subscription/checkout" : "/checkout/session";
      const payload = kind === "subscription"
        ? { plan_id, origin_url: window.location.origin }
        : { kind, plan_id, origin_url: window.location.origin };
      const { data } = await api.post(endpoint, payload);
      window.location.href = data.url;
    } catch (e) {
      toast.error(formatApiError(e.response?.data?.detail) || e.message);
      setBusy("");
    }
  };

  const subs = Object.entries(plans.subscriptions || {});
  const packs = Object.entries(plans.credit_packs || {});
  const highlight = "quarterly";

  return (
    <div className="min-h-screen bg-base text-white">
      <header className="border-b border-white/10 bg-surface1">
        <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
          <Link to={user ? "/dashboard" : "/"} className="flex items-center gap-2 text-white/70 hover:text-white transition-colors duration-300">
            <ArrowLeft className="w-4 h-4" /> {user ? "Dashboard" : "Home"}
          </Link>
          {user && (
            <div className="flex items-center gap-2 border border-white/10 px-3 py-1.5">
              <Zap className="w-4 h-4 text-brand" /><span className="font-mono text-sm" data-testid="pricing-credits">{user.credits} credits</span>
            </div>
          )}
        </div>
      </header>

      <div className="max-w-6xl mx-auto px-6 py-16">
        <div className="text-center mb-14">
          <h1 className="font-display text-4xl md:text-5xl font-bold">Choose your plan</h1>
          <p className="mt-4 text-white/50">Subscribe for monthly credits. <span className="font-mono text-white/70">1 credit = 1 website</span>.</p>
        </div>

        {/* Subscriptions */}
        <div className="grid md:grid-cols-3 gap-4">
          {subs.map(([id, p]) => (
            <div key={id} className={`relative border p-8 bg-surface1 transition-all duration-300 ${id === highlight ? "border-brand" : "border-white/10 hover:border-white/30"}`}>
              {id === highlight && <div className="absolute -top-3 left-8 bg-brand text-xs font-mono px-3 py-1">BEST VALUE</div>}
              <div className="font-display text-lg font-semibold">{p.name}</div>
              <div className="mt-4 flex items-end gap-1">
                <span className="font-display text-5xl font-bold">${p.amount}</span>
              </div>
              <div className="mt-6 font-mono text-brand text-2xl font-bold">{p.credits} credits</div>
              <ul className="mt-6 space-y-3 text-sm text-white/60">
                <li className="flex gap-2"><Check className="w-4 h-4 text-brand shrink-0" /> {p.credits} AI website generations</li>
                <li className="flex gap-2"><Check className="w-4 h-4 text-brand shrink-0" /> Unlimited previews & exports</li>
                <li className="flex gap-2"><Check className="w-4 h-4 text-brand shrink-0" /> Buy extra credits anytime</li>
              </ul>
              <button data-testid={`subscribe-${id}`} disabled={busy === `subscription-${id}`} onClick={() => checkout("subscription", id)}
                className={`mt-8 w-full flex items-center justify-center gap-2 py-3 font-medium transition-colors duration-300 disabled:opacity-60 ${id === highlight ? "bg-brand hover:bg-brand-hover" : "border border-white/15 hover:border-white/40"}`}>
                {busy === `subscription-${id}` ? <Loader2 className="w-4 h-4 animate-spin" /> : null}
                Subscribe
              </button>
            </div>
          ))}
        </div>

        {/* Credit packs */}
        <div className="mt-20">
          <div className="text-center mb-10">
            <h2 className="font-display text-3xl font-bold">Need more credits?</h2>
            <p className="mt-3 text-white/50">Hit your limit? Top up instantly — no subscription change required.</p>
          </div>
          <div className="grid sm:grid-cols-3 gap-4">
            {packs.map(([id, p]) => (
              <div key={id} className="border border-white/10 hover:border-neon/50 bg-surface1 p-8 text-center transition-colors duration-300">
                <div className="font-mono text-neon text-4xl font-bold">+{p.credits}</div>
                <div className="text-white/50 text-sm mt-1">{p.name}</div>
                <div className="font-display text-2xl font-bold mt-4">${p.amount}</div>
                <button data-testid={`buy-${id}`} disabled={busy === `credits-${id}`} onClick={() => checkout("credits", id)}
                  className="mt-6 w-full flex items-center justify-center gap-2 border border-white/15 hover:border-neon hover:text-neon py-3 transition-colors duration-300 disabled:opacity-60">
                  {busy === `credits-${id}` ? <Loader2 className="w-4 h-4 animate-spin" /> : null}
                  Buy credits
                </button>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
