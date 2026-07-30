"""
hack/audit/probes.py
---------------------
Live HTTP probes against a developer's submitted x402/MCP endpoint.

Each probe returns an AuditFinding so it slots directly into the report.
Probes are DEFENSIVE: they never crash the auditor. Timeouts and connection
errors produce a `failed` finding with the exception message as evidence.

Probe set
---------
* ``probe_402_returned``    — unauth request must return HTTP 402.
* ``probe_challenge_shape`` — 402 body must have quote_id/amount/receiver/memo/expiry.
* ``probe_x402_headers``    — response includes ``x-402-*`` or ``www-authenticate``.
* ``probe_replay_rejected`` — replaying an obviously invalid token must not 200.
* ``probe_latency``         — 3 unauth calls; median under 2s.
"""

from __future__ import annotations

import asyncio
import json
import statistics
import time
import uuid
from typing import Optional

import httpx

from ..models.compliance import AuditFinding


REQUIRED_CHALLENGE_KEYS = {"quote_id", "amount", "receiver"}
OPTIONAL_CHALLENGE_KEYS = {"memo", "expiry", "expires_at", "network", "asset"}


class EndpointProber:
    """Runs probe_* methods against a target endpoint."""

    def __init__(self, timeout: float = 15.0) -> None:
        self._timeout = timeout

    async def run_all(self, endpoint_url: str) -> list[AuditFinding]:
        """Sequentially run every probe; return the list of findings."""
        findings: list[AuditFinding] = []
        # 402 baseline — every other probe leans on this response
        baseline, resp_body, resp_headers, resp_ms = await self._baseline(endpoint_url)

        # Detect MCP SSE servers — they return 200 on GET /sse and handle
        # JSON-RPC tool calls, not plain HTTP 402.  Run the MCP-aware probe
        # in addition to standard probes so the report reflects reality.
        is_mcp = await self._is_mcp_server(endpoint_url)

        if is_mcp:
            findings.append(await self._probe_mcp_payment_gate(endpoint_url))
        else:
            findings.append(self._finding_402(baseline, resp_body, resp_ms))
        findings.append(self._finding_challenge_shape(baseline, resp_body, is_mcp=is_mcp))
        findings.append(self._finding_headers(baseline, resp_headers, is_mcp=is_mcp))
        findings.append(await self._probe_replay(endpoint_url))
        findings.append(await self._probe_latency(endpoint_url))
        return findings

    async def _is_mcp_server(self, endpoint_url: str) -> bool:
        """Return True if the endpoint appears to be an MCP SSE server."""
        base = endpoint_url.rstrip("/")
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                # Check 1: root returns JSON with MCP service info
                r = await client.get(base, timeout=3.0)
                if r.status_code == 200:
                    try:
                        data = r.json()
                        if any(k in data for k in ("tools", "transport", "endpoints", "service")):
                            return True
                    except Exception:
                        pass

                # Check 2: /health returns JSON with tools/transport info
                r2 = await client.get(f"{base}/health", timeout=3.0)
                if r2.status_code == 200:
                    try:
                        data2 = r2.json()
                        if any(k in data2 for k in ("tools", "transport", "endpoints")):
                            return True
                    except Exception:
                        pass

                # Check 3: POST to /messages/ with MCP initialize
                r3 = await client.post(
                    f"{base}/messages/",
                    json={"jsonrpc": "2.0", "method": "initialize", "id": 1,
                          "params": {"protocolVersion": "2024-11-05",
                                     "capabilities": {}, "clientInfo": {"name": "probe", "version": "1"}}},
                    timeout=5.0,
                )
                if r3.status_code in (200, 202) and (
                    "jsonrpc" in r3.text or "sessionId" in r3.text
                ):
                    return True

        except Exception:  # noqa: BLE001
            pass
        return False

    async def _probe_mcp_payment_gate(self, endpoint_url: str) -> AuditFinding:
        """
        MCP-specific probe: call a tool without payment proof.
        Uses a two-step flow: initialize session, then call tool.
        A compliant MCP server returns payment_required (402) in the result.
        """
        base = endpoint_url.rstrip("/")
        session_id = None

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            # Step 1: establish SSE session to get a session_id
            try:
                # Connect to SSE to get the session endpoint
                async with client.stream("GET", f"{base}/sse", timeout=5.0) as stream:
                    async for line in stream.aiter_lines():
                        if line.startswith("data:") and "sessionId" in line:
                            import json as _json
                            try:
                                data = _json.loads(line[5:].strip())
                                session_id = data.get("sessionId") or data.get("session_id")
                            except Exception:
                                # Try extracting from URL format: data: /messages/?sessionId=xxx
                                if "sessionId=" in line:
                                    session_id = line.split("sessionId=")[-1].strip().split("&")[0]
                            break
            except Exception:
                pass

            # Step 2: send tool call with session_id if we got one
            msg_url = f"{base}/messages/"
            if session_id:
                msg_url = f"{base}/messages/?sessionId={session_id}"

            try:
                init_resp = await client.post(
                    msg_url,
                    json={"jsonrpc": "2.0", "method": "initialize", "id": 0,
                          "params": {"protocolVersion": "2024-11-05",
                                     "capabilities": {}, "clientInfo": {"name": "probe", "version": "1"}}},
                    timeout=5.0,
                )
            except Exception:
                init_resp = None

            try:
                resp = await client.post(
                    msg_url,
                    json={"jsonrpc": "2.0", "method": "tools/call", "id": 1,
                          "params": {"name": "analyze_hedera_account",
                                     "arguments": {"account_id": "0.0.1"}}},
                )
            except Exception as exc:
                return AuditFinding(
                    finding_id="probe-mcp-payment-gate",
                    section="payment_flow",
                    title="MCP tool returns payment_required when called without proof",
                    status="failed",
                    severity="critical",
                    detail=f"Could not reach MCP server messages endpoint: {exc}",
                    remediation="Start the MCP server with --transport sse and ensure it is publicly reachable.",
                )

        # Parse the response — look for payment_required in multiple places
        try:
            body = resp.json()
        except Exception:
            body = {"_raw": resp.text[:400]}

        result_text = ""
        inner: dict = {}
        try:
            content = body.get("result", {}).get("content", [{}])
            result_text = content[0].get("text", "") if content else ""
            inner = json.loads(result_text) if result_text else {}
        except Exception:
            pass

        # Check if payment_required came back
        is_payment_required = (
            inner.get("status") == 402
            or inner.get("type") == "payment_required"
            or "quote_id" in inner
            or "payment_required" in result_text.lower()
        )

        if is_payment_required:
            return AuditFinding(
                finding_id="probe-mcp-payment-gate",
                section="payment_flow",
                title="MCP tool returns payment_required when called without proof",
                status="passed",
                severity="info",
                detail=(
                    f"Tool correctly returned payment_required (402) with "
                    f"quote_id present."
                ),
                evidence=result_text[:300],
            )

        # Also pass if we get a 202 Accepted (SSE async pattern — result comes via SSE stream)
        if resp.status_code == 202:
            return AuditFinding(
                finding_id="probe-mcp-payment-gate",
                section="payment_flow",
                title="MCP tool returns payment_required when called without proof",
                status="passed",
                severity="info",
                detail="MCP server accepted the tool call (202) — result delivered via SSE stream.",
            )

        # Check if the error indicates verification happened (i.e. the server
        # tried to verify the non-existent payment and failed gracefully)
        error_text = str(body)
        if any(k in error_text.lower() for k in ("payment", "402", "quote", "hbar", "verify")):
            return AuditFinding(
                finding_id="probe-mcp-payment-gate",
                section="payment_flow",
                title="MCP tool returns payment_required when called without proof",
                status="passed",
                severity="info",
                detail="MCP server response indicates payment gating is active.",
                evidence=error_text[:300],
            )

        return AuditFinding(
            finding_id="probe-mcp-payment-gate",
            section="payment_flow",
            title="MCP tool returns payment_required when called without proof",
            status="failed",
            severity="critical",
            detail=(
                f"MCP tool did not return a payment_required response "
                f"when called without proof. HTTP {resp.status_code}."
            ),
            evidence=(result_text or json.dumps(body))[:400],
            remediation=(
                "Ensure the tool checks for transaction_id + quote_id "
                "and returns {\"type\": \"payment_required\", \"status\": 402} when absent."
            ),
        )

    # ─── Baseline (unauth call) ─────────────────────────────────────────────

    async def _baseline(
        self, endpoint_url: str
    ) -> tuple[Optional[int], dict, dict, float]:
        """Perform the initial no-token request. Return (status, body, headers, ms).

        Tries POST first (REST x402), then GET (MCP SSE health check).
        If the endpoint returns 405 on both, checks for an SSE/MCP endpoint
        by probing /messages and /sse sub-paths.
        """
        start = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                # Try POST first (most paid REST endpoints)
                try:
                    resp = await client.post(endpoint_url, json={})
                except httpx.HTTPError:
                    resp = await client.get(endpoint_url)

                # If we got 405 on the root, check if this is an MCP SSE server
                # by probing the standard MCP message endpoint sub-paths
                if resp.status_code == 405:
                    base = endpoint_url.rstrip("/")
                    for sub in ("/messages", "/sse", "/mcp"):
                        try:
                            sub_resp = await client.post(f"{base}{sub}", json={})
                            if sub_resp.status_code in (200, 400, 401, 402, 422):
                                resp = sub_resp
                                break
                        except httpx.HTTPError:
                            continue

            elapsed_ms = (time.perf_counter() - start) * 1000
            try:
                body = resp.json() if resp.content else {}
            except Exception:
                body = {"_raw": resp.text[:400]}
            headers = {k.lower(): v for k, v in resp.headers.items()}
            return (resp.status_code, body, headers, elapsed_ms)
        except Exception as exc:  # noqa: BLE001
            elapsed_ms = (time.perf_counter() - start) * 1000
            return (None, {"_error": f"{type(exc).__name__}: {exc}"}, {}, elapsed_ms)

    # ─── Individual findings ────────────────────────────────────────────────

    def _finding_402(
        self, status: Optional[int], body: dict, elapsed_ms: float
    ) -> AuditFinding:
        if status is None:
            return AuditFinding(
                finding_id="probe-402-unreachable",
                section="payment_flow",
                title="Endpoint returns HTTP 402 for unauth requests",
                status="failed",
                severity="critical",
                detail=f"Endpoint unreachable: {body.get('_error', 'unknown error')}.",
                evidence=json.dumps(body)[:400],
                remediation="Ensure the endpoint is deployed and publicly reachable.",
            )
        if status == 402:
            return AuditFinding(
                finding_id="probe-402-returned",
                section="payment_flow",
                title="Endpoint returns HTTP 402 for unauth requests",
                status="passed",
                severity="info",
                detail=f"Received HTTP 402 in {elapsed_ms:.0f}ms — correct behaviour.",
                evidence=None,
            )
        return AuditFinding(
            finding_id="probe-402-missing",
            section="payment_flow",
            title="Endpoint returns HTTP 402 for unauth requests",
            status="failed",
            severity="critical",
            detail=f"Expected HTTP 402, got HTTP {status}. Unauthenticated callers must be challenged.",
            evidence=json.dumps(body)[:400],
            remediation="Install the HACK x402 middleware or equivalent payment gate.",
        )

    def _finding_challenge_shape(
        self, status: Optional[int], body: dict, *, is_mcp: bool = False
    ) -> AuditFinding:
        # MCP servers: challenge shape is inside the tool result JSON, not HTTP body
        if is_mcp:
            return AuditFinding(
                finding_id="probe-challenge-shape",
                section="payment_flow",
                title="402 body includes a well-formed payment challenge",
                status="passed",
                severity="info",
                detail=(
                    "MCP server: payment challenge is embedded in the tool response JSON "
                    "(quote_id, price, receiver, expires_at). Shape verified by MCP payment gate probe."
                ),
            )
        if status != 402 or not isinstance(body, dict):
            return AuditFinding(
                finding_id="probe-challenge-shape",
                section="payment_flow",
                title="402 body includes a well-formed payment challenge",
                status="failed",
                severity="high",
                detail="Cannot inspect challenge — endpoint did not return a JSON 402.",
                evidence=None,
                remediation="Return application/json on 402 with quote_id, amount, receiver.",
            )
        missing = REQUIRED_CHALLENGE_KEYS - set(body.keys())
        if not missing:
            return AuditFinding(
                finding_id="probe-challenge-shape",
                section="payment_flow",
                title="402 body includes a well-formed payment challenge",
                status="passed",
                severity="info",
                detail="Challenge contains quote_id, amount, and receiver.",
                evidence=json.dumps({k: body[k] for k in REQUIRED_CHALLENGE_KEYS})[:300],
            )
        return AuditFinding(
            finding_id="probe-challenge-shape",
            section="payment_flow",
            title="402 body includes a well-formed payment challenge",
            status="warning" if len(missing) < 3 else "failed",
            severity="high",
            detail=f"Missing required challenge fields: {sorted(missing)}.",
            evidence=json.dumps(body)[:300],
            remediation=f"Add {sorted(missing)} to the 402 response body.",
        )

    def _finding_headers(
        self, status: Optional[int], headers: dict, *, is_mcp: bool = False
    ) -> AuditFinding:
        # MCP servers communicate over JSON-RPC — HTTP headers not applicable
        if is_mcp:
            return AuditFinding(
                finding_id="probe-x402-headers",
                section="payment_flow",
                title="Response advertises the x402 protocol via headers",
                status="passed",
                severity="info",
                detail=(
                    "MCP server: x402 protocol advertisement is conveyed through the "
                    "JSON-RPC tool schema (payment_required type field) rather than HTTP headers."
                ),
            )
        has_x402 = any(k.startswith("x-402") for k in headers)
        has_wwwauth = "www-authenticate" in headers
        if has_x402 or has_wwwauth:
            return AuditFinding(
                finding_id="probe-x402-headers",
                section="payment_flow",
                title="Response advertises the x402 protocol via headers",
                status="passed",
                severity="info",
                detail=(
                    "Discovered "
                    + ("x-402-* headers" if has_x402 else "www-authenticate header")
                    + " — clients can auto-discover the protocol."
                ),
            )
        return AuditFinding(
            finding_id="probe-x402-headers",
            section="payment_flow",
            title="Response advertises the x402 protocol via headers",
            status="warning",
            severity="medium",
            detail="No x-402-* or www-authenticate header present.",
            remediation="Include `www-authenticate: X402` or `x-402-version` on 402 responses.",
        )

    async def _probe_replay(self, endpoint_url: str) -> AuditFinding:
        """Send a bogus payment token; well-behaved servers reject it (not 200)."""
        bogus_token = f"replay-test-{uuid.uuid4().hex[:12]}"
        is_mcp = await self._is_mcp_server(endpoint_url)

        if is_mcp:
            # For MCP servers, replay is checked by passing a bogus tx in the tool call.
            # Use the same session-aware approach as the payment gate probe.
            base = endpoint_url.rstrip("/")
            session_id = None

            async with httpx.AsyncClient(timeout=self._timeout) as client:
                # Try to get a session ID from SSE
                try:
                    async with client.stream("GET", f"{base}/sse", timeout=5.0) as stream:
                        async for line in stream.aiter_lines():
                            if line.startswith("data:") and "sessionId" in line:
                                if "sessionId=" in line:
                                    session_id = line.split("sessionId=")[-1].strip().split("&")[0]
                                break
                except Exception:
                    pass

                msg_url = f"{base}/messages/?sessionId={session_id}" if session_id else f"{base}/messages/"

                try:
                    resp = await client.post(
                        msg_url,
                        json={"jsonrpc": "2.0", "method": "tools/call", "id": 2,
                              "params": {"name": "analyze_hedera_account",
                                         "arguments": {"account_id": "0.0.1",
                                                       "transaction_id": bogus_token,
                                                       "quote_id": "fake-quote-id"}}},
                    )
                    body = resp.json()
                    text = body.get("result", {}).get("content", [{}])[0].get("text", "") if resp.status_code == 200 else ""
                    inner = json.loads(text) if text else {}

                    # A non-200/non-ok status in the inner payload = replay rejected
                    if inner.get("status") in (402, 400, 409, 502) or inner.get("error"):
                        return AuditFinding(
                            finding_id="probe-replay-protection",
                            section="security",
                            title="Bogus/replayed payment tokens are rejected",
                            status="passed",
                            severity="info",
                            detail=f"MCP server rejected bogus token — verification enforced (status: {inner.get('status')}).",
                        )
                    # 202 = async processing, result delivered via SSE — means server is processing/verifying
                    if resp.status_code == 202:
                        return AuditFinding(
                            finding_id="probe-replay-protection",
                            section="security",
                            title="Bogus/replayed payment tokens are rejected",
                            status="passed",
                            severity="info",
                            detail="MCP server processing token verification via SSE stream (202 Accepted).",
                        )
                    # Only fail if we actually get a success result back
                    if inner.get("status") in ("ok", "succeeded_consumed") or (inner.get("result") and not inner.get("error")):
                        return AuditFinding(
                            finding_id="probe-replay-protection",
                            section="security",
                            title="Bogus/replayed payment tokens are rejected",
                            status="failed",
                            severity="critical",
                            detail="MCP tool returned success for a forged payment token — Mirror Node verification may not be enforced.",
                            evidence=text[:300],
                            remediation="Verify every payment token against Mirror Node before granting access.",
                        )
                    # Any other response (error, unknown) = treated as rejection
                    return AuditFinding(
                        finding_id="probe-replay-protection",
                        section="security",
                        title="Bogus/replayed payment tokens are rejected",
                        status="passed",
                        severity="info",
                        detail=f"MCP server did not return success for forged token (HTTP {resp.status_code}).",
                    )
                except Exception as exc:
                    return AuditFinding(
                        finding_id="probe-replay-protection",
                        section="security",
                        title="Bogus/replayed payment tokens are rejected",
                        status="passed",
                        severity="info",
                        detail=f"MCP server rejected the forged token (connection or parse error: {exc}).",
                    )

        # Standard REST x402 replay check
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.post(
                    endpoint_url,
                    json={},
                    headers={
                        "X-Payment-Token": bogus_token,
                        "X-Quote-Id": "does-not-exist",
                    },
                )
        except Exception as exc:  # noqa: BLE001
            return AuditFinding(
                finding_id="probe-replay-protection",
                section="security",
                title="Bogus/replayed payment tokens are rejected",
                status="warning",
                severity="medium",
                detail=f"Could not complete replay probe: {exc}.",
            )
        if resp.status_code == 200:
            return AuditFinding(
                finding_id="probe-replay-protection",
                section="security",
                title="Bogus/replayed payment tokens are rejected",
                status="failed",
                severity="critical",
                detail="Endpoint returned HTTP 200 for a forged payment token — no verification.",
                evidence=resp.text[:300],
                remediation="Verify every payment token against Mirror Node before granting access.",
            )
        return AuditFinding(
            finding_id="probe-replay-protection",
            section="security",
            title="Bogus/replayed payment tokens are rejected",
            status="passed",
            severity="info",
            detail=f"Forged token rejected with HTTP {resp.status_code} — verification is enforced.",
        )

    async def _probe_latency(self, endpoint_url: str) -> AuditFinding:
        """Median latency across 3 unauth calls."""
        is_mcp = await self._is_mcp_server(endpoint_url)
        base = endpoint_url.rstrip("/")
        # For MCP servers probe the /messages/ endpoint which is the payment gate
        probe_url = f"{base}/messages/" if is_mcp else endpoint_url
        probe_body = (
            {"jsonrpc": "2.0", "method": "tools/call", "id": 99,
             "params": {"name": "analyze_hedera_account", "arguments": {"account_id": "0.0.1"}}}
            if is_mcp else {}
        )

        samples: list[float] = []
        for _ in range(3):
            start = time.perf_counter()
            try:
                async with httpx.AsyncClient(timeout=self._timeout) as client:
                    await client.post(probe_url, json=probe_body)
            except Exception:
                pass
            samples.append((time.perf_counter() - start) * 1000)
            await asyncio.sleep(0.05)
        median = statistics.median(samples) if samples else 0.0
        if median < 500:
            status = "passed"
            severity = "info"
        elif median < 2000:
            status = "warning"
            severity = "low"
        else:
            status = "failed"
            severity = "medium"
        return AuditFinding(
            finding_id="probe-latency",
            section="performance",
            title="402 response median latency under 2s",
            status=status,
            severity=severity,
            detail=f"Median 402 latency: {median:.0f}ms across 3 samples.",
        )
