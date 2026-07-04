import { useEffect, useState, useRef } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api, API } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { toast } from "sonner";
import {
  Store, Crown, Check, ExternalLink, Loader2, ShoppingCart, Trash2, Wand2,
  Pencil, Sparkles,
} from "lucide-react";

// A listing is a "flagship" if the owner tagged it Premium or priced it >= $400.
const isFlagship = (l) => (l?.tier === "Premium") || (Number(l?.price_usd) >= 400);

export default function Market() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [listings, setListings] = useState(null);
  const [owned, setOwned] = useState({});
  const [buying, setBuying] = useState(null);

  const isOwner = !!user && (user.role === "owner" || user.role === "admin");

  const load = () => api.get("/market").then(({ data }) => setListings(data)).catch(() => setListings([]));
  useEffect(() => { load(); }, []);
  useEffect(() => {
    if (user) api.get("/market/owned").then(({ data }) => setOwned(data)).catch(() => {});
  }, [user]);

  const buy = async (l) => {
    if (!user) {
      toast.info("Log in or create a free account to purchase templates.");
      navigate("/login");
      return;
    }
    setBuying(l.market_id);
    try {
      const { data } = await api.post(`/market/${l.market_id}/checkout`, { origin_url: window.location.origin });
      window.location.href = data.url;
    } catch (e) {
      if (e.response?.status === 409) toast.error("You already own this template.");
      else toast.error("Could not start checkout. Please try again.");
      setBuying(null);
    }
  };

  const delist = async (l) => {
    if (!window.confirm(`Remove "${l.title}" from the Market?`)) return;
    try {
      await api.delete(`/market/${l.market_id}`);
      toast.success("Listing removed.");
      load();
    } catch (e) { toast.error("Could not remove listing."); }
  };

  const overridePrice = async (l) => {
    const raw = window.prompt(`Set new price for "${l.title}" (USD). Current: $${l.price_usd}`, String(l.price_usd));
    if (raw == null) return;
    const price = parseFloat(String(raw).replace(/[^\d.]/g, ""));
    if (!Number.isFinite(price) || price <= 0) {
      toast.error("Enter a valid positive number.");
      return;
    }
    try {
      await api.put(`/market/${l.market_id}/price`, { price_usd: price });
      toast.success(`Price updated to $${price}.`);
      load();
    } catch (e) {
      toast.error(e.response?.data?.detail || "Could not update price.");
    }
  };

  const flagships = (listings || []).filter(isFlagship);
  const rest = (listings || []).filter((l) => !isFlagship(l));

  const cardProps = { isOwner, buying, onBuy: buy, onDelist: delist, onOverride: overridePrice };

  return (
    <div className="min-h-screen bg-base text-white">
      <header className="sticky top-0 z-30 bg-base/80 backdrop-blur-md border-b border-white/10">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-2.5" data-testid="market-logo">
            <img src="/sitegenie_logo_mark.png" alt="SiteGenie" className="w-9 h-9 object-contain" />
            <span className="font-display font-bold text-lg tracking-tight">SiteGenie</span>
          </Link>
          <nav className="hidden md:flex items-center gap-8 text-sm text-white/60">
            <Link to="/" className="hover:text-white transition-colors duration-300">Home</Link>
            <span className="text-amber-300">Template Market</span>
            <a href="/api/blog" data-testid="market-nav-blog" className="hover:text-white transition-colors duration-300">Blog</a>
            <Link to="/pricing" className="hover:text-white transition-colors duration-300">Pricing</Link>
          </nav>
          {user ? (
            <Link to="/dashboard" data-testid="market-dashboard-btn" className="text-sm bg-brand hover:bg-brand-hover px-5 py-2.5 transition-colors duration-300">Dashboard</Link>
          ) : (
            <div className="flex items-center gap-3">
              <Link to="/login" data-testid="market-login-btn" className="text-sm text-white/70 hover:text-white transition-colors duration-300">Log in</Link>
              <Link to="/register" data-testid="market-signup-btn" className="text-sm bg-brand hover:bg-brand-hover px-5 py-2.5 transition-colors duration-300">Get started</Link>
            </div>
          )}
        </div>
      </header>

      <section className="max-w-7xl mx-auto px-6 pt-16 pb-8">
        <div className="flex items-center gap-2 font-mono text-xs text-amber-300/80 uppercase tracking-widest">
          <Store className="w-4 h-4" /> Template Market
        </div>
        <h1 className="font-display text-4xl sm:text-5xl lg:text-6xl font-bold mt-3 max-w-3xl">
          Premium websites, ready to own.
        </h1>
        <p className="text-white/50 mt-4 max-w-2xl text-base md:text-lg">
          Crafted by our AI studio and priced by our AI pricing agent based on depth and craftsmanship.
          Buy once, own it forever — <span className="text-white">unlimited free AI edits</span>, instant
          ZIP export and one-click publishing included.
        </p>
      </section>

      {/* FLAGSHIP HERO BAND */}
      {listings && flagships.length > 0 && (
        <section className="relative overflow-hidden border-y border-amber-300/20 bg-gradient-to-b from-amber-950/30 via-amber-900/10 to-transparent">
          <div className="pointer-events-none absolute inset-0 opacity-30" style={{
            background: "radial-gradient(circle at 20% 30%, rgba(251,191,36,0.25), transparent 55%), radial-gradient(circle at 80% 60%, rgba(217,119,6,0.2), transparent 55%)",
          }} />
          <div className="relative max-w-7xl mx-auto px-6 py-12" data-testid="flagship-hero">
            <div className="flex flex-wrap items-end justify-between gap-4 mb-8">
              <div>
                <div className="flex items-center gap-2 font-mono text-xs text-amber-300 uppercase tracking-widest">
                  <Crown className="w-4 h-4" /> Flagship Collection
                </div>
                <h2 className="font-display text-3xl md:text-4xl font-bold mt-2">Our most crafted, most complete builds.</h2>
                <p className="text-white/60 mt-2 max-w-2xl text-sm md:text-base">
                  Deep multi-pass builds with gallery, sliders, animations, full contact forms, FAQ and premium copywriting. Anchor pieces you can ship as-is.
                </p>
              </div>
              <div className="flex items-center gap-2 text-xs font-mono text-amber-300/80">
                <Sparkles className="w-4 h-4" /> {flagships.length} flagship{flagships.length === 1 ? "" : "s"}
              </div>
            </div>
            <div className="grid md:grid-cols-2 xl:grid-cols-3 gap-5" data-testid="flagship-grid">
              {flagships.map((l) => (
                <FlagshipCard key={l.market_id} l={l} ownedTemplateId={owned[l.market_id]} {...cardProps} />
              ))}
            </div>
          </div>
        </section>
      )}

      {/* Regular grid */}
      <section className="max-w-7xl mx-auto px-6 py-16">
        {listings === null ? (
          <div className="font-mono text-white/40 text-sm" data-testid="market-loading">Loading the Market…</div>
        ) : listings.length === 0 ? (
          <div data-testid="market-empty" className="border border-dashed border-white/15 p-16 text-center text-white/40">
            New templates are being crafted — check back soon.
          </div>
        ) : rest.length === 0 ? null : (
          <>
            <div className="flex items-center gap-2 font-mono text-xs text-white/40 uppercase tracking-widest mb-6">
              <Store className="w-4 h-4" /> More templates
            </div>
            <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-5" data-testid="market-grid">
              {rest.map((l) => (
                <ListingCard key={l.market_id} l={l} ownedTemplateId={owned[l.market_id]} {...cardProps} />
              ))}
            </div>
          </>
        )}
      </section>
    </div>
  );
}

