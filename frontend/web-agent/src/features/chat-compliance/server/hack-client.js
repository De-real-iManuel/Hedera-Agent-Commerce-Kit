/**
 * Thin fetch wrapper for the Hedera Agent Commerce Kit backend.
 * Recognises HTTP 402 (Payment Required) and returns a structured
 * PAYMENT_REQUIRED envelope so tools can surface a payment gate to the user.
 */

const DEFAULT_BASE = process.env.HACK_BACKEND_URL || "http://localhost:8000";

export class HackBackendError extends Error {
  constructor(message, { status, body } = {}) {
    super(message);
    this.name = "HackBackendError";
    this.status = status;
    this.body = body;
  }
}

async function parseBody(res) {
  const ct = res.headers.get("content-type") || "";
  if (ct.includes("application/json")) {
    try {
      return await res.json();
    } catch {
      return null;
    }
  }
  try {
    return await res.text();
  } catch {
    return null;
  }
}

/**
 * Perform a request against the HACK backend.
 * Returns { status: "OK", data } on 2xx.
 * Returns { status: "PAYMENT_REQUIRED", challenge } on 402.
 * Throws HackBackendError on other failures.
 */
export async function hackRequest(path, { method = "GET", headers = {}, body, base } = {}) {
  const url = `${base || DEFAULT_BASE}${path}`;
  const init = {
    method,
    headers: {
      Accept: "application/json",
      ...(body ? { "Content-Type": "application/json" } : {}),
      ...headers,
    },
  };
  if (body !== undefined) init.body = typeof body === "string" ? body : JSON.stringify(body);

  let res;
  try {
    res = await fetch(url, init);
  } catch (err) {
    throw new HackBackendError(`Network error contacting HACK backend: ${err.message}`, {
      status: 0,
    });
  }

  const data = await parseBody(res);

  if (res.status === 402) {
    // x402 Payment Required. Backend returns the payment challenge in the body.
    return {
      status: "PAYMENT_REQUIRED",
      challenge: data,
      resource: path,
      method,
    };
  }

  if (!res.ok) {
    throw new HackBackendError(
      `HACK backend ${method} ${path} failed with ${res.status}`,
      { status: res.status, body: data },
    );
  }

  return { status: "OK", data };
}
