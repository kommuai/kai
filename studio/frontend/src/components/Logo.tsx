import { Zap } from "lucide-react";
import clsx from "clsx";

interface LogoProps {
  size?: "sm" | "md" | "lg";
  className?: string;
}

const sizes = {
  sm: { icon: 16, text: "text-base" },
  md: { icon: 22, text: "text-xl" },
  lg: { icon: 32, text: "text-3xl" },
};

export default function Logo({ size = "md", className }: LogoProps) {
  const s = sizes[size];
  return (
    <div className={clsx("flex items-center gap-2 select-none", className)}>
      <div className="flex items-center justify-center rounded-xl bg-gradient-to-br from-brand-500 to-brand-700 p-1.5 shadow-sm">
        <Zap size={s.icon} className="text-white" fill="currentColor" />
      </div>
      <span className={clsx("font-bold tracking-tight text-gray-900", s.text)}>
        Kai <span className="text-brand-600">Studio</span>
      </span>
    </div>
  );
}
