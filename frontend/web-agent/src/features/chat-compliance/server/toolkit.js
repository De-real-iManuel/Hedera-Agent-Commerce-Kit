import { tool } from "ai";
import { z } from "zod";
import { hackRequest, HackBackendError } from "./hack-client.js";

/**
 * Envelope helpers — every tool returns a structured object with `raw`
 * (machine-readable, consumed by client card renderers) and `humanMessage`
 * (LLM-facing prose so the model can narrate the outcome).
 */
function paymentRequiredEnvelope({ toolName, resource, method, challenge, submission }) {
  const amt = challenge?.amount_hbar ?? challenge?.amount ?? "unknown";
  const receiver = challenge?.receiver ?? challenge?.pay_to ?? "unknown";
  return {
    raw: {
      status: "PAYMENT_REQUIRED",
      toolName,
      resource,
      method,
      challenge,
      submission,
    },
    humanMessage:
      `Payment of ${amt} HBAR is required to run \`${toolName}\`. ` +
      `The backend returned an x402 challenge for \`${resource}\`. ` +
      `Receiver: ${receiver}. The user must authorize the transfer with their wallet. ` +
      `Do not retry the tool until the user confirms payment.`,
  };
}

function okEnvelope({ status, data, humanMessage }) {
  return {
    raw: { status: status || "OK", data },
    humanMessage,
  };
}

function errorEnvelope({ toolName, err }) {
  const status = err instanceof HackBackendError ? err.status : 0;
  return {
    raw: {
      status: "ERROR",
      toolName,
      httpStatus: status,
      message: err.message,
      body: err instanceof HackBackendError ? err.body : null,
    },
    humanMessage:
      `\`${toolName}\` failed (HTTP ${status || "network"}): ${err.message}. ` +
      `Verify the HACK backend is reachable at HACK_BACKEND_URL and try again.`,
  };
}

const submissionShape = z.object({
  service_name: z.string().min(1).describe("Name of the service being audited"),
  service_type: z.enum(["mcp", "agent", "api"]).describe("Kind of service"),
  primary_endpoint: z.string().url().describe("The main HTTP endpoint or MCP URL"),
  repo_url: z.string().url().optional().describe("Public source repository"),
  openapi_url: z.string().url().optional().describe("OpenAPI/Swagger spec URL"),
  description: z.string().optional().describe("One-line summary of the service"),
});

