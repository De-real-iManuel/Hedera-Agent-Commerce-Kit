# hack/models/

Pydantic v2 domain models — the shared type vocabulary for the entire toolkit.

All models use `BaseModel` with `model_config = ConfigDict(frozen=False)`. Every API response, state object, and service return value is typed here.

## Files

| File | Models |
|---|---|
| `quote.py` | `PaymentStatus`, `Quote`, `ChallengeResponse`, `VerifyResponse`, `ReceiptModel`, `UsageRecord`, `UsageSummary` |
| `compliance.py` | `ComplianceRule`, `ComplianceCheckResult`, `CertificationReport` |

## Key types

```python
from hack.models.quote import Quote, PaymentStatus, ReceiptModel
from hack.models.compliance import ComplianceCheckResult, CertificationReport

# PaymentStatus enum
PaymentStatus.QUOTED    # challenge issued
PaymentStatus.VERIFIED  # Mirror Node confirmed
PaymentStatus.GRANTED   # access window open
PaymentStatus.CONSUMED  # result delivered (exactly once)
PaymentStatus.EXPIRED   # TTL elapsed
PaymentStatus.DUPLICATE # tx_id reused on different quote
```

## Why Pydantic models (not dataclasses)

- Automatic validation on assignment
- JSON serialization for API responses out of the box
- IDE autocomplete and type checking via `py.typed`
- Compatible with FastAPI response models
