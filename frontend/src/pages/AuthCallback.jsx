import { useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";

export default function AuthCallback() {
  const navigate = useNavigate();
  const { setUser } = useAuth();
  const processed = useRef(false);

  useEffect(() => {
    if (processed.current) return;
    processed.current = true;
    const hash = window.location.hash || "";
    const match = hash.match(/session_id=([^&]+)/);
    const sessionId = match ? decodeURIComponent(match[1]) : null;
    (async () => {
      if (!sessionId) { navigate("/login"); return; }
      try {
        const { data } = await api.post("/auth/google-session", { session_id: sessionId });
        setUser(data);
        window.history.replaceState(null, "", "/dashboard");
        navigate("/dashboard", { state: { user: data } });
      } catch (e) {
        navigate("/login");
      }
    })();
  }, [navigate, setUser]);

  return (
    <div className="min-h-screen bg-base flex items-center justify-center">
      <div className="font-mono text-sm text-white/60">Signing you in…</div>
    </div>
  );
}
