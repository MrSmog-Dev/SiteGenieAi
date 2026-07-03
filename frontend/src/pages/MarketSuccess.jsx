import { useEffect, useState, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "@/lib/api";
import { CheckCircle2, XCircle, Loader2, Wand2 } from "lucide-react";

export default function MarketSuccess() {
  const navigate = useNavigate();
  const [state, setState] = useState("checking"); // checking | success | error | timeout
  const [info, setInfo] = useState(null);
  const started = useRef(false);

  useEffect(() => {
    if (started.current) return;
    started.current = true;
    const sessionId = new URLSearchParams(window.location.search).get("session_id");
    if (!sessionId) { setState("error"); return; }
    let attempts = 0;
    const poll = async () => {
      attempts += 1;
      if (attempts > 10) { setState("timeout"); return; }
      try {
        const { data } = await api.get(`/market/purchase/status/${sessionId}`);
        if (data.payment_status === "paid" && data.template_id) {
          setInfo(data);
          setState("success");
          return;
        }
        if (data.status === "expired") { setState("error"); return; }
        setTimeout(poll, 2000);
      } catch (e) {
        setTimeout(poll, 2000);
      }
    };
    poll();
  }, []);

  return (
    <div className="min-h-screen bg-base text-white flex items-center justify-center p-6">
      <div className="w-full max-w-md border border-white/10 bg-surface1 p-10 text-center" data-testid="market-success-card">
        {state === "checking" && (
          <>
            <Loader2 className="w-12 h-12 text-brand animate-spin mx-auto" />
            <h1 className="font-display text-2xl font-bold mt-6">Confirming your purchase…</h1>
            <p className="text-white/50 mt-2 text-sm">Setting up your copy of the template.</p>
          </>
        )}
        {state === "success" && (
          <>
            <CheckCircle2 className="w-12 h-12 text-emerald-400 mx-auto" />
            <h1 className="font-display text-2xl font-bold mt-6">The template is yours!</h1>
            <p className="text-white/50 mt-2 text-sm">
              It's been added to My Websites. You own it forever — publish it, export the ZIP, and make
              unlimited AI edits at no extra cost.
            </p>
            <div className="mt-6 flex items-center justify-center gap-2 border border-amber-400/30 text-amber-300 py-3">
              <Wand2 className="w-4 h-4" />
              <span className="font-mono text-sm">Free unlimited AI edits included</span>
            </div>
            <button data-testid="open-purchased-btn" onClick={() => navigate(`/templates/${info.template_id}`)}
              className="mt-6 w-full bg-brand hover:bg-brand-hover py-3 transition-colors duration-300">
              Open your website
            </button>
            <button data-testid="back-to-market-btn" onClick={() => navigate("/market")}
              className="mt-3 w-full border border-white/15 hover:border-white/40 py-3 transition-colors duration-300">
              Back to Market
            </button>
          </>
        )}
        {(state === "error" || state === "timeout") && (
          <>
            <XCircle className="w-12 h-12 text-neon mx-auto" />
            <h1 className="font-display text-2xl font-bold mt-6">{state === "timeout" ? "Still processing" : "Purchase issue"}</h1>
            <p className="text-white/50 mt-2 text-sm">
              {state === "timeout"
                ? "We couldn't confirm your purchase in time. Check My Websites in a moment — if it's not there, contact support."
                : "Your payment was cancelled or failed. You have not been charged."}
            </p>
            <button data-testid="market-retry-btn" onClick={() => navigate("/market")}
              className="mt-6 w-full border border-white/15 hover:border-white/40 py-3 transition-colors duration-300">
              Back to Market
            </button>
          </>
        )}
      </div>
    </div>
  );
}
