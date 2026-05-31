import clsx from "clsx";
import ShadouMark from "./ShadouMark";

interface LogoProps {
  size?: "sm" | "md" | "lg";
  className?: string;
  /** Hide "Shadou Studio" wordmark — mark only */
  markOnly?: boolean;
}

const markSize = {
  sm: "sm" as const,
  md: "md" as const,
  lg: "lg" as const,
};

const textSize = {
  sm: "text-base",
  md: "text-xl",
  lg: "text-3xl",
};

export default function Logo({ size = "md", className, markOnly = false }: LogoProps) {
  return (
    <div className={clsx("flex items-center gap-2.5 select-none", className)}>
      <ShadouMark size={markSize[size]} className="shrink-0" />
      {!markOnly && (
        <span className={clsx("font-bold tracking-tight text-gray-900 leading-none", textSize[size])}>
          Shadou <span className="text-brand-600">Studio</span>
        </span>
      )}
    </div>
  );
}
