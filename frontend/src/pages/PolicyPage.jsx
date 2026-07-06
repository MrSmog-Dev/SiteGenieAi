import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import axios from "axios";
import { ArrowLeft, Loader2, MessageCircle } from "lucide-react";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const META = {
  faq: { kind: "faq", fallback: "Frequently Asked Questions" },
  "refund-policy": { kind: "refund", fallback: "Refund Policy" },
  terms: { kind: "terms", fallback: "Terms of Service" },
};

export default function PolicyPage({ kind: fixedKind }) {
  const params = useParams();
  const routeKey = fixedKind || params.kind;
  const meta = META[routeKey] || META.faq;
  const [page, setPage] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    setLoading(true);
    setError(false);
    axios.get(`${API}/support/pages/${meta.kind}`)
      .then(({ data }) => setPage(data))
      .catch(() => setError(true))
      .finally(() => setLoading(false));
  }, [meta.kind]);

  return (
    <div className="min-h-screen bg-base text-white">
      {/* nav */}
      <header className="border-b border-white/10 px-6 py-4 sticky top-0 bg-base/90 backdrop-blur z-10">
        <div className="max-w-3xl mx-auto flex items-center justify-between">
          <Link to="/" className="flex items-center gap-2.5" data-testid="policy-home-link">
            <img src="/sitegenie_logo_mark.png" alt="SiteGenie" className="w-8 h-8 object-contain" />
            <span className="font-display font-bold tracking-tight">SiteGenie</span>
          </Link>
          <Link to="/" className="text-sm text-white/50 hover:text-white flex items-center gap-1.5 transition-colors duration-300">
            <ArrowLeft className="w-4 h-4" /> Home
          </Link>
        </div>
      </header>

      <main className="max-w-3xl mx-auto px-6 py-12" data-testid="policy-page">
        <div className="font-mono text-xs text-white/40 uppercase tracking-wider mb-2">SiteGenie</div>
        <h1 className="font-display text-3xl md:text-4xl font-bold" data-testid="policy-title">
          {page?.title || meta.fallback}
        </h1>
        {page?.updated_at && (
          <p className="text-white/40 text-sm mt-2">Last updated {new Date(page.updated_at).toLocaleDateString()} · drafted by Halo, our support lead</p>
        )}

        <div className="mt-8">
          {loading ? (
            <div className="flex items-center gap-2 text-white/40 font-mono text-sm py-12">
              <Loader2 className="w-4 h-4 animate-spin" /> Loading…
            </div>
          ) : error ? (
            <div className="border border-white/10 bg-surface1 p-8 text-center text-white/50">
              This page isn't available right now. Please try again shortly or ask Halo in the chat.
            </div>
          ) : (
            <article
              className="policy-content max-w-none"
              dangerouslySetInnerHTML={{ __html: page.html }}
            />
          )}
        </div>

        <div className="mt-12 border-t border-white/10 pt-6 flex items-center gap-2 text-sm text-white/50">
          <MessageCircle className="w-4 h-4 text-brand" />
          Still have questions? Chat with Halo using the bubble in the corner.
        </div>
      </main>
    </div>
  );
}