function FlagshipCard({ l, ownedTemplateId, isOwner, buying, onBuy, onDelist, onOverride }) {
  return (
    <div data-testid={`flagship-card-${l.market_id}`}
      className="relative border border-amber-300/30 hover:border-amber-300/60 bg-gradient-to-b from-surface1 to-black transition-colors duration-300 flex flex-col">
      <div className="relative">
        <MarketThumb marketId={l.market_id} tall />
        <div className="absolute top-2 left-2 flex items-center gap-2 z-10">
          <span className="flex items-center gap-1 text-[10px] font-mono uppercase tracking-wider bg-amber-400 text-black px-2 py-1">
            <Crown className="w-3 h-3" /> Flagship
          </span>
          {l.popular && (
            <span className="flex items-center gap-1 text-[10px] font-mono uppercase tracking-wider bg-black/70 backdrop-blur-sm text-amber-300 px-2 py-1">
              Most Popular
            </span>
          )}
        </div>
        <div className="absolute top-2 right-2 z-10">
          <span className="text-[10px] font-mono uppercase tracking-wider bg-black/70 backdrop-blur-sm text-white/70 px-2 py-1">{l.tier}</span>
        </div>
      </div>
      <div className="p-6 flex flex-col flex-1">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <h3 className="font-display font-semibold text-lg truncate">{l.title}</h3>
            <p className="text-white/40 text-xs mt-0.5 truncate">{l.category}</p>
          </div>
          <div className="text-right shrink-0">
            <div data-testid={`price-${l.market_id}`} className="font-mono text-3xl font-bold text-amber-300">${l.price_usd}</div>
            <div className="text-[10px] text-white/30 font-mono uppercase">one-time</div>
          </div>
        </div>
        <p className="text-white/60 text-sm mt-3 line-clamp-3">{l.summary}</p>
        <ul className="mt-4 space-y-1.5">
          {(l.highlights || []).slice(0, 4).map((h, i) => (
            <li key={i} className="flex items-start gap-2 text-xs text-white/70">
              <Check className="w-3.5 h-3.5 text-amber-300 shrink-0 mt-0.5" /> {h}
            </li>
          ))}
        </ul>
        <div className="flex items-center gap-3 text-[11px] text-white/40 font-mono mt-4">
          <span data-testid={`sold-${l.market_id}`}>{l.purchases || 0} sold</span>
          <span className="flex items-center gap-1"><Wand2 className="w-3 h-3 text-neon" /> Free AI edits after purchase</span>
        </div>
        <CardActions l={l} ownedTemplateId={ownedTemplateId} isOwner={isOwner} buying={buying}
          onBuy={onBuy} onDelist={onDelist} onOverride={onOverride} accent="amber" />
      </div>
    </div>
  );
}