export function createComplianceToolkit() {
  const tools = {
    run_compliance_check: tool({
      description:
        "Run the HACK compliance audit pipeline against an AI service (MCP server, agent, or API). " +
        "Backend is gated by x402; if HTTP 402 is returned the tool surfaces a payment challenge and MUST NOT be retried until the user pays.",
      inputSchema: submissionShape,
      execute: async (submission) => {
        try {
          const res = await hackRequest("/api/compliance/check", {
            method: "POST",
            body: submission,
          });
          if (res.status === "PAYMENT_REQUIRED") {
            return paymentRequiredEnvelope({
              toolName: "run_compliance_check",
              resource: res.resource,
              method: res.method,
              challenge: res.challenge,
              submission,
            });
          }
          return okEnvelope({
            data: { submission, check: res.data },
            humanMessage:
              `Compliance check completed for ${submission.service_name}. ` +
              `Present the score and top findings to the user, then offer to certify or export.`,
          });
        } catch (err) {
          return errorEnvelope({ toolName: "run_compliance_check", err });
        }
      },
    }),

    certify_service: tool({
      description:
        "Finalise certification after a successful compliance check. Requires the quote_id and transaction_id from the paid x402 challenge. Produces the full signed report.",
      inputSchema: z.object({
        quote_id: z.string().describe("Quote ID from the x402 payment challenge"),
        transaction_id: z.string().describe("Hedera transaction ID proving payment"),
        submission: submissionShape.describe("Original submission the check was run against"),
      }),
      execute: async ({ quote_id, transaction_id, submission }) => {
        try {
          const res = await hackRequest(`/api/compliance/certify/${encodeURIComponent(quote_id)}`, {
            method: "POST",
            headers: {
              "X-Payment-Token": transaction_id,
              "X-Transaction-Id": transaction_id,
            },
            body: submission,
          });
          if (res.status === "PAYMENT_REQUIRED") {
            return paymentRequiredEnvelope({
              toolName: "certify_service",
              resource: res.resource,
              method: res.method,
              challenge: res.challenge,
              submission,
            });
          }
          return {
            raw: { status: "REPORT_READY", report: res.data },
            humanMessage:
              `Certification complete. Report ID: ${res.data?.report_id ?? "n/a"}. ` +
              `Score: ${res.data?.score ?? "n/a"}/100. Offer PDF, SKILL.md, and soulbound NFT next.`,
          };
        } catch (err) {
          return errorEnvelope({ toolName: "certify_service", err });
        }
      },
    }),

    get_report: tool({
      description: "Fetch a previously generated compliance report by its report_id. Free.",
      inputSchema: z.object({ report_id: z.string() }),
      execute: async ({ report_id }) => {
        try {
          const res = await hackRequest(`/api/compliance/report/${encodeURIComponent(report_id)}`);
          if (res.status === "PAYMENT_REQUIRED") {
            return paymentRequiredEnvelope({
              toolName: "get_report",
              resource: res.resource,
              method: res.method,
              challenge: res.challenge,
            });
          }
          return {
            raw: { status: "REPORT_READY", report: res.data },
            humanMessage: `Loaded report ${report_id}.`,
          };
        } catch (err) {
          return errorEnvelope({ toolName: "get_report", err });
        }
      },
    }),

    generate_skill_md: tool({
      description:
        "Produce the SKILL.md integration guide for a certified service. This is a plaintext markdown artifact developers drop into their repo to expose the service to UiPath Autopilot / other AI agents.",
      inputSchema: z.object({ report_id: z.string() }),
      execute: async ({ report_id }) => {
        try {
          const res = await hackRequest(
            `/api/compliance/report/${encodeURIComponent(report_id)}/skill-md`,
          );
          if (res.status === "PAYMENT_REQUIRED") {
            return paymentRequiredEnvelope({
              toolName: "generate_skill_md",
              resource: res.resource,
              method: res.method,
              challenge: res.challenge,
            });
          }
          const content =
            typeof res.data === "string" ? res.data : res.data?.content || res.data?.skill_md;
          return {
            raw: {
              status: "SKILL_MD_READY",
              report_id,
              filename: `SKILL.md`,
              content: content || "# SKILL.md\n\n(empty)",
              download_url: `/api/compliance/report/${encodeURIComponent(report_id)}/skill-md?download=1`,
            },
            humanMessage: `SKILL.md is ready for report ${report_id}. The user can copy or download it.`,
          };
        } catch (err) {
          return errorEnvelope({ toolName: "generate_skill_md", err });
        }
      },
    }),

    mint_soulbound_certificate: tool({
      description:
        "Mint the optional non-transferable (soulbound) NFT certificate on Hedera for a certified service. Requires a report_id and the recipient's Hedera account ID.",
      inputSchema: z.object({
        report_id: z.string(),
        recipient_account_id: z
          .string()
          .describe("Hedera account ID in shard.realm.num form, e.g. 0.0.12345"),
      }),
      execute: async ({ report_id, recipient_account_id }) => {
        try {
          const res = await hackRequest(
            `/api/compliance/report/${encodeURIComponent(report_id)}/certificate`,
            {
              method: "POST",
              body: { recipient_account_id },
            },
          );
          if (res.status === "PAYMENT_REQUIRED") {
            return paymentRequiredEnvelope({
              toolName: "mint_soulbound_certificate",
              resource: res.resource,
              method: res.method,
              challenge: res.challenge,
            });
          }
          return {
            raw: { status: "CERTIFICATE_MINTED", certificate: res.data },
            humanMessage:
              `Soulbound certificate minted. Token ID: ${res.data?.token_id ?? "n/a"} · ` +
              `TX: ${res.data?.transaction_id ?? "n/a"}.`,
          };
        } catch (err) {
          return errorEnvelope({ toolName: "mint_soulbound_certificate", err });
        }
      },
    }),
  };

  // Every compliance tool may return a PAYMENT_REQUIRED envelope which pauses the stream —
  // register all of them as "mutating" (approval-gated) so the chat handler stops after each call.
  const mutatingToolMethods = new Set([
    "run_compliance_check",
    "certify_service",
    "generate_skill_md",
    "mint_soulbound_certificate",
  ]);

  return { tools, mutatingToolMethods };
}
