import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import DashboardLayout from "@/components/DashboardLayout";
import { TeamPanel } from "@/components/TeamPanel";
import { api } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { toast } from "sonner";
import { Zap, Calendar, RefreshCw, CreditCard, AlertTriangle, Check, Loader2, Receipt } from "lucide-react";

const fmtDate = (iso) => (iso ? new Date(iso).toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" }) : "—");

export default function Billing() {
  const { user, refreshUser } = useAuth();
  const navigate = useNavigate();
  const [sub, setSub] = useState(null);
  const [busy, setBusy] = useState(false);

  const load = () => api.get("/subscription").then(({ data }) => setSub(data)).catch(() => {});
  useEffect(() => { load(); }, []);

  const cancel = async () => {
    setBusy(true);
    try { await api.post("/subscription/cancel"); await load(); await refreshUser(); toast.success("Subscription set to cancel at period end."); }
    catch (e) { toast.error(e.response?.data?.detail || "Failed to cancel."); }
    finally { setBusy(false); }
  };
  const reactivate = async () => {
    setBusy(true);
    try { await api.post("/subscription/reactivate"); await load(); await refreshUser(); toast.success("Subscription reactivated."); }
    catch (e) { toast.error(e.response?.data?.detail || "Failed."); }
    finally { setBusy(false); }
  };

  if (!sub) return <DashboardLayout><div className="p-10 font-mono text-white/40">Loading…</div></DashboardLayout>;

  const active = sub.status === "active";

  return (
    <DashboardLayout>
      <div className="p-6 md:p-10 max-w-5xl">
        <div className="mb-8">
          <div className="font-mono text-xs text-white/40 uppercase tracking-wider">Account</div>
          <h1 className="font-display text-3xl md:text-4xl font-bold mt-1">Billing & Credits</h1>
        </div>

        <div className="grid md:grid-cols-3 gap-4 mb-6">
          {/* Subscription status */}
          <div className="md:col-span-2 border border-white/10 bg-surface1 p-6" data-testid="subscription-card">
            <div className="flex items-start justify-between">
              <div>
                <div className="text-xs text-white/40 uppercase font-mono">Current plan</div>
                <div className="font-display text-3xl font-bold mt-1">{active ? sub.plan_name : "No active plan"}</div>
              </div>
              <span data-testid="sub-status-badge" className={`text-xs font-mono px-3 py-1 border ${active ? (sub.cancel_at_period_end ? "border-neon text-neon" : "border-brand text-brand") : "border-white/20 text-white/50"}`}>
                {active ? (sub.cancel_at_period_end ? "CANCELLING" : "ACTIVE") : "INACTIVE"}
              </span>
            </div>

            {active && (
              <>
                <div className="grid grid-cols-2 gap-4 mt-6 text-sm">
                  <div className="border border-white/10 p-4">
                    <div className="text-white/40 text-xs flex items-center gap-1"><CreditCard className="w-3 h-3" /> Price</div>
                    <div className="font-mono text-lg mt-1">${sub.amount}<span className="text-white/40 text-xs"> / {sub.billing_days}d</span></div>
                  </div>
                  <div className="border border-white/10 p-4">
                    <div className="text-white/40 text-xs flex items-center gap-1"><Zap className="w-3 h-3" /> Monthly credits</div>
                    <div className="font-mono text-lg mt-1">{sub.unlimited ? "Unlimited" : sub.monthly_credits}</div>
                  </div>
                  <div className="border border-white/10 p-4">
                    <div className="text-white/40 text-xs flex items-center gap-1"><Calendar className="w-3 h-3" /> {sub.cancel_at_period_end ? "Access until" : "Renews on"}</div>
                    <div className="font-mono text-sm mt-1">{fmtDate(sub.current_period_end)}</div>
                  </div>
                  <div className="border border-white/10 p-4">
                    <div className="text-white/40 text-xs flex items-center gap-1"><RefreshCw className="w-3 h-3" /> Next credit refill</div>
                    <div className="font-mono text-sm mt-1">{fmtDate(sub.next_credit_reset)}</div>
                  </div>
                </div>

                {sub.cancel_at_period_end ? (
                  <div className="mt-5 flex items-center gap-3 flex-wrap">
                    <div className="flex items-center gap-2 text-neon text-sm"><AlertTriangle className="w-4 h-4" /> Cancels on {fmtDate(sub.current_period_end)}</div>
                    <button data-testid="reactivate-btn" onClick={reactivate} disabled={busy} className="flex items-center gap-2 bg-brand hover:bg-brand-hover px-4 py-2 text-sm transition-colors duration-300 disabled:opacity-50">
                      {busy ? <Loader2 className="w-4 h-4 animate-spin" /> : <Check className="w-4 h-4" />} Keep my plan
                    </button>
                  </div>
                ) : (
                  <div className="mt-5 flex items-center gap-3 flex-wrap">
                    <button data-testid="change-plan-btn" onClick={() => navigate("/pricing")} className="border border-white/15 hover:border-white/40 px-4 py-2 text-sm transition-colors duration-300">Change plan</button>
                    <button data-testid="cancel-btn" onClick={cancel} disabled={busy} className="flex items-center gap-2 border border-white/15 hover:border-neon hover:text-neon px-4 py-2 text-sm transition-colors duration-300 disabled:opacity-50">
                      {busy ? <Loader2 className="w-4 h-4 animate-spin" /> : null} Cancel subscription
                    </button>
                  </div>
                )}
              </>
            )}

            {!active && (
              <div className="mt-6">
                <p className="text-white/50 text-sm">Subscribe to a plan to get monthly AI credits and unlock the generator at scale.</p>
                <Link to="/pricing" data-testid="choose-plan-btn" className="inline-block mt-4 bg-brand hover:bg-brand-hover px-5 py-3 text-sm transition-colors duration-300">Choose a plan</Link>
              </div>
            )}
          </div>

          {/* Credits breakdown */}
          <div className="border border-white/10 bg-surface1 p-6 flex flex-col" data-testid="credits-breakdown">
            <div className="text-xs text-white/40 uppercase font-mono">Available credits</div>
            <div className="font-mono text-5xl font-bold text-brand mt-2" data-testid="billing-total-credits">{sub.unlimited ? "∞" : sub.plan_credits + sub.extra_credits}</div>
            <div className="mt-6 space-y-3 text-sm">
              <div className="flex items-center justify-between"><span className="text-white/50">Plan credits</span><span className="font-mono">{sub.unlimited ? "∞" : sub.plan_credits}</span></div>
              <div className="flex items-center justify-between"><span className="text-white/50">Purchased credits</span><span className="font-mono">{sub.extra_credits}</span></div>
            </div>
            <button onClick={() => navigate("/pricing")} data-testid="buy-credits-btn" className="mt-auto pt-6 text-neon text-sm hover:underline text-left flex items-center gap-1">
              <Zap className="w-4 h-4" /> Buy more credits →
            </button>
          </div>
        </div>

        {/* Team (multi-seat) */}
        <TeamPanel onChange={() => { load(); refreshUser(); }} />

        {/* Invoices */}
        <div className="border border-white/10 bg-surface1">
          <div className="px-6 py-4 border-b border-white/10 flex items-center gap-2">
            <Receipt className="w-4 h-4 text-white/60" /><h2 className="font-display font-bold">Payment history</h2>
          </div>
          {sub.invoices.length === 0 ? (
            <div className="p-8 text-center text-white/40 text-sm">No payments yet.</div>
          ) : (
            <div className="divide-y divide-white/5">
              {sub.invoices.map((inv, i) => (
                <div key={i} className="px-6 py-4 flex items-center justify-between text-sm" data-testid={`invoice-${i}`}>
                  <div>
                    <div className="font-medium capitalize">{inv.kind === "renewal" ? "Renewal" : inv.kind === "subscription" ? "Subscription" : "Credit pack"} — {inv.plan_id}</div>
                    <div className="text-white/40 text-xs font-mono">{fmtDate(inv.created_at)}</div>
                  </div>
                  <div className="flex items-center gap-4">
                    <span className="text-white/50">+{inv.credits} cr</span>
                    <span className="font-mono">${inv.amount}</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        {user?.role === "owner" && (
          <div className="mt-10 border border-red-500/30 bg-red-500/5 p-5" data-testid="danger-zone">
            <div className="flex items-center gap-2 text-red-300 font-semibold text-sm">
              <AlertTriangle className="w-4 h-4" /> Danger zone — owner only
            </div>
            <p className="text-white/50 text-sm mt-2">
              Reset business data: removes all non-owner users, payment history, subscriptions, AI jobs and
              agent chat history so Titan &amp; the team report from a true zero. Keeps your account, your
              templates, Market listings and blog posts.
            </p>
            <button data-testid="reset-business-btn"
              onClick={async () => {
                const phrase = window.prompt('This wipes all test users, revenue records and AI chat history. Type RESET to confirm:');
                if (phrase !== "RESET") return;
                const includeLeads = window.confirm("Also clear Rex's lead board? (OK = yes, Cancel = keep leads)");
                try {
                  const { data } = await api.post("/auth/admin/reset-business-data", { confirm: "RESET", include_leads: includeLeads });
                  toast.success(`Fresh start: ${data.removed_users} test user(s) removed${data.leads_cleared ? ", lead board cleared" : ""}.`);
                } catch (e) {
                  toast.error(e.response?.data?.detail || "Reset failed.");
                }
              }}
              className="mt-3 text-sm border border-red-400/50 text-red-300 hover:border-red-300 px-4 py-2 transition-colors duration-300">
              Reset business data
            </button>
          </div>
        )}
        </div>
      </div>
    </DashboardLayout>
  );
}
