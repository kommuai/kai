import { useEffect, useRef, useState } from "react";
import { Loader2, Smartphone, CheckCircle2, AlertCircle } from "lucide-react";
import clsx from "clsx";
import { onboardingApi, tenantsApi } from "../lib/api";
import { formatApiError } from "../lib/apiErrors";

type LinkStatus = "idle" | "starting" | "qr" | "connecting" | "connected" | "disconnected" | "error";

interface Props {
  /** Onboarding wizard — uses session-scoped bridge auth. */
  sessionId?: string | null;
  onSessionNeeded?: () => Promise<string>;
  /** Existing tenant — uses tenant workspace auth dir. */
  tenantId?: string | null;
  onConnected: (phone: string) => void;
  disabled?: boolean;
}

export default function WhatsAppBaileysLink({
  sessionId = null,
  onSessionNeeded,
  tenantId = null,
  onConnected,
  disabled,
}: Props) {
  const [status, setStatus] = useState<LinkStatus>("idle");
  const [qrDataUrl, setQrDataUrl] = useState<string | null>(null);
  const [phone, setPhone] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [starting, setStarting] = useState(false);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const connectedRef = useRef(false);
  const startRequestedRef = useRef(false);

  async function ensureStart() {
    if (disabled || connectedRef.current) return;
    setStarting(true);
    setError(null);
    try {
      let res;
      if (tenantId) {
        res = await tenantsApi.whatsappStart(tenantId);
      } else {
        let sid = sessionId;
        if (!sid) {
          if (!onSessionNeeded) throw new Error("Session required");
          sid = await onSessionNeeded();
        }
        res = await onboardingApi.whatsappStart(sid);
      }
      setStatus((res.status as LinkStatus) || "starting");
      if (res.qr_data_url) setQrDataUrl(res.qr_data_url);
      if (res.phone) {
        setPhone(res.phone);
        setStatus("connected");
        connectedRef.current = true;
        onConnected(res.phone);
      }
    } catch (e: unknown) {
      setStatus("error");
      setError(formatApiError(e, "Could not start WhatsApp linking"));
    } finally {
      setStarting(false);
    }
  }

  useEffect(() => {
    const scopeId = tenantId || sessionId;
    if (!scopeId || disabled || startRequestedRef.current) return;
    startRequestedRef.current = true;
    ensureStart();
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sessionId, tenantId, disabled]);

  useEffect(() => {
    const scopeId = tenantId || sessionId;
    if (!scopeId || status === "connected" || status === "error" || status === "idle") {
      if (pollRef.current) clearInterval(pollRef.current);
      return;
    }
    pollRef.current = setInterval(async () => {
      try {
        const res = tenantId
          ? await tenantsApi.whatsappStatus(tenantId)
          : await onboardingApi.whatsappStatus(sessionId!);
        setStatus((res.status as LinkStatus) || "starting");
        setQrDataUrl(res.qr_data_url ?? null);
        if (res.status === "connecting") {
          setError(null);
        } else if (res.error && res.status !== "connected") {
          setError(res.error);
        }
        if (res.status === "connected" && res.phone) {
          setPhone(res.phone);
          connectedRef.current = true;
          onConnected(res.phone);
          if (pollRef.current) clearInterval(pollRef.current);
        }
      } catch (e: unknown) {
        setError(formatApiError(e, "Status check failed"));
      }
    }, 2000);
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, [sessionId, tenantId, status, onConnected]);

  return (
    <div className="rounded-xl border border-emerald-200 bg-emerald-50/40 p-4 space-y-4">
      <div className="flex items-start gap-3">
        <div className="h-10 w-10 rounded-xl bg-emerald-600 flex items-center justify-center shrink-0">
          <Smartphone size={20} className="text-white" />
        </div>
        <div>
          <p className="text-sm font-semibold text-gray-900">Link WhatsApp</p>
          <p className="text-xs text-gray-600 mt-0.5">
            Open WhatsApp on your phone → <strong>Linked devices</strong> → <strong>Link a device</strong> → scan
            this QR code.
          </p>
        </div>
      </div>

      {status === "connected" && phone && (
        <div className="flex items-center gap-2 text-sm text-emerald-800 bg-emerald-100/80 rounded-lg px-3 py-2">
          <CheckCircle2 size={18} />
          Connected as <span className="font-mono font-medium">{phone}</span>
        </div>
      )}

      {error && (
        <div className="flex items-start gap-2 text-sm text-red-800 bg-red-50 rounded-lg px-3 py-2">
          <AlertCircle size={18} className="shrink-0 mt-0.5" />
          <span>{error}</span>
        </div>
      )}

      {(status === "qr" || status === "starting") && qrDataUrl && (
        <div className="flex flex-col items-center gap-2">
          <img
            src={qrDataUrl}
            alt="WhatsApp QR code"
            className="rounded-xl border border-white shadow-sm bg-white p-2 w-[280px] h-[280px]"
          />
          <p className="text-xs text-gray-500">QR refreshes automatically — scan within 60 seconds</p>
        </div>
      )}

      {status === "connecting" && (
        <div className="flex flex-col items-center gap-2 py-4">
          <Loader2 size={28} className="animate-spin text-emerald-600" />
          <p className="text-sm font-medium text-gray-800">Finishing link on your phone…</p>
          <p className="text-xs text-gray-500 text-center max-w-xs">
            After you scan, WhatsApp reconnects automatically. Keep this page open for a few seconds.
          </p>
        </div>
      )}

      {(starting || (status === "starting" && !qrDataUrl)) && (
        <div className="flex items-center justify-center gap-2 text-sm text-gray-600 py-6">
          <Loader2 size={18} className="animate-spin text-emerald-600" />
          Preparing QR code…
        </div>
      )}

      {!sessionId && !tenantId && !starting && (
        <button type="button" className="btn-secondary w-full" onClick={() => ensureStart()} disabled={disabled}>
          Start WhatsApp linking
        </button>
      )}

      {(sessionId || tenantId) &&
        status !== "connected" &&
        !qrDataUrl &&
        status !== "starting" &&
        status !== "connecting" && (
        <button
          type="button"
          className={clsx("btn-secondary w-full", disabled && "opacity-50")}
          onClick={() => {
            startRequestedRef.current = true;
            setStatus("idle");
            setQrDataUrl(null);
            setError(null);
            connectedRef.current = false;
            ensureStart();
          }}
          disabled={disabled}
        >
          Retry linking
        </button>
      )}
    </div>
  );
}