function ListingCard({ l, ownedTemplateId, isOwner, buying, onBuy, onDelist, onOverride }) {
  return (
    <div data-testid={`market-card-${l.market_id}`} className="border border-white/10 hover:border-white/25 bg-surface1 transition-colors duration-300 flex flex-col">
      <div className="relative">
        <MarketThumb marketId={l.market_id} />
        <div className="absolute top-2 left-2 flex items-center gap-2 z-10">
          {l.popular && (
            <span data-testid={`popular-badge-${l.market_id}`} className="flex items-center gap-1 text-[10px] font-mono uppercase tracking-wider bg-amber-400 text-black px-2 py-1">
              <Crown className="w-3 h-3" /> Most Popular
            </span>
          )}
          <span className="text-[10px] font-mono uppercase tracking-wider bg-black/70 backdrop-blur-sm text-white/70 px-2 py-1">{l.tier}</span>
        </div>
      </div>
      <div className="p-5 flex flex-col flex-1">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <h3 className="font-display font-semibold truncate">{l.title}</h3>
            <p className="text-white/40 text-xs mt-0.5 truncate">{l.category}</p>
          </div>
          <div className="text-right shrink-0">
            <div data-testid={`price-${l.market_id}`} className="font-mono text-2xl font-bold text-amber-300">${l.price_usd}</div>
            <div className="text-[10px] text-white/30 font-mono uppercase">one-time</div>
          </div>
        </div>
        <p className="text-white/50 text-sm mt-3 line-clamp-2">{l.summary}</p>
        <ul className="mt-3 space-y-1.5">
          {(l.highlights || []).slice(0, 3).map((h, i) => (
            <li key={i} className="flex items-start gap-2 text-xs text-white/60">
              <Check className="w-3.5 h-3.5 text-brand shrink-0 mt-0.5" /> {h}
            </li>
          ))}
        </ul>
        <div className="flex items-center gap-3 text-[11px] text-white/30 font-mono mt-3">
          <span data-testid={`sold-${l.market_id}`}>{l.purchases || 0} sold</span>
          <span className="flex items-center gap-1 text-white/40"><Wand2 className="w-3 h-3 text-neon" /> Free AI edits after purchase</span>
        </div>
        <CardActions l={l} ownedTemplateId={ownedTemplateId} isOwner={isOwner} buying={buying}
          onBuy={onBuy} onDelist={onDelist} onOverride={onOverride} accent="brand" />
      </div>
    </div>
  );
}

