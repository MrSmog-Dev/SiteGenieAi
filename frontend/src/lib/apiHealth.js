const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

const listeners = new Set();
let down = false;
let checking = false;

export const subscribeApiHealth = (fn) => {
  listeners.add(fn);
  fn(down);
  return () => listeners.delete(fn);
};

const set = (v) => {
  if (down !== v) {
    down = v;
    listeners.forEach((f) => f(v));
  }
};

export const checkApiHealth = async () => {
  try {
    const res = await fetch(`${BACKEND_URL}/api/status`, { cache: "no-store" });
    const data = await res.json();
    set(!(res.ok && data.db));
  } catch {
    set(true);
  }
};

// Called by the axios interceptor on network errors / 5xx. Verifies via /api/status
// before showing the banner, so one-off endpoint failures don't cause false alarms.
export const reportApiError = () => {
  if (checking) return;
  checking = true;
  checkApiHealth().finally(() => { checking = false; });
};
