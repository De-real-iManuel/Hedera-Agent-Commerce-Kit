# hack/verifiers/

`PaymentVerifier` implementations — on-chain payment confirmation.

## Files

### `mirror_node.py` — `MirrorNodeVerifier`
Verifies HBAR transfers via the [Hedera Mirror Node REST API](https://docs.hedera.com/hedera/sdks-and-apis/rest-api).

```python
from hack.verifiers.mirror_node import MirrorNodeVerifier

verifier = MirrorNodeVerifier(
    base_url="https://testnet.mirrornode.hedera.com",
    timeout=15,
)

tx_data = await verifier.verify(
    transaction_id="0.0.1234@1700000000.000000000",
    receiver="0.0.9999",
    min_tinybars=50_000_000,   # 0.5 HBAR
    network="testnet",
)
```

**TX ID normalisation:** `0.0.1234@1700000000.000000000` → `0.0.1234-1700000000-000000000` (account dots preserved; `@` becomes `-`).

**Error handling:**
| Condition | Exception |
|---|---|
| 404 from Mirror Node | `ValueError` with "Mirror Node lag ~3s" hint |
| 5xx from Mirror Node | `VerifierUnavailableError` (retryable) |
| `received < min_tinybars` | `InsufficientPaymentError` |
| Wrong receiver | `InsufficientPaymentError` |

Mirror Node can lag ~3 seconds behind consensus. Callers should surface a retryable `502` to clients on `ValueError`, not a hard `400`.
