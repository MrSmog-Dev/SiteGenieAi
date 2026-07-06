import { useState, useEffect, useRef } from "react";
import { Link, useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { useAuth } from "@/context/AuthContext";
import { Sparkles, Gauge, Palette, Rocket, ArrowUp, Check, Coffee, Scissors, Dumbbell, UtensilsCrossed, Scale, Flower2, RotateCcw } from "lucide-react";

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
  { id: "coffee", icon: Coffee, label: "Coffee shop", industry: "Coffee shop", prompt: "A cozy neighborhood coffee shop with specialty espresso, fresh pastries, and a warm space to work or catch up with friends." },
  { id: "barber", icon: Scissors, label: "Barber shop", industry: "Barber shop", prompt: "A modern barber shop offering classic cuts, beard trims, and hot towel shaves — walk-ins welcome, appointments preferred." },
  { id: "fitness", icon: Dumbbell, label: "Fitness studio", industry: "Fitness studio", prompt: "A boutique fitness studio with small-group HIIT classes, personal training, and flexible monthly memberships." },
  { id: "restaurant", icon: UtensilsCrossed, label: "Restaurant", industry: "Restaurant", prompt: "A family-owned Italian restaurant serving handmade pasta, wood-fired pizza, and a curated local wine list." },
  { id: "law", icon: Scale, label: "Law firm", industry: "Law firm", prompt: "A boutique law firm specializing in small business and estate law, with free 30-minute consultations." },
  { id: "florist", icon: Flower2, label: "Florist", industry: "Florist", prompt: "A florist studio creating seasonal bouquets, wedding florals, and same-day local delivery." },
];

