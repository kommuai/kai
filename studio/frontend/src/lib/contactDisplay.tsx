/** Name and phone on one line: Handle · +60123456789 */
export function correspondentInlineLabel(
  displayName: string | null | undefined,
  phone: string | null | undefined,
  userId: string,
): string {
  const name = (displayName || "").trim() || userId;
  const num = (phone || "").trim();
  if (num && num !== name) {
    return `${name} · ${num}`;
  }
  return name;
}

type CorrespondentHeadingProps = {
  displayName: string | null | undefined;
  phone: string | null | undefined;
  userId: string;
  className?: string;
};

/** Inbox / thread title with muted phone beside the WhatsApp handle. */
export function CorrespondentHeading({
  displayName,
  phone,
  userId,
  className = "",
}: CorrespondentHeadingProps) {
  const name = (displayName || "").trim() || userId;
  const num = (phone || "").trim();
  if (num && num !== name) {
    return (
      <span className={`truncate ${className}`.trim()}>
        <span className="font-semibold text-gray-900">{name}</span>
        <span className="font-normal text-gray-500"> · {num}</span>
      </span>
    );
  }
  return <span className={`truncate font-semibold text-gray-900 ${className}`.trim()}>{name}</span>;
}
