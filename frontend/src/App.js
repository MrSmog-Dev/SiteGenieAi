import "@/App.css";
import { BrowserRouter, Routes, Route, useLocation } from "react-router-dom";
import { Toaster } from "sonner";
import { AuthProvider } from "@/context/AuthContext";
import ProtectedRoute from "@/components/ProtectedRoute";
import { GenieWaking } from "@/components/GenieWaking";
import Landing from "@/pages/Landing";
import Login from "@/pages/Login";
import Register from "@/pages/Register";
import AuthCallback from "@/pages/AuthCallback";
import Dashboard from "@/pages/Dashboard";
import Generator from "@/pages/Generator";
import MyTemplates from "@/pages/MyTemplates";
import TemplateView from "@/pages/TemplateView";
import Pricing from "@/pages/Pricing";
import Billing from "@/pages/Billing";
import PaymentReturn from "@/pages/PaymentReturn";
import PublicSite from "@/pages/PublicSite";
import DomainSite from "@/pages/DomainSite";
import Market from "@/pages/Market";
import MarketSuccess from "@/pages/MarketSuccess";
import AiTeam from "@/pages/AiTeam";
import PolicyPage from "@/pages/PolicyPage";
import HaloWidget from "@/components/HaloWidget";
import { useAuth } from "@/context/AuthContext";

const backendHost = (() => {
  try { return new URL(process.env.REACT_APP_BACKEND_URL).hostname; } catch (e) { return window.location.hostname; }
})();
// Hostnames that always serve the MAIN SiteGenie app (never a published customer site).
const APP_HOSTS = ["localhost", "sitegenie-ai.com", "www.sitegenie-ai.com", "sitegenie.dev", "www.sitegenie.dev"];
const currentHost = window.location.hostname;
// A "custom domain" (published customer site) is any host that is NOT our backend host, NOT a known
// app host, and NOT an Emergent platform host (preview/deploy URLs can differ from the backend host).
const isEmergentHost = /\.(emergentagent\.com|emergent\.host)$/.test(currentHost);
const isCustomDomain = currentHost !== backendHost && !APP_HOSTS.includes(currentHost) && !isEmergentHost;

function AppRouter() {
  const location = useLocation();
  if (location.hash?.includes("session_id=")) {
    return <AuthCallback />;
  }
  return (
    <Routes>
      <Route path="/" element={<Landing />} />
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />
      <Route path="/pricing" element={<Pricing />} />
      <Route path="/billing" element={<ProtectedRoute><Billing /></ProtectedRoute>} />
      <Route path="/payment-return" element={<PaymentReturn />} />
      <Route path="/market" element={<Market />} />
      <Route path="/market/success" element={<ProtectedRoute><MarketSuccess /></ProtectedRoute>} />
      <Route path="/team" element={<ProtectedRoute><AiTeam /></ProtectedRoute>} />
      <Route path="/faq" element={<PolicyPage kind="faq" />} />
      <Route path="/refund-policy" element={<PolicyPage kind="refund-policy" />} />
      <Route path="/terms" element={<PolicyPage kind="terms" />} />
      <Route path="/privacy" element={<PolicyPage kind="privacy" />} />
      <Route path="/s/:slug" element={<PublicSite />} />
      <Route path="/dashboard" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
      <Route path="/generate" element={<ProtectedRoute><Generator /></ProtectedRoute>} />
      <Route path="/templates" element={<ProtectedRoute><MyTemplates /></ProtectedRoute>} />
      <Route path="/templates/:id" element={<ProtectedRoute><TemplateView /></ProtectedRoute>} />
    </Routes>
  );
}

function SupportWidget() {
  const { user } = useAuth();
  const location = useLocation();
  // Show Halo to visitors and customers; hide for the owner/admin (they have the internal AI Team)
  // and on the internal team console / published customer sites.
  const isStaff = user && (user.role === "owner" || user.role === "admin");
  const hiddenRoutes = ["/team"];
  if (isStaff || hiddenRoutes.some((r) => location.pathname.startsWith(r))) return null;
  return <HaloWidget />;
}

function App() {
  if (isCustomDomain) return <DomainSite />;
  return (
    <div className="App font-body">
      <AuthProvider>
        <BrowserRouter>
          <GenieWaking />
          <AppRouter />
          <SupportWidget />
          <Toaster theme="dark" position="top-right" richColors />
        </BrowserRouter>
      </AuthProvider>
    </div>
  );
}

export default App;
