import { useState, useRef, useEffect, useCallback } from "react";
import {
  Sparkles,
  Send,
  Loader2,
  CheckCircle2,
  XCircle,
  RefreshCw,
  ChevronDown,
  ChevronUp,
  Info,
} from "lucide-react";
import clsx from "clsx";
import toast from "react-hot-toast";
import { useQueryClient } from "@tanstack/react-query";
import { aiAssistApi, type AiAssistPatch } from "../lib/api";
import FileDiffViewer from "./FileDiffViewer";

interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  patches?: AiAssistPatch[];
  patchSummary?: string;
  patchState?: "pending" | "applied" | "rejected";
  isStreaming?: boolean;
}

const FILE_LABELS: Record<string, string> = {
  workspace: "workspace.yaml",
  system_prompt: "system_prompt.md",
  faq: "knowledge/master_faq.md",
};

function patchLabel(patch: AiAssistPatch): string {
  if (patch.intent_id) {
    return `knowledge/master_faq.md → ${patch.intent_id}`;
  }
  if (patch.file.startsWith("plugin:")) {
    const name = patch.file.slice("plugin:".length);
    return `tools/plugins/${name}/main.py`;
  }
  return FILE_LABELS[patch.file] ?? patch.path;
}

/** Hide raw kai-patch JSON from the chat bubble; diff card shows changes. */
function assistantDisplayContent(content: string): string {
  const stripped = content.replace(/```kai-patch[\s\S]*?```/g, "").trim();
  return stripped || content;
}

const STARTER_SUGGESTIONS = [
  "Help me set up my AI support agent's personality",
  "I want to update the FAQ knowledge base",
  "Change the escalation rules in the system prompt",
  "Add new office hours to workspace config",
  "Show me what skills/plugins are currently active",
  "Disable a skill I don't need",
  "Add a new custom plugin skill",
];

