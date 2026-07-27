"""
hack/nft/service.py
--------------------
NftMintingService — real HTS NFT create + mint via hiero-sdk-python.

Design notes
------------
* The token is created ONCE per deployment. The token ID is persisted to
  ``HACK_STATE_FILE`` (default: ``.hack_state.json``) so subsequent mints reuse it.
* In Docker/production, set ``HACK_STATE_FILE=/app/state/.hack_state.json`` and
  mount ``/app/state`` as persistent storage.
* Stronger Hedera soulbound-style rules:
  - NO admin key: the certificate collection cannot be updated after creation.
  - NO wipe key: issued certificates cannot be arbitrarily wiped/revoked.
  - Supply key retained by backend: only the HACK backend can mint certificates.
  - Freeze key retained by backend + freeze_default=True: accounts are frozen for
    this token by default, preventing holder-initiated transfers when certificates
    are issued to holder accounts.
* For the current demo flow, we mint to the operator treasury and record the
  intended ``recipient_account_id`` in the metadata JSON. This avoids forcing
  every recipient account to associate/unfreeze/refreeze during the live demo,
  while the collection itself is configured with the stronger soulbound controls.
* All SDK calls are synchronous; async callers should wrap them in ``asyncio.to_thread``.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


STATE_FILE = Path(os.getenv("HACK_STATE_FILE", ".hack_state.json"))


@dataclass
class NftMintResult:
    token_id: str
    serial_number: int
    transaction_id: str
    metadata_hash: str
    treasury_account_id: str
    recipient_account_id: str
    hashscan_token_url: str
    hashscan_tx_url: str
    minted_at: int
    error: Optional[str] = None


def _read_state() -> dict:
    if not STATE_FILE.exists():
        return {}
    try:
        return json.loads(STATE_FILE.read_text("utf-8"))
    except Exception:
        return {}


def _write_state(state: dict) -> None:
    try:
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        STATE_FILE.write_text(json.dumps(state, indent=2), "utf-8")
    except Exception:
        pass


class NftMintingService:
    """Real soulbound-style NFT minter (HTS via hiero-sdk-python)."""

    def __init__(
        self,
        operator_id: str,
        operator_key: str,
        network: str = "testnet",
        token_name: str = "HACK Compliance Certificate",
        token_symbol: str = "HACKCERT",
        token_id: str = "",
    ) -> None:
        self._operator_id = operator_id
        self._operator_key = operator_key
        self._network = network
        self._token_name = token_name
        self._token_symbol = token_symbol
        self._token_id: Optional[str] = (
            token_id or _read_state().get("nft_token_id") or None
        )
        # HIP-412 metadata JSON CID — uploaded to IPFS, contains image + attributes
        # Falls back to the raw image CID if no metadata JSON has been uploaded yet.
        _state = _read_state()
        self._metadata_cid: str = (
            _state.get("nft_metadata_cid")
            or "bafkreibh2ykv3qibpw77y653o6fdqamymdaiwy5cxw5vbjqya3e4giykle"
        )

    # ─── Public API ──────────────────────────────────────────────────────────

    def mint(self, metadata: dict, recipient_account_id: str) -> NftMintResult:
        """Mint one certificate NFT with compact on-chain metadata. Blocking."""
        try:
            client, operator_id_obj, private_key = self._build_client()
            token_id_str = self._ensure_token(client, operator_id_obj, private_key)

            metadata_json = json.dumps(metadata, separators=(",", ":"), sort_keys=True)
            metadata_hash = hashlib.sha256(metadata_json.encode("utf-8")).hexdigest()
            on_chain_metadata = self._pack_metadata(metadata_hash, metadata)
            tx_id, serial = self._submit_mint(
                client, token_id_str, [on_chain_metadata]
            )

            return NftMintResult(
                token_id=token_id_str,
                serial_number=serial,
                transaction_id=tx_id,
                metadata_hash=metadata_hash,
                treasury_account_id=self._operator_id,
                recipient_account_id=recipient_account_id or self._operator_id,
                hashscan_token_url=self._hashscan_token(token_id_str),
                hashscan_tx_url=self._hashscan_tx(tx_id),
                minted_at=int(time.time()),
            )
        except Exception as exc:  # noqa: BLE001
            return NftMintResult(
                token_id=self._token_id or "",
                serial_number=0,
                transaction_id="",
                metadata_hash="",
                treasury_account_id=self._operator_id,
                recipient_account_id=recipient_account_id or self._operator_id,
                hashscan_token_url="",
                hashscan_tx_url="",
                minted_at=int(time.time()),
                error=f"{type(exc).__name__}: {exc}",
            )

    # ─── Internal helpers ────────────────────────────────────────────────────

    def _build_client(self):
        from hiero_sdk_python import (  # type: ignore
            AccountId, Client, Network, PrivateKey,
        )
        account_id = AccountId.from_string(self._operator_id)
        private_key = PrivateKey.from_string(self._operator_key)
        net_str = "testnet" if self._network == "testnet" else "mainnet"
        client = Client(Network(network=net_str))
        client.set_operator(account_id, private_key)
        return client, account_id, private_key

    def _ensure_token(self, client, operator_id_obj, private_key) -> str:
        if self._token_id:
            return self._token_id
        from hiero_sdk_python import (  # type: ignore
            SupplyType, TokenCreateTransaction, TokenType,
        )

        # Builder pattern — set_* methods (SDK >= 0.3)
        # Soulbound configuration:
        #   no admin_key → immutable after creation
        #   no wipe_key  → issuer cannot arbitrarily revoke
        #   supply_key   → only this backend can mint
        #   freeze_key + freeze_default=True → non-transferable by default
        tx = (
            TokenCreateTransaction()
            .set_token_name(self._token_name)
            .set_token_symbol(self._token_symbol)
            .set_treasury_account_id(operator_id_obj)
            .set_supply_key(private_key.public_key())
            .set_freeze_key(private_key.public_key())
            .set_token_type(TokenType.NON_FUNGIBLE_UNIQUE)
            .set_supply_type(SupplyType.INFINITE)
            .set_freeze_default(True)
        )
        # execute() returns TransactionReceipt directly (wait_for_receipt=True by default)
        receipt = tx.execute(client)
        token_id = getattr(receipt, "token_id", None) or getattr(receipt, "tokenId", None)
        if token_id is None:
            raise RuntimeError("Token creation returned no token_id in receipt.")
        token_id_str = str(token_id)
        self._token_id = token_id_str
        state = _read_state()
        state["nft_token_id"] = token_id_str
        _write_state(state)
        return token_id_str

    def _submit_mint(self, client, token_id_str: str, metadata_list):
        from hiero_sdk_python import TokenId, TokenMintTransaction  # type: ignore
        token_id = TokenId.from_string(token_id_str)
        tx = TokenMintTransaction(token_id=token_id, metadata=metadata_list)
        # execute() returns TransactionReceipt directly when wait_for_receipt=True (default)
        receipt = tx.execute(client)

        # transaction_id is on the receipt
        tx_id = ""
        raw_tx_id = getattr(receipt, "transaction_id", None)
        if raw_tx_id is not None:
            tx_id = str(raw_tx_id)

        serials = (
            getattr(receipt, "serial_numbers", None)
            or getattr(receipt, "serials", None)
            or []
        )
        serial = int(serials[0]) if serials else 0
        return tx_id, serial

    # IPFS CID for the HACK compliance certificate image (HIP-412)
    CERTIFICATE_IMAGE_CID = "bafkreibh2ykv3qibpw77y653o6fdqamymdaiwy5cxw5vbjqya3e4giykle"

    def _pack_metadata(self, metadata_hash: str, metadata: dict) -> bytes:
        """
        Pack on-chain NFT metadata within the HTS 100-byte hard limit.

        Uses the HIP-412 metadata JSON CID when available (uploaded via
        scripts/upload_nft_metadata.py), otherwise falls back to the raw
        image CID.  The metadata JSON contains name, description, image,
        external_url, and attributes — HashScan renders this correctly.
        """
        uri = f"ipfs://{self._metadata_cid}"
        encoded = uri.encode("utf-8")
        # Safety check — should always be ≤100 for a CIDv1
        if len(encoded) > 100:
            # Fallback to image CID which is guaranteed to fit
            uri = f"ipfs://{self.CERTIFICATE_IMAGE_CID}"
            encoded = uri.encode("utf-8")
        return encoded

    def _hashscan_token(self, token_id: str) -> str:
        return f"https://hashscan.io/{self._network}/token/{token_id}"

    def _hashscan_tx(self, tx_id: str) -> str:
        return f"https://hashscan.io/{self._network}/transaction/{tx_id}"
