import { useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  ArrowLeft,
  ArrowRight,
  Building2,
  CheckCircle2,
  FileUp,
  HeartHandshake,
  ShieldCheck,
  Smile,
  Sparkles,
  Zap,
  Briefcase,
  MessageCircle,
  Send,
  Cloud,
} from "lucide-react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import toast from "react-hot-toast";
import clsx from "clsx";
import {
  consumeBootstrapStream,
  onboardingApi,
  tenantsApi,
  type OnboardingDocument,
} from "../lib/api";
import { formatApiError } from "../lib/apiErrors";
import Spinner from "../components/Spinner";
import WhatsAppBaileysLink from "../components/WhatsAppBaileysLink";

type WizardStep = 1 | 2 | 3;

const WIZARD_STEPS: { n: WizardStep; label: string }[] = [
  { n: 1, label: "Business setup" },
  { n: 2, label: "Channel" },
  { n: 3, label: "Done" },
];

function WizardStepper({ step }: { step: WizardStep }) {
  return (
    <div
      className="flex w-full items-center justify-center gap-2 mb-4 text-xs text-gray-500 flex-wrap"
      aria-label="Creation progress"
    >
      {WIZARD_STEPS.map((s, i) => (
        <span key={s.n} className="inline-flex items-center gap-2">
          {i > 0 && <span className="text-gray-300">→</span>}
          <span
            className={clsx(
              "px-2 py-1 rounded-full whitespace-nowrap",
              step === s.n ? "bg-brand-100 text-brand-800 font-medium" : "bg-gray-100",
            )}
          >
            {s.n}. {s.label}
          </span>
        </span>
      ))}
    </div>
  );
}
type ChannelType = "none" | "telegram" | "whatsapp_cloud" | "whatsapp_baileys";

function slugify(s: string) {
  return s
    .toLowerCase()
    .replace(/[^a-z0-9\s-]/g, "")
    .trim()
    .replace(/\s+/g, "-")
    .replace(/-+/g, "-")
    .slice(0, 50);
}

