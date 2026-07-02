import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import DashboardLayout from "@/components/DashboardLayout";
import { api } from "@/lib/api";
import { toast } from "sonner";
import { ArrowLeft, Download, Copy, Monitor, Smartphone, Code } from "lucide-react";

export default function TemplateView() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [tpl, setTpl] = useState(null);
  const [view, setView] = useState("desktop");
  const [showCode, setShowCode] = useState(false);

  useEffect(() => {
    api.get(`/templates/${id}`).then(({ data }) => setTpl(data)).catch(() => { toast.error("Not found"); navigate("/templates"); });
  }, [id, navigate]);

  const download = () => {
    const blob = new Blob([tpl.html], { type: "text/html" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url; a.download = `${tpl.business_name.replace(/\s+/g, "-").toLowerCase()}.html`; a.click();
    URL.revokeObjectURL(url);
  };
  const copy = () => { navigator.clipboard.writeText(tpl.html); toast.success("HTML copied to clipboard"); };

  if (!tpl) return <DashboardLayout><div className="p-10 font-mono text-white/40">Loading…</div></DashboardLayout>;

  return (
    <DashboardLayout>
      <div className="flex flex-col h-screen">
        <div className="flex items-center justify-between p-4 border-b border-white/10 bg-surface1">
          <div className="flex items-center gap-3 min-w-0">
            <button onClick={() => navigate("/templates")} data-testid="back-btn" className="p-2 border border-white/15 hover:border-white/40 transition-colors duration-300"><ArrowLeft className="w-4 h-4" /></button>
            <div className="min-w-0">
              <h1 className="font-display font-bold truncate">{tpl.business_name}</h1>
              <p className="text-white/40 text-xs truncate">{tpl.industry}</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <div className="hidden sm:flex border border-white/10">
              <button onClick={() => setView("desktop")} className={`p-2 ${view === "desktop" ? "bg-brand" : "hover:bg-surface2"} transition-colors duration-300`}><Monitor className="w-4 h-4" /></button>
              <button onClick={() => setView("mobile")} className={`p-2 ${view === "mobile" ? "bg-brand" : "hover:bg-surface2"} transition-colors duration-300`}><Smartphone className="w-4 h-4" /></button>
            </div>
            <button data-testid="view-code-btn" onClick={() => setShowCode((s) => !s)} className={`flex items-center gap-2 text-sm px-3 py-2 border transition-colors duration-300 ${showCode ? "border-brand text-brand" : "border-white/15 hover:border-white/40"}`}><Code className="w-4 h-4" /> Code</button>
            <button data-testid="copy-btn" onClick={copy} className="flex items-center gap-2 text-sm border border-white/15 hover:border-white/40 px-3 py-2 transition-colors duration-300"><Copy className="w-4 h-4" /> Copy</button>
            <button data-testid="download-btn" onClick={download} className="flex items-center gap-2 text-sm bg-brand hover:bg-brand-hover px-3 py-2 transition-colors duration-300"><Download className="w-4 h-4" /> Download</button>
          </div>
        </div>
        <div className="flex-1 overflow-auto bg-surface2 p-4 flex justify-center">
          {showCode ? (
            <pre className="w-full max-w-4xl bg-base border border-white/10 p-4 overflow-auto text-xs font-mono text-white/70">{tpl.html}</pre>
          ) : (
            <div className={`bg-white h-full ${view === "mobile" ? "w-[390px]" : "w-full max-w-6xl"} border border-white/10 transition-all duration-300`}>
              <iframe data-testid="template-iframe" title="site" srcDoc={tpl.html} className="w-full h-full" />
            </div>
          )}
        </div>
      </div>
    </DashboardLayout>
  );
}
