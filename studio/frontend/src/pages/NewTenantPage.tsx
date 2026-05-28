import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { ArrowLeft, ArrowRight, Building2, HeartHandshake, ShieldCheck, Smile, Sparkles, Zap, Briefcase } from "lucide-react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import toast from "react-hot-toast";
import { tenantsApi } from "../lib/api";
import Spinner from "../components/Spinner";

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

  const { mutate, isPending } = useMutation({
    mutationFn: () =>
      tenantsApi.create({
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
      }),
    onSuccess: (tenant) => {
      qc.invalidateQueries({ queryKey: ["tenants"] });
      toast.success("Tenant created!");
      navigate(`/t/${tenant.slug}`);
    },
    onError: (err: any) => {
      toast.error(err?.response?.data?.detail || "Failed to create tenant");
    },
  });

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!slugValid) {
      toast.error("Company name must produce a valid slug (3–50 lowercase letters/numbers/hyphens).");
      return;
    }
    mutate();
  }

  return (
    <div className="max-w-xl mx-auto animate-fade-in">
      <button onClick={() => navigate(-1)} className="btn-ghost mb-6 -ml-2 text-gray-500">
        <ArrowLeft size={16} />
        Back
      </button>

      <div className="flex items-center gap-4 mb-8">
        <div className="h-12 w-12 rounded-2xl bg-brand-50 flex items-center justify-center">
          <Building2 size={24} className="text-brand-600" />
        </div>
        <div>
          <h1 className="text-xl font-bold text-gray-900">New tenant</h1>
          <p className="text-sm text-gray-500">
            Fill what you know. You can refine later in Configuration → System prompt.
          </p>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="card p-6 space-y-5">
        <div className="space-y-4">
          <div>
            <label className="label" htmlFor="bot_name">Role & identity — AI support agent name</label>
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
              placeholder="Kommu builds aftermarket ADAS hardware that enhances supported cars with better Level 2 driver assistance features."
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

        <button type="submit" disabled={isPending} className="btn-primary btn-lg w-full">
          {isPending ? <Spinner size="sm" className="text-white" /> : (
            <>
              Create tenant
              <ArrowRight size={18} />
            </>
          )}
        </button>
      </form>
    </div>
  );
}
