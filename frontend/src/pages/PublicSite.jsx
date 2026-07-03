import { useEffect } from "react";
import { useParams } from "react-router-dom";
import { Loader2 } from "lucide-react";

export default function PublicSite() {
  const { slug } = useParams();
  useEffect(() => {
    window.location.replace(`${window.location.origin}/api/p/${slug}`);
  }, [slug]);
  return (
    <div data-testid="public-site-redirect" className="fixed inset-0 flex flex-col items-center justify-center gap-3 bg-base text-white">
      <Loader2 className="w-8 h-8 animate-spin text-brand" />
      <div className="font-mono text-sm text-white/50">Opening site…</div>
    </div>
  );
}
