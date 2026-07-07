import { useEffect, useState } from "react";
import { api, formatApiError } from "@/lib/api";
import { toast } from "sonner";
import { X, Loader2, Sparkles, Zap } from "lucide-react";

/** In-app "buy top-up credits" modal (Emergent-style). Reuses the /checkout/session credits flow. */
export function TopUpModal({ onClose }) {
  const [packs, setPacks] = useState([]);
  const [busy, setBusy] = useState("");

  useEffect(() => {
    api.get("/plans").then(({ data }) => setPacks(Object.entries(data.credit_packs || {}))).catch(() => {});
  }, []);

  const buy = async (id) => {
    setBusy(id);
    try {
      const { data } = await api.post("/checkout/session", { kind: "credits", plan_id: id, origin_url: window.location.origin });
      window.location.href = data.url;
    } catch (e) {
      toast.error(formatApiError(e.response?.data?.detail) || e.message);
      setBusy("");
    }
  };

  return (
    <div className="fixed inset-0 z-[70] flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm" onClick={onClose} data-testid="topup-modal">
      <div className="w-full max-w-2xl bg-surface1 border border-white/12 rounded-xl overflow-hidden max-h-[90vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between px-6 py-4 border-b border-white/10">
          <div className="flex items-center gap-2">
            <Zap className="w-5 h-5 text-brand" />
            <h2 className="font-display font-bold">Buy more credits</h2>
          </div>
          <button data-testid="topup-close" onClick={onClose} className="text-white/40 hover:text-white"><X className="w-5 h-5" /></button>
        </div>
        <p className="px-6 pt-4 text-sm text-white/50">One-time top-ups that <span className="text-white/70">never expire</span>. Used after your monthly plan credits run out.</p>
        <div className="grid sm:grid-cols-3 gap-3 p-6">
          {packs.map(([id, p]) => {
            const popular = p.note === "Most popular";
            const value = p.note && !popular;
            return (
              <button key={id} data-testid={`topup-buy-${id}`} onClick={() => buy(id)} disabled={busy === id}
                className={`relative text-center border p-4 transition-colors duration-200 disabled:opacity-60 ${
                  popular ? "border-brand bg-brand/5" : value ? "border-amber-400/40 bg-amber-400/5" : "border-white/10 hover:border-white/30"}`}>
                {p.note && (
                  <div className={`absolute -top-2.5 left-1/2 -translate-x-1/2 text-[9px] font-mono px-2 py-0.5 rounded whitespace-nowrap ${popular ? "bg-brand" : "bg-amber-400 text-black"}`}>
                    {p.note.toUpperCase()}
                  </div>
                )}
                <div className="font-mono text-brand text-2xl font-bold mt-1">+{p.credits.toLocaleString()}</div>
                <div className="font-display text-lg font-bold mt-1">${p.amount.toLocaleString()}</div>
                <div className="text-white/30 text-[10px] mt-0.5">${(p.amount / p.credits).toFixed(2)}/credit</div>
                <div className="mt-3 flex items-center justify-center gap-1.5 text-xs text-white/60">
                  {busy === id ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Sparkles className="w-3.5 h-3.5" />} Buy
                </div>
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
}
