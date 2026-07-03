import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { api } from "@/lib/api";
import { Loader2, Ghost } from "lucide-react";

export default function PublicSite() {
  const { slug } = useParams();
  const [state, setState] = useState({ loading: true, html: null, error: null });

  useEffect(() => {
    let active = true;
    api
      .get(`/public/site/${slug}`)
      .then(({ data }) => {
        if (!active) return;
        document.title = data.business_name || "SiteGenie";
        setState({ loading: false, html: data.html, error: null });
      })
      .catch(() => active && setState({ loading: false, html: null, error: "notfound" }));
    return () => { active = false; };
  }, [slug]);

  if (state.loading) {
    return (
      <div data-testid="public-site-loading" className="fixed inset-0 flex flex-col items-center justify-center gap-3 bg-base text-white">
        <Loader2 className="w-8 h-8 animate-spin text-brand" />
        <div className="font-mono text-sm text-white/50">Loading site…</div>
      </div>
    );
  }

  if (state.error) {
    return (
      <div data-testid="public-site-notfound" className="fixed inset-0 flex flex-col items-center justify-center gap-4 bg-base text-white px-6 text-center">
        <Ghost className="w-12 h-12 text-white/30" />
        <h1 className="font-display text-2xl font-bold">This site isn't available</h1>
        <p className="text-white/50 max-w-md">The link may be wrong or the owner has unpublished it.</p>
        <Link to="/" className="mt-2 bg-brand hover:bg-brand-hover px-5 py-3 transition-colors duration-300">Build your own with SiteGenie</Link>
      </div>
    );
  }

  return (
    <iframe
      data-testid="public-site-frame"
      title="site"
      sandbox="allow-scripts allow-popups allow-forms allow-top-navigation-by-user-activation"
      srcDoc={state.html}
      className="fixed inset-0 w-screen h-screen border-0"
    />
  );
}