export default function AiAssistPanel({ tenantId }: { tenantId: string }) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [expandedDiffs, setExpandedDiffs] = useState<Set<number>>(new Set());
  const scrollRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const qc = useQueryClient();

  const scrollToBottom = useCallback(() => {
    setTimeout(() => {
      scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
    }, 50);
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, scrollToBottom]);

  async function sendMessage(userText?: string) {
    const text = (userText ?? input).trim();
    if (!text || isLoading) return;

    setInput("");
    const userMsg: ChatMessage = { role: "user", content: text };
    setMessages((prev) => [...prev, userMsg]);
    setIsLoading(true);

    const historyForApi = [...messages, userMsg].map(({ role, content }) => ({ role, content }));

    const assistantMsg: ChatMessage = {
      role: "assistant",
      content: "",
      isStreaming: true,
    };
    setMessages((prev) => [...prev, assistantMsg]);

    try {
      const response = await aiAssistApi.chat(tenantId, historyForApi);
      if (!response.ok || !response.body) {
        let detail = "";
        try {
          const t = await response.text();
          detail = t?.slice(0, 400) || "";
        } catch {}
        throw new Error(detail || `HTTP ${response.status}`);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      let fullContent = "";
      let patches: AiAssistPatch[] = [];
      let patchSummary = "";

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });

        const lines = buffer.split("\n");
        buffer = lines.pop() ?? "";

        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          const payload = line.slice(6).trim();
          if (!payload) continue;
          try {
            const evt = JSON.parse(payload);
            if (evt.type === "delta") {
              fullContent += evt.content;
              setMessages((prev) => {
                const updated = [...prev];
                updated[updated.length - 1] = {
                  ...updated[updated.length - 1],
                  content: fullContent,
                };
                return updated;
              });
            } else if (evt.type === "done") {
              patches = evt.patches ?? [];
              patchSummary = evt.summary ?? "";
            } else if (evt.type === "error") {
              throw new Error(evt.content);
            }
          } catch {
            // malformed SSE line
          }
        }
      }

      setMessages((prev) => {
        const updated = [...prev];
        updated[updated.length - 1] = {
          role: "assistant",
          content: fullContent,
          patches: patches.length ? patches : undefined,
          patchSummary: patchSummary || undefined,
          patchState: patches.length ? "pending" : undefined,
          isStreaming: false,
        };
        return updated;
      });
    } catch (err: any) {
      setMessages((prev) => {
        const updated = [...prev];
        updated[updated.length - 1] = {
          role: "assistant",
          content:
            "Sorry — AI Assist couldn't reach the server. Please try again. If it keeps happening, check you are logged in and the backend is running.",
          isStreaming: false,
        };
        return updated;
      });
      toast.error(err?.message ?? "AI Assist request failed");
    } finally {
      setIsLoading(false);
      inputRef.current?.focus();
    }
  }

  async function applyPatches(msgIdx: number) {
    const fullHistory = messages.map(({ role, content }) => ({ role, content }));
    try {
      const result = await aiAssistApi.applyPatches(tenantId, fullHistory);
      if (!result.ok) {
        toast.error(result.summary || "Failed to apply changes");
        return;
      }
      setMessages((prev) => {
        const updated = [...prev];
        updated[msgIdx] = { ...updated[msgIdx], patchState: "applied" };
        return updated;
      });
      // Invalidate file queries so the editor reflects the changes.
      for (const a of result.applied) {
        if (!a.file.startsWith("plugin:")) {
          qc.invalidateQueries({ queryKey: ["file", tenantId, a.file] });
        }
        // Invalidate capabilities so the Skills panel refreshes after plugin/workspace changes.
        qc.invalidateQueries({ queryKey: ["tenant-capabilities", tenantId] });
      }
      toast.success(`Changes applied: ${result.summary || "done"}`);
    } catch (err: any) {
      toast.error(err?.message ?? "Apply failed");
    }
  }

  function rejectPatches(msgIdx: number) {
    setMessages((prev) => {
      const updated = [...prev];
      updated[msgIdx] = { ...updated[msgIdx], patchState: "rejected" };
      return updated;
    });
  }

  function toggleDiff(msgIdx: number) {
    setExpandedDiffs((prev) => {
      const s = new Set(prev);
      s.has(msgIdx) ? s.delete(msgIdx) : s.add(msgIdx);
      return s;
    });
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  }

  const isEmpty = messages.length === 0;

  return (
    <div className="studio-panel-fill h-full min-h-0">
      {/* ── Header banner ── */}
      <div className="shrink-0 px-3 sm:px-4 py-3 border-b border-purple-100 bg-gradient-to-r from-purple-50 to-indigo-50 flex flex-col gap-2 sm:flex-row sm:items-start sm:gap-3">
        <div className="flex items-start gap-3 min-w-0 flex-1">
          <div className="h-8 w-8 rounded-xl bg-purple-600 flex items-center justify-center flex-shrink-0">
            <Sparkles size={16} className="text-white" />
          </div>
          <div className="min-w-0">
            <p className="text-sm font-semibold text-purple-900">AI Config Assistant</p>
            <p className="text-xs text-purple-600 leading-snug mt-0.5">
              Chat to update your system prompt, knowledge base, workspace settings, or skills &amp; plugins — no code
              needed.
            </p>
          </div>
        </div>
        <div className="flex-shrink-0 self-start sm:self-auto">
          <div className="inline-flex items-center gap-1 bg-purple-100 rounded-full px-2 py-0.5 text-[10px] text-purple-700 font-medium">
            <Info size={10} />
            DeepSeek powered
          </div>
        </div>
      </div>

      {/* ── Chat messages ── */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto px-4 py-4 space-y-4">
        {isEmpty && (
          <div className="space-y-6 py-4">
            <div className="text-center">
              <div className="h-14 w-14 rounded-2xl bg-purple-100 flex items-center justify-center mx-auto mb-3">
                <Sparkles size={26} className="text-purple-600" />
              </div>
              <p className="text-sm font-semibold text-gray-800">What would you like to configure?</p>
              <p className="text-xs text-gray-500 mt-1 max-w-xs mx-auto">
                I'll guide you through updating your AI support agent's configuration, skills, and plugins — no technical knowledge needed.
              </p>
            </div>
            <div className="grid grid-cols-1 gap-2">
              {STARTER_SUGGESTIONS.map((s) => (
                <button
                  key={s}
                  onClick={() => sendMessage(s)}
                  className="text-left text-xs text-purple-800 bg-purple-50 hover:bg-purple-100 border border-purple-200 rounded-xl px-3 py-2.5 transition-colors"
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((msg, i) => {
          const isUser = msg.role === "user";
          return (
            <div key={i} className={clsx("flex gap-2", isUser ? "justify-end" : "justify-start")}>
              {!isUser && (
                <div className="h-7 w-7 rounded-xl bg-purple-600 flex items-center justify-center flex-shrink-0 mt-0.5">
                  <Sparkles size={13} className="text-white" />
                </div>
              )}
              <div className={clsx("max-w-[min(100%,20rem)] sm:max-w-[80%] space-y-2", isUser && "items-end flex flex-col")}>
                <div
                  className={clsx(
                    "rounded-2xl px-4 py-3 text-sm leading-relaxed whitespace-pre-wrap",
                    isUser
                      ? "bg-purple-600 text-white rounded-tr-sm"
                      : "bg-white border border-gray-200 text-gray-800 rounded-tl-sm shadow-sm",
                  )}
                >
                  {msg.role === "assistant" ? assistantDisplayContent(msg.content) : msg.content}
                  {msg.isStreaming && (
                    <span className="inline-block ml-1 w-1.5 h-4 bg-purple-400 rounded-sm animate-pulse align-bottom" />
                  )}
                </div>

                {/* ── Patch preview card ── */}
                {msg.patches && msg.patches.length > 0 && !msg.isStreaming && (
                  <div
                    className={clsx(
                      "w-full rounded-2xl border overflow-hidden shadow-sm",
                      msg.patchState === "applied"
                        ? "border-emerald-200 bg-emerald-50"
                        : msg.patchState === "rejected"
                          ? "border-gray-200 bg-gray-50 opacity-60"
                          : "border-amber-200 bg-amber-50",
                    )}
                  >
                    <div className="px-3 py-2 flex items-center justify-between gap-2">
                      <div className="flex items-center gap-2 text-xs font-semibold">
                        {msg.patchState === "applied" ? (
                          <CheckCircle2 size={14} className="text-emerald-600" />
                        ) : msg.patchState === "rejected" ? (
                          <XCircle size={14} className="text-gray-400" />
                        ) : (
                          <RefreshCw size={14} className="text-amber-600" />
                        )}
                        <span
                          className={clsx(
                            msg.patchState === "applied"
                              ? "text-emerald-700"
                              : msg.patchState === "rejected"
                                ? "text-gray-500"
                                : "text-amber-800",
                          )}
                        >
                          {msg.patchState === "applied"
                            ? "Changes applied"
                            : msg.patchState === "rejected"
                              ? "Changes dismissed"
                              : `${msg.patches.length} file${msg.patches.length > 1 ? "s" : ""} will be updated`}
                        </span>
                      </div>
                      <button
                        onClick={() => toggleDiff(i)}
                        className="text-xs text-gray-500 hover:text-gray-700 flex items-center gap-0.5"
                      >
                        {expandedDiffs.has(i) ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
                        {expandedDiffs.has(i) ? "Hide" : "Show"} diff
                      </button>
                    </div>

                    {expandedDiffs.has(i) && (
                      <div className="px-3 pb-3 space-y-2">
                        {msg.patches.map((p, pi) => (
                          <div key={pi}>
                            <p className="text-[10px] text-gray-500 font-mono mb-1 flex items-center gap-1">
                              {p.file.startsWith("plugin:") ? "🔧" : "📄"}
                              {patchLabel(p)}
                            </p>
                            <FileDiffViewer diff={p.diff} filename={patchLabel(p)} />
                          </div>
                        ))}
                        {msg.patchSummary && (
                          <p className="text-xs text-gray-500 mt-1 italic">{msg.patchSummary}</p>
                        )}
                      </div>
                    )}

                    {msg.patchState === "pending" && (
                      <div className="px-3 pb-3 flex gap-2">
                        <button
                          onClick={() => applyPatches(i)}
                          className="flex-1 btn-primary btn-sm text-xs"
                        >
                          <CheckCircle2 size={13} />
                          Apply changes
                        </button>
                        <button
                          onClick={() => rejectPatches(i)}
                          className="flex-1 btn-secondary btn-sm text-xs"
                        >
                          <XCircle size={13} />
                          Dismiss
                        </button>
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          );
        })}

        {isLoading && messages[messages.length - 1]?.role !== "assistant" && (
          <div className="flex gap-2 justify-start">
            <div className="h-7 w-7 rounded-xl bg-purple-600 flex items-center justify-center flex-shrink-0">
              <Loader2 size={13} className="text-white animate-spin" />
            </div>
            <div className="bg-white border border-gray-200 rounded-2xl rounded-tl-sm px-4 py-3">
              <div className="flex gap-1">
                <span className="h-1.5 w-1.5 bg-purple-300 rounded-full animate-bounce [animation-delay:0ms]" />
                <span className="h-1.5 w-1.5 bg-purple-300 rounded-full animate-bounce [animation-delay:150ms]" />
                <span className="h-1.5 w-1.5 bg-purple-300 rounded-full animate-bounce [animation-delay:300ms]" />
              </div>
            </div>
          </div>
        )}
      </div>

      {/* ── Scope notice ── */}
      <div className="flex-none px-4 pb-1">
        <p className="text-[10px] text-gray-400 text-center">
          Wiring (workspace.yaml), brain rules (system_prompt.md), truth (master_faq.md), and plugin scripts only.
        </p>
      </div>

      {/* ── Input bar ── */}
      <div className="shrink-0 px-3 sm:px-4 pb-3 sm:pb-4 pb-safe">
        <div className="flex items-end gap-2 bg-white rounded-2xl border border-gray-200 shadow-sm px-3 py-2 focus-within:border-purple-400 focus-within:ring-2 focus-within:ring-purple-100 transition-all">
          <textarea
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask me to update your config… (Enter to send, Shift+Enter for new line)"
            rows={1}
            style={{ resize: "none", minHeight: 36, maxHeight: 120, overflow: "auto" }}
            className="flex-1 text-sm text-gray-800 placeholder-gray-400 bg-transparent outline-none"
            disabled={isLoading}
          />
          <button
            onClick={() => sendMessage()}
            disabled={!input.trim() || isLoading}
            className={clsx(
              "h-8 w-8 rounded-xl flex items-center justify-center transition-all flex-shrink-0",
              input.trim() && !isLoading
                ? "bg-purple-600 hover:bg-purple-700 text-white"
                : "bg-gray-100 text-gray-300 cursor-not-allowed",
            )}
          >
            {isLoading ? (
              <Loader2 size={15} className="animate-spin" />
            ) : (
              <Send size={14} />
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