export default function NewTenantPage() {
  const navigate = useNavigate();
  const qc = useQueryClient();

  const [personality, setPersonality] = useState<
    "friendly" | "professional" | "empathetic" | "direct" | "playful" | "premium"
  >("friendly");
  const [botName, setBotName] = useState("");
  const [companyName, setCompanyName] = useState("");
  const [productSummary, setProductSummary] = useState("");
  const [scopeCannotAnswer, setScopeCannotAnswer] = useState<string[]>([]);
  const [escalationRules, setEscalationRules] = useState<string[]>([]);
  const [fallbackBehavior, setFallbackBehavior] = useState<
    | "ask_one_question_then_escalate"
    | "escalate_if_unsure"
    | "say_not_confirmed_and_escalate"
    | "best_effort_hallucination_risk"
  >("escalate_if_unsure");

  const [onboardingSessionId, setOnboardingSessionId] = useState<string | null>(null);
  const onboardingSessionRef = useRef<string | null>(null);
  const onboardingSessionPromiseRef = useRef<Promise<string> | null>(null);
  const [uploadedDocs, setUploadedDocs] = useState<OnboardingDocument[]>([]);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [bootstrapActive, setBootstrapActive] = useState(false);
  const [bootstrapPercent, setBootstrapPercent] = useState(0);
  const [bootstrapMessage, setBootstrapMessage] = useState("");
  const [step, setStep] = useState<WizardStep>(1);
  const [channelType, setChannelType] = useState<ChannelType>("whatsapp_baileys");
  const [whatsappConnected, setWhatsappConnected] = useState(false);
  const [whatsappPhone, setWhatsappPhone] = useState<string | null>(null);
  const [createdTenant, setCreatedTenant] = useState<{ slug: string; display_name: string } | null>(null);

  const displayName = companyName.trim();
  const description = productSummary.trim();
  const slug = slugify(displayName);
  const slugValid = /^[a-z0-9][a-z0-9-]{1,48}[a-z0-9]$/.test(slug);

  const PERSONALITIES = [
    {
      id: "friendly" as const,
      label: "Friendly",
      icon: Smile,
      tip: "Warm and helpful, concise by default.",
    },
    {
      id: "professional" as const,
      label: "Professional",
      icon: Briefcase,
      tip: "Structured, calm, confirms key details.",
    },
    {
      id: "empathetic" as const,
      label: "Empathetic",
      icon: HeartHandshake,
      tip: "Reassuring tone, acknowledges frustration.",
    },
    {
      id: "direct" as const,
      label: "Direct",
      icon: Zap,
      tip: "Fastest path to resolution, minimal questions.",
    },
    {
      id: "playful" as const,
      label: "Playful",
      icon: Sparkles,
      tip: "Light and upbeat (avoids jokes when user is upset).",
    },
    {
      id: "premium" as const,
      label: "Premium",
      icon: ShieldCheck,
      tip: "Concierge tone: polished and proactive options.",
    },
  ];

  const CANNOT_ANSWER_OPTIONS = [
    "Unrelated general knowledge",
    "Anything not in knowledge base",
  ];

  const ESCALATION_OPTIONS = [
    "Customer requests a live agent",
    "Unsure or answer not confirmed in knowledge base",
    "Refund / payment / warranty dispute",
    "Technical troubleshooting reaches a dead end",
  ];

  const questionnairePayload = () => ({
    display_name: displayName,
    description,
    personality,
    bot_name: botName,
    company_name: companyName || displayName,
    product_summary: productSummary,
    scope_cannot_answer: scopeCannotAnswer,
    escalation_rules: escalationRules,
    fallback_behavior: fallbackBehavior,
  });

  const { mutate, isPending } = useMutation({
    mutationFn: async () => {
      const tenant = await tenantsApi.create({
        display_name: displayName,
        slug,
        description,
        personality,
        bot_name: botName,
        company_name: companyName || displayName,
        product_summary: productSummary,
        scope_cannot_answer: scopeCannotAnswer,
        escalation_rules: escalationRules,
        fallback_behavior: fallbackBehavior,
        onboarding_session_id: onboardingSessionRef.current ?? onboardingSessionId,
        channel_type: channelType,
      });

      if (uploadedDocs.length > 0) {
        setBootstrapActive(true);
        setBootstrapPercent(5);
        setBootstrapMessage("Creating workspace…");
        const res = await onboardingApi.bootstrap(tenant.id, questionnairePayload());
        await consumeBootstrapStream(res, (evt) => {
          if (evt.type === "progress") {
            setBootstrapPercent(evt.percent);
            setBootstrapMessage(evt.message);
          } else if (evt.type === "done") {
            setBootstrapPercent(100);
            setBootstrapMessage(evt.summary || "Configuration ready.");
          } else if (evt.type === "error") {
            throw new Error(evt.message);
          }
        });
      }
      return tenant;
    },
    onSuccess: (tenant) => {
      qc.invalidateQueries({ queryKey: ["tenants"] });
      toast.success(
        uploadedDocs.length > 0
          ? "Support agent created and configured from your documents!"
          : "Support agent created!",
      );
      setCreatedTenant({ slug: tenant.slug, display_name: tenant.display_name });
      setStep(3);
    },
    onError: (err: any) => {
      setBootstrapActive(false);
      toast.error(err?.message || err?.response?.data?.detail || "Failed to create agent");
    },
  });

  async function ensureOnboardingSession(): Promise<string> {
    if (onboardingSessionRef.current) return onboardingSessionRef.current;
    if (!onboardingSessionPromiseRef.current) {
      onboardingSessionPromiseRef.current = onboardingApi.createSession().then(({ session_id }) => {
        onboardingSessionRef.current = session_id;
        setOnboardingSessionId(session_id);
        return session_id;
      });
    }
    return onboardingSessionPromiseRef.current;
  }

  async function handleDocumentsSelected(fileList: FileList | null) {
    // Snapshot immediately — clearing the input (e.target.value = "") empties live FileList refs.
    const files = fileList?.length ? Array.from(fileList) : [];
    if (!files.length) return;
    setUploading(true);
    setUploadError(null);
    try {
      const sid = await ensureOnboardingSession();
      const docs = await onboardingApi.uploadDocuments(sid, files);
      setUploadedDocs(docs);
      if (docs.length === 0) {
        throw new Error("Upload completed but no files were saved. Try again or use a .txt / .md file.");
      }
      toast.success(
        docs.length === 1
          ? `Uploaded ${docs[0].name}`
          : `Uploaded ${docs.length} files (${docs.map((d) => d.name).join(", ")})`,
      );
    } catch (err: unknown) {
      const msg =
        err instanceof Error && err.message.trim()
          ? err.message
          : formatApiError(err, "Upload failed");
      setUploadError(msg);
      toast.error(msg);
    } finally {
      setUploading(false);
    }
  }

  async function goToChannelStep() {
    if (!slugValid) {
      toast.error("Company name must produce a valid slug (3–50 lowercase letters/numbers/hyphens).");
      return;
    }
    if (!companyName.trim()) {
      toast.error("Please enter a company name.");
      return;
    }
    setStep(2);
    if (channelType === "whatsapp_baileys") {
      await ensureOnboardingSession();
    }
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (step === 3) return;
    if (step === 1) {
      goToChannelStep();
      return;
    }
    if (channelType === "whatsapp_baileys" && !whatsappConnected) {
      toast.error("Scan the QR code to connect WhatsApp before creating the agent.");
      return;
    }
    mutate();
  }

  const busy = isPending || uploading || bootstrapActive;

  const CHANNEL_OPTIONS: {
    id: ChannelType;
    label: string;
    subtitle: string;
    icon: typeof MessageCircle;
    soon?: boolean;
  }[] = [
    {
      id: "whatsapp_baileys",
      label: "WhatsApp",
      subtitle: "Personal or Business — scan QR (Baileys)",
      icon: MessageCircle,
    },
    {
      id: "telegram",
      label: "Telegram",
      subtitle: "Bot channel — setup coming soon",
      icon: Send,
      soon: true,
    },
    {
      id: "whatsapp_cloud",
      label: "WhatsApp Cloud API",
      subtitle: "Meta Cloud API — setup coming soon",
      icon: Cloud,
      soon: true,
    },
  ];

  return (
    <div className="studio-page max-w-xl mx-auto animate-fade-in pb-6">
      <button onClick={() => navigate(-1)} className="btn-ghost mb-6 -ml-2 text-gray-500">
        <ArrowLeft size={16} />
        Back
      </button>

      <div className="flex items-start gap-3 sm:gap-4 mb-6 sm:mb-8">
        <div className="h-11 w-11 sm:h-12 sm:w-12 rounded-2xl bg-brand-50 flex items-center justify-center shrink-0">
          <Building2 size={24} className="text-brand-600" />
        </div>
        <div className="min-w-0">
          <h1 className="text-lg sm:text-xl font-bold text-gray-900">New Support Agent Creation</h1>
          <p className="text-sm text-gray-500">
            {step === 1
              ? "Fill what you know. You can refine later in Configuration."
              : step === 2
                ? "Choose how customers reach your AI support agent."
                : "Your support agent is ready. Open Configuration to review or adjust settings."}
          </p>
        </div>
      </div>

      <WizardStepper step={step} />

      <form onSubmit={handleSubmit} className="card p-4 sm:p-6 space-y-5">
        {step === 3 && createdTenant && (
          <div className="py-4 sm:py-6 text-center space-y-4">
            <div className="mx-auto h-14 w-14 rounded-2xl bg-emerald-50 flex items-center justify-center">
              <CheckCircle2 size={32} className="text-emerald-600" />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-gray-900">{createdTenant.display_name}</h2>
              <p className="text-sm text-gray-500 mt-1">
                Support agent created
                {uploadedDocs.length > 0 ? " and configured from your documents" : ""}.
              </p>
            </div>
            <button
              type="button"
              className="btn-primary btn-lg w-full"
              onClick={() => navigate(`/t/${createdTenant.slug}/configuration`)}
            >
              Open configuration
              <ArrowRight size={18} />
            </button>
          </div>
        )}

        {step === 2 && (
          <div className="space-y-4">
            <div>
              <label className="label">Customer channel</label>
              <p className="text-xs text-gray-500 mb-3">Pick how messages arrive. You can add more channels later.</p>
              <div className="grid grid-cols-1 gap-2">
                {CHANNEL_OPTIONS.map((ch) => {
                  const Icon = ch.icon;
                  const active = channelType === ch.id;
                  return (
                    <button
                      key={ch.id}
                      type="button"
                      disabled={busy}
                      onClick={async () => {
                        setChannelType(ch.id);
                        if (ch.id === "whatsapp_baileys") {
                          await ensureOnboardingSession();
                        }
                      }}
                      className={clsx(
                        "rounded-xl border px-4 py-3 flex items-start gap-3 text-left transition-all",
                        active
                          ? "border-emerald-300 bg-emerald-50/60 ring-1 ring-emerald-200"
                          : "border-gray-200 bg-white hover:bg-gray-50",
                      )}
                    >
                      <Icon size={20} className={active ? "text-emerald-600" : "text-gray-400"} />
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="text-sm font-medium text-gray-900">{ch.label}</span>
                          {ch.soon && (
                            <span className="text-[10px] uppercase tracking-wide text-gray-400 bg-gray-100 px-1.5 py-0.5 rounded">
                              Soon
                            </span>
                          )}
                        </div>
                        <p className="text-xs text-gray-500 mt-0.5">{ch.subtitle}</p>
                      </div>
                    </button>
                  );
                })}
              </div>
            </div>

            {channelType === "whatsapp_baileys" && (
              <WhatsAppBaileysLink
                sessionId={onboardingSessionId}
                onSessionNeeded={ensureOnboardingSession}
                onConnected={(phone) => {
                  setWhatsappConnected(true);
                  setWhatsappPhone(phone);
                }}
                disabled={busy}
              />
            )}

            {(channelType === "telegram" || channelType === "whatsapp_cloud") && (
              <p className="text-xs text-gray-500 bg-gray-50 rounded-lg px-3 py-2 border border-gray-100">
                This channel will be saved as your choice. Connection setup is coming in a future release.
              </p>
            )}
          </div>
        )}

        {step === 1 && (
          <>
        {/* Optional document upload */}
        <div className="rounded-xl border border-dashed border-gray-200 bg-gray-50/80 p-4 space-y-3">
          <div className="flex items-start gap-3">
            <div className="h-9 w-9 rounded-lg bg-brand-50 flex items-center justify-center shrink-0">
              <FileUp size={18} className="text-brand-600" />
            </div>
            <div className="min-w-0 flex-1">
              <p className="text-sm font-medium text-gray-900">Upload documents (optional)</p>
              <p className="text-xs text-gray-500 mt-0.5">
                Add FAQs, product sheets, or policies (.txt, .md, .pdf, .csv). We&apos;ll use AI to fill your system
                prompt, knowledge base, and skills when you create the agent.
              </p>
            </div>
          </div>
          <label
            className={clsx(
              "btn-secondary w-full cursor-pointer justify-center",
              (uploading || bootstrapActive) && "opacity-50 pointer-events-none",
            )}
          >
            {uploading ? <Spinner size="sm" /> : <FileUp size={16} />}
            {uploading ? "Uploading…" : "Choose files"}
            <input
              type="file"
              className="sr-only"
              multiple
              accept=".txt,.md,.markdown,.csv,.json,.yaml,.yml,.html,.htm,.pdf"
              disabled={busy}
              onChange={(e) => {
                handleDocumentsSelected(e.target.files);
                e.target.value = "";
              }}
            />
          </label>
          {uploadError && (
            <p className="text-xs text-red-700 bg-red-50 border border-red-100 rounded-lg px-2 py-1.5" role="alert">
              {uploadError}
            </p>
          )}
          {uploadedDocs.length > 0 ? (
            <div className="space-y-1.5">
              <p className="text-xs font-medium text-emerald-800">
                {uploadedDocs.length} file{uploadedDocs.length === 1 ? "" : "s"} ready — will configure the agent on
                create
              </p>
              <ul className="space-y-1">
                {uploadedDocs.map((d) => (
                  <li
                    key={d.name}
                    className="flex items-center justify-between text-xs text-gray-600 bg-white rounded-lg px-2 py-1.5 border border-emerald-100"
                  >
                    <span className="truncate font-mono">{d.name}</span>
                    <span className="text-gray-400 shrink-0 ml-2">{(d.size / 1024).toFixed(1)} KB</span>
                  </li>
                ))}
              </ul>
            </div>
          ) : (
            !uploading &&
            !uploadError && (
              <p className="text-xs text-gray-400">No files staged yet. Choose one or more files above.</p>
            )
          )}
        </div>

        {bootstrapActive && (
          <div className="rounded-xl border border-purple-100 bg-purple-50/60 p-4 space-y-2">
            <div className="flex items-center justify-between text-xs text-purple-800">
              <span className="font-medium">Setting up from your documents</span>
              <span>{bootstrapPercent}%</span>
            </div>
            <div className="h-2 rounded-full bg-purple-100 overflow-hidden">
              <div
                className="h-full bg-purple-600 transition-all duration-300 ease-out"
                style={{ width: `${bootstrapPercent}%` }}
              />
            </div>
            <p className="text-xs text-purple-700">{bootstrapMessage}</p>
          </div>
        )}

        <div className="space-y-4">
          <div>
            <label className="label" htmlFor="bot_name">Support Agent Name</label>
            <input
              id="bot_name"
              className="input text-gray-500 placeholder:text-gray-400"
              type="text"
              value={botName}
              onChange={(e) => setBotName(e.target.value)}
              placeholder="Kai"
              maxLength={40}
            />
          </div>

          <div>
            <label className="label" htmlFor="company_name">Company name</label>
            <input
              id="company_name"
              className="input"
              type="text"
              value={companyName}
              onChange={(e) => setCompanyName(e.target.value)}
              placeholder="Kommu"
              required
              maxLength={80}
            />
          </div>

          <div>
            <label className="label" htmlFor="product_summary">What you sell & who it’s for</label>
            <textarea
              id="product_summary"
              className="input resize-none"
              rows={3}
              value={productSummary}
              onChange={(e) => setProductSummary(e.target.value)}
              placeholder="Kommu — a Malaysian company that makes KommuAssist, an advanced driving assistance system (ADAS aftermarket device) based on openpilot / bukapilot."
              maxLength={600}
            />
          </div>

          <div>
            <label className="label">Scope — what the AI support agent MUST NOT answer</label>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
              {CANNOT_ANSWER_OPTIONS.map((opt) => {
                const checked = scopeCannotAnswer.includes(opt);
                return (
                  <label key={opt} className="flex items-start gap-2 rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm text-gray-700">
                    <input
                      type="checkbox"
                      className="mt-1"
                      checked={checked}
                      onChange={(e) => {
                        const on = e.target.checked;
                        setScopeCannotAnswer((prev) => (on ? [...prev, opt] : prev.filter((x) => x !== opt)));
                      }}
                    />
                    <span className="leading-snug">{opt}</span>
                  </label>
                );
              })}
            </div>
          </div>

          <div>
            <label className="label">Escalation rules (handover to human)</label>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
              {ESCALATION_OPTIONS.map((opt) => {
                const checked = escalationRules.includes(opt);
                return (
                  <label key={opt} className="flex items-start gap-2 rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm text-gray-700">
                    <input
                      type="checkbox"
                      className="mt-1"
                      checked={checked}
                      onChange={(e) => {
                        const on = e.target.checked;
                        setEscalationRules((prev) => (on ? [...prev, opt] : prev.filter((x) => x !== opt)));
                      }}
                    />
                    <span className="leading-snug">{opt}</span>
                  </label>
                );
              })}
            </div>
          </div>

          <div>
            <label className="label">Fallback behavior (when unsure)</label>
            <div className="space-y-2">
              <label className="flex items-start gap-2 rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm text-gray-700">
                <input
                  type="radio"
                  name="fallback_behavior"
                  className="mt-1"
                  checked={fallbackBehavior === "escalate_if_unsure"}
                  onChange={() => setFallbackBehavior("escalate_if_unsure")}
                />
                <span className="leading-snug">
                  Escalate if unsure (no guessing)
                </span>
              </label>
              <label className="flex items-start gap-2 rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm text-gray-700">
                <input
                  type="radio"
                  name="fallback_behavior"
                  className="mt-1"
                  checked={fallbackBehavior === "say_not_confirmed_and_escalate"}
                  onChange={() => setFallbackBehavior("say_not_confirmed_and_escalate")}
                />
                <span className="leading-snug">
                  Say “not confirmed” then escalate
                </span>
              </label>
              <label className="flex items-start gap-2 rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm text-gray-700">
                <input
                  type="radio"
                  name="fallback_behavior"
                  className="mt-1"
                  checked={fallbackBehavior === "ask_one_question_then_escalate"}
                  onChange={() => setFallbackBehavior("ask_one_question_then_escalate")}
                />
                <span className="leading-snug">
                  Ask one clarifying question, then escalate if still unsure
                </span>
              </label>
              <label className="flex items-start gap-2 rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm text-gray-700">
                <input
                  type="radio"
                  name="fallback_behavior"
                  className="mt-1"
                  checked={fallbackBehavior === "best_effort_hallucination_risk"}
                  onChange={() => setFallbackBehavior("best_effort_hallucination_risk")}
                />
                <span className="leading-snug">Try to answer with hallucination risk</span>
              </label>
            </div>
          </div>
        </div>

        <div>
          <div className="flex items-center justify-between gap-3">
            <label className="label">AI agent personality</label>
            <p className="text-xs text-gray-400">Hover an icon to learn more</p>
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
            {PERSONALITIES.map((p) => {
              const Icon = p.icon;
              const active = personality === p.id;
              return (
                <button
                  key={p.id}
                  type="button"
                  title={p.tip}
                  onClick={() => setPersonality(p.id)}
                  className={[
                    "rounded-xl border px-3 py-2 flex items-center gap-2 text-sm font-medium",
                    active
                      ? "border-brand-200 bg-brand-50 text-brand-800"
                      : "border-gray-200 bg-white text-gray-700 hover:bg-gray-50",
                  ].join(" ")}
                >
                  <Icon size={16} className={active ? "text-brand-700" : "text-gray-500"} />
                  {p.label}
                </button>
              );
            })}
          </div>
        </div>
          </>
        )}

        {step !== 3 && (
          <div className="flex gap-2 pt-1">
            {step === 2 && (
              <button
                type="button"
                className="btn-secondary flex-1"
                disabled={busy}
                onClick={() => setStep(1)}
              >
                Back
              </button>
            )}
            <button type="submit" disabled={busy} className="btn-primary btn-lg flex-1">
              {busy ? (
                <Spinner size="sm" className="text-white" />
              ) : step === 1 ? (
                <>
                  Continue to channel
                  <ArrowRight size={18} />
                </>
              ) : (
                <>
                  {uploadedDocs.length > 0 ? "Create support agent & configure" : "Create support agent"}
                  {channelType === "whatsapp_baileys" && whatsappPhone ? ` (${whatsappPhone})` : null}
                  <ArrowRight size={18} />
                </>
              )}
            </button>
          </div>
        )}
      </form>
    </div>
  );
}
