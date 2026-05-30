import { useEffect, useRef, useState } from "react";
import Editor from "@monaco-editor/react";

interface Props {
  language: string;
  value: string;
  onChange: (value: string) => void;
  /** Remount when tab changes so layout + value stay in sync. */
  editorKey: string;
}

export default function ConfigMonacoEditor({ language, value, onChange, editorKey }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [height, setHeight] = useState(360);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;

    const measure = () => {
      const next = Math.floor(el.getBoundingClientRect().height);
      if (next > 0) setHeight(next);
    };

    measure();
    const ro = new ResizeObserver(measure);
    ro.observe(el);
    window.addEventListener("resize", measure);
    return () => {
      ro.disconnect();
      window.removeEventListener("resize", measure);
    };
  }, [editorKey]);

  return (
    <div ref={containerRef} className="flex-1 min-h-[280px] w-full">
      <Editor
        key={editorKey}
        height={height}
        language={language}
        value={value}
        onChange={(v) => onChange(v ?? "")}
        theme="vs"
        options={{
          fontSize: 13,
          lineHeight: 22,
          fontFamily: "'JetBrains Mono', 'Fira Code', monospace",
          fontLigatures: true,
          minimap: { enabled: false },
          scrollBeyondLastLine: false,
          wordWrap: "on",
          renderLineHighlight: "gutter",
          smoothScrolling: true,
          padding: { top: 16, bottom: 16 },
          overviewRulerLanes: 0,
          folding: true,
          lineNumbers: typeof window !== "undefined" && window.innerWidth < 640 ? "off" : "on",
          tabSize: 2,
          automaticLayout: true,
        }}
      />
    </div>
  );
}
