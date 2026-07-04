import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api, formatApiError } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { Sparkles } from "lucide-react";

const SIDE_IMG = "https://images.pexels.com/photos/27141316/pexels-photo-27141316.jpeg?auto=compress&cs=tinysrgb&w=1200";

export default function Login() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const { setUser } = useAuth();
  const navigate = useNavigate();

  const submit = async (e) => {
    e.preventDefault();
    setError(""); setLoading(true);
    try {
      const { data } = await api.post("/auth/login", { email, password });
      setUser(data);
      navigate(sessionStorage.getItem("sg_pending_brief") ? "/generate" : "/dashboard");
    } catch (e) {
      setError(formatApiError(e.response?.data?.detail) || e.message);
    } finally { setLoading(false); }
  };

  const googleLogin = () => {
    // REMINDER: DO NOT HARDCODE THE URL, OR ADD ANY FALLBACKS OR REDIRECT URLS, THIS BREAKS THE AUTH
    const redirectUrl = window.location.origin + "/dashboard";
    window.location.href = `https://auth.emergentagent.com/?redirect=${encodeURIComponent(redirectUrl)}`;
  };

  return (
    <div className="min-h-screen bg-base text-white grid lg:grid-cols-2">
      <div className="flex items-center justify-center p-6">
        <div className="w-full max-w-sm">
          <Link to="/" className="inline-block mb-8">
            <img src="/sitegenie_logo_full.png" alt="SiteGenie — Your Website Wish, Granted" className="h-32 object-contain" data-testid="login-logo-lockup" />
          </Link>
          <h1 className="font-display text-3xl font-bold">Welcome back</h1>
          <p className="text-white/50 mt-2 text-sm">Log in to generate and manage your websites.</p>

          {!!sessionStorage.getItem("sg_pending_brief") && (
            <div data-testid="login-brief-banner" className="mt-4 flex items-center gap-2 border border-brand/40 bg-brand/10 px-3 py-2.5 text-sm text-white/80">
              <Sparkles className="w-4 h-4 text-brand shrink-0" /> Your website brief is saved — log in and I'll drop you into the build.
            </div>
          )}

          <button onClick={googleLogin} data-testid="google-login-btn"
            className="mt-8 w-full flex items-center justify-center gap-3 border border-white/15 hover:border-white/40 py-3 transition-colors duration-300">
            <img src="https://www.gstatic.com/firebasejs/ui/2.0.0/images/auth/google.svg" alt="" className="w-5 h-5 bg-white rounded-full" />
            Continue with Google
          </button>

          <div className="flex items-center gap-4 my-6 text-xs text-white/30">
            <div className="flex-1 h-px bg-white/10" /> OR <div className="flex-1 h-px bg-white/10" />
          </div>

          <form onSubmit={submit} className="space-y-4">
            {error && <div data-testid="login-error" className="text-neon text-sm border border-neon/30 bg-neon/10 px-3 py-2">{error}</div>}
            <div>
              <label className="text-xs text-white/50 font-mono uppercase">Email</label>
              <input data-testid="login-email" type="email" required value={email} onChange={(e) => setEmail(e.target.value)}
                className="mt-1 w-full bg-surface1 border border-white/10 focus:border-brand px-4 py-3 outline-none transition-colors duration-300" placeholder="you@business.com" />
            </div>
            <div>
              <label className="text-xs text-white/50 font-mono uppercase">Password</label>
              <input data-testid="login-password" type="password" required value={password} onChange={(e) => setPassword(e.target.value)}
                className="mt-1 w-full bg-surface1 border border-white/10 focus:border-brand px-4 py-3 outline-none transition-colors duration-300" placeholder="••••••••" />
            </div>
            <button data-testid="login-submit" disabled={loading} className="w-full bg-brand hover:bg-brand-hover py-3 font-medium transition-colors duration-300 disabled:opacity-50">
              {loading ? "Logging in…" : "Log in"}
            </button>
          </form>
          <p className="mt-6 text-sm text-white/50">No account? <Link to="/register" className="text-brand hover:underline">Sign up free</Link></p>
        </div>
      </div>
      <div className="hidden lg:block relative">
        <img src={SIDE_IMG} alt="" className="absolute inset-0 w-full h-full object-cover opacity-40" />
        <div className="absolute inset-0 bg-gradient-to-tr from-base via-base/60 to-transparent" />
        <div className="relative h-full flex flex-col justify-end p-12">
          <div className="font-display text-4xl font-bold leading-tight">Your website,<br />written by AI.</div>
          <p className="text-white/50 mt-3 max-w-sm">Join businesses launching beautiful sites in seconds — no code required.</p>
        </div>
      </div>
    </div>
  );
}
