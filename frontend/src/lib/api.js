import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
export const API = `${BACKEND_URL}/api`;

export const api = axios.create({
  baseURL: API,
  withCredentials: true,
});

export function formatApiError(detail) {
  if (detail == null) return "Something went wrong. Please try again.";
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail))
    return detail.map((e) => (e && typeof e.msg === "string" ? e.msg : JSON.stringify(e))).filter(Boolean).join(" ");
  if (detail && typeof detail.msg === "string") return detail.msg;
  return String(detail);
}

// Polls a generation job until done/error. Returns the final job payload (with .template).
export function pollGenerationJob(jobId, { interval = 2500, maxAttempts = 90 } = {}) {
  return new Promise((resolve, reject) => {
    let attempts = 0;
    const tick = async () => {
      attempts += 1;
      if (attempts > maxAttempts) return reject(new Error("Generation timed out. Please try again."));
      try {
        const { data } = await api.get(`/templates/job/${jobId}`);
        if (data.status === "done" && data.template) return resolve(data);
        if (data.status === "error") return reject(new Error(data.error || "Generation failed."));
      } catch (e) { /* network hiccup — keep polling */ }
      setTimeout(tick, interval);
    };
    setTimeout(tick, 3000);
  });
}
