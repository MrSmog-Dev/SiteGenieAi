import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import DashboardLayout from "@/components/DashboardLayout";
import { api } from "@/lib/api";
import { toast } from "sonner";
import { LayoutTemplate, Trash2, Plus, Eye } from "lucide-react";

export default function MyTemplates() {
  const [templates, setTemplates] = useState([]);
  const [loading, setLoading] = useState(true);

  const load = () => api.get("/templates").then(({ data }) => setTemplates(data)).catch(() => {}).finally(() => setLoading(false));
  useEffect(() => { load(); }, []);

  const del = async (id) => {
    try {
      await api.delete(`/templates/${id}`);
      setTemplates((t) => t.filter((x) => x.template_id !== id));
      toast.success("Website deleted.");
    } catch (e) { toast.error("Failed to delete."); }
  };

  return (
    <DashboardLayout>
      <div className="p-6 md:p-10 max-w-6xl">
        <div className="flex items-center justify-between mb-8">
          <div>
            <div className="font-mono text-xs text-white/40 uppercase tracking-wider">Library</div>
            <h1 className="font-display text-3xl md:text-4xl font-bold mt-1">My Websites</h1>
          </div>
          <Link to="/generate" data-testid="templates-new-btn" className="flex items-center gap-2 bg-brand hover:bg-brand-hover px-5 py-3 transition-colors duration-300">
            <Plus className="w-4 h-4" /> New
          </Link>
        </div>

        {loading ? (
          <div className="font-mono text-white/40 text-sm">Loading…</div>
        ) : templates.length === 0 ? (
          <div className="border border-dashed border-white/15 p-16 text-center text-white/40">
            You haven't generated any websites yet.<br />
            <Link to="/generate" className="text-brand hover:underline">Generate your first one →</Link>
          </div>
        ) : (
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {templates.map((t) => (
              <div key={t.template_id} data-testid={`template-card-${t.template_id}`} className="border border-white/10 hover:border-white/30 bg-surface1 transition-colors duration-300 group">
                <div className="h-28 flex items-center justify-center relative" style={{ background: t.primary_color || "#0055FF" }}>
                  <LayoutTemplate className="w-8 h-8 text-white/80" />
                  {t.published && (
                    <span data-testid={`live-badge-${t.template_id}`} className="absolute top-2 right-2 flex items-center gap-1 text-[10px] font-mono uppercase tracking-wider bg-black/50 backdrop-blur-sm text-neon px-2 py-1">
                      <span className="w-1.5 h-1.5 rounded-full bg-neon animate-pulse" /> Live
                    </span>
                  )}
                </div>
                <div className="p-5">
                  <h3 className="font-display font-semibold truncate">{t.business_name}</h3>
                  <p className="text-white/40 text-xs mt-1">{t.industry}</p>
                  <p className="text-white/30 text-xs mt-1 font-mono">{new Date(t.created_at).toLocaleDateString()}</p>
                  <div className="flex items-center gap-2 mt-4">
                    <Link to={`/templates/${t.template_id}`} className="flex-1 flex items-center justify-center gap-2 text-sm border border-white/15 hover:border-white/40 py-2 transition-colors duration-300">
                      <Eye className="w-4 h-4" /> View
                    </Link>
                    <button data-testid={`delete-${t.template_id}`} onClick={() => del(t.template_id)} className="p-2 border border-white/15 hover:border-neon hover:text-neon transition-colors duration-300">
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </DashboardLayout>
  );
}
