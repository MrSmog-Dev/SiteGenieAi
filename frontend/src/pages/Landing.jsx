import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import { useAuth } from "@/context/AuthContext";
import { Zap, Sparkles, Gauge, Palette, Rocket, ArrowRight, Check } from "lucide-react";

const HERO_BG = "https://images.unsplash.com/photo-1546497974-b213c9efb599?crop=entropy&cs=srgb&fm=jpg&q=85&w=2000";
const PREVIEW = "https://images.unsplash.com/photo-1634084462412-b54873c0a56d?crop=entropy&cs=srgb&fm=jpg&q=85&w=1200";

const plans = [
  { id: "monthly", name: "Monthly", price: 20, per: "/mo", credits: 20, highlight: false },
  { id: "quarterly", name: "3-Month", price: 49, per: "/qtr", credits: 75, highlight: true },
  { id: "annual", name: "Annual", price: 149, per: "/yr", credits: 160, highlight: false },
];

const features = [
  { icon: Sparkles, title: "AI-crafted sites", desc: "Describe your business. Our AI writes copy and designs a full responsive site in seconds." },
  { icon: Palette, title: "On-brand styling", desc: "Pick your brand color and style — every template is tailored to your industry." },
  { icon: Gauge, title: "Credit-based", desc: "One credit generates one complete website. Simple, predictable, no surprises." },
  { icon: Rocket, title: "Export & ship", desc: "Download production-ready HTML and launch anywhere in minutes." },
];

export default function Landing() {
  const { user } = useAuth();
  const cta = user ? "/dashboard" : "/register";

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

      {/* Hero */}
      <section className="relative pt-40 pb-28 px-6">
        <div className="absolute inset-0 opacity-20 mix-blend-screen" style={{ backgroundImage: `url(${HERO_BG})`, backgroundSize: "cover", backgroundPosition: "center" }} />
        <div className="absolute inset-0 bg-gradient-to-b from-transparent via-base/40 to-base" />
        <div className="relative max-w-6xl mx-auto">
          <motion.div initial={{ opacity: 0, y: 24 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.7 }}>
            <div className="inline-flex items-center gap-2 border border-white/15 px-4 py-1.5 text-xs font-mono text-white/70 mb-8">
              <span className="w-2 h-2 bg-neon animate-pulse" /> AI WEBSITE GENERATOR FOR BUSINESSES
            </div>
            <h1 className="font-display text-5xl sm:text-6xl lg:text-7xl font-bold leading-[0.95] tracking-tight max-w-4xl">
              Generate a stunning<br /><span className="text-brand">website with AI</span> — no code, no designer.
            </h1>
            <p className="mt-8 text-lg text-white/60 max-w-xl">
              For businesses without a website. Describe what you do, and SiteGenie builds a complete, branded, responsive site in seconds. Powered by credits.
            </p>
            <div className="mt-10 flex flex-wrap items-center gap-4">
              <Link to={cta} data-testid="hero-cta-btn" className="group inline-flex items-center gap-2 bg-brand hover:bg-brand-hover px-8 py-4 font-medium transition-colors duration-300">
                Start building free <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform duration-300" />
              </Link>
              <a href="#pricing" className="inline-flex items-center gap-2 border border-white/15 hover:border-white/40 px-8 py-4 transition-colors duration-300">View pricing</a>
            </div>
            <div className="mt-6 text-sm text-white/40 font-mono">3 free credits on sign up · 1 credit = 1 full website</div>
          </motion.div>

          <motion.div initial={{ opacity: 0, y: 40 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.8, delay: 0.2 }}
            className="mt-20 border border-white/10 bg-surface1 overflow-hidden">
            <div className="flex items-center gap-2 px-4 py-3 border-b border-white/10 bg-surface2">
              <span className="w-3 h-3 rounded-full bg-neon" /><span className="w-3 h-3 rounded-full bg-white/20" /><span className="w-3 h-3 rounded-full bg-white/20" />
              <span className="ml-3 font-mono text-xs text-white/40">yourbusiness.sitegenie.app</span>
            </div>
            <img src={PREVIEW} alt="Generated website preview" className="w-full h-[380px] object-cover" />
          </motion.div>
        </div>
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
            { n: "01", t: "Describe your business", d: "Name, industry, and a short description of what you offer." },
            { n: "02", t: "AI generates your site", d: "A complete, branded, responsive website — copy, sections, and styling." },
            { n: "03", t: "Preview & export", d: "Preview instantly, tweak by regenerating, and download the HTML." },
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
          <p className="mt-4 text-white/50">Every plan includes AI generation credits. <span className="font-mono text-white/70">1 credit = 1 website</span>. Need more? Buy credit packs anytime.</p>
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
              <div className="mt-6 font-mono text-brand text-2xl font-bold">{p.credits} credits</div>
              <ul className="mt-6 space-y-3 text-sm text-white/60">
                <li className="flex gap-2"><Check className="w-4 h-4 text-brand shrink-0" /> {p.credits} AI website generations</li>
                <li className="flex gap-2"><Check className="w-4 h-4 text-brand shrink-0" /> Unlimited previews & edits</li>
                <li className="flex gap-2"><Check className="w-4 h-4 text-brand shrink-0" /> HTML export</li>
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
