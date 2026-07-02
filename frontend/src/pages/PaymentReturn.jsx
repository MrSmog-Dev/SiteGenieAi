import { useEffect, useState, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { CheckCircle2, XCircle, Loader2, Zap } from "lucide-react";

export default function PaymentReturn() {
  const navigate = useNavigate();
  const { refreshUser } = useAuth();
  const [state, setState] = useState("checking"); // checking | success | error | timeout
  const [info, setInfo] = useState(null);
  const started = useRef(false);

  useEffect(() => {
    if (started.current) return;
    started.current = true;
    const params = new URLSearchParams(window.location.search);
    const sessionId = params.get("session_id");
    const isSubscription = params.get("type") === "subscription";
    if (!sessionId) { setState("error"); return; }
    const statusUrl = isSubscription
      ? `/subscription/checkout-status/${sessionId}`
      : `/checkout/status/${sessionId}`;

    let attempts = 0;
    const poll = async () => {
      attempts += 1;
      if (attempts > 8) { setState("timeout"); return; }
      try {
        const { data } = await api.get(statusUrl);
        const done = isSubscription ? data.status === "complete" : data.payment_status === "paid";
        if (done) {
          setInfo(data);
          await refreshUser();
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
  }, [refreshUser]);

  return (
    <div className="min-h-screen bg-base text-white flex items-center justify-center p-6">
      <div className="w-full max-w-md border border-white/10 bg-surface1 p-10 text-center">
        {state === "checking" && (
          <>
            <Loader2 className="w-12 h-12 text-brand animate-spin mx-auto" />
            <h1 className="font-display text-2xl font-bold mt-6">Confirming payment…</h1>
            <p className="text-white/50 mt-2 text-sm">Please wait, this only takes a moment.</p>
          </>
        )}
        {state === "success" && (
          <>
            <CheckCircle2 className="w-12 h-12 text-brand mx-auto" />
            <h1 className="font-display text-2xl font-bold mt-6">Payment successful!</h1>
            <p className="text-white/50 mt-2 text-sm">
              {info?.kind === "subscription" ? "Your plan is active." : "Credits added to your account."}
            </p>
            <div className="mt-6 flex items-center justify-center gap-2 border border-white/10 py-3">
              <Zap className="w-4 h-4 text-brand" />
              <span className="font-mono">{info?.user?.credits} credits available</span>
            </div>
            <button data-testid="payment-continue" onClick={() => navigate("/dashboard")} className="mt-6 w-full bg-brand hover:bg-brand-hover py-3 transition-colors duration-300">
              Go to dashboard
            </button>
          </>
        )}
        {(state === "error" || state === "timeout") && (
          <>
            <XCircle className="w-12 h-12 text-neon mx-auto" />
            <h1 className="font-display text-2xl font-bold mt-6">{state === "timeout" ? "Still processing" : "Payment issue"}</h1>
            <p className="text-white/50 mt-2 text-sm">
              {state === "timeout" ? "We couldn't confirm your payment in time. Check your dashboard shortly." : "Your payment was cancelled or failed."}
            </p>
            <button data-testid="payment-retry" onClick={() => navigate("/pricing")} className="mt-6 w-full border border-white/15 hover:border-white/40 py-3 transition-colors duration-300">
              Back to pricing
            </button>
          </>
        )}
      </div>
    </div>
  );
}
