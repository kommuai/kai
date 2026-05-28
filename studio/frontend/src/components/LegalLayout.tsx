import { Link } from "react-router-dom";
import { ArrowLeft } from "lucide-react";
import Logo from "./Logo";
import type { LegalSection } from "../content/legal";
import { EFFECTIVE_DATE, LEGAL_ENTITY, SERVICE_NAME } from "../content/legal";

interface LegalLayoutProps {
  title: string;
  subtitle: string;
  sections: LegalSection[];
}

export default function LegalLayout({ title, subtitle, sections }: LegalLayoutProps) {
  return (
    <div className="min-h-screen bg-surface-muted">
      <header className="sticky top-0 z-10 border-b border-gray-100 bg-white/90 backdrop-blur-sm">
        <div className="max-w-3xl mx-auto px-4 sm:px-6 py-4 flex items-center justify-between gap-4">
          <Logo size="sm" />
          <Link
            to="/login"
            className="inline-flex items-center gap-1.5 text-sm font-medium text-gray-600 hover:text-gray-900"
          >
            <ArrowLeft size={16} />
            Back to sign in
          </Link>
        </div>
      </header>

      <main className="max-w-3xl mx-auto px-4 sm:px-6 py-10 pb-16">
        <h1 className="text-3xl font-bold text-gray-900">{title}</h1>
        <p className="mt-2 text-sm text-gray-500">{subtitle}</p>
        <p className="mt-1 text-xs text-gray-400">
          {LEGAL_ENTITY} · {SERVICE_NAME} · Effective {EFFECTIVE_DATE}
        </p>

        <nav className="mt-8 rounded-2xl border border-gray-100 bg-white p-4 text-sm">
          <p className="font-semibold text-gray-700 mb-2">Contents</p>
          <ul className="space-y-1">
            {sections.map((s) => (
              <li key={s.id}>
                <a href={`#${s.id}`} className="text-brand-600 hover:underline">
                  {s.title}
                </a>
              </li>
            ))}
          </ul>
        </nav>

        <article className="mt-10 space-y-10">
          {sections.map((section) => (
            <section key={section.id} id={section.id} className="scroll-mt-24">
              <h2 className="text-lg font-semibold text-gray-900 mb-3">{section.title}</h2>
              <div className="space-y-3 text-sm text-gray-700 leading-relaxed">
                {section.paragraphs.map((p, i) => (
                  <p key={i}>{p}</p>
                ))}
              </div>
            </section>
          ))}
        </article>

        <footer className="mt-12 pt-8 border-t border-gray-200 text-center text-xs text-gray-400">
          <Link to="/terms" className="text-brand-600 hover:underline">
            Terms of Service
          </Link>
          {" · "}
          <Link to="/privacy" className="text-brand-600 hover:underline">
            Privacy Policy
          </Link>
        </footer>
      </main>
    </div>
  );
}
