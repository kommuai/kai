import clsx from "clsx";

/** Pixel-style support agent avatar; evolves with core level and specialization badges. */
export default function AgentSprite({
  level = 0,
  earnedBadges = [],
  agentJob = "customer_support",
  size = "md",
  className,
}: {
  level?: number;
  earnedBadges?: string[];
  agentJob?: string;
  size?: "sm" | "md" | "lg";
  className?: string;
}) {
  const isCeo = agentJob === "ceo";
  const px = size === "sm" ? 3 : size === "lg" ? 5 : 4;
  const w = 16 * px;
  const h = 20 * px;

  const skin = isCeo
    ? level >= 3
      ? "#fcd34d"
      : level >= 2
        ? "#e5e7eb"
        : level >= 1
          ? "#f3f4f6"
          : "#e2e8f0"
    : level >= 3
      ? "#34d399"
      : level >= 2
        ? "#7dd3fc"
        : level >= 1
          ? "#fde68a"
          : "#e2e8f0";
  const suit = isCeo
    ? level >= 3
      ? "#1e293b"
      : level >= 2
        ? "#334155"
        : level >= 1
          ? "#475569"
          : "#64748b"
    : level >= 3
      ? "#059669"
      : level >= 2
        ? "#0284c7"
        : level >= 1
          ? "#a78bfa"
          : "#94a3b8";
  const accent = isCeo ? "#f59e0b" : level >= 3 ? "#fbbf24" : level >= 2 ? "#38bdf8" : "#c4b5fd";

  const hasSales = earnedBadges.includes("deal_whisperer");
  const hasTech = earnedBadges.includes("bug_buster");
  const hasLogistics = earnedBadges.includes("parcel_pathfinder");

  return (
    <div
      className={clsx("relative inline-flex items-end justify-center select-none", className)}
      style={{ width: w + 16, height: h + 8 }}
      aria-hidden
    >
      {hasSales && (
        <span
          className="absolute -left-1 top-2 text-[10px] sm:text-xs bg-amber-100 border border-amber-300 rounded px-1"
          title="Deal Whisperer"
        >
          💼
        </span>
      )}
      {hasTech && (
        <span
          className="absolute -right-1 top-1 text-[10px] sm:text-xs bg-indigo-100 border border-indigo-300 rounded px-1"
          title="Bug Buster"
        >
          🔧
        </span>
      )}
      {hasLogistics && (
        <span
          className="absolute left-1/2 -translate-x-1/2 -top-1 text-[10px] sm:text-xs bg-sky-100 border border-sky-300 rounded px-1"
          title="Parcel Pathfinder"
        >
          📦
        </span>
      )}

      <svg width={w} height={h} viewBox="0 0 16 20" className="drop-shadow-sm" style={{ imageRendering: "pixelated" }}>
        {/* shadow */}
        <rect x="4" y="18" width="8" height="1" fill="#00000022" />
        {/* legs */}
        <rect x="5" y="15" width="2" height="3" fill={suit} />
        <rect x="9" y="15" width="2" height="3" fill={suit} />
        {/* body */}
        <rect x="4" y="9" width="8" height="6" fill={suit} />
        {/* arms */}
        <rect x="2" y="10" width="2" height="4" fill={skin} />
        <rect x="12" y="10" width="2" height="4" fill={skin} />
        {/* head */}
        <rect x="4" y="4" width="8" height="6" fill={skin} />
        {/* eyes */}
        <rect x="6" y="6" width="1" height="2" fill="#1e293b" />
        <rect x="9" y="6" width="1" height="2" fill="#1e293b" />
        {/* mouth */}
        {level === 0 && <rect x="7" y="9" width="2" height="1" fill="#64748b" />}
        {level === 1 && <rect x="6" y="9" width="4" height="1" fill="#64748b" />}
        {level >= 2 && <rect x="6" y="9" width="4" height="1" fill="#334155" />}
        {/* level 1 — confused */}
        {level === 1 && (
          <>
            <rect x="12" y="2" width="3" height="3" fill="#fef3c7" stroke="#f59e0b" strokeWidth="0.5" />
            <text x="12.2" y="4.5" fontSize="2.5" fill="#b45309">
              ?
            </text>
          </>
        )}
        {/* level 2 — headset */}
        {level >= 2 && (
          <>
            <rect x="3" y="5" width="10" height="1" fill={accent} />
            <rect x="2" y="6" width="2" height="3" fill={accent} />
            <rect x="12" y="6" width="2" height="3" fill={accent} />
          </>
        )}
        {/* level 3 — ranger cape + badge */}
        {level >= 3 && (
          <>
            <polygon points="2,10 4,9 4,14 2,15" fill="#10b981" />
            <polygon points="14,10 12,9 12,14 14,15" fill="#10b981" />
            <rect x="7" y="2" width="2" height="2" fill={accent} />
          </>
        )}
      </svg>
    </div>
  );
}
