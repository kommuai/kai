import { useMemo, useState } from "react";
import { format, parseISO } from "date-fns";
import clsx from "clsx";

export interface DailyUsagePoint {
  date: string;
  total_tokens: number;
  cost_usd: number;
  request_count: number;
}

type Metric = "tokens" | "cost";

function formatUsd(n: number) {
  if (n <= 0) return "$0";
  if (n < 0.01) return "< $0.01";
  return `$${n.toFixed(n >= 1 ? 2 : 4)}`;
}

function formatTokens(n: number) {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1000) return `${(n / 1000).toFixed(1)}k`;
  return String(n);
}

export default function UsageDailyChart({ daily }: { daily: DailyUsagePoint[] }) {
  const [metric, setMetric] = useState<Metric>("tokens");
  const [hoverIdx, setHoverIdx] = useState<number | null>(null);

  const { values, maxVal, labels } = useMemo(() => {
    const vals = daily.map((d) => (metric === "tokens" ? d.total_tokens : d.cost_usd));
    const max = Math.max(...vals, metric === "cost" ? 0.0001 : 1);
    const lbls = daily.map((d) => format(parseISO(d.date), "MMM d"));
    return { values: vals, maxVal: max, labels: lbls };
  }, [daily, metric]);

  const chartW = 640;
  const chartH = 160;
  const padX = 8;
  const padY = 12;
  const innerW = chartW - padX * 2;
  const innerH = chartH - padY * 2;
  const n = Math.max(values.length, 1);
  const step = innerW / n;

  const points = values.map((v, i) => {
    const x = padX + step * i + step / 2;
    const y = padY + innerH - (v / maxVal) * innerH;
    return { x, y, v, i };
  });

  const linePath =
    points.length > 0
      ? points.map((p, idx) => `${idx === 0 ? "M" : "L"} ${p.x.toFixed(1)} ${p.y.toFixed(1)}`).join(" ")
      : "";

  const areaPath =
    points.length > 0
      ? `${linePath} L ${points[points.length - 1].x.toFixed(1)} ${(padY + innerH).toFixed(1)} L ${points[0].x.toFixed(1)} ${(padY + innerH).toFixed(1)} Z`
      : "";

  const hovered = hoverIdx != null ? daily[hoverIdx] : null;

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex rounded-lg border border-gray-200 p-0.5 text-xs">
          <button
            type="button"
            onClick={() => setMetric("tokens")}
            className={clsx(
              "px-3 py-1 rounded-md font-medium transition-colors",
              metric === "tokens" ? "bg-brand-600 text-white" : "text-gray-600 hover:bg-gray-50",
            )}
          >
            Tokens
          </button>
          <button
            type="button"
            onClick={() => setMetric("cost")}
            className={clsx(
              "px-3 py-1 rounded-md font-medium transition-colors",
              metric === "cost" ? "bg-brand-600 text-white" : "text-gray-600 hover:bg-gray-50",
            )}
          >
            Spend
          </button>
        </div>
        {hovered && (
          <div className="text-xs text-gray-600 tabular-nums">
            <span className="font-medium text-gray-900">
              {format(parseISO(hovered.date), "EEE, MMM d")}
            </span>
            {" · "}
            {formatTokens(hovered.total_tokens)} tokens
            {" · "}
            {formatUsd(hovered.cost_usd)}
            {hovered.request_count > 0 && ` · ${hovered.request_count} calls`}
          </div>
        )}
      </div>

      <div className="relative w-full overflow-x-auto">
        <svg
          viewBox={`0 0 ${chartW} ${chartH + 24}`}
          className="w-full min-w-[320px] h-auto"
          role="img"
          aria-label="Daily DeepSeek usage over the last 14 days"
        >
          <defs>
            <linearGradient id="usageArea" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="rgb(99 102 241)" stopOpacity="0.35" />
              <stop offset="100%" stopColor="rgb(99 102 241)" stopOpacity="0.02" />
            </linearGradient>
          </defs>
          {areaPath && <path d={areaPath} fill="url(#usageArea)" />}
          {linePath && (
            <path
              d={linePath}
              fill="none"
              stroke="rgb(79 70 229)"
              strokeWidth="2"
              strokeLinejoin="round"
              strokeLinecap="round"
            />
          )}
          {points.map((p) => (
            <circle
              key={p.i}
              cx={p.x}
              cy={p.y}
              r={hoverIdx === p.i ? 5 : 3}
              fill={hoverIdx === p.i ? "rgb(67 56 202)" : "rgb(99 102 241)"}
              className="cursor-pointer"
              onMouseEnter={() => setHoverIdx(p.i)}
              onMouseLeave={() => setHoverIdx(null)}
            />
          ))}
          {labels.map((label, i) => {
            const show = i === 0 || i === labels.length - 1 || i % 2 === 0;
            if (!show) return null;
            const x = padX + step * i + step / 2;
            return (
              <text
                key={label + i}
                x={x}
                y={chartH + 18}
                textAnchor="middle"
                className="fill-gray-400 text-[10px]"
              >
                {label}
              </text>
            );
          })}
        </svg>
      </div>
    </div>
  );
}
