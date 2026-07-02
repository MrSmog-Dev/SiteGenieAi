import { Link, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { LayoutDashboard, Sparkles, LayoutTemplate, CreditCard, LogOut, Zap } from "lucide-react";

const nav = [
  { to: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { to: "/generate", label: "Generate", icon: Sparkles },
  { to: "/templates", label: "My Templates", icon: LayoutTemplate },
  { to: "/billing", label: "Billing", icon: CreditCard },
];

export default function DashboardLayout({ children }) {
  const { user, logout } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-base text-white flex">
      {/* Sidebar */}
      <aside className="w-64 shrink-0 hidden md:flex flex-col hairline border-l-0 border-t-0 border-b-0 bg-surface1 sticky top-0 h-screen">
        <div className="p-6 border-b border-white/10">
          <Link to="/dashboard" className="flex items-center gap-2" data-testid="sidebar-logo">
            <div className="w-8 h-8 bg-brand flex items-center justify-center">
              <Zap className="w-5 h-5 text-white" />
            </div>
            <span className="font-display font-bold text-lg tracking-tight">SiteGenie</span>
          </Link>
        </div>
        <nav className="flex-1 p-3 space-y-1">
          {nav.map((item) => {
            const active = location.pathname === item.to;
            const Icon = item.icon;
            return (
              <Link
                key={item.to}
                to={item.to}
                data-testid={`nav-${item.label.toLowerCase().replace(/[^a-z]+/g, "-")}`}
                className={`flex items-center gap-3 px-4 py-3 text-sm transition-all duration-300 ${
                  active ? "bg-brand text-white" : "text-white/60 hover:text-white hover:bg-surface2"
                }`}
              >
                <Icon className="w-4 h-4" /> {item.label}
              </Link>
            );
          })}
        </nav>
        <div className="p-3 border-t border-white/10">
          <div className="px-4 py-3 mb-2 bg-surface2">
            <div className="text-xs text-white/40 uppercase tracking-wider">Credits</div>
            <div className="font-mono text-2xl font-bold text-brand" data-testid="sidebar-credits">{user?.unlimited ? "∞" : (user?.credits ?? 0)}</div>
          </div>
          <button
            onClick={logout}
            data-testid="logout-btn"
            className="w-full flex items-center gap-3 px-4 py-3 text-sm text-white/60 hover:text-neon hover:bg-surface2 transition-all duration-300"
          >
            <LogOut className="w-4 h-4" /> Log out
          </button>
        </div>
      </aside>

      {/* Main */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* mobile top bar */}
        <header className="md:hidden flex items-center justify-between p-4 border-b border-white/10 bg-surface1 sticky top-0 z-20">
          <Link to="/dashboard" className="flex items-center gap-2">
            <div className="w-7 h-7 bg-brand flex items-center justify-center"><Zap className="w-4 h-4" /></div>
            <span className="font-display font-bold">SiteGenie</span>
          </Link>
          <div className="flex items-center gap-3">
            <span className="font-mono text-brand font-bold" data-testid="mobile-credits">{user?.unlimited ? "∞" : (user?.credits ?? 0)} cr</span>
            <button onClick={() => navigate("/generate")} className="text-xs bg-brand px-3 py-1.5">New</button>
          </div>
        </header>
        <main className="flex-1 min-w-0">{children}</main>
      </div>
    </div>
  );
}
