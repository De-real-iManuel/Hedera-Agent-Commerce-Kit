"use client";
import { PaymentGateCard, PaymentGateRow } from "./components/PaymentGateCard.jsx";
import { ComplianceReportCard, ComplianceReportRow } from "./components/ComplianceReportCard.jsx";
import { SkillMdCard, SkillMdRow } from "./components/SkillMdCard.jsx";
import { CertificateCard, CertificateRow } from "./components/CertificateCard.jsx";
import { complianceSuggestions } from "./utils/suggestions.js";

/**
 * Client-side extension for the Compliance Review Agent.
 * Registers per-tool card & row renderers plus starter prompts.
 * The chat runtime picks these up via `registerExtensions` in providers.jsx.
 */
export const complianceExtension = {
  id: "compliance",

  toolRenderers: {
    run_compliance_check: {
      card: ({ output }) => {
        const status = output?.raw?.status;
        if (status === "PAYMENT_REQUIRED") return <PaymentGateCard output={output} />;
        if (status === "OK" || status === "REPORT_READY")
          return <ComplianceReportCard output={output} />;
        return null;
      },
      row: ({ output }) => {
        const status = output?.raw?.status;
        if (status === "PAYMENT_REQUIRED") return <PaymentGateRow output={output} />;
        return <ComplianceReportRow output={output} />;
      },
    },
    certify_service: {
      card: ({ output }) => {
        const status = output?.raw?.status;
        if (status === "PAYMENT_REQUIRED") return <PaymentGateCard output={output} />;
        return <ComplianceReportCard output={output} />;
      },
      row: ({ output }) => {
        const status = output?.raw?.status;
        if (status === "PAYMENT_REQUIRED") return <PaymentGateRow output={output} />;
        return <ComplianceReportRow output={output} />;
      },
    },
    get_report: {
      card: ({ output }) => <ComplianceReportCard output={output} />,
      row: ({ output }) => <ComplianceReportRow output={output} />,
    },
    generate_skill_md: {
      card: ({ output }) => {
        const status = output?.raw?.status;
        if (status === "PAYMENT_REQUIRED") return <PaymentGateCard output={output} />;
        return <SkillMdCard output={output} />;
      },
      row: ({ output }) => <SkillMdRow output={output} />,
    },
    mint_soulbound_certificate: {
      card: ({ output }) => {
        const status = output?.raw?.status;
        if (status === "PAYMENT_REQUIRED") return <PaymentGateCard output={output} />;
        return <CertificateCard output={output} />;
      },
      row: ({ output }) => <CertificateRow output={output} />,
    },
  },

  suggestions: complianceSuggestions,

  emptyState: {
    title: "HACK Compliance Review Agent",
    subtitle:
      "Audit AI services against the Hedera Agent Commerce Kit standards. Every check is paid on-chain via x402.",
  },
};

export default complianceExtension;