function CardActions({ l, ownedTemplateId, isOwner, buying, onBuy, onDelist, onOverride, accent }) {
  const previewUrl = `${API}/market/${l.market_id}/preview?count=1`;
  const buyClass = accent === "amber"
    ? "bg-amber-400 hover:bg-amber-300 text-black"
    : "bg-brand hover:bg-brand-hover text-white";
  return (
    <div className="flex items-center gap-2 mt-auto pt-4">
      <a data-testid={`preview-${l.market_id}`} href={previewUrl} target="_blank" rel="noopener noreferrer"
        className="flex items-center justify-center gap-2 text-sm border border-white/15 hover:border-white/40 px-3 py-2.5 transition-colors duration-300">
        <ExternalLink className="w-4 h-4" /> Preview
      </a>
      {ownedTemplateId ? (
        <Link data-testid={`owned-open-${l.market_id}`} to={`/templates/${ownedTemplateId}`}
          className="flex-1 flex items-center justify-center gap-2 text-sm bg-surface2 border border-emerald-400/30 text-emerald-300 px-3 py-2.5 transition-colors duration-300">
          <Check className="w-4 h-4" /> Owned — Open
        </Link>
      ) : (
        <button data-testid={`buy-${l.market_id}`} onClick={() => onBuy(l)} disabled={buying === l.market_id}
          className={`flex-1 flex items-center justify-center gap-2 text-sm px-3 py-2.5 transition-colors duration-300 disabled:opacity-50 ${buyClass}`}>
          {buying === l.market_id ? <Loader2 className="w-4 h-4 animate-spin" /> : <ShoppingCart className="w-4 h-4" />} Buy — ${l.price_usd}
        </button>
      )}
      {isOwner && (
        <>
          <button data-testid={`override-${l.market_id}`} onClick={() => onOverride(l)} title="Owner: override price"
            className="p-2.5 border border-white/15 hover:border-amber-300 hover:text-amber-300 transition-colors duration-300">
            <Pencil className="w-4 h-4" />
          </button>
          <button data-testid={`delist-${l.market_id}`} onClick={() => onDelist(l)} title="Remove from Market"
            className="p-2.5 border border-white/15 hover:border-neon hover:text-neon transition-colors duration-300">
            <Trash2 className="w-4 h-4" />
          </button>
        </>
      )}
    </div>
  );
}

function MarketThumb({ marketId, tall }) {
  const [visible, setVisible] = useState(false);
  const ref = useRef(null);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const io = new IntersectionObserver(([e]) => {
      if (e.isIntersecting) { setVisible(true); io.disconnect(); }
    }, { rootMargin: "400px" });
    io.observe(el);
    return () => io.disconnect();
  }, []);
  return (
    <div ref={ref} data-testid={`market-thumb-${marketId}`}
      className={`${tall ? "h-64" : "h-52"} overflow-hidden relative bg-white border-b border-white/10`}>
      {visible && (
        <iframe title="preview" sandbox="allow-scripts" src={`${API}/market/${marketId}/preview`} scrolling="no"
          className="pointer-events-none border-0"
          style={{ width: "300%", height: tall ? "768px" : "624px", transform: "scale(0.3333)", transformOrigin: "top left" }} />
      )}
    </div>
  );
}
