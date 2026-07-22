#!/usr/bin/env python3
"""
Structure and safety validation for Hedera Agent Commerce Kit.
Run from the project root:  python scripts/validate.py

Exits 0 if all checks pass, 1 if any FAIL.
"""

from __future__ import annotations

import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PASS = "\033[32mPASS\033[0m"
FAIL = "\033[31mFAIL\033[0m"

failures: list[str] = []


def check(label: str, condition: bool, hint: str = "") -> None:
    if condition:
        print(f"  {PASS}  {label}")
    else:
        tag = f"  {FAIL}  {label}"
        if hint:
            tag += f"\n        hint: {hint}"
        print(tag)
        failures.append(label)


def file_exists(rel: str) -> bool:
    return os.path.isfile(os.path.join(ROOT, rel))


def file_contains(rel: str, pattern: str) -> bool:
    path = os.path.join(ROOT, rel)
    if not os.path.isfile(path):
        return False
    with open(path, encoding="utf-8") as f:
        return bool(re.search(pattern, f.read()))


def file_not_contains(rel: str, pattern: str) -> bool:
    path = os.path.join(ROOT, rel)
    if not os.path.isfile(path):
        return True
    with open(path, encoding="utf-8") as f:
        return not re.search(pattern, f.read())


print("\n=== Hedera Agent Commerce Kit — Structure Validation ===\n")

# ── Required files ────────────────────────────────────────────────────────────
print("[ Required files ]")
required_files = [
    "README.md",
    "ARCHITECTURE.md",
    "QUICKSTART.md",
    "ROADMAP.md",
    ".env.example",
    ".gitignore",
    # Backend core
    "backend/main.py",
    "backend/config.py",
    "backend/requirements.txt",
    "backend/hack.py",
    # Middleware & verification
    "backend/middleware/x402.py",
    "backend/verification/mirror_node.py",
    "backend/verification/payment_state.py",
    # Agent Kit integration
    "backend/agent/hedera_agent.py",
    # Receipts, metering
    "backend/receipts/hcs.py",
    "backend/metering/usage.py",
    # Routers
    "backend/routers/payment.py",
    "backend/routers/premium.py",
    "backend/routers/health.py",
    "backend/routers/receipts.py",
    "backend/routers/usage.py",
    "backend/routers/hashscan.py",
    "backend/routers/agent.py",
    # Examples
    "examples/mcp/paid_tool.py",
    "examples/paid-mcp-hedera.md",
    # Frontend
    "frontend/src/app/page.tsx",
    "frontend/package.json",
    # Scripts
    "scripts/install.sh",
    "scripts/start-backend.sh",
    "scripts/start-frontend.sh",
    # Templates
    "templates/payment-challenge.json",
    "templates/proof-retry.json",
    "templates/success-receipt.json",
    "templates/risk-register.md",
    "templates/submission-questionnaire.md",
    # Docs
    "docs/SAFETY.md",
    "docs/DEMO_SCRIPT.md",
    "docs/SUBMISSION_CHECKLIST.md",
    "docs/DECORATOR.md",
    "scripts/create_topic.py",
    "LICENSE",
    # Skill
    "skill/SKILL.md",
    "skill/hedera-agent-kit-integration.md",
    # Rules
    "rules/custody.md",
    "rules/signing.md",
    "rules/payments.md",
    # Commands
    "commands/audit-payment-flow.md",
    "commands/generate-launch-checklist.md",
]
for f in required_files:
    check(f"exists: {f}", file_exists(f))

# ── Safety checks ─────────────────────────────────────────────────────────────
print("\n[ Safety — no dangerous patterns in source ]")
source_files = [
    "backend/middleware/x402.py",
    "backend/verification/mirror_node.py",
    "backend/verification/payment_state.py",
    "backend/receipts/hcs.py",
    "backend/routers/payment.py",
    "backend/routers/premium.py",
    "backend/agent/hedera_agent.py",
    "examples/mcp/paid_tool.py",
]
for f in source_files:
    check(
        f"no private_key logging: {f}",
        file_not_contains(f, r"print.*private_key|log.*private_key|echo.*private_key"),
        "remove any logging of private keys",
    )
    check(
        f"no auto-sign: {f}",
        file_not_contains(f, r"signTransaction\(|wallet\.sign\(|\.autoSign\("),
        "remove auto-signing logic",
    )

# ── .env not committed ────────────────────────────────────────────────────────
print("\n[ .env safety ]")
check(".env in .gitignore", file_contains(".gitignore", r"\.env"))
check(".env.example has no real keys", file_not_contains(".env.example", r"sk-proj-[a-zA-Z0-9]{20,}"))

# ── Hedera Agent Kit integration ──────────────────────────────────────────────
print("\n[ Hedera Agent Kit integration ]")
check("hedera-agent-kit in requirements.txt",
      file_contains("backend/requirements.txt", r"hedera-agent-kit"))
check("hiero-sdk-python in requirements.txt",
      file_contains("backend/requirements.txt", r"hiero-sdk-python"))
