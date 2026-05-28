import clsx from "clsx";

interface Props {
  diff: string;
  filename: string;
}

export default function FileDiffViewer({ diff, filename }: Props) {
  if (!diff.trim()) {
    return (
      <div className="text-xs text-gray-400 italic px-2 py-1">No changes detected.</div>
    );
  }

  const lines = diff.split("\n");

  return (
    <div className="rounded-xl overflow-hidden border border-gray-200 text-xs font-mono">
      <div className="bg-gray-100 border-b border-gray-200 px-3 py-1.5 text-gray-600 flex items-center gap-2">
        <span className="text-gray-400">📄</span>
        <span className="font-semibold">{filename}</span>
      </div>
      <div className="overflow-x-auto max-h-56 overflow-y-auto">
        <table className="w-full border-collapse">
          <tbody>
            {lines.map((line, i) => {
              const isAdd = line.startsWith("+") && !line.startsWith("+++");
              const isRemove = line.startsWith("-") && !line.startsWith("---");
              const isHeader = line.startsWith("@@");
              const isMeta = line.startsWith("---") || line.startsWith("+++");
              return (
                <tr
                  key={i}
                  className={clsx(
                    isAdd && "bg-emerald-50",
                    isRemove && "bg-red-50",
                    isHeader && "bg-blue-50",
                  )}
                >
                  <td
                    className={clsx(
                      "select-none px-2 py-0.5 border-r border-gray-100 w-4 text-right",
                      isAdd ? "text-emerald-600" : isRemove ? "text-red-500" : "text-gray-300",
                    )}
                  >
                    {isAdd ? "+" : isRemove ? "−" : isHeader || isMeta ? "~" : ""}
                  </td>
                  <td
                    className={clsx(
                      "px-3 py-0.5 whitespace-pre",
                      isAdd && "text-emerald-800",
                      isRemove && "text-red-700 line-through decoration-red-300",
                      isHeader && "text-blue-600 font-semibold",
                      isMeta && "text-gray-400",
                      !isAdd && !isRemove && !isHeader && !isMeta && "text-gray-600",
                    )}
                  >
                    {line.startsWith("+") || line.startsWith("-") ? line.slice(1) : line}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
