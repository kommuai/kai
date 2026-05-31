import LegalLayout from "../components/LegalLayout";
import { PRIVACY_SECTIONS } from "../content/legal";

export default function PrivacyPage() {
  return (
    <LegalLayout
      title="Privacy Policy"
      subtitle="How we collect, use, and protect information when you use Shadou Studio."
      sections={PRIVACY_SECTIONS}
    />
  );
}
