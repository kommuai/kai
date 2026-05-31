import clsx from "clsx";

const LEVEL_LABELS: Record<number, string> = {
  0: "Unranked",
  1: "Confused Intern",
  2: "Helpdesk Rookie",
  3: "Certified Chat Ranger",
};

const LEVEL_EMOJI: Record<number, string> = {
  0: "🌱",
  1: "🐣",
  2: "🎧",
  3: "🛡️",
};

export function levelLabel(level: number, title?: string) {
  if (title) return title;
  return LEVEL_LABELS[level] ?? `Level ${level}`;
}

export function levelEmoji(level: number, emoji?: string) {
  if (emoji) return emoji;
  return LEVEL_EMOJI[level] ?? "⭐";
}

export default function LevelBadge({
  level,
  title,
  emoji,
  progress,
  size = "md",
  className,
}: {
  level: number;
  title?: string;
  emoji?: string;
  progress?: number;
  size?: "sm" | "md";
  className?: string;
}) {
  const em = levelEmoji(level, emoji);
  const label = levelLabel(level, title);
  const pct = progress != null ? Math.round(progress * 100) : null;

  return (
    <div className={clsx("inline-flex flex-col gap-1", className)}>
      <span
        className={clsx(
          "inline-flex items-center gap-1.5 rounded-full font-semibold bg-gradient-to-r from-violet-100 to-indigo-100 text-violet-900 border border-violet-200/80",
          size === "sm" ? "px-2 py-0.5 text-[10px]" : "px-2.5 py-1 text-xs",
        )}
      >
        <span aria-hidden>{em}</span>
        <span>
          {level > 0 ? `Lv.${level}` : "Lv.0"} · {label}
        </span>
      </span>
      {pct != null && level < 3 && (
        <div className="h-1.5 w-full min-w-[80px] rounded-full bg-gray-200 overflow-hidden">
          <div
            className="h-full rounded-full bg-gradient-to-r from-brand-500 to-violet-500 transition-all duration-500"
            style={{ width: `${Math.min(100, pct)}%` }}
          />
        </div>
      )}
    </div>
  );
}
