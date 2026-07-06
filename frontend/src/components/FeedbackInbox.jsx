import { useEffect, useState, useCallback } from "react";
import { api } from "@/lib/api";
import { toast } from "sonner";
import { X, Loader2, Trash2, Inbox, Lightbulb, Bug, Frown, Heart, MessageSquare,
  CheckCircle2, Eye, Archive, RotateCcw } from "lucide-react";

function ago(iso) {
  if (!iso) return "";
  const s = Math.max(0, Math.floor((Date.now() - new Date(iso).getTime()) / 1000));
  if (s < 60) return "just now";
  const m = Math.floor(s / 60); if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60); if (h < 24) return `${h}h ago`;
  return `${Math.floor(h / 24)}d ago`;
}

const KIND = {
  feature: { icon: Lightbulb, label: "Feature request", tint: "text-yellow-300", bg: "bg-yellow-400/10 border-yellow-400/30" },
  bug: { icon: Bug, label: "Bug", tint: "text-red-300", bg: "bg-red-400/10 border-red-400/30" },
  complaint: { icon: Frown, label: "Complaint", tint: "text-orange-300", bg: "bg-orange-400/10 border-orange-400/30" },
  praise: { icon: Heart, label: "Praise", tint: "text-pink-300", bg: "bg-pink-400/10 border-pink-400/30" },
  feedback: { icon: MessageSquare, label: "Feedback", tint: "text-sky-300", bg: "bg-sky-400/10 border-sky-400/30" },
};

const STATUS_TABS = [
  { key: null, label: "All" },
  { key: "new", label: "New" },
  { key: "reviewed", label: "Reviewed" },
  { key: "actioned", label: "Actioned" },
  { key: "dismissed", label: "Dismissed" },
];

const SENTIMENT_DOT = { positive: "bg-emerald-400", neutral: "bg-white/40", negative: "bg-red-400" };