const VIBES = [
  { label: "Warm & cozy", keywords: "warm, cozy, welcoming", style: "modern" },
  { label: "Premium & elegant", keywords: "premium, elegant, refined", style: "elegant" },
  { label: "Playful & bold", keywords: "playful, bold, vibrant", style: "playful" },
  { label: "Clean & minimal", keywords: "clean, minimal, airy", style: "minimal" },
  { label: "Modern & techy", keywords: "modern, sleek, innovative", style: "modern" },
  { label: "Classic & trustworthy", keywords: "classic, trustworthy, established", style: "corporate" },
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

const PLACEHOLDERS = {
  name: "e.g. Fade Factory Barbershop",
  vibe: "e.g. warm and welcoming, upscale, minimalist…",
  done: "",
};

const STEP_HINTS = {
  idle: "2-pass AI build · strategist + builder",
  name: "Step 2 of 3 · business name",
  vibe: "Step 3 of 3 · brand vibe",
  done: "Brief ready ✓",
};

export default function Landing() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [input, setInput] = useState("");
  const [stage, setStage] = useState("idle"); // idle | name | vibe | done
  const [messages, setMessages] = useState([]);
  const [typing, setTyping] = useState(false);
  const [brief, setBrief] = useState({});
  const textareaRef = useRef(null);
  const endRef = useRef(null);
  const placeholder = useTypewriter(stage === "idle" && !input);

  useEffect(() => {
    if (messages.length) endRef.current?.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }, [messages, typing]);

  const pushAi = (text, after) => {
    setTyping(true);
    setTimeout(() => {
      setMessages((m) => [...m, { role: "ai", text }]);
      setTyping(false);
      after?.();
    }, 750);
  };

  const startIdea = (idea, industry = "") => {
    setMessages([{ role: "user", text: idea }]);
    setBrief({ description: idea, industry });
    setStage("name");
    setInput("");
    pushAi("Love it — let's make this real. Quick question: what's your business called?");
    textareaRef.current?.focus();
  };

  const submitName = (name) => {
    setMessages((m) => [...m, { role: "user", text: name }]);
    setBrief((b) => ({ ...b, business_name: name }));
    setStage("vibe");
    setInput("");
    pushAi(`${name} — great name. Last one: what vibe should the website have? Pick one below or type your own.`);
  };

  const skipStep = () => {
    if (typing) return;
    if (stage === "name") {
      setStage("vibe");
      setInput("");
      pushAi("No worries — you can add the name later. What vibe should the site have? Pick one below or type your own.");
    } else if (stage === "vibe") {
      finishFlow(null, null);
    }
  };

  const finishFlow = (vibeLabel, vibe) => {
    if (typing) return;
    const final = { ...brief };
    if (vibeLabel) {
      final.brand_keywords = vibe?.keywords || vibeLabel;
      if (vibe?.style) final.style = vibe.style;
      setMessages((m) => [...m, { role: "user", text: vibeLabel }]);
    }
    setStage("done");
    setInput("");
    sessionStorage.setItem("sg_pending_brief", JSON.stringify(final));
    const n = final.business_name;
    pushAi(
      user
        ? `Perfect — I've got everything I need. Taking you to the builder${n ? ` for ${n}` : ""}…`
        : `Perfect — I've got everything I need${n ? ` for ${n}` : ""}. Create a free account and I'll drop you straight into the build.`,
      () => setTimeout(() => navigate(user ? "/generate" : "/register"), 1000)
    );
  };

  const restart = () => {
    setStage("idle"); setMessages([]); setBrief({}); setInput(""); setTyping(false);
  };

  const send = (text) => {
    if (stage === "done" || typing) return;
    const val = (text ?? input).trim();
    if (!val) { textareaRef.current?.focus(); return; }
    if (stage === "idle") startIdea(val);
    else if (stage === "name") submitName(val);
    else if (stage === "vibe") finishFlow(val, null);
  };

  const onKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); }
  };

  const chatActive = stage !== "idle";

  return (
    <div className="min-h-screen bg-base text-white font-body overflow-x-hidden">
      {/* Nav */}
      <header className="fixed top-0 inset-x-0 z-40 bg-black/60 backdrop-blur-xl border-b border-white/10">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-2.5" data-testid="landing-logo">
            <img src="/sitegenie_logo_mark.png" alt="SiteGenie" className="w-9 h-9 object-contain" />
            <span className="font-display font-bold text-lg tracking-tight">SiteGenie</span>
          </Link>
          <nav className="hidden md:flex items-center gap-8 text-sm text-white/60">
            <Link to="/market" data-testid="nav-market-link" className="text-amber-300/90 hover:text-amber-200 transition-colors duration-300">Template Market</Link>
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
      <section className="relative min-h-screen flex flex-col items-center justify-center px-6 pt-24 pb-16">
        <div className="pointer-events-none absolute inset-0 overflow-hidden">
          <div className="absolute left-1/2 top-1/3 -translate-x-1/2 -translate-y-1/2 w-[900px] h-[500px] rounded-full opacity-25"
            style={{ background: "radial-gradient(ellipse at center, rgba(0,85,255,0.55) 0%, rgba(0,85,255,0.12) 45%, transparent 70%)" }} />
          <div className="absolute inset-0 opacity-[0.05]"
            style={{ backgroundImage: "linear-gradient(rgba(255,255,255,0.6) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.6) 1px, transparent 1px)", backgroundSize: "64px 64px" }} />
        </div>

        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.6 }}
          className="relative w-full max-w-3xl flex flex-col items-center text-center">
          <div className="flex flex-col items-center gap-3 mb-6" data-testid="hero-agent-badge">
            <img src="/sitegenie_logo_full.png" alt="SiteGenie — Your Website Wish, Granted" className="h-40 md:h-48 object-contain" data-testid="hero-logo-lockup" />
            <span className="font-mono text-sm text-white/60 flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-emerald-400 animate-pulse" /> SiteGenie AI · online
            </span>
          </div>

          {!chatActive && (
            <>
              <h1 className="font-display text-4xl sm:text-5xl lg:text-6xl font-bold tracking-tight leading-[1.05]">
                {user ? <>Welcome back{user.name ? `, ${user.name.split(" ")[0]}` : ""}.<br /><span className="text-brand">What are we building?</span></> : <>Tell me about your business.<br /><span className="text-brand">I'll build the website.</span></>}
              </h1>
              <p className="mt-5 text-white/50 max-w-lg text-base md:text-lg">
                Describe what you do — copy, design, and a full responsive site are generated in minutes. No code, no designer.
              </p>
            </>
          )}

          {/* Chat thread */}
          {messages.length > 0 && (
            <div data-testid="chat-thread" className="mt-6 w-full space-y-3 text-left max-h-[340px] overflow-y-auto pr-1">
              {messages.map((m, i) => m.role === "ai" ? (
                <motion.div key={i} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="flex items-start gap-2.5" data-testid={`chat-msg-ai-${i}`}>
                  <div className="w-7 h-7 flex items-center justify-center shrink-0 mt-0.5"><img src="/sitegenie_logo_mark.png" alt="AI" className="w-7 h-7 object-contain" /></div>
                  <div className="rounded-2xl rounded-tl-sm bg-surface1 border border-white/10 px-4 py-3 text-sm text-white/85 max-w-[85%]">{m.text}</div>
                </motion.div>
              ) : (
                <motion.div key={i} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="flex justify-end" data-testid={`chat-msg-user-${i}`}>
                  <div className="rounded-2xl rounded-tr-sm bg-brand px-4 py-3 text-sm max-w-[85%]">{m.text}</div>
                </motion.div>
              ))}
              {typing && (
                <div className="flex items-start gap-2.5" data-testid="chat-typing">
                  <div className="w-7 h-7 flex items-center justify-center shrink-0 mt-0.5"><img src="/sitegenie_logo_mark.png" alt="AI" className="w-7 h-7 object-contain" /></div>
                  <div className="rounded-2xl rounded-tl-sm bg-surface1 border border-white/10 px-4 py-3.5 flex gap-1.5 items-center">
                    <span className="w-1.5 h-1.5 rounded-full bg-white/50 animate-bounce" />
                    <span className="w-1.5 h-1.5 rounded-full bg-white/50 animate-bounce [animation-delay:0.15s]" />
                    <span className="w-1.5 h-1.5 rounded-full bg-white/50 animate-bounce [animation-delay:0.3s]" />
                  </div>
                </div>
              )}
              <div ref={endRef} />
            </div>
          )}

          {/* Prompt box */}
          <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.6, delay: 0.15 }}
            className={`${chatActive ? "mt-4" : "mt-10"} w-full`}>
            <div className="group relative rounded-2xl border border-white/15 bg-surface1/90 backdrop-blur-xl transition-all duration-300 focus-within:border-brand/70 focus-within:shadow-[0_0_60px_-12px_rgba(0,85,255,0.55)]"
              data-testid="hero-prompt-box">
              <textarea
                ref={textareaRef}
                data-testid="hero-prompt-input"
                aria-label="Describe your business"
                rows={chatActive ? 1 : 3}
                value={input}
                disabled={stage === "done"}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={onKeyDown}
                placeholder={stage === "idle" ? (placeholder || "Describe your business…") : PLACEHOLDERS[stage]}
                className="w-full resize-none bg-transparent px-5 pt-5 pb-2 text-left text-base text-white placeholder:text-white/30 outline-none disabled:opacity-50"
              />
              <div className="flex items-center justify-between px-4 pb-3.5">
                <div className="flex items-center gap-2 text-xs font-mono text-white/35">
                  <Sparkles className="w-3.5 h-3.5 text-brand" />
                  <span>{STEP_HINTS[stage]}</span>
                </div>
                <div className="flex items-center gap-2">
                  {(stage === "name" || stage === "vibe") && (
                    <button data-testid="chat-skip-btn" onClick={skipStep}
                      className="text-xs font-mono text-white/35 hover:text-white/70 px-2 py-1 transition-colors duration-300">
                      Skip →
                    </button>
                  )}
                  <button
                    data-testid="hero-prompt-submit"
                    onClick={() => send()}
                    disabled={stage === "done"}
                    aria-label="Send"
                    className={`flex items-center justify-center w-10 h-10 rounded-xl transition-all duration-300 ${input.trim() ? "bg-brand hover:bg-brand-hover scale-100" : "bg-white/10 text-white/40 hover:bg-white/15"} disabled:opacity-40`}>
                    <ArrowUp className="w-5 h-5" />
                  </button>
                </div>
              </div>
            </div>
            <div className="mt-3 flex items-center justify-center gap-4 text-xs font-mono text-white/30">
              <span>{stage === "idle" ? "Press Enter to start · 15 free credits on sign up" : "Enter to send"}</span>
              {chatActive && stage !== "done" && (
                <button data-testid="chat-restart-btn" onClick={restart} className="flex items-center gap-1 hover:text-white/70 transition-colors duration-300">
                  <RotateCcw className="w-3 h-3" /> Start over
                </button>
              )}
            </div>
          </motion.div>

          {/* Vibe chips */}
          {stage === "vibe" && !typing && (
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="mt-5 flex flex-wrap justify-center gap-2.5">
              {VIBES.map((v, i) => (
                <button key={v.label} data-testid={`vibe-chip-${i}`} onClick={() => finishFlow(v.label, v)}
                  className="rounded-full border border-white/12 bg-surface1/70 px-4 py-2 text-sm text-white/60 hover:text-white hover:border-brand/60 transition-colors duration-300">
                  {v.label}
                </button>
              ))}
            </motion.div>
          )}

          {/* Idea chips */}
          {stage === "idle" && (
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.6, delay: 0.3 }}
              className="mt-8 flex flex-wrap justify-center gap-2.5">
              {CHIPS.map((c) => {
                const Icon = c.icon;
                return (
                  <button key={c.id} data-testid={`hero-chip-${c.id}`} onClick={() => startIdea(c.prompt, c.industry)}
                    className="flex items-center gap-2 rounded-full border border-white/12 bg-surface1/70 px-4 py-2 text-sm text-white/60 hover:text-white hover:border-white/35 transition-colors duration-300">
                    <Icon className="w-4 h-4 text-brand" /> {c.label}
                  </button>
                );
              })}
            </motion.div>
          )}
        </motion.div>

        {stage === "idle" && (
          <a href="#features" className="absolute bottom-8 text-white/25 hover:text-white/60 font-mono text-xs transition-colors duration-300">↓ scroll to explore</a>
        )}
      </section>

      {/* Features bento */}
      <section id="features" className="px-6 py-24 max-w-7xl mx-auto">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="sm:col-span-2 lg:col-span-4 border border-white/10 p-10 bg-surface1">
            <h2 className="font-display text-3xl md:text-4xl font-bold leading-tight max-w-2xl">Everything you need to<br />get online, fast.</h2>
            <p className="mt-4 text-white/50 max-w-2xl">No templates to fiddle with. No blank canvas anxiety. Just answer a few questions and ship.</p>
          </div>
          {features.map((f, i) => {
            const Icon = f.icon;
            return (
              <motion.div key={f.title} initial={{ opacity: 0, y: 20 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} transition={{ delay: i * 0.08 }}
                className="border border-white/10 p-8 bg-surface1 hover:border-white/30 transition-colors duration-300">
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
          <div className="flex items-center gap-2"><img src="/sitegenie_logo_mark.png" alt="SiteGenie" className="w-6 h-6 object-contain" /> SiteGenie © 2026</div>
          <div className="flex items-center gap-5">
            <Link to="/faq" className="hover:text-white transition-colors duration-300" data-testid="footer-faq">FAQ</Link>
            <Link to="/refund-policy" className="hover:text-white transition-colors duration-300" data-testid="footer-refund">Refund Policy</Link>
            <Link to="/terms" className="hover:text-white transition-colors duration-300" data-testid="footer-terms">Terms</Link>
          </div>
        </div>
      </footer>
    </div>
  );
}
