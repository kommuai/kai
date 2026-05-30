/** Legal copy for Kai Studio. Update LEGAL_ENTITY and contact before production. */

export const LEGAL_ENTITY = "Kommu AI";
export const SERVICE_NAME = "Kai Studio";
export const CONTACT_EMAIL = "legal@kommu.ai";
export const PRIVACY_EMAIL = "privacy@kommu.ai";
export const EFFECTIVE_DATE = "28 May 2026";
export const GOVERNING_LAW = "Malaysia";

export type LegalSection = { id: string; title: string; paragraphs: string[] };

export const TERMS_SECTIONS: LegalSection[] = [
  {
    id: "acceptance",
    title: "1. Acceptance of terms",
    paragraphs: [
      `These Terms of Service ("Terms") govern access to and use of ${SERVICE_NAME} (the "Service"), operated by ${LEGAL_ENTITY} ("we", "us", "our"). By creating an account, signing in, or using the Service, you agree to these Terms. If you do not agree, do not use the Service.`,
      "If you use the Service on behalf of an organisation, you represent that you have authority to bind that organisation, and \"you\" includes that organisation.",
    ],
  },
  {
    id: "service",
    title: "2. Description of the Service",
    paragraphs: [
      `${SERVICE_NAME} is a web-based administration console for configuring and operating AI-powered customer-support agents ("Agents"). Features may include workspace configuration, knowledge-base editing, compilation, conversation inbox views, contact management, messaging channel setup, and related tooling.`,
      "The Service is an operator tool. It does not replace your own policies, contracts, or compliance obligations toward your end customers. Deployed Agents may interact with third-party channels (e.g. messaging platforms) under your configuration and credentials.",
    ],
  },
  {
    id: "accounts",
    title: "3. Accounts and security",
    paragraphs: [
      "You must provide accurate registration information and keep credentials confidential. You are responsible for all activity under your account and for restricting access to authorised personnel only.",
      "You must notify us promptly of any unauthorised access. We may suspend or terminate accounts that appear compromised or used in violation of these Terms.",
      "We may offer sign-in via email/password and third-party identity providers (e.g. Google, Facebook). Their terms and privacy policies also apply to that sign-in flow.",
    ],
  },
  {
    id: "acceptable-use",
    title: "4. Acceptable use",
    paragraphs: [
      "You will not use the Service to: violate law or third-party rights; transmit malware or abusive content; attempt unauthorised access to systems or data; reverse engineer the Service except where permitted by law; overload or disrupt infrastructure; or misrepresent identity or affiliation.",
      "You are solely responsible for Agent content (prompts, FAQs, configurations, tags, replies sent through integrated channels) and for ensuring it is lawful, accurate, and appropriate for your audience.",
    ],
  },
  {
    id: "content",
    title: "5. Your content and data",
    paragraphs: [
      "You retain ownership of content you upload or configure. You grant us a non-exclusive, worldwide licence to host, process, copy, and display that content solely to provide, secure, and improve the Service, including running compile jobs and reading agent session databases you point the Service at.",
      "You represent that you have all rights necessary for your content and that it does not infringe others' rights. We may remove content or suspend Agents that we reasonably believe violate these Terms or pose risk to the Service or others.",
    ],
  },
  {
    id: "ai",
    title: "6. AI and automated outputs",
    paragraphs: [
      "Agents produce automated outputs that may be incorrect, incomplete, offensive, or unsuitable. Outputs are not professional, legal, medical, or financial advice. You must implement human oversight where required and not rely on the Service as the sole basis for decisions affecting individuals.",
      "We do not guarantee accuracy, availability, or fitness for a particular purpose of any Agent response. You assume all risk from deploying Agents to end users.",
    ],
  },
  {
    id: "third-party",
    title: "7. Third-party services",
    paragraphs: [
      "The Service may integrate with or depend on third parties (hosting, OAuth providers, messaging APIs, model providers). We are not responsible for their availability, terms, or acts. Your use of those services is at your own risk and under their agreements.",
      "You are responsible for API keys, webhooks, and channel credentials you configure in Agent workspaces.",
    ],
  },
  {
    id: "fees",
    title: "8. Fees",
    paragraphs: [
      "If we introduce paid plans, pricing and billing terms will be presented separately. Until then, access may be provided at our discretion. We may change or discontinue free access with reasonable notice where practicable.",
    ],
  },
  {
    id: "ip",
    title: "9. Our intellectual property",
    paragraphs: [
      `The Service software, branding, and documentation (excluding your content) are owned by ${LEGAL_ENTITY} or licensors and protected by intellectual-property laws. These Terms do not grant you any right to our trademarks or to copy the Service except as needed for normal use.`,
    ],
  },
  {
    id: "disclaimer",
    title: "10. Disclaimers",
    paragraphs: [
      `THE SERVICE IS PROVIDED "AS IS" AND "AS AVAILABLE" WITHOUT WARRANTIES OF ANY KIND, WHETHER EXPRESS, IMPLIED, OR STATUTORY, INCLUDING MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE, NON-INFRINGEMENT, AND QUIET ENJOYMENT.`,
      "We do not warrant uninterrupted or error-free operation, that defects will be corrected, or that the Service or servers are free of harmful components.",
    ],
  },
  {
    id: "liability",
    title: "11. Limitation of liability",
    paragraphs: [
      `TO THE MAXIMUM EXTENT PERMITTED BY APPLICABLE LAW, ${LEGAL_ENTITY.toUpperCase()} AND ITS OFFICERS, DIRECTORS, EMPLOYEES, AND AGENTS WILL NOT BE LIABLE FOR ANY INDIRECT, INCIDENTAL, SPECIAL, CONSEQUENTIAL, EXEMPLARY, OR PUNITIVE DAMAGES, OR FOR LOSS OF PROFITS, REVENUE, DATA, GOODWILL, OR BUSINESS INTERRUPTION, ARISING FROM OR RELATED TO THE SERVICE OR THESE TERMS, EVEN IF ADVISED OF THE POSSIBILITY.`,
      "Our aggregate liability for all claims arising from or related to the Service in any twelve (12) month period will not exceed the greater of (a) amounts you paid us for the Service in that period, or (b) one hundred Malaysian Ringgit (MYR 100), unless mandatory law requires otherwise.",
      "Some jurisdictions do not allow certain limitations; in those cases our liability is limited to the fullest extent permitted by law.",
    ],
  },
  {
    id: "indemnity",
    title: "12. Indemnification",
    paragraphs: [
      `You will defend, indemnify, and hold harmless ${LEGAL_ENTITY} and its affiliates from claims, damages, losses, and expenses (including reasonable legal fees) arising from: your content; your use of the Service; your Agents' interactions with end users; violation of these Terms or law; or dispute between you and your customers.`,
    ],
  },
  {
    id: "termination",
    title: "13. Suspension and termination",
    paragraphs: [
      "You may stop using the Service at any time. We may suspend or terminate access immediately if you breach these Terms, create security risk, or if required by law.",
      "Upon termination, your right to use the Service ends. Provisions that by nature should survive (disclaimers, liability limits, indemnity, governing law) remain in effect.",
    ],
  },
  {
    id: "changes",
    title: "14. Changes",
    paragraphs: [
      "We may update these Terms. Material changes will be indicated by updating the effective date and, where appropriate, notice in the Service. Continued use after changes constitutes acceptance.",
    ],
  },
  {
    id: "law",
    title: "15. Governing law and disputes",
    paragraphs: [
      `These Terms are governed by the laws of ${GOVERNING_LAW}, without regard to conflict-of-law rules. Courts in ${GOVERNING_LAW} have exclusive jurisdiction, unless mandatory consumer protection law in your country requires otherwise.`,
      "Before formal proceedings, the parties will attempt in good faith to resolve disputes informally by contacting the email below.",
    ],
  },
  {
    id: "contact",
    title: "16. Contact",
    paragraphs: [`Questions about these Terms: ${CONTACT_EMAIL}.`],
  },
];

