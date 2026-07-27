# hack/stores/

`QuoteStore` implementations — persistence layer for payment quotes.

## Files

### `memory.py` — `InMemoryQuoteStore`
The default implementation. Stores quotes in two in-process dicts:
- `_quotes: dict[str, Quote]` — keyed by `quote_id`
- `_tx_to_quote: dict[str, str]` — `transaction_id → quote_id` for duplicate detection

Suitable for single-process deployments and all tests.

## Swapping the store

To use a persistent store (e.g. Redis or Postgres), implement the `QuoteStore` interface:

```python
from hack.core.interfaces import QuoteStore
from hack.models.quote import Quote

class RedisQuoteStore(QuoteStore):
    def create_quote(self, quote: Quote) -> Quote: ...
    def get_quote(self, quote_id: str) -> Quote | None: ...
    def save_quote(self, quote: Quote) -> Quote: ...
    def list_quotes(self) -> list[Quote]: ...
    def sweep_expired(self) -> int: ...
```

Then inject it into `QuoteLifecycleService` and `ServiceContainer`:

```python
container = ServiceContainer(settings)
container._quote_store = RedisQuoteStore(redis_url="redis://localhost")
```
