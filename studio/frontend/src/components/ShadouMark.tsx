import clsx from "clsx";

const SIZES = {
  xs: "h-5 w-5",
  sm: "h-7 w-7",
  md: "h-9 w-9",
  lg: "h-12 w-12",
  xl: "h-16 w-16",
  "2xl": "h-20 w-20",
} as const;

/** Icon-only 影 mark — favicon / avatars / compact UI. */
export default function ShadouMark({
  size = "md",
  className,
  alt = "Shadou",
}: {
  size?: keyof typeof SIZES;
  className?: string;
  alt?: string;
}) {
  return (
    <img
      src="/brand/shadou-logo.png"
      alt={alt}
      className={clsx("block object-contain object-center select-none", SIZES[size], className)}
      draggable={false}
    />
  );
}
