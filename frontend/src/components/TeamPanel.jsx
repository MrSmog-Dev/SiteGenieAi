import { useEffect, useState, useCallback } from "react";
import { api, formatApiError } from "@/lib/api";
import { toast } from "sonner";
import { Users, Loader2, Plus, Trash2, Mail, Crown, Check, X, LogOut } from "lucide-react";

/** Team multi-seat management on the Billing page. Shows for team owners & members, plus
 *  any user who has a pending invite (so they can accept). */
export function TeamPanel({ onChange }) {
  const [state, setState] = useState(null);
  const [invites, setInvites] = useState([]);
  const [email, setEmail] = useState("");
  const [busy, setBusy] = useState("");

  const load = useCallback(async () => {
    try {
      const [{ data: st }, { data: inv }] = await Promise.all([
        api.get("/team-account"),
        api.get("/team-account/invites"),
      ]);
      setState(st);
      setInvites(inv.invites || []);
    } catch { setState({ is_team: false }); }
  }, []);

  useEffect(() => { load(); }, [load]);

  const invite = async () => {
    if (!email.trim()) return;
    setBusy("invite");
    try {
      await api.post("/team-account/invite", { email: email.trim() });
      setEmail(""); toast.success("Invite sent.");
      await load();
    } catch (e) { toast.error(formatApiError(e.response?.data?.detail)); }
    finally { setBusy(""); }
  };

  const revoke = async (id) => {
    setBusy(id);
    try { await api.delete(`/team-account/invite/${id}`); await load(); }
    catch { toast.error("Couldn't revoke."); } finally { setBusy(""); }
  };

  const removeMember = async (id) => {
    if (!window.confirm("Remove this member from the team?")) return;
    setBusy(id);
    try { await api.delete(`/team-account/member/${id}`); toast.success("Member removed."); await load(); }
    catch (e) { toast.error(formatApiError(e.response?.data?.detail)); } finally { setBusy(""); }
  };

  const accept = async (id) => {
    setBusy(id);
    try { await api.post(`/team-account/accept/${id}`); toast.success("You've joined the team!"); await load(); onChange?.(); }
    catch (e) { toast.error(formatApiError(e.response?.data?.detail)); } finally { setBusy(""); }
  };

  const leave = async () => {
    if (!window.confirm("Leave this team? You'll go back to your own Free tier.")) return;
    setBusy("leave");
    try { await api.post("/team-account/leave"); toast.success("You left the team."); await load(); onChange?.(); }
    catch (e) { toast.error(formatApiError(e.response?.data?.detail)); } finally { setBusy(""); }
  };

  if (state === null) return null;

  // Not on a team, but has pending invite(s) → show accept card.
  if (!state.is_team && invites.length > 0) {
    return (
      <div className="mt-6 border border-brand/40 bg-brand/5 p-5" data-testid="team-invites">
        <div className="flex items-center gap-2 mb-3"><Mail className="w-4 h-4 text-brand" /><h2 className="font-display font-bold">Team invitations</h2></div>
        {invites.map((iv) => (
          <div key={iv.invite_id} className="flex items-center justify-between border border-white/10 bg-surface1 px-4 py-3 mt-2">
            <span className="text-sm">You've been invited to join a SiteGenie Team.</span>
            <button data-testid={`accept-invite-${iv.invite_id}`} onClick={() => accept(iv.invite_id)} disabled={busy === iv.invite_id}
              className="flex items-center gap-1.5 bg-brand hover:bg-brand-hover px-3 py-1.5 text-sm transition-colors duration-200 disabled:opacity-50">
              {busy === iv.invite_id ? <Loader2 className="w-4 h-4 animate-spin" /> : <Check className="w-4 h-4" />} Accept &amp; join
            </button>
          </div>
        ))}
      </div>
    );
  }

  if (!state.is_team) return null;

  const isOwner = state.role === "owner";

  return (
    <div className="mt-6 border border-white/10 bg-surface1 p-6" data-testid="team-panel">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Users className="w-4 h-4 text-brand" />
          <h2 className="font-display font-bold">Team</h2>
          <span className="text-[11px] font-mono text-white/40" data-testid="team-seats">{state.seats_used}/{state.seats_total} seats</span>
        </div>
        {!isOwner && (
          <button data-testid="leave-team-btn" onClick={leave} disabled={busy === "leave"}
            className="flex items-center gap-1.5 text-xs border border-white/15 hover:border-neon hover:text-neon px-2.5 py-1.5 transition-colors duration-200">
            <LogOut className="w-3.5 h-3.5" /> Leave team
          </button>
        )}
      </div>

      {/* Members */}
      <div className="space-y-2">
        <div className="flex items-center justify-between border border-white/8 bg-surface2/40 px-4 py-2.5">
          <div className="flex items-center gap-2 min-w-0">
            <Crown className="w-4 h-4 text-amber-300 shrink-0" />
            <span className="text-sm font-medium truncate">{state.owner?.name || state.owner?.email}</span>
            <span className="text-[10px] font-mono uppercase text-amber-300/70">owner</span>
          </div>
          <span className="text-xs text-white/40 truncate hidden sm:block">{state.owner?.email}</span>
        </div>
        {state.members.map((m) => (
          <div key={m.user_id} data-testid={`team-member-${m.user_id}`} className="flex items-center justify-between border border-white/8 bg-surface2/40 px-4 py-2.5">
            <div className="flex items-center gap-2 min-w-0">
              <Users className="w-4 h-4 text-white/40 shrink-0" />
              <span className="text-sm truncate">{m.name || m.email}</span>
              <span className="text-[10px] font-mono uppercase text-white/30">member</span>
            </div>
            {isOwner && (
              <button data-testid={`remove-member-${m.user_id}`} onClick={() => removeMember(m.user_id)} disabled={busy === m.user_id}
                className="text-white/30 hover:text-red-300 transition-colors duration-200"><Trash2 className="w-4 h-4" /></button>
            )}
          </div>
        ))}
        {state.pending_invites.map((iv) => (
          <div key={iv.invite_id} className="flex items-center justify-between border border-dashed border-white/12 px-4 py-2.5">
            <div className="flex items-center gap-2 min-w-0">
              <Mail className="w-4 h-4 text-white/30 shrink-0" />
              <span className="text-sm text-white/60 truncate">{iv.email}</span>
              <span className="text-[10px] font-mono uppercase text-white/30">pending</span>
            </div>
            {isOwner && (
              <button data-testid={`revoke-invite-${iv.invite_id}`} onClick={() => revoke(iv.invite_id)} disabled={busy === iv.invite_id}
                className="text-white/30 hover:text-red-300 transition-colors duration-200"><X className="w-4 h-4" /></button>
            )}
          </div>
        ))}
      </div>

      {/* Invite form (owner only) */}
      {isOwner && (
        <div className="mt-4">
          {state.seats_available > 0 ? (
            <div className="flex gap-2">
              <input data-testid="team-invite-email" value={email} onChange={(e) => setEmail(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && invite()} type="email"
                placeholder="teammate@email.com"
                className="flex-1 bg-surface2 border border-white/10 focus:border-brand outline-none px-3 py-2 text-sm transition-colors duration-200" />
              <button data-testid="team-invite-btn" onClick={invite} disabled={busy === "invite" || !email.trim()}
                className="flex items-center gap-1.5 bg-brand hover:bg-brand-hover px-4 py-2 text-sm transition-colors duration-200 disabled:opacity-50">
                {busy === "invite" ? <Loader2 className="w-4 h-4 animate-spin" /> : <Plus className="w-4 h-4" />} Invite
              </button>
            </div>
          ) : (
            <p className="text-xs text-white/40">All {state.seats_total} seats are used. Remove a member to invite someone new.</p>
          )}
          <p className="text-[11px] text-white/30 mt-2">Members share your Team credit pool. Only you are billed.</p>
        </div>
      )}
      {!isOwner && <p className="text-[11px] text-white/30 mt-3">You share this team's credit pool. Your builds draw from it.</p>}
    </div>
  );
}
