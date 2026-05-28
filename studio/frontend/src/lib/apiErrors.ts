import type { AxiosError } from "axios";

type ValidationItem = { msg?: string; loc?: unknown[] };

export function formatApiError(err: unknown, fallback = "Something went wrong. Please try again."): string {
  if (!err || typeof err !== "object") return fallback;

  const ax = err as AxiosError<{ detail?: string | ValidationItem[] }>;

  if (!ax.response) {
    if (ax.code === "ERR_NETWORK" || ax.message === "Network Error") {
      return "Cannot reach the Studio API. Start the backend (port 8080) and use the Vite dev server on port 5173, or set VITE_API_URL to your API URL.";
    }
    if (ax.code === "ECONNABORTED") {
      return "The request timed out. Please try again.";
    }
    return fallback;
  }

  const status = ax.response.status;
  const detail = ax.response.data?.detail;

  if (typeof detail === "string" && detail.trim()) return detail;

  if (Array.isArray(detail)) {
    const msgs = detail
      .map((item) => (typeof item === "object" && item?.msg ? String(item.msg) : ""))
      .filter(Boolean);
    if (msgs.length) return msgs.join(" ");
  }

  if (status === 401) return "Invalid email or password.";
  if (status === 400) return "Please check your details and try again.";
  if (status === 403) return "You do not have permission to perform this action.";
  if (status === 404) return "The requested resource was not found.";
  if (status === 422) return "Please check the form and try again.";
  if (status === 503) return "Sign-in service is temporarily unavailable. Try email and password.";
  if (status >= 500) return "Server error. Please try again in a few minutes.";

  return fallback;
}