export const PRIVACY_SECTIONS: LegalSection[] = [
  {
    id: "intro",
    title: "1. Introduction",
    paragraphs: [
      `${LEGAL_ENTITY} ("we") operates ${SERVICE_NAME}. This Privacy Policy explains how we collect, use, disclose, and protect personal data when you use the Service.`,
      "This policy applies to the Studio web application and related APIs. It does not govern third-party messaging platforms, model providers, or your own privacy notices to your end customers — you remain responsible for those.",
    ],
  },
  {
    id: "roles",
    title: "2. Roles",
    paragraphs: [
      "For account and Studio usage data, we act as data controller (or equivalent) for the purposes described here.",
      "For end-customer messages and contact data stored in agent session databases that you connect to the Service, you are typically the controller and we process on your instructions when displaying inbox, tags, or sending replies you authorise.",
    ],
  },
  {
    id: "collect",
    title: "3. Data we collect",
    paragraphs: [
      "Account data: name, email address, authentication provider identifiers, password hash (for email sign-in), profile picture URL from OAuth, and account timestamps.",
      "Agent metadata: agent names, slugs, workspace paths, membership and invite records stored in the Studio admin database.",
      "Configuration content: files you edit in the Service (e.g. workspace.yaml, system prompts, FAQ/knowledge files) and compile outputs triggered through the Service.",
      "Operational data: conversation and message content read from agent session databases you configure; contact tags you create; server logs (IP address, user agent, request paths, errors, timestamps).",
      "Cookies and local storage: session tokens (e.g. JWT in browser storage) to keep you signed in.",
    ],
  },
  {
    id: "use",
    title: "4. How we use data",
    paragraphs: [
      "Provide, maintain, and secure the Service; authenticate users; enforce access to Agents you are permitted to use.",
      "Display inbox and contact features; execute compile and integration actions you request.",
      "Diagnose errors, prevent abuse, and improve reliability.",
      "Comply with law and respond to lawful requests.",
      "We do not sell your personal data.",
    ],
  },
  {
    id: "legal-bases",
    title: "5. Legal bases (where applicable)",
    paragraphs: [
      "Depending on jurisdiction, we rely on: performance of a contract (providing the Service); legitimate interests (security, fraud prevention, improvement); consent (where required, e.g. optional marketing if ever offered); and legal obligation.",
    ],
  },
  {
    id: "sharing",
    title: "6. Sharing and subprocessors",
    paragraphs: [
      "We may share data with: cloud hosting providers; OAuth providers (Google, Meta/Facebook) when you choose social login; messaging or model providers you enable; and professional advisers or authorities when required by law.",
      "Subprocessors are bound by confidentiality and data-protection obligations appropriate to their role. A list may be provided on request.",
    ],
  },
  {
    id: "retention",
    title: "7. Retention",
    paragraphs: [
      "Account and admin-database records are kept while your account is active and for a reasonable period afterward for backup, audit, and legal compliance.",
      "Agent session and message data remain in locations you control (agent workspace databases); the Service reads them on demand and does not necessarily copy full histories into the admin database.",
      "Logs may be retained for a limited period unless longer retention is required for security or legal reasons.",
    ],
  },
  {
    id: "security",
    title: "8. Security",
    paragraphs: [
      "We use reasonable technical and organisational measures (access controls, hashing of passwords, HTTPS in production deployments, least-privilege practices). No method of transmission or storage is 100% secure.",
      "You are responsible for securing deployment credentials, API keys, and agent workspace access on your infrastructure.",
    ],
  },
  {
    id: "rights",
    title: "9. Your rights",
    paragraphs: [
      "Depending on applicable law (including PDPA in Malaysia where relevant), you may request access, correction, deletion, restriction, or portability of your account data, or object to certain processing.",
      "Contact us at the email below. We may verify identity before responding. You may also lodge a complaint with a supervisory authority where applicable.",
    ],
  },
  {
    id: "international",
    title: "10. International transfers",
    paragraphs: [
      "Data may be processed in countries other than where you are located. Where required, we implement appropriate safeguards for cross-border transfers.",
    ],
  },
  {
    id: "children",
    title: "11. Children",
    paragraphs: [
      "The Service is not directed at children under 13 (or higher age where local law requires). We do not knowingly collect their data.",
    ],
  },
  {
    id: "changes-privacy",
    title: "12. Changes to this policy",
    paragraphs: [
      "We may update this Privacy Policy. The effective date at the top will change. Material updates may be highlighted in the Service.",
    ],
  },
  {
    id: "contact-privacy",
    title: "13. Contact",
    paragraphs: [`Privacy enquiries: ${PRIVACY_EMAIL}. General legal: ${CONTACT_EMAIL}.`],
  },
];
