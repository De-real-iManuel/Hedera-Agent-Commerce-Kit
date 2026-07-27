# hack/core/

The domain logic layer — interfaces, exceptions, and the payment state machine.

Nothing in `core/` imports from concrete implementations. This is the dependency inversion boundary.

## Files

### `interfaces.py`
Abstract base classes that every concrete implementation must satisfy:

| Interface | Implementations |
|---|---|
| `QuoteStore` | `hack.stores.memory.InMemoryQuoteStore` |
| `PaymentVerifier` | `hack.verifiers.mirror_node.MirrorNodeVerifier` |
| `ReceiptService` | `hack.receipts.hcs.HCSReceiptService`, `hack.receipts.memory.InMemoryReceiptService` |
| `MeteringService` | `hack.metering.service.InMemoryMeteringService` |

### `exceptions.py`
Typed exception hierarchy — catch specific errors instead of bare `ValueError`:

```
HACKError
├── PaymentExpiredError   — quote or grant TTL elapsed
├── ReplayError           — tx_id reused on a different quote
├── InsufficientPaymentError — underpayment detected
├── VerifierUnavailableError — Mirror Node 5xx (retryable)
├── AlreadyConsumedError  — quote already consumed
└── QuoteNotFoundError    — unknown quote_id
```

### `quote_lifecycle.py`
`QuoteLifecycleService` — the authoritative state machine.

```python
from hack.core.quote_lifecycle import QuoteLifecycleService
from hack.stores.memory import InMemoryQuoteStore

lifecycle = QuoteLifecycleService(store=InMemoryQuoteStore())

quote = lifecycle.create_quote("/api/report", amount_hbar=0.5, receiver="0.0.123")
# quote.status == PaymentStatus.QUOTED

lifecycle.advance_to_verified(quote.quote_id, "0.0.123@1700000000.000000000")
lifecycle.advance_to_granted(quote.quote_id)
lifecycle.advance_to_consumed(quote.quote_id)
# quote.status == PaymentStatus.CONSUMED
```

The service itself has no storage — it delegates to the injected `QuoteStore`, making it fully testable.