export function FeedbackInbox({ onClose }) {
  const [data, setData] = useState(null);
  const [status, setStatus] = useState("new");
  const [kind, setKind] = useState(null);
  const [busy, setBusy] = useState(null);

  const load = useCallback(async () => {
    try {
      const params = {};
      if (status) params.status = status;
      if (kind) params.kind = kind;
      const { data } = await api.get("/support/feedback", { params });
      setData(data);
    } catch {
      setData({ feedback: [], total: 0, new_count: 0, by_status: {}, by_kind: {} });
    }
  }, [status, kind]);

  useEffect(() => { load(); }, [load]);

  const setItemStatus = async (id, newStatus) => {
    setBusy(id);
    try {
      await api.patch(`/support/feedback/${id}`, { status: newStatus });
      toast.success(`Marked ${newStatus}.`);
      await load();
    } catch (e) {
      toast.error(e.response?.data?.detail || "Couldn't update.");
    } finally { setBusy(null); }
  };

  const remove = async (id) => {
    if (!window.confirm("Delete this feedback permanently?")) return;
    setBusy(id);
    try {
      await api.delete(`/support/feedback/${id}`);
      toast.success("Deleted.");
      await load();
    } catch (e) {
      toast.error(e.response?.data?.detail || "Couldn't delete.");
    } finally { setBusy(null); }
  };

  const items = data?.feedback || [];

  return (
    <div className="border-b border-sky-400/20 bg-sky-400/5 px-6 py-4" data-testid="feedback-inbox">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Inbox className="w-4 h-4 text-sky-300" />
          <p className="text-sm font-semibold text-sky-100">Customer Feedback Inbox</p>
          {data && (
            <span className="text-[11px] font-mono text-white/40">
              {data.total} total{data.new_count ? ` · ${data.new_count} new` : ""}
            </span>
          )}
        </div>
        <button onClick={onClose} className="text-white/40 hover:text-white p-1"><X className="w-4 h-4" /></button>
      </div>

      {/* status tabs */}
      <div className="flex gap-2 mt-3 flex-wrap">
        {STATUS_TABS.map((t) => (
          <button key={t.label} data-testid={`fb-status-${t.key || "all"}`} onClick={() => setStatus(t.key)}
            className={`text-xs px-3 py-1.5 border transition-colors duration-200 ${
              status === t.key ? "border-sky-400 text-sky-200" : "border-white/10 text-white/50 hover:text-white"}`}>
            {t.label}{t.key && data?.by_status?.[t.key] ? ` (${data.by_status[t.key]})` : ""}
          </button>
        ))}
      </div>

      {/* kind filter */}
      <div className="flex gap-2 mt-2 flex-wrap">
        <button onClick={() => setKind(null)}
          className={`text-[11px] px-2.5 py-1 border transition-colors duration-200 ${
            !kind ? "border-white/30 text-white" : "border-white/10 text-white/40 hover:text-white"}`}>All types</button>
        {Object.entries(KIND).map(([k, meta]) => {
          const Icon = meta.icon;
          return (
            <button key={k} onClick={() => setKind(k === kind ? null : k)}
              className={`flex items-center gap-1.5 text-[11px] px-2.5 py-1 border transition-colors duration-200 ${
                kind === k ? `${meta.bg} ${meta.tint}` : "border-white/10 text-white/40 hover:text-white"}`}>
              <Icon className="w-3 h-3" /> {meta.label}{data?.by_kind?.[k] ? ` ${data.by_kind[k]}` : ""}
            </button>
          );
        })}
      </div>

      {/* list */}
      <div className="mt-4 space-y-2 max-h-[52vh] overflow-y-auto pr-1" data-testid="feedback-list">
        {data === null ? (
          <div className="flex items-center gap-2 text-white/40 text-sm font-mono py-6">
            <Loader2 className="w-4 h-4 animate-spin" /> Loading feedback…
          </div>
        ) : items.length === 0 ? (
          <div className="text-center text-white/40 text-sm py-10 border border-dashed border-white/10">
            {status === "new"
              ? "No new feedback — you're all caught up. 🎉"
              : "No feedback here yet. Halo routes customer feature requests, bugs, complaints and praise straight to this inbox."}
          </div>
        ) : (
          items.map((f) => {
            const meta = KIND[f.kind] || KIND.feedback;
            const Icon = meta.icon;
            return (
              <div key={f.feedback_id} data-testid={`feedback-item-${f.feedback_id}`}
                className={`border ${meta.bg} p-3.5`}>
                <div className="flex items-start gap-3">
                  <div className={`shrink-0 w-8 h-8 rounded-full flex items-center justify-center border ${meta.bg}`}>
                    <Icon className={`w-4 h-4 ${meta.tint}`} />
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className={`text-[10px] font-mono uppercase tracking-wider ${meta.tint}`}>{meta.label}</span>
                      <span className={`w-1.5 h-1.5 rounded-full ${SENTIMENT_DOT[f.sentiment] || "bg-white/40"}`}
                        title={`${f.sentiment} sentiment`} />
                      {f.status !== "new" && (
                        <span className="text-[10px] font-mono uppercase text-white/40 border border-white/10 px-1.5">{f.status}</span>
                      )}
                      <span className="text-[11px] text-white/30 ml-auto">{ago(f.created_at)}</span>
                    </div>
                    <p className="text-sm text-white/90 mt-1 font-medium leading-snug">{f.summary}</p>
                    <p className="text-xs text-white/50 mt-1.5 leading-relaxed">&ldquo;{f.message}&rdquo;</p>
                    {f.contact?.email && (
                      <p className="text-[11px] text-brand mt-1.5">Contact: {f.contact.email}</p>
                    )}
                    <div className="flex items-center gap-1.5 mt-2.5">
                      {f.status !== "reviewed" && (
                        <button data-testid={`fb-review-${f.feedback_id}`} disabled={busy === f.feedback_id}
                          onClick={() => setItemStatus(f.feedback_id, "reviewed")}
                          className="flex items-center gap-1 text-[11px] border border-white/15 hover:border-white/40 px-2 py-1 text-white/60 disabled:opacity-40">
                          <Eye className="w-3 h-3" /> Reviewed
                        </button>
                      )}
                      {f.status !== "actioned" && (
                        <button data-testid={`fb-action-${f.feedback_id}`} disabled={busy === f.feedback_id}
                          onClick={() => setItemStatus(f.feedback_id, "actioned")}
                          className="flex items-center gap-1 text-[11px] border border-emerald-400/30 hover:border-emerald-300 px-2 py-1 text-emerald-300 disabled:opacity-40">
                          <CheckCircle2 className="w-3 h-3" /> Actioned
                        </button>
                      )}
                      {f.status !== "dismissed" ? (
                        <button data-testid={`fb-dismiss-${f.feedback_id}`} disabled={busy === f.feedback_id}
                          onClick={() => setItemStatus(f.feedback_id, "dismissed")}
                          className="flex items-center gap-1 text-[11px] border border-white/15 hover:border-white/40 px-2 py-1 text-white/50 disabled:opacity-40">
                          <Archive className="w-3 h-3" /> Dismiss
                        </button>
                      ) : (
                        <button disabled={busy === f.feedback_id} onClick={() => setItemStatus(f.feedback_id, "new")}
                          className="flex items-center gap-1 text-[11px] border border-white/15 hover:border-white/40 px-2 py-1 text-white/50 disabled:opacity-40">
                          <RotateCcw className="w-3 h-3" /> Reopen
                        </button>
                      )}
                      <button data-testid={`fb-delete-${f.feedback_id}`} disabled={busy === f.feedback_id}
                        onClick={() => remove(f.feedback_id)}
                        className="flex items-center gap-1 text-[11px] text-white/30 hover:text-red-300 px-2 py-1 ml-auto disabled:opacity-40">
                        <Trash2 className="w-3 h-3" />
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
