import "@/App.css";
import { BrowserRouter, Routes, Route, useLocation } from "react-router-dom";
import { Toaster } from "sonner";
import { AuthProvider } from "@/context/AuthContext";
import ProtectedRoute from "@/components/ProtectedRoute";
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

const backendHost = (() => {
  try { return new URL(process.env.REACT_APP_BACKEND_URL).hostname; } catch (e) { return window.location.hostname; }
})();
const isCustomDomain = window.location.hostname !== backendHost && window.location.hostname !== "localhost";

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
      <Route path="/s/:slug" element={<PublicSite />} />
      <Route path="/dashboard" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
      <Route path="/generate" element={<ProtectedRoute><Generator /></ProtectedRoute>} />
      <Route path="/templates" element={<ProtectedRoute><MyTemplates /></ProtectedRoute>} />
      <Route path="/templates/:id" element={<ProtectedRoute><TemplateView /></ProtectedRoute>} />
    </Routes>
  );
}

function App() {
  if (isCustomDomain) return <DomainSite />;
  return (
    <div className="App font-body">
      <AuthProvider>
        <BrowserRouter>
          <AppRouter />
          <Toaster theme="dark" position="top-right" richColors />
        </BrowserRouter>
      </AuthProvider>
    </div>
  );
}

export default App;
