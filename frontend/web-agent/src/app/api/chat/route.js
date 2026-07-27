import { createChatHandler } from "@/features/chat-runtime/server";
import { HederaRequestError } from "@/features/chat-hedera/server";
import { createLLM } from "@/features/chat-hedera/server/llm";
import {
  getComplianceSystemPrompt,
  getComplianceTools,
  HackBackendError,
} from "@/features/chat-compliance/server";

export const runtime = "nodejs";
export const maxDuration = 60;

// The Compliance Review Agent is the primary chat experience. Every tool call
// goes through the HACK backend and is gated by x402. See system-prompt.js.
const handler = createChatHandler({
  llm: createLLM(),
  getTools: getComplianceTools,
  getSystemPrompt: getComplianceSystemPrompt,
});

export async function POST(req) {
  try {
    return await handler(req);
  } catch (err) {
    if (err instanceof HederaRequestError) {
      return new Response(JSON.stringify({ error: err.message }), {
        status: err.status,
        headers: { "content-type": "application/json" },
      });
    }
    if (err instanceof HackBackendError) {
      return new Response(
        JSON.stringify({ error: err.message, backendStatus: err.status }),
        {
          status: 502,
          headers: { "content-type": "application/json" },
        },
      );
    }
    throw err;
  }
}