check("langchain in requirements.txt",
      file_contains("backend/requirements.txt", r"langchain"))
check("HederaLangchainToolkit imported in agent",
      file_contains("backend/agent/hedera_agent.py", r"HederaLangchainToolkit"))
check("core_consensus_plugin referenced in agent",
      file_contains("backend/agent/hedera_agent.py", r"core_consensus_plugin"))
check("core_account_query_plugin referenced in agent",
      file_contains("backend/agent/hedera_agent.py", r"core_account_query_plugin"))
check("AgentMode imported",
      file_contains("backend/agent/hedera_agent.py", r"AgentMode"))
check("hiero_sdk_python used in hcs.py",
      file_contains("backend/receipts/hcs.py", r"hiero_sdk_python"))
check("agent router registered in main.py",
      file_contains("backend/main.py", r"agent"))

# ── State machine coverage ────────────────────────────────────────────────────
print("\n[ Payment state machine ]")
check("QUOTED state defined",   file_contains("backend/verification/payment_state.py", r"QUOTED"))
check("VERIFIED state defined", file_contains("backend/verification/payment_state.py", r"VERIFIED"))
check("GRANTED state defined",  file_contains("backend/verification/payment_state.py", r"GRANTED"))
check("CONSUMED state defined", file_contains("backend/verification/payment_state.py", r"CONSUMED"))
check("EXPIRED state defined",  file_contains("backend/verification/payment_state.py", r"EXPIRED"))
check("DUPLICATE state defined",file_contains("backend/verification/payment_state.py", r"DUPLICATE"))
check("quote expiry enforced",  file_contains("backend/verification/payment_state.py", r"expires_at"))
check("replay rejection present",file_contains("backend/verification/payment_state.py", r"Replay rejected"))

# ── API endpoints ─────────────────────────────────────────────────────────────
print("\n[ API endpoints ]")
check("/api/health defined",           file_contains("backend/routers/health.py",   r"/health"))
check("/api/payment/challenge defined",file_contains("backend/routers/payment.py",  r"/challenge"))
check("/api/payment/verify defined",   file_contains("backend/routers/payment.py",  r"/verify"))
check("/api/payment/status defined",   file_contains("backend/routers/payment.py",  r"/status"))
check("/api/premium-query defined",    file_contains("backend/routers/premium.py",  r"/premium-query"))
check("/api/receipt defined",          file_contains("backend/routers/receipts.py", r"/receipt"))
check("/api/usage defined",            file_contains("backend/routers/usage.py",    r"/usage"))
check("/api/hashscan defined",         file_contains("backend/routers/hashscan.py", r"/hashscan"))
check("/api/agent/query defined",      file_contains("backend/routers/agent.py",    r"/query"))

# ── Templates ─────────────────────────────────────────────────────────────────
print("\n[ Templates ]")
check("challenge template has quote_id",
      file_contains("templates/payment-challenge.json", r"quote_id"))
check("proof-retry template has quote_id",
      file_contains("templates/proof-retry.json", r"quote_id"))
check("success-receipt template has hashscan_url",
      file_contains("templates/success-receipt.json", r"hashscan_url"))
check("risk-register has critical severity",
      file_contains("templates/risk-register.md", r"Critical"))
check("submission questionnaire has Hedera Agent Kit",
      file_contains("templates/submission-questionnaire.md", r"Hedera Agent Kit"))

# ── Skill docs ────────────────────────────────────────────────────────────────
print("\n[ Developer API (@PaidEndpoint) ]")
check("PaidEndpoint class defined in hack.py",
      file_contains("backend/hack.py", r"class PaidEndpoint"))
check("PaidEndpoint parses HBAR price",
      file_contains("backend/hack.py", r"_parse_hbar"))
check("PaidEndpoint enforces CONSUMED state",
      file_contains("backend/hack.py", r"CONSUMED"))
check("PaidEndpoint returns 402 challenge",
      file_contains("backend/hack.py", r"payment_required"))
check("get_paid_routes exported",
      file_contains("backend/hack.py", r"get_paid_routes"))


check("SKILL.md has routing table",
      file_contains("skill/SKILL.md", r"hedera-agent-kit-integration"))
check("agent-kit integration doc mentions plugins",
      file_contains("skill/hedera-agent-kit-integration.md", r"core_consensus_plugin"))
check("custody rules present",
      file_contains("rules/custody.md", r"Never"))
check("signing rules present",
      file_contains("rules/signing.md", r"Never"))
check("payment rules have error states table",
      file_contains("rules/payments.md", r"verifier_unavailable"))

# ── Summary ───────────────────────────────────────────────────────────────────
print()
total = sum(1 for _ in required_files) + 8 + 2 + 9 + 8 + 9 + 5 + 5
if failures:
    print(f"❌  {len(failures)} check(s) failed:")
    for f in failures:
        print(f"    - {f}")
    sys.exit(1)
else:
    print("✅  All checks passed. Ready to submit.")
    sys.exit(0)
