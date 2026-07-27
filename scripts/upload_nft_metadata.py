"""
scripts/upload_nft_metadata.py
-------------------------------
Uploads the HIP-412 compliant metadata JSON to IPFS via Pinata,
then mints a new NFT using the returned metadata CID.

Usage:
    python scripts/upload_nft_metadata.py --jwt YOUR_PINATA_JWT

Or set PINATA_JWT in .env and run:
    python scripts/upload_nft_metadata.py

The uploaded metadata JSON follows the HIP-412 / OpenSea metadata standard:
https://hips.hedera.com/hip/hip-412
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv
load_dotenv()

import httpx

# ── Constants ─────────────────────────────────────────────────────────────────

IMAGE_CID = "bafkreibh2ykv3qibpw77y653o6fdqamymdaiwy5cxw5vbjqya3e4giykle"
IMAGE_IPFS_URI = f"ipfs://{IMAGE_CID}"
IMAGE_GATEWAY_URL = f"https://fuchsia-worrying-chickadee-416.mypinata.cloud/ipfs/{IMAGE_CID}"

# HIP-412 compliant metadata JSON
METADATA_JSON = {
    "name": "HACK Compliance Certificate",
    "description": (
        "Soulbound x402 Compliance Certificate issued by the "
        "Hedera Agent Commerce Kit (HACK). "
        "This NFT is proof that the holder's wallet paid for and passed "
        "automated compliance analysis of an x402-powered service on Hedera. "
        "Non-transferable by design."
    ),
    "image": IMAGE_IPFS_URI,
    "external_url": "https://github.com/De-real-iManuel/Hedera-Agent-Commerce-Kit",
    "type": "image/png",
    "format": "HIP412@2.0.0",
    "properties": {
        "collection": {
            "name": "HACK Compliance Certificates",
            "creator": "Hedera Agent Commerce Kit"
        }
    },
    "attributes": [
        {"trait_type": "Standard",        "value": "HTTP 402 (x402)"},
        {"trait_type": "Network",         "value": "Hedera Testnet"},
        {"trait_type": "Transferable",    "value": "No — Soulbound"},
        {"trait_type": "Framework",       "value": "HACK v1.0.0"},
        {"trait_type": "Issuer",          "value": "Hedera Agent Commerce Kit"},
        {"trait_type": "Certificate Type","value": "Compliance Assessment"},
    ],
    "localization": {
        "uri":     f"ipfs://{IMAGE_CID}/{{locale}}.json",
        "default": "en",
        "locales": ["en"]
    }
}


def upload_to_pinata(jwt: str) -> str:
    """Upload the metadata JSON to Pinata and return the IPFS CID."""
    print("Uploading HIP-412 metadata JSON to Pinata IPFS...")

    headers = {
        "Authorization": f"Bearer {jwt}",
        "Content-Type": "application/json",
    }
    payload = {
        "pinataContent": METADATA_JSON,
        "pinataMetadata": {
            "name": "HACK-Compliance-Certificate-Metadata.json",
            "keyvalues": {
                "project": "Hedera-Agent-Commerce-Kit",
                "type": "nft-metadata",
                "version": "1.0.0",
            }
        },
        "pinataOptions": {"cidVersion": 1},
    }

    with httpx.Client(timeout=30.0) as client:
        resp = client.post(
            "https://api.pinata.cloud/pinning/pinJSONToIPFS",
            headers=headers,
            json=payload,
        )

    if resp.status_code != 200:
        print(f"Pinata error {resp.status_code}: {resp.text}")
        sys.exit(1)

    data = resp.json()
    cid = data["IpfsHash"]
    print(f"Metadata uploaded successfully!")
    print(f"  CID     : {cid}")
    print(f"  IPFS URI: ipfs://{cid}")
    print(f"  Gateway : https://gateway.pinata.cloud/ipfs/{cid}")
    return cid


def update_env_and_service(metadata_cid: str) -> None:
    """Update .hack_state.json with the metadata CID."""
    from hack.nft.service import _read_state, _write_state, STATE_FILE
    state = _read_state()
    state["nft_metadata_cid"] = metadata_cid
    state["nft_metadata_uri"] = f"ipfs://{metadata_cid}"
    _write_state(state)
    print(f"\nSaved metadata CID to {STATE_FILE}")


def mint_test_nft(metadata_cid: str) -> None:
    """Mint a test NFT with the new metadata CID to verify it renders."""
    from hack.container import ServiceContainer
    container = ServiceContainer.from_settings()
    s = container.settings
    svc = container.nft_service

    # Temporarily override _pack_metadata to use the new CID
    metadata_uri = f"ipfs://{metadata_cid}"
    print(f"\nMinting test NFT with metadata URI: {metadata_uri}")
    print(f"URI size: {len(metadata_uri.encode())} bytes (limit: 100)")

    metadata = {
        "score": 95.0, "grade": "A+",
        "report_id": "metadata-test-final",
        "agent_name": "HACK Compliance Certificate",
        "service_type": "x402",
        "issued_at": int(time.time()),
        "recipient": s.hedera_operator_id,
        "network": s.hedera_network,
    }

    import hashlib
    meta_json = json.dumps(metadata, separators=(",", ":"), sort_keys=True)
    metadata_hash = hashlib.sha256(meta_json.encode()).hexdigest()

    # Directly use the metadata URI as the on-chain bytes
    on_chain_bytes = metadata_uri.encode("utf-8")
    if len(on_chain_bytes) > 100:
        print(f"WARNING: URI is {len(on_chain_bytes)} bytes — truncating to 100")
        on_chain_bytes = on_chain_bytes[:100]

    # Call the low-level mint directly
    client, _, _ = svc._build_client()
    tx_id, serial = svc._submit_mint(client, svc._token_id, [on_chain_bytes])

    if serial == 0:
        print("WARNING: Serial is 0 — check HashScan for status")
    else:
        print(f"\nSUCCESS — Serial #{serial}")
        print(f"Mint TX : {tx_id}")
        print(f"\nView on HashScan:")
        print(f"  NFT : https://hashscan.io/{s.hedera_network}/token/{svc._token_id}/{serial}")
        print(f"  TX  : https://hashscan.io/{s.hedera_network}/transaction/{tx_id}")
        print(f"\nHashScan should now render the certificate image.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Upload NFT metadata to IPFS and mint")
    parser.add_argument("--jwt", default=os.environ.get("PINATA_JWT", ""),
                        help="Pinata JWT token")
    parser.add_argument("--cid", default="",
                        help="Skip upload — use this existing metadata CID directly")
    parser.add_argument("--mint-only", action="store_true",
                        help="Only mint, skip upload (requires --cid)")
    args = parser.parse_args()

    if args.cid:
        metadata_cid = args.cid
        print(f"Using existing metadata CID: {metadata_cid}")
    elif args.jwt:
        # Show what we're uploading
        print("Metadata JSON to upload:")
        print(json.dumps(METADATA_JSON, indent=2))
        print()
        metadata_cid = upload_to_pinata(args.jwt)
        update_env_and_service(metadata_cid)
    else:
        print("ERROR: Provide --jwt YOUR_PINATA_JWT or --cid EXISTING_CID")
        print()
        print("Get your Pinata JWT from: https://app.pinata.cloud/keys")
        print()
        print("Metadata JSON that will be uploaded:")
        print(json.dumps(METADATA_JSON, indent=2))
        sys.exit(1)

    if not args.mint_only or args.cid:
        mint_test_nft(metadata_cid)


if __name__ == "__main__":
    main()
