import { useEffect, useState, useRef } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api, API } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { toast } from "sonner";
import { Zap, Store, Crown, Check, ExternalLink, Loader2, ShoppingCart, Trash2, Wand2 } from "lucide-react";

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

  return (
    <div className="min-h-screen bg-base text-white">
      <header className="sticky top-0 z-30 bg-base/80 backdrop-blur-md border-b border-white/10">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-2" data-testid="market-logo">
            <div className="w-8 h-8 bg-brand flex items-center justify-center"><Zap className="w-5 h-5 text-white" /></div>
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

      <section className="max-w-7xl mx-auto px-6 pt-16 pb-10">
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

      <section className="max-w-7xl mx-auto px-6 pb-24">
        {listings === null ? (
          <div className="font-mono text-white/40 text-sm" data-testid="market-loading">Loading the Market…</div>
        ) : listings.length === 0 ? (
          <div data-testid="market-empty" className="border border-dashed border-white/15 p-16 text-center text-white/40">
            New templates are being crafted — check back soon.
          </div>
        ) : (
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-5" data-testid="market-grid">
            {listings.map((l) => (
              <ListingCard key={l.market_id} l={l} ownedTemplateId={owned[l.market_id]}
                isOwner={isOwner} buying={buying} onBuy={buy} onDelist={delist} />
            ))}
          </div>
        )}
      </section>
    </div>
  );
}

function ListingCard({ l, ownedTemplateId, isOwner, buying, onBuy, onDelist }) {
  const previewUrl = `${API}/market/${l.market_id}/preview?count=1`;
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
              className="flex-1 flex items-center justify-center gap-2 text-sm bg-brand hover:bg-brand-hover px-3 py-2.5 transition-colors duration-300 disabled:opacity-50">
              {buying === l.market_id ? <Loader2 className="w-4 h-4 animate-spin" /> : <ShoppingCart className="w-4 h-4" />} Buy — ${l.price_usd}
            </button>
          )}
          {isOwner && (
            <button data-testid={`delist-${l.market_id}`} onClick={() => onDelist(l)} title="Remove from Market"
              className="p-2.5 border border-white/15 hover:border-neon hover:text-neon transition-colors duration-300">
              <Trash2 className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

function MarketThumb({ marketId }) {
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
    <div ref={ref} data-testid={`market-thumb-${marketId}`} className="h-52 overflow-hidden relative bg-white border-b border-white/10">
      {visible && (
        <iframe title="preview" sandbox="allow-scripts" src={`${API}/market/${marketId}/preview`} scrolling="no"
          className="pointer-events-none border-0"
          style={{ width: "300%", height: "624px", transform: "scale(0.3333)", transformOrigin: "top left" }} />
      )}
    </div>
  );
}
