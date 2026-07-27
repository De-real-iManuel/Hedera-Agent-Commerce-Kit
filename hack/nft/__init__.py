"""
hack/nft
---------
Soulbound NFT minting for HACK compliance certificates.

Uses Hedera Token Service via hiero-sdk-python. On first use, auto-creates
a non-fungible token collection under the operator's treasury and persists
the token ID to .hack_state.json in the current working directory.
"""

from __future__ import annotations

from .service import NftMintingService, NftMintResult

__all__ = ["NftMintingService", "NftMintResult"]
