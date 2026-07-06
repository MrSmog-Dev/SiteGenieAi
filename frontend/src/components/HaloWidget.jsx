import { useState, useRef, useEffect, useCallback } from "react";
import axios from "axios";
import { MessageCircle, X, Send, Loader2, Sparkles } from "lucide-react";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
const SESSION_KEY = "sg_support_session";
const GREETING = "Hi! I'm Halo, SiteGenie's support assistant. 👋 Ask me anything about building your site, plans, the Template Market, or anything else — or share feedback and I'll pass it to the team.";

const QUICK = [
  "How does SiteGenie work?",
  "What do the plans cost?",
  "What's the Template Market?",
];

export default function HaloWidget() {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState([{ role: "assistant", content: GREETING }]);
  const [input, setInput] = useState("");
  const [thinking, setThinking] = useState(false);
  const [sessionId, setSessionId] = useState(null);
  const [unread, setUnread] = useState(false);
  const scrollRef = useRef(null);

  useEffect(() => {
    setSessionId(localStorage.getItem(SESSION_KEY));
  }, []);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, thinking, open]);

  const send = useCallback(async (text) => {
    const message = (text || input).trim();
    if (!message || thinking) return;
    setInput("");
    const history = messages.filter((m) => m.role !== "system");
    setMessages((m) => [...m, { role: "user", content: message }]);
    setThinking(true);
    try {
      const { data } = await axios.post(`${API}/support/chat`, {
        message, session_id: sessionId, history: history.slice(-10),
      });
      if (data.session_id && data.session_id !== sessionId) {
        setSessionId(data.session_id);
        localStorage.setItem(SESSION_KEY, data.session_id);
      }
      setMessages((m) => [...m, { role: "assistant", content: data.reply }]);
      if (!open) setUnread(true);
    } catch (e) {
      const detail = e.response?.data?.detail || "I couldn't respond just now — please try again in a moment.";
      setMessages((m) => [...m, { role: "assistant", content: detail }]);
    } finally {
      setThinking(false);
    }
  }, [input, thinking, messages, sessionId, open]);

  return (
    <>
      {/* Launcher */}
      <button
        data-testid="halo-launcher"
        onClick={() => { setOpen((o) => !o); setUnread(false); }}
        aria-label="Chat with Halo support"
        className="fixed bottom-20 right-5 z-[60] group"
      >
        {!open ? (
          <span className="relative flex items-center justify-center w-14 h-14 rounded-full bg-brand shadow-[0_8px_30px_rgba(0,85,255,0.5)] hover:scale-105 transition-transform duration-300">
            <img src="/agents/halo.png" alt="Halo" className="w-12 h-12 rounded-full object-cover" />
            {unread && <span className="absolute -top-0.5 -right-0.5 w-3.5 h-3.5 bg-emerald-400 rounded-full border-2 border-base" />}
            <span className="absolute inset-0 rounded-full ring-2 ring-brand/40 animate-ping" />
          </span>
        ) : (
          <span className="flex items-center justify-center w-14 h-14 rounded-full bg-surface2 border border-white/15 hover:bg-surface1 transition-colors duration-300">
            <X className="w-6 h-6 text-white/80" />
          </span>
        )}
      </button>

      {/* Panel */}
      {open && (
        <div
          data-testid="halo-panel"
          className="fixed bottom-36 right-5 z-[60] w-[92vw] max-w-[380px] h-[70vh] max-h-[560px] flex flex-col bg-surface1 border border-white/12 shadow-2xl rounded-xl overflow-hidden animate-in slide-in-from-bottom-4 duration-300"
        >
          {/* header */}
          <div className="flex items-center gap-3 px-4 py-3.5 bg-gradient-to-r from-brand/25 to-brand/5 border-b border-white/10">
            <div className="relative">
              <img src="/agents/halo.png" alt="Halo" className="w-10 h-10 rounded-full object-cover" />
              <span className="absolute -bottom-0.5 -right-0.5 w-3 h-3 bg-emerald-400 rounded-full border-2 border-surface1" />
            </div>
            <div className="min-w-0">
              <div className="font-display font-bold text-sm">Halo — Support</div>
              <div className="text-[11px] text-emerald-300/90 font-mono">● Online · replies in seconds</div>
            </div>
          </div>

          {/* messages */}
          <div ref={scrollRef} className="flex-1 overflow-y-auto px-4 py-4 space-y-3" data-testid="halo-messages">
            {messages.map((m, i) => (
              <div key={i} className={`flex gap-2 ${m.role === "user" ? "justify-end" : ""}`}>
                {m.role !== "user" && (
                  <img src="/agents/halo.png" alt="" className="w-6 h-6 rounded-full object-cover shrink-0 mt-0.5" />
                )}
                <div className={`max-w-[80%] px-3.5 py-2.5 text-sm whitespace-pre-wrap leading-relaxed rounded-2xl ${
                  m.role === "user" ? "bg-brand text-white rounded-br-sm" : "bg-surface2 text-white/90 rounded-bl-sm"}`}>
                  {m.content}
                </div>
              </div>
            ))}
            {thinking && (
              <div className="flex gap-2" data-testid="halo-typing">
                <img src="/agents/halo.png" alt="" className="w-6 h-6 rounded-full object-cover shrink-0 mt-0.5" />
                <div className="bg-surface2 px-3.5 py-3 rounded-2xl rounded-bl-sm flex items-center gap-1.5">
                  <span className="w-1.5 h-1.5 bg-white/50 rounded-full animate-bounce" />
                  <span className="w-1.5 h-1.5 bg-white/50 rounded-full animate-bounce" style={{ animationDelay: "150ms" }} />
                  <span className="w-1.5 h-1.5 bg-white/50 rounded-full animate-bounce" style={{ animationDelay: "300ms" }} />
                </div>
              </div>
            )}
            {messages.length <= 1 && !thinking && (
              <div className="flex flex-wrap gap-2 pt-1">
                {QUICK.map((q) => (
                  <button key={q} onClick={() => send(q)}
                    className="flex items-center gap-1.5 text-xs border border-white/12 hover:border-brand hover:text-brand text-white/60 px-2.5 py-1.5 rounded-full transition-colors duration-200">
                    <Sparkles className="w-3 h-3" /> {q}
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* input */}
          <div className="border-t border-white/10 p-3 bg-surface1">
            <div className="flex gap-2">
              <input
                data-testid="halo-input"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && send()}
                placeholder="Ask Halo anything…"
                disabled={thinking}
                className="flex-1 bg-surface2 border border-white/10 focus:border-brand outline-none px-3.5 py-2.5 text-sm rounded-lg transition-colors duration-300"
              />
              <button data-testid="halo-send" onClick={() => send()} disabled={thinking || !input.trim()}
                className="bg-brand hover:bg-brand-hover px-3.5 rounded-lg transition-colors duration-300 disabled:opacity-40">
                {thinking ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
              </button>
            </div>
            <div className="text-[10px] text-white/25 text-center mt-2 font-mono">Powered by SiteGenie AI · Halo</div>
          </div>
        </div>
      )}
    </>
  );
}
