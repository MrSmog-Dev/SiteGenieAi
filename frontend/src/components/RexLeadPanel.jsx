import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { toast } from "sonner";
import { Crosshair, Globe, Loader2, X, Trash2, Flame, Search, KeyRound, Star, Phone } from "lucide-react";

const STATUS_COLORS = { new: "text-white/60", contacted: "text-sky-300", won: "text-emerald-300", lost: "text-white/30" };

export const RexLeadPanel = ({ onClose }) => {
  const [leads, setLeads] = useState(null);
  const [configured, setConfigured] = useState(null);
  const [scanUrl, setScanUrl] = useState("");
  const [scanning, setScanning] = useState(false);
  const [scanResult, setScanResult] = useState(null);
  const [huntLocation, setHuntLocation] = useState("");
  const [huntCategory, setHuntCategory] = useState("");
  const [hunting, setHunting] = useState(false);
  const [huntResult, setHuntResult] = useState(null);

  const loadLeads = () => api.get("/leads").then(({ data }) => setLeads(data)).catch(() => setLeads([]));
  useEffect(() => {
    loadLeads();
    api.get("/leads/hunt/status").then(({ data }) => setConfigured(data.places_configured)).catch(() => setConfigured(false));
  }, []);

  const scan = async (urlOverride) => {
    const url = (urlOverride || scanUrl).trim();
    if (!url || scanning) return;
    setScanning(true);
    setScanResult(null);
    try {
      const { data } = await api.post("/leads/scan", { url });
      setScanResult(data);
      if (data.lead_added) { toast.success(`Rex scored it ${data.score}/100 — added to the lead board.`); loadLeads(); }
      else toast.info(`Rex scored it ${data.score}/100 — too strong to be a lead (needs ≤65).`);
    } catch (e) {
      toast.error(e.response?.data?.detail || "Rex couldn't scan that site.");
    } finally { setScanning(false); }
  };

  const hunt = async () => {
    if (!huntLocation.trim() || !huntCategory.trim() || hunting) return;
    setHunting(true);
    setHuntResult(null);
    try {
      const { data } = await api.post("/leads/hunt", { location: huntLocation, category: huntCategory });
      setHuntResult(data);
      toast.success(`Rex found ${data.new_leads} new no-website lead${data.new_leads === 1 ? "" : "s"}.`);
      loadLeads();
    } catch (e) {
      toast.error(e.response?.data?.detail || "Hunt failed.");
    } finally { setHunting(false); }
  };

  const setStatus = async (lead, status) => {
    try {
      await api.patch(`/leads/${lead.lead_id}`, { status });
      setLeads((ls) => ls.map((l) => (l.lead_id === lead.lead_id ? { ...l, status } : l)));
    } catch { toast.error("Couldn't update the lead."); }
  };

  const remove = async (lead) => {
    if (!window.confirm(`Remove "${lead.business_name}" from the lead board?`)) return;
    try {
      await api.delete(`/leads/${lead.lead_id}`);
      setLeads((ls) => ls.filter((l) => l.lead_id !== lead.lead_id));
    } catch { toast.error("Couldn't delete the lead."); }
  };

  return (
    <div className="border-b border-red-400/20 bg-red-400/5 max-h-[55vh] overflow-y-auto" data-testid="rex-panel">
      <div className="px-6 py-4">
        <div className="flex items-center justify-between">
          <p className="text-sm text-red-200/90 flex items-center gap-2">
            <Crosshair className="w-4 h-4" /> Rex's Lead Hunter — scan any business website (0–100, ≤65 = lead, ≤40 = HOT) or hunt businesses with 15+ reviews and no website.
          </p>
          <button onClick={onClose} className="text-white/40 hover:text-white p-1" data-testid="rex-panel-close"><X className="w-4 h-4" /></button>
        </div>

        <div className="grid md:grid-cols-2 gap-4 mt-4">
          {/* Scan */}
          <div className="border border-white/10 bg-surface1 p-4">
            <div className="text-xs font-mono uppercase tracking-wider text-white/40 flex items-center gap-2"><Globe className="w-3.5 h-3.5" /> Scan a website</div>
            <div className="flex gap-2 mt-3">
              <input data-testid="rex-scan-input" value={scanUrl} onChange={(e) => setScanUrl(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && scan()} placeholder="acme-plumbing.com" disabled={scanning}
                className="flex-1 min-w-0 bg-surface2 border border-white/10 focus:border-red-300 outline-none px-3 py-2.5 text-sm transition-colors duration-300" />
              <button data-testid="rex-scan-btn" onClick={() => scan()} disabled={scanning || !scanUrl.trim()}
                className="flex items-center gap-2 bg-red-500 hover:bg-red-400 px-4 py-2.5 text-sm font-semibold transition-colors duration-300 disabled:opacity-40">
                {scanning ? <Loader2 className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />} Scan
              </button>
            </div>
            {scanning && <p className="text-xs text-white/40 mt-2 font-mono">Rex is fetching and grading the site (~30s)…</p>}
            {scanResult && (
              <div className="mt-3 border border-white/10 bg-surface2 p-3" data-testid="rex-scan-result">
                <div className="flex items-center gap-3">
                  <span className={`font-mono text-2xl font-bold ${scanResult.score <= 40 ? "text-red-400" : scanResult.score <= 65 ? "text-amber-300" : "text-emerald-300"}`}>{scanResult.score}/100</span>
                  {scanResult.tier === "hot" && <span className="flex items-center gap-1 text-[10px] font-mono uppercase bg-red-500 px-2 py-0.5"><Flame className="w-3 h-3" /> Hot lead</span>}
                  {scanResult.tier === "warm" && <span className="text-[10px] font-mono uppercase bg-amber-400 text-black px-2 py-0.5">Warm lead</span>}
                  {!scanResult.tier && <span className="text-[10px] font-mono uppercase text-emerald-300 border border-emerald-400/30 px-2 py-0.5">Not a lead</span>}
                  <span className="text-xs text-white/50 truncate">{scanResult.business_name}</span>
                </div>
                {scanResult.issues?.length > 0 && (
                  <ul className="mt-2 space-y-1">{scanResult.issues.map((i, k) => <li key={k} className="text-xs text-white/60">• {i}</li>)}</ul>
                )}
                {scanResult.pitch && <p className="text-xs text-red-200/80 mt-2 italic">Rex's pitch: {scanResult.pitch}</p>}
              </div>
            )}
          </div>

          {/* Hunt */}
          <div className="border border-white/10 bg-surface1 p-4">
            <div className="text-xs font-mono uppercase tracking-wider text-white/40 flex items-center gap-2"><Crosshair className="w-3.5 h-3.5" /> Hunt businesses without websites</div>
            {configured === false ? (
              <div className="mt-3 border border-amber-400/30 bg-amber-400/10 p-3 flex items-start gap-2" data-testid="rex-hunt-locked">
                <KeyRound className="w-4 h-4 text-amber-300 shrink-0 mt-0.5" />
                <p className="text-xs text-amber-200/90">Hunting needs a Google Places API key. Create one free at console.cloud.google.com (enable "Places API (New)"), then send it to me in chat and I'll connect it. Scanning works right now without it.</p>
              </div>
            ) : (
              <>
                <div className="flex gap-2 mt-3">
                  <input data-testid="rex-hunt-location" value={huntLocation} onChange={(e) => setHuntLocation(e.target.value)}
                    placeholder="City, State" disabled={hunting}
                    className="flex-1 min-w-0 bg-surface2 border border-white/10 focus:border-red-300 outline-none px-3 py-2.5 text-sm transition-colors duration-300" />
                  <input data-testid="rex-hunt-category" value={huntCategory} onChange={(e) => setHuntCategory(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && hunt()} placeholder="plumbers, salons…" disabled={hunting}
                    className="flex-1 min-w-0 bg-surface2 border border-white/10 focus:border-red-300 outline-none px-3 py-2.5 text-sm transition-colors duration-300" />
                  <button data-testid="rex-hunt-btn" onClick={hunt} disabled={hunting || !huntLocation.trim() || !huntCategory.trim()}
                    className="flex items-center gap-2 bg-red-500 hover:bg-red-400 px-4 py-2.5 text-sm font-semibold transition-colors duration-300 disabled:opacity-40">
                    {hunting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Crosshair className="w-4 h-4" />} Hunt
                  </button>
                </div>
                {huntResult && (
                  <div className="mt-3 text-xs text-white/60" data-testid="rex-hunt-result">
                    Found {huntResult.found} businesses meeting criteria area · <span className="text-red-300">{huntResult.new_leads} new no-website leads</span>
                    {huntResult.skipped_existing > 0 && ` · ${huntResult.skipped_existing} already on the board`}
                    {huntResult.website_candidates?.length > 0 && (
                      <div className="mt-2 space-y-1.5">
                        <div className="text-white/40 font-mono uppercase text-[10px]">Have websites — scan them:</div>
                        {huntResult.website_candidates.slice(0, 6).map((c, i) => (
                          <div key={i} className="flex items-center justify-between gap-2">
                            <span className="truncate">{c.business_name} · {c.reviews_count} reviews</span>
                            <button onClick={() => scan(c.website)} disabled={scanning}
                              className="text-red-300 hover:text-red-200 underline shrink-0 disabled:opacity-40">Scan</button>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </>
            )}
          </div>
        </div>

        {/* Lead board */}
        <div className="mt-4">
          <div className="text-xs font-mono uppercase tracking-wider text-white/40">Lead board {leads ? `(${leads.length})` : ""}</div>
          {leads === null ? (
            <p className="text-xs text-white/30 font-mono mt-2">Loading…</p>
          ) : leads.length === 0 ? (
            <p className="text-xs text-white/30 mt-2" data-testid="rex-leads-empty">No leads yet — scan a weak website or hunt a market to fill the board.</p>
          ) : (
            <div className="mt-2 space-y-2" data-testid="rex-leads-list">
              {leads.map((l) => (
                <div key={l.lead_id} data-testid={`lead-${l.lead_id}`} className="flex items-center gap-3 border border-white/10 bg-surface1 px-3 py-2.5">
                  {l.source === "no_website" ? (
                    <span className="shrink-0 text-[10px] font-mono uppercase bg-red-500/20 text-red-300 border border-red-400/30 px-2 py-0.5">No website</span>
                  ) : (
                    <span className={`shrink-0 text-[10px] font-mono uppercase px-2 py-0.5 ${l.score <= 40 ? "bg-red-500 text-white" : "bg-amber-400 text-black"}`}>{l.score}/100</span>
                  )}
                  {l.tier === "hot" && <Flame className="w-3.5 h-3.5 text-red-400 shrink-0" />}
                  <div className="min-w-0 flex-1">
                    <div className="text-sm truncate">{l.business_name}{l.category ? <span className="text-white/30"> · {l.category}</span> : null}</div>
                    <div className="text-[11px] text-white/40 truncate flex items-center gap-2">
                      {l.reviews_count ? <span className="flex items-center gap-0.5"><Star className="w-3 h-3" /> {l.reviews_count} reviews{l.rating ? ` (${l.rating}★)` : ""}</span> : null}
                      {l.phone ? <span className="flex items-center gap-0.5"><Phone className="w-3 h-3" /> {l.phone}</span> : null}
                      {l.website ? <a href={l.website} target="_blank" rel="noopener noreferrer" className="underline hover:text-white/70 truncate">{l.website.replace(/^https?:\/\//, "")}</a> : null}
                    </div>
                  </div>
                  <select data-testid={`lead-status-${l.lead_id}`} value={l.status} onChange={(e) => setStatus(l, e.target.value)}
                    className={`bg-surface2 border border-white/10 text-xs px-2 py-1.5 outline-none ${STATUS_COLORS[l.status] || ""}`}>
                    <option value="new">New</option>
                    <option value="contacted">Contacted</option>
                    <option value="won">Won</option>
                    <option value="lost">Lost</option>
                  </select>
                  <button data-testid={`lead-delete-${l.lead_id}`} onClick={() => remove(l)}
                    className="p-1.5 text-white/30 hover:text-red-400 transition-colors duration-300"><Trash2 className="w-4 h-4" /></button>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
