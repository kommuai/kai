import clsx from "clsx";
import { Radio, WifiOff, AlertTriangle, Circle } from "lucide-react";

export type WhatsAppDelivery =
  | "live"
  | "configured_only"
  | "bridge_offline"
  | "worker_disabled"
  | "not_configured"
  | "needs_config";

export interface WhatsAppChannelInfo {
  enabled?: boolean;
  phone?: string | null;
  auth_present?: boolean;
  configured?: boolean;
  worker_live?: boolean;
  worker_state?: string | null;
  delivery?: WhatsAppDelivery;
}

const LABELS: Record<WhatsAppDelivery, string> = {
  live: "WhatsApp live",
  configured_only: "Linked — worker connecting",
  bridge_offline: "Bridge offline",
  worker_disabled: "Worker disabled",
  not_configured: "WhatsApp not set up",
  needs_config: "Credentials need workspace sync",
};

const STYLES: Record<WhatsAppDelivery, string> = {
  live: "bg-emerald-100 text-emerald-800 border-emerald-200",
  configured_only: "bg-amber-100 text-amber-900 border-amber-200",
  bridge_offline: "bg-red-100 text-red-800 border-red-200",
  worker_disabled: "bg-gray-100 text-gray-700 border-gray-200",
  not_configured: "bg-gray-100 text-gray-500 border-gray-200",
  needs_config: "bg-amber-50 text-amber-800 border-amber-200",
};

function Icon({ delivery }: { delivery: WhatsAppDelivery }) {
  const cls = "shrink-0";
  if (delivery === "live") return <Radio size={12} className={cls} />;
  if (delivery === "bridge_offline") return <WifiOff size={12} className={cls} />;
  if (delivery === "configured_only" || delivery === "needs_config")
    return <AlertTriangle size={12} className={cls} />;
  return <Circle size={12} className={cls} />;
}

export default function WhatsAppDeliveryBadge({
  wa,
  size = "sm",
}: {
  wa?: WhatsAppChannelInfo | null;
  size?: "sm" | "xs";
}) {
  if (!wa) return null;
  const delivery = (wa.delivery ||
    (wa.worker_live ? "live" : wa.configured ? "configured_only" : wa.auth_present ? "needs_config" : "not_configured")) as WhatsAppDelivery;
  if (delivery === "not_configured") return null;
  const label = LABELS[delivery] || delivery;

  return (
    <span
      className={clsx(
        "inline-flex items-center gap-1 rounded-full border font-medium",
        STYLES[delivery] || STYLES.not_configured,
        size === "xs" ? "px-1.5 py-0.5 text-[10px]" : "px-2 py-0.5 text-xs",
      )}
      title={wa.phone ? `Number: ${wa.phone}` : undefined}
    >
      <Icon delivery={delivery} />
      {label}
    </span>
  );
}
