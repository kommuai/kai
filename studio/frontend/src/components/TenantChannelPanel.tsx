import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { CheckCircle2, MessageCircle, AlertCircle, Radio, WifiOff } from "lucide-react";
import { tenantsApi } from "../lib/api";
import WhatsAppBaileysLink from "./WhatsAppBaileysLink";
import WhatsAppDeliveryBadge from "./WhatsAppDeliveryBadge";

interface Props {
  tenantId: string;
}

export default function TenantChannelPanel({ tenantId }: Props) {
  const qc = useQueryClient();
  const [relink, setRelink] = useState(false);

  const { data, isLoading, refetch } = useQuery({
    queryKey: ["tenant-channels", tenantId],
    queryFn: () => tenantsApi.channels(tenantId),
    refetchInterval: 15_000,
  });

  const wa = data?.whatsapp_baileys;
  const configured = wa?.configured;
  const phone = wa?.phone;
  const live = wa?.delivery === "live" || wa?.worker_live;

  if (isLoading) {
    return (
      <div className="rounded-xl border border-gray-200 bg-gray-50/80 px-4 py-3 text-sm text-gray-500">
        Checking channel status…
      </div>
    );
  }

  if (live && !relink) {
    return (
      <div className="rounded-xl border border-emerald-200 bg-emerald-50/50 px-4 py-3 space-y-2">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-center gap-2 text-sm text-emerald-900 min-w-0">
            <Radio size={18} className="text-emerald-600 shrink-0" />
            <div>
              <p className="font-medium">WhatsApp live</p>
              <p className="text-xs text-emerald-800/80 mt-0.5">
                Incoming messages are handled by the AI agent and appear in Inbox.
              </p>
              {phone && <p className="text-xs font-mono text-emerald-800/90 mt-1">{phone}</p>}
            </div>
          </div>
          <button type="button" className="btn-secondary btn-sm shrink-0" onClick={() => setRelink(true)}>
            Re-link
          </button>
        </div>
        <WhatsAppDeliveryBadge wa={wa} />
      </div>
    );
  }

  if (configured && !relink) {
    return (
      <div className="rounded-xl border border-emerald-200 bg-emerald-50/40 px-4 py-3 space-y-3">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
          <div className="flex items-start gap-2 text-sm text-emerald-900 min-w-0">
            <CheckCircle2 size={18} className="text-emerald-600 shrink-0 mt-0.5" />
            <div>
              <p className="font-medium">WhatsApp linked in Shadou Studio</p>
              {phone && <p className="text-xs font-mono text-emerald-800/80 mt-0.5">{phone}</p>}
              <div className="mt-2">
                <WhatsAppDeliveryBadge wa={wa} />
              </div>
            </div>
          </div>
          <button type="button" className="btn-secondary btn-sm shrink-0" onClick={() => setRelink(true)}>
            Re-link
          </button>
        </div>
        {wa?.delivery === "bridge_offline" && (
          <div className="flex items-start gap-2 text-xs text-red-800 bg-red-50 rounded-lg px-3 py-2 border border-red-100">
            <WifiOff size={14} className="shrink-0 mt-0.5" />
            <p>
              Credentials are saved but the message worker is not running. Start it with{" "}
              <code className="font-mono text-[11px]">systemctl --user start shadou-whatsapp-bridge.service</code>
            </p>
          </div>
        )}
        {wa?.delivery === "configured_only" && data?.bridge_reachable && (
          <p className="text-xs text-amber-800 bg-amber-50 rounded-lg px-3 py-2 border border-amber-100">
            Worker state: <span className="font-mono">{wa.worker_state || "starting"}</span>
            {wa.worker_error ? ` — ${wa.worker_error}` : ""}. Usually connects within 30 seconds.
          </p>
        )}
      </div>
    );
  }

  if (wa?.auth_present && !configured && !relink) {
    return (
      <div className="rounded-xl border border-amber-200 bg-amber-50/60 px-4 py-3 space-y-2">
        <div className="flex items-start gap-2 text-sm text-amber-900">
          <AlertCircle size={18} className="shrink-0 mt-0.5" />
          <p>
            WhatsApp credentials are saved but <strong>workspace.yaml</strong> was not set to use them
            (often after document bootstrap). Refresh this page — settings should auto-repair. If not, use
            Re-link below.
          </p>
        </div>
        <button
          type="button"
          className="btn-secondary btn-sm"
          onClick={() => {
            refetch();
            qc.invalidateQueries({ queryKey: ["file", tenantId, "workspace"] });
          }}
        >
          Refresh status
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2 text-sm text-gray-700">
        <MessageCircle size={16} className="text-emerald-600" />
        <span className="font-medium">Connect WhatsApp for this agent</span>
      </div>
      <WhatsAppBaileysLink
        tenantId={tenantId}
        onConnected={() => {
          setRelink(false);
          qc.invalidateQueries({ queryKey: ["tenant-channels", tenantId] });
          qc.invalidateQueries({ queryKey: ["whatsapp-worker"] });
          qc.invalidateQueries({ queryKey: ["file", tenantId, "workspace"] });
        }}
      />
    </div>
  );
}
