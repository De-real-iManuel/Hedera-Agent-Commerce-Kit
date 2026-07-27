export const complianceSuggestions = [
  {
    id: "start-check",
    category: "Compliance",
    label: "Audit my MCP server",
    prompt:
      "I want to run a compliance check on my MCP server. Walk me through the submission fields you need.",
    mutating: true,
  },
  {
    id: "audit-agent",
    category: "Compliance",
    label: "Audit an AI agent",
    prompt: "Help me audit an agent I just built. Which fields do you need to get started?",
    mutating: true,
  },
  {
    id: "explain-x402",
    category: "How it works",
    label: "How does x402 work here?",
    prompt:
      "Explain how payments work inside this chat. What happens when the backend returns 402?",
    mutating: false,
  },
  {
    id: "explain-report",
    category: "How it works",
    label: "What's in a compliance report?",
    prompt:
      "What checks does the HACK compliance pipeline actually run, and what artifacts do I get out?",
    mutating: false,
  },
  {
    id: "fetch-report",
    category: "Reports",
    label: "Load a report by ID",
    prompt: "I have an existing report ID. Can you fetch it and summarise the score?",
    mutating: false,
  },
  {
    id: "mint-cert",
    category: "Reports",
    label: "Mint my soulbound certificate",
    prompt:
      "I already have a certified report. Mint the soulbound NFT certificate to my Hedera account.",
    mutating: true,
  },
];
