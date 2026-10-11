#!/usr/bin/env python3
import argparse
import base64
import hashlib
import json
import os
import subprocess
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PKG = ROOT / "marketplace/packages/global-dharma/1.1.0"
SRC = PKG / "src"
SOURCE = PKG / "source.json"
MIME = {
    "index.html": "text/html",
    "style.css": "text/css",
    "app.js": "text/javascript",
}
DOMAIN = b"fabushi.fabapp.manifest.v1\x00"
SPKI_ED25519_PREFIX = bytes.fromhex("302a300506032b6570032100")

def die(message):
    raise SystemExit(message)

def b64url_decode(value):
    value = str(value)
    return base64.urlsafe_b64decode(value + "=" * ((4 - len(value) % 4) % 4))

def canonical_json(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")

def expected_unsigned_manifest():
    source = json.loads(SOURCE.read_text(encoding="utf-8"))
    files = {}
    actual = sorted(p for p in SRC.rglob("*") if p.is_file())
    if {p.relative_to(SRC).as_posix() for p in actual} != set(MIME):
        die("unexpected Global Dharma resource set")
    for path in actual:
        rel = path.relative_to(SRC).as_posix()
        data = path.read_bytes()
        files[rel] = {
            "sha256": hashlib.sha256(data).hexdigest(),
            "bytes": len(data),
            "mime": MIME[rel],
        }
    return {
        "manifestVersion": 1,
        "packageClass": "catalog",
        "appId": source["appId"],
        "publisherId": source["publisherId"],
        "version": source["version"],
        "displayName": source["displayName"],
        "entrypoint": source["entrypoint"],
        "runtime": source["runtime"],
        "minHostApi": source["minHostApi"],
        "offlineCore": source["offlineCore"],
        "requestedCapabilities": source["requestedCapabilities"],
        "networkPolicy": source["networkPolicy"],
        "files": files,
    }

def verify_signature(unsigned, signature, trust):
    if signature.get("algorithm") != "Ed25519":
        die("signed manifest algorithm must be Ed25519")
    if signature.get("keyId") != trust.get("keyId"):
        die("signed manifest keyId does not match returned trust")
    raw_key = b64url_decode(trust.get("rawPublicKeyBase64URL", ""))
    raw_sig = b64url_decode(signature.get("value", ""))
    if len(raw_key) != 32 or len(raw_sig) != 64:
        die("invalid raw Ed25519 key/signature size")
    payload = DOMAIN + canonical_json(unsigned)
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        (td / "key.der").write_bytes(SPKI_ED25519_PREFIX + raw_key)
        (td / "sig.bin").write_bytes(raw_sig)
        (td / "payload.bin").write_bytes(payload)
        verified = subprocess.run(
            [
                "openssl", "pkeyutl", "-verify", "-rawin", "-pubin",
                "-inkey", str(td / "key.der"), "-keyform", "DER",
                "-sigfile", str(td / "sig.bin"), "-in", str(td / "payload.bin"),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        if verified.returncode != 0:
            die("Backend-managed Ed25519 signature did not verify: " + verified.stderr.strip())
    return payload

def build_deterministic_fabapp(output_path, manifest_bytes):
    output_path.parent.mkdir(parents=True, exist_ok=True)
    entries = [("manifest.json", manifest_bytes)]
    entries.extend((rel, (SRC / rel).read_bytes()) for rel in sorted(MIME))
    with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_STORED, allowZip64=False) as archive:
        for name, data in entries:
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_STORED
            info.create_system = 3
            info.external_attr = (0o100644 << 16)
            archive.writestr(info, data)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--signed-response", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--source-sha", default=os.environ.get("GITHUB_SHA"))
    parser.add_argument("--signing-environment", choices=["test", "production"], required=True)
    args = parser.parse_args()

    response = json.loads(Path(args.signed_response).read_text(encoding="utf-8"))
    signed = response.get("manifest")
    trust = response.get("trust")
    if not isinstance(signed, dict) or not isinstance(trust, dict):
        die("signing response must contain manifest and trust")
    signature = signed.get("signature")
    if not isinstance(signature, dict):
        die("signed manifest is missing signature")
    unsigned = dict(signed)
    unsigned.pop("signature", None)
    expected = expected_unsigned_manifest()
    if unsigned != expected:
        die("signed manifest does not exactly match current reviewed resources/source contract")

    payload = verify_signature(unsigned, signature, trust)
    manifest_bytes = canonical_json(signed)
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "manifest.json").write_bytes(manifest_bytes + b"\n")
    (out / "signing-payload.bin").write_bytes(payload)
    (out / "trust.json").write_text(
        json.dumps(trust, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )

    fabapp = out / "global-dharma-1.1.0.fabapp"
    build_deterministic_fabapp(fabapp, manifest_bytes)
    package = fabapp.read_bytes()
    evidence = {
        "schemaVersion": 1,
        "appId": expected["appId"],
        "publisherId": expected["publisherId"],
        "version": expected["version"],
        "sourceSha": args.source_sha,
        "signingEnvironment": args.signing_environment,
        "signature": {
            "algorithm": signature["algorithm"],
            "keyId": signature["keyId"],
            "trustEpoch": trust.get("trustEpoch"),
            "publicKeyFingerprint": trust.get("publicKeyFingerprint"),
        },
        "package": {
            "filename": fabapp.name,
            "sha256": hashlib.sha256(package).hexdigest(),
            "bytes": len(package),
        },
        "resources": expected["files"],
    }
    (out / "release-evidence.json").write_text(
        json.dumps(evidence, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(evidence, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
