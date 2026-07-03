import { useState, useEffect, useRef } from "react";
import { Link, useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { useAuth } from "@/context/AuthContext";
import { Zap, Sparkles, Gauge, Palette, Rocket, ArrowUp, Check, Coffee, Scissors, Dumbbell, UtensilsCrossed, Scale, Flower2 } from "lucide-react";

const plans = [
  { id: "monthly", name: "Monthly", price: 20, per: "/mo", credits: 50, unlimited: false, highlight: false },
  { id: "quarterly", name: "3-Month", price: 49, per: "/qtr", credits: 120, unlimited: false, highlight: true },
  { id: "annual", name: "Annual", price: 149, per: "/yr", credits: 300, unlimited: true, highlight: false },
];

const features = [
  { icon: Sparkles, title: "AI-crafted sites", desc: "Describe your business. Our AI writes copy and designs a full responsive site in seconds." },
  { icon: Palette, title: "On-brand styling", desc: "Pick your brand color and style — every template is tailored to your industry." },
  { icon: Gauge, title: "Credits as currency", desc: "Credits are spent as you build — bigger jobs cost more. Top up anytime with a credit pack." },
  { icon: Rocket, title: "Publish & ship", desc: "Publish to a live link, share it anywhere, or download production-ready HTML." },
];

const EXAMPLES = [
  "A cozy neighborhood coffee shop with specialty espresso and fresh pastries…",
  "A modern barber shop offering classic cuts, fades, and hot towel shaves…",
  "A boutique fitness studio with small-group HIIT classes and personal training…",
  "A family-owned Italian restaurant serving handmade pasta and wood-fired pizza…",
  "A florist studio creating seasonal bouquets and wedding florals…",
];

const CHIPS = [
  { id: "coffee", icon: Coffee, label: "Coffee shop", prompt: "A cozy neighborhood coffee shop with specialty espresso, fresh pastries, and a warm space to work or catch up with friends." },
  { id: "barber", icon: Scissors, label: "Barber shop", prompt: "A modern barber shop offering classic cuts, beard trims, and hot towel shaves — walk-ins welcome, appointments preferred." },
  { id: "fitness", icon: Dumbbell, label: "Fitness studio", prompt: "A boutique fitness studio with small-group HIIT classes, personal training, and flexible monthly memberships." },
  { id: "restaurant", icon: UtensilsCrossed, label: "Restaurant", prompt: "A family-owned Italian restaurant serving handmade pasta, wood-fired pizza, and a curated local wine list." },
  { id: "law", icon: Scale, label: "Law firm", prompt: "A boutique law firm specializing in small business and estate law, with free 30-minute consultations." },
  { id: "florist", icon: Flower2, label: "Florist", prompt: "A florist studio creating seasonal bouquets, wedding florals, and same-day local delivery." },
];

function useTypewriter(active) {
  const [text, setText] = useState("");
  useEffect(() => {
    if (!active) return;
    let i = 0, char = 0, del = false, t;
    const tick = () => {
      const cur = EXAMPLES[i];
      if (!del) {
        char++;
        setText(cur.slice(0, char));
        if (char >= cur.length) { del = true; t = setTimeout(tick, 2200); return; }
        t = setTimeout(tick, 32);
      } else {
        char -= 3;
        if (char <= 0) { char = 0; del = false; i = (i + 1) % EXAMPLES.length; }
        setText(cur.slice(0, char));
        t = setTimeout(tick, 10);
      }
    };
    t = setTimeout(tick, 500);
    return () => clearTimeout(t);
  }, [active]);
  return text;
}

export default function Landing() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [prompt, setPrompt] = useState("");
  const textareaRef = useRef(null);
  const placeholder = useTypewriter(!prompt);

  const start = (text) => {
    const idea = (text ?? prompt).trim();
    if (!idea) { textareaRef.current?.focus(); return; }
    sessionStorage.setItem("sg_pending_prompt", idea);
    navigate(user ? "/generate" : "/register");
  };

  const onKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); start(); }
  };

  const pickChip = (c) => {
    setPrompt(c.prompt);
    textareaRef.current?.focus();
  };

  return (
    <div className="min-h-screen bg-base text-white font-body overflow-x-hidden">
      {/* Nav */}
      <header className="fixed top-0 inset-x-0 z-40 bg-black/60 backdrop-blur-xl border-b border-white/10">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-2" data-testid="landing-logo">
            <div className="w-8 h-8 bg-brand flex items-center justify-center"><Zap className="w-5 h-5" /></div>
            <span className="font-display font-bold text-lg tracking-tight">SiteGenie</span>
          </Link>
          <nav className="hidden md:flex items-center gap-8 text-sm text-white/60">
            <a href="#features" className="hover:text-white transition-colors duration-300">Features</a>
            <a href="#pricing" className="hover:text-white transition-colors duration-300">Pricing</a>
            <a href="#how" className="hover:text-white transition-colors duration-300">How it works</a>
          </nav>
          <div className="flex items-center gap-3">
            {user ? (
              <Link to="/dashboard" data-testid="nav-dashboard-btn" className="text-sm bg-brand hover:bg-brand-hover px-5 py-2.5 transition-colors duration-300">Dashboard</Link>
            ) : (
              <>
                <Link to="/login" data-testid="nav-login-btn" className="text-sm text-white/70 hover:text-white transition-colors duration-300">Log in</Link>
                <Link to="/register" data-testid="nav-signup-btn" className="text-sm bg-brand hover:bg-brand-hover px-5 py-2.5 transition-colors duration-300">Get started</Link>
              </>
            )}
          </div>
        </div>
      </header>

      {/* Chat-first hero */}
      <section className="relative min-h-screen flex flex-col items-center justify-center px-6 pt-16">
        <div className="pointer-events-none absolute inset-0 overflow-hidden">
          <div className="absolute left-1/2 top-1/3 -translate-x-1/2 -translate-y-1/2 w-[900px] h-[500px] rounded-full opacity-25"
            style={{ background: "radial-gradient(ellipse at center, rgba(0,85,255,0.55) 0%, rgba(0,85,255,0.12) 45%, transparent 70%)" }} />
          <div className="absolute inset-0 opacity-[0.05]"
            style={{ backgroundImage: "linear-gradient(rgba(255,255,255,0.6) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.6) 1px, transparent 1px)", backgroundSize: "64px 64px" }} />
        </div>

        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.6 }}
          className="relative w-full max-w-3xl flex flex-col items-center text-center">
          <div className="flex items-center gap-2.5 mb-6" data-testid="hero-agent-badge">
            <div className="relative w-9 h-9 bg-brand flex items-center justify-center">
              <Zap className="w-5 h-5" />
              <span className="absolute -bottom-0.5 -right-0.5 w-2.5 h-2.5 rounded-full bg-emerald-400 border-2 border-base" />
            </div>
            <span className="font-mono text-sm text-white/60">SiteGenie AI · online</span>
          </div>

          <h1 className="font-display text-4xl sm:text-5xl lg:text-6xl font-bold tracking-tight leading-[1.05]">
            {user ? <>Welcome back{user.name ? `, ${user.name.split(" ")[0]}` : ""}.<br /><span className="text-brand">What are we building?</span></> : <>Tell me about your business.<br /><span className="text-brand">I'll build the website.</span></>}
          </h1>
          <p className="mt-5 text-white/50 max-w-lg text-base md:text-lg">
            Describe what you do — copy, design, and a full responsive site are generated in minutes. No code, no designer.
          </p>

          {/* Prompt box */}
          <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.6, delay: 0.15 }}
            className="mt-10 w-full">
            <div className="group relative rounded-2xl border border-white/15 bg-surface1/90 backdrop-blur-xl transition-all duration-300 focus-within:border-brand/70 focus-within:shadow-[0_0_60px_-12px_rgba(0,85,255,0.55)]"
              data-testid="hero-prompt-box">
              <textarea
                ref={textareaRef}
                data-testid="hero-prompt-input"
                rows={3}
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                onKeyDown={onKeyDown}
                placeholder={placeholder || "Describe your business…"}
                className="w-full resize-none bg-transparent px-5 pt-5 pb-2 text-left text-base text-white placeholder:text-white/30 outline-none"
              />
              <div className="flex items-center justify-between px-4 pb-3.5">
                <div className="flex items-center gap-2 text-xs font-mono text-white/35">
                  <Sparkles className="w-3.5 h-3.5 text-brand" />
                  <span className="hidden sm:inline">2-pass AI build · strategist + builder</span>
                  <span className="sm:hidden">2-pass AI build</span>
                </div>
                <button
                  data-testid="hero-prompt-submit"
                  onClick={() => start()}
                  aria-label="Start building"
                  className={`flex items-center justify-center w-10 h-10 rounded-xl transition-all duration-300 ${prompt.trim() ? "bg-brand hover:bg-brand-hover scale-100" : "bg-white/10 text-white/40 hover:bg-white/15"}`}>
                  <ArrowUp className="w-5 h-5" />
                </button>
              </div>
            </div>
            <div className="mt-3 text-xs font-mono text-white/30">Press Enter to start · 15 free credits on sign up</div>
          </motion.div>

          {/* Suggestion chips */}
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.6, delay: 0.3 }}
            className="mt-8 flex flex-wrap justify-center gap-2.5">
            {CHIPS.map((c) => {
              const Icon = c.icon;
              return (
                <button key={c.id} data-testid={`hero-chip-${c.id}`} onClick={() => pickChip(c)}
                  className="flex items-center gap-2 rounded-full border border-white/12 bg-surface1/70 px-4 py-2 text-sm text-white/60 hover:text-white hover:border-white/35 transition-colors duration-300">
                  <Icon className="w-4 h-4 text-brand" /> {c.label}
                </button>
              );
            })}
          </motion.div>
        </motion.div>

        <a href="#features" className="absolute bottom-8 text-white/25 hover:text-white/60 font-mono text-xs transition-colors duration-300">↓ scroll to explore</a>
      </section>

      {/* Features bento */}
      <section id="features" className="px-6 py-24 max-w-7xl mx-auto">
        <div className="grid grid-cols-1 md:grid-cols-12 gap-4">
          <div className="md:col-span-5 border border-white/10 p-10 bg-surface1">
            <h2 className="font-display text-3xl font-bold leading-tight">Everything you need to<br />get online, fast.</h2>
            <p className="mt-4 text-white/50">No templates to fiddle with. No blank canvas anxiety. Just answer a few questions and ship.</p>
          </div>
          {features.map((f, i) => {
            const Icon = f.icon;
            return (
              <motion.div key={f.title} initial={{ opacity: 0, y: 20 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} transition={{ delay: i * 0.08 }}
                className="md:col-span-3.5 border border-white/10 p-8 bg-surface1 hover:border-white/30 transition-colors duration-300"
                style={{ gridColumn: i < 2 ? "span 3.5" : "span 3.5" }}>
                <Icon className="w-8 h-8 text-brand mb-4" />
                <h3 className="font-display text-lg font-semibold">{f.title}</h3>
                <p className="mt-2 text-sm text-white/50">{f.desc}</p>
              </motion.div>
            );
          })}
        </div>
      </section>

      {/* How */}
      <section id="how" className="px-6 py-24 border-y border-white/10 bg-surface1">
        <div className="max-w-6xl mx-auto grid md:grid-cols-3 gap-8">
          {[
            { n: "01", t: "Tell the AI about your business", d: "Type it like a message — what you do, who it's for, what makes you special." },
            { n: "02", t: "AI generates your site", d: "A complete, branded, responsive website — copy, sections, and styling." },
            { n: "03", t: "Publish & share", d: "Preview instantly, publish to a live link, or download the HTML." },
          ].map((s) => (
            <div key={s.n} className="p-2">
              <div className="font-mono text-neon text-sm">{s.n}</div>
              <h3 className="font-display text-xl font-semibold mt-3">{s.t}</h3>
              <p className="mt-2 text-white/50 text-sm">{s.d}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Pricing */}
      <section id="pricing" className="px-6 py-24 max-w-6xl mx-auto">
        <div className="text-center mb-14">
          <h2 className="font-display text-4xl sm:text-5xl font-bold">Simple subscription pricing</h2>
          <p className="mt-4 text-white/50">Every plan includes AI credits you spend as you build & edit. Bigger jobs cost more. Need more? <span className="font-mono text-white/70">Buy credit packs anytime.</span></p>
        </div>
        <div className="grid md:grid-cols-3 gap-4">
          {plans.map((p) => (
            <div key={p.id} className={`relative border p-8 bg-surface1 transition-all duration-300 ${p.highlight ? "border-brand" : "border-white/10 hover:border-white/30"}`}>
              {p.highlight && <div className="absolute -top-3 left-8 bg-brand text-xs font-mono px-3 py-1">MOST POPULAR</div>}
              <div className="font-display text-lg font-semibold">{p.name}</div>
              <div className="mt-4 flex items-end gap-1">
                <span className="font-display text-5xl font-bold">${p.price}</span>
                <span className="text-white/40 mb-2 text-sm">{p.per}</span>
              </div>
              <div className="mt-6 font-mono text-brand text-2xl font-bold">{p.unlimited ? "Unlimited" : `${p.credits} credits`}</div>
              <ul className="mt-6 space-y-3 text-sm text-white/60">
                <li className="flex gap-2"><Check className="w-4 h-4 text-brand shrink-0" /> {p.unlimited ? "Unlimited AI builds & edits" : `${p.credits} credits / cycle`}</li>
                <li className="flex gap-2"><Check className="w-4 h-4 text-brand shrink-0" /> Unlimited previews & exports</li>
                <li className="flex gap-2"><Check className="w-4 h-4 text-brand shrink-0" /> AI edits & regenerations</li>
                <li className="flex gap-2"><Check className="w-4 h-4 text-brand shrink-0" /> Buy extra credits anytime</li>
              </ul>
              <Link to={user ? "/pricing" : "/register"} data-testid={`landing-plan-${p.id}`}
                className={`mt-8 block text-center py-3 font-medium transition-colors duration-300 ${p.highlight ? "bg-brand hover:bg-brand-hover" : "border border-white/15 hover:border-white/40"}`}>
                Choose {p.name}
              </Link>
            </div>
          ))}
        </div>
      </section>

      <footer className="border-t border-white/10 px-6 py-10">
        <div className="max-w-7xl mx-auto flex flex-col md:flex-row items-center justify-between gap-4 text-sm text-white/40">
          <div className="flex items-center gap-2"><div className="w-6 h-6 bg-brand flex items-center justify-center"><Zap className="w-4 h-4" /></div> SiteGenie © 2026</div>
          <div className="font-mono">Websites, generated.</div>
        </div>
      </footer>
    </div>
  );
}
