import { useEffect, useState } from "react";
import { Loader2 } from "lucide-react";
import axios from "axios";

export default function DomainSite() {
  const [state, setState] = useState({ status: "loading", html: "" });

  useEffect(() => {
    axios.get(`/api/public/domain/${window.location.hostname}`)
      .then(({ data }) => {
        document.title = data.business_name || "Website";
        setState({ status: "ok", html: data.html });
      })
      .catch(() => setState({ status: "notfound", html: "" }));
  }, []);

  if (state.status === "loading") {
    return (
      <div data-testid="domain-site-loading" className="fixed inset-0 flex flex-col items-center justify-center gap-3 bg-base text-white">
        <Loader2 className="w-8 h-8 animate-spin text-brand" />
        <div className="font-mono text-sm text-white/50">Loading site…</div>
      </div>
    );
  }
  if (state.status === "notfound") {
    return (
      <div data-testid="domain-site-notfound" className="fixed inset-0 flex flex-col items-center justify-center gap-4 bg-base text-white px-6 text-center">
        <h1 className="font-display text-2xl font-bold">No site connected to this domain</h1>
        <p className="text-white/50 text-sm max-w-md">The owner may have unpublished it, or DNS was pointed here before connecting the domain in SiteGenie.</p>
      </div>
    );
  }
  return (
    <iframe
      data-testid="domain-site-iframe"
      title="site"
      sandbox="allow-scripts"
      srcDoc={state.html}
      className="fixed inset-0 w-full h-full border-0 bg-white"
    />
  );
}
