import { useQuery } from "@tanstack/react-query";
import { AlertTriangle, WifiOff, Radio } from "lucide-react";
import { tenantsApi } from "../lib/api";

export default function WhatsAppWorkerBanner() {
  const { data } = useQuery({
    queryKey: ["whatsapp-worker"],
    queryFn: () => tenantsApi.whatsappWorker(),
    refetchInterval: 20_000,
  });

  if (!data) return null;

  const { bridge_reachable, live_tenant_count, tenants, detail } = data;
  const configuredWorkers = (tenants || []).filter(
    (t) => t.state && t.state !== "paused_linking",
  );
  const needsAttention =
    !bridge_reachable ||
    (configuredWorkers.length > 0 && (live_tenant_count ?? 0) < configuredWorkers.length);

  if (!needsAttention && bridge_reachable) return null;

  if (!bridge_reachable) {
    return (
      <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 flex items-start gap-3 text-sm text-red-900">
        <WifiOff size={18} className="shrink-0 mt-0.5" />
        <div>
          <p className="font-medium">WhatsApp bridge is not running</p>
          <p className="text-red-800/90 mt-1 text-xs">
            {detail ||
              "Start it with: systemctl --user start kai-whatsapp-bridge.service (see studio/deploy/systemd-user/)."}
          </p>
        </div>
      </div>
    );
  }

  const stale = configuredWorkers.filter((t) => t.state !== "connected");
  if (stale.length === 0) return null;

  return (
    <div className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 flex items-start gap-3 text-sm text-amber-950">
      <AlertTriangle size={18} className="shrink-0 mt-0.5" />
      <div>
        <p className="font-medium flex items-center gap-2">
          <Radio size={14} className="text-amber-600" />
          WhatsApp linked but not live ({stale.length} agent{stale.length === 1 ? "" : "s"})
        </p>
        <ul className="mt-1.5 text-xs text-amber-900/90 list-disc list-inside">
          {stale.map((t) => (
            <li key={t.slug}>
              {t.slug}: {t.state}
              {t.error ? ` — ${t.error}` : ""}
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
