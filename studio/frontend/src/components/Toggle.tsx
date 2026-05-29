import clsx from "clsx";

export interface ToggleProps {
  checked: boolean;
  onChange: (checked: boolean) => void;
  disabled?: boolean;
  /** Accessible name when no visible label is associated */
  "aria-label"?: string;
  className?: string;
}

/** Accessible on/off switch (replaces checkboxes for boolean settings). */
export default function Toggle({
  checked,
  onChange,
  disabled = false,
  "aria-label": ariaLabel,
  className,
}: ToggleProps) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      aria-label={ariaLabel}
      disabled={disabled}
      onClick={() => onChange(!checked)}
      className={clsx(
        "relative inline-flex h-6 w-11 shrink-0 items-center rounded-full border transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 focus-visible:ring-offset-2",
        checked ? "border-brand-600 bg-brand-600" : "border-gray-300 bg-gray-200",
        disabled ? "cursor-not-allowed opacity-50" : "cursor-pointer",
        className,
      )}
    >
      <span
        aria-hidden
        className={clsx(
          "pointer-events-none inline-block h-5 w-5 rounded-full bg-white shadow-sm transition-transform",
          checked ? "translate-x-[1.375rem]" : "translate-x-0.5",
        )}
      />
    </button>
  );
}
