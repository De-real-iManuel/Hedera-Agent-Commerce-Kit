import { createComplianceToolkit } from "./toolkit.js";

export { getComplianceSystemPrompt } from "./system-prompt.js";
export { HackBackendError } from "./hack-client.js";

/**
 * Signature matches the `getTools` contract in create-chat-handler.js:
 *   (body) => { tools, mutatingToolMethods }
 */
export function getComplianceTools(_body) {
  return createComplianceToolkit();
}
