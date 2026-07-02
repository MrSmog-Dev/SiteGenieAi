import { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";

export default function ProtectedRoute({ children }) {
  const { user, loading } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    if (!loading && user === false) navigate("/login");
  }, [loading, user, navigate]);

  if (loading || user === null) {
    return (
      <div className="min-h-screen bg-base flex items-center justify-center">
        <div className="font-mono text-sm text-white/50 animate-pulse">Loading…</div>
      </div>
    );
  }
  if (!user) return null;
  return children;
}
