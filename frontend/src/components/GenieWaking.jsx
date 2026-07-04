import { useEffect, useState } from "react";
import { subscribeApiHealth, checkApiHealth } from "@/lib/apiHealth";

export const GenieWaking = () => {
  const [down, setDown] = useState(false);

  useEffect(() => subscribeApiHealth(setDown), []);

  useEffect(() => {
    if (!down) return;
    const timer = setInterval(checkApiHealth, 8000);
    return () => clearInterval(timer);
  }, [down]);

  if (!down) return null;
  return (
    <div data-testid="genie-waking-banner"
      className="fixed top-0 inset-x-0 z-[100] flex items-center justify-center gap-3 px-4 py-2.5 bg-[#0B1220]/95 backdrop-blur-md border-b border-brand/40 shadow-[0_4px_24px_rgba(37,99,235,0.25)]">
      <img src="/sitegenie_logo_mark.png" alt="" className="w-6 h-6 object-contain animate-pulse" />
      <span className="text-sm text-white/85 font-medium">We're waking the genie — back in a moment.</span>
      <span className="flex gap-1">
        <span className="w-1 h-1 rounded-full bg-brand animate-bounce" />
        <span className="w-1 h-1 rounded-full bg-brand animate-bounce" style={{ animationDelay: "150ms" }} />
        <span className="w-1 h-1 rounded-full bg-brand animate-bounce" style={{ animationDelay: "300ms" }} />
      </span>
    </div>
  );
};
