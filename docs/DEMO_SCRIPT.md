# Demo Script (< 5 minutes)

For judges and maintainers. Each step has an expected result.

---

## Setup (before demo)

```bash
cp .env.example .env   # fill in testnet credentials
./scripts/install.sh
# Terminal 1:
./scripts/start-backend.sh
# Terminal 2:
./scripts/start-frontend.sh
```

---

## Step 1 — Health check (10 s)

```bash
curl http://localhost:8000/api/health
```

Expected:
```json
{"status": "ok", "service": "Hedera Agent Commerce Kit"}
```

---

## Step 2 — Hit the premium endpoint without paying (20 s)

```bash
curl http://localhost:8000/api/premium-query
```

Expected: **HTTP 402** with `detail: "Missing X-Payment-Token or X-Quote-Id headers."`

---

## Step 3 — Request a payment challenge (20 s)

```bash
curl -s -X POST http://localhost:8000/api/payment/challenge \
  -H "Content-Type: application/json" \
  -d '{"endpoint": "/api/premium-query"}' | jq .
```

Expected: a `quote_id`, `resource_hash`, receiver account, amount, and expiry.

---

## Step 4 — Pay on testnet (60 s)

Open [HashPack](https://www.hashpack.app/) or the [Hedera Portal faucet](https://portal.hedera.com/faucet).
Send the specified HBAR to the receiver account with the memo from the challenge.
Copy the transaction ID (format: `0.0.XXXXX@XXXXXXXXXX.XXXXXXXXX`).

---

## Step 5 — Verify payment (20 s)

```bash
curl -s -X POST http://localhost:8000/api/payment/verify \
  -H "Content-Type: application/json" \
  -d '{"transaction_id": "<your-tx-id>", "quote_id": "<quote_id>"}' | jq .
```

Expected: `"verified": true`, receipt with HCS timestamp, and `grant_expires_at`.

---

## Step 6 — Retry premium endpoint (10 s)

```bash
curl -s http://localhost:8000/api/premium-query \
  -H "X-Payment-Token: <your-tx-id>" \
  -H "X-Quote-Id: <quote_id>" | jq .
```

Expected: **HTTP 200** with the premium result, receipt URL, and HashScan link.

---

## Step 7 — Replay protection (10 s)

```bash
# Same headers — should be rejected
curl -s http://localhost:8000/api/premium-query \
  -H "X-Payment-Token: <your-tx-id>" \
  -H "X-Quote-Id: <quote_id>"
```

Expected: **HTTP 402** — "This payment has already been consumed."

---

## Step 8 — View HCS receipt (10 s)

```bash
curl http://localhost:8000/api/receipt/<your-tx-id>
```

Then open the `hashscan_url` in a browser to show the immutable on-chain record.

---

## Step 9 — Usage metering (10 s)

```bash
curl http://localhost:8000/api/usage | jq .
```

Expected: total requests, total HBAR revenue, caller, endpoint, and timestamp.

---

## Total: ~2.5 minutes

The frontend at `http://localhost:3000` walks through the same flow visually.
