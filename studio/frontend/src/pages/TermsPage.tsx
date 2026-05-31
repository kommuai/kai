import LegalLayout from "../components/LegalLayout";
import { TERMS_SECTIONS } from "../content/legal";

export default function TermsPage() {
  return (
    <LegalLayout
      title="Terms of Service"
      subtitle="Please read these terms carefully before using Shadou Studio."
      sections={TERMS_SECTIONS}
    />
  );
}
