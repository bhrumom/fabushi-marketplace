#!/usr/bin/env python3
import hashlib
import json
import os
import re
import shutil
import sys
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PKG = ROOT / "marketplace/packages/global-dharma/1.1.0"
SRC = PKG / "src"
OUT = Path(os.environ.get("GLOBAL_DHARMA_OUT", ROOT / "dist/global-dharma-1.1.0"))
REQUIRED = {
    "index.html": "text/html",
    "style.css": "text/css",
    "app.js": "text/javascript",
}
TOOLS = [
    "offline.capabilities",
    "offline.state.read",
    "offline.practice.record",
    "local.prayer-wheel.start",
]

def fail(message):
    raise SystemExit(message)

def load_json(path):
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)

source = load_json(PKG / "source.json")
catalog = load_json(PKG / "catalog.json")
if source != {
    "schemaVersion": 1,
    "appId": "global-dharma",
    "publisherId": "fabushi-official",
    "version": "1.1.0",
    "displayName": "全球法布施",
    "entrypoint": "index.html",
    "runtime": "web",
    "minHostApi": 1,
    "offlineCore": True,
    "requestedCapabilities": TOOLS,
    "networkPolicy": {"mode": "deny", "allowedOrigins": []},
}:
    fail("source.json is not the reviewed strict Global Dharma package contract")

if catalog.get("pluginId") != source["appId"] or catalog.get("version") != source["version"]:
    fail("catalog identity/version does not match source contract")
catalog_tools = catalog.get("tools")
if not isinstance(catalog_tools, list) or [item.get("name") for item in catalog_tools] != TOOLS:
    fail("catalog tool grant envelope is not the exact reviewed local tool set")
for item in catalog_tools:
    if item["name"] in {"offline.capabilities", "offline.state.read"}:
        if item.get("approval") != "none" or item.get("annotations", {}).get("readOnlyHint") is not True:
            fail("read-only tool must stay no-prompt/read-only")
    else:
        if item.get("approval") != "required" or item.get("annotations", {}).get("readOnlyHint") is not False:
            fail("mutation tool must require approval")

paths = sorted(path for path in SRC.rglob("*") if path.is_file())
if {path.relative_to(SRC).as_posix() for path in paths} != set(REQUIRED):
    fail("Global Dharma source resources must be exactly index.html, style.css, app.js")

html = (SRC / "index.html").read_text(encoding="utf-8")
js = (SRC / "app.js").read_text(encoding="utf-8")
all_text = html + "\n" + js + "\n" + (SRC / "style.css").read_text(encoding="utf-8")
if "connect-src 'none'" not in html:
    fail("offline CSP must deny all network connections")
if re.search(r"https?://", all_text, re.IGNORECASE):
    fail("offline package contains a remote URL")
for forbidden in ("fetch(", "XMLHttpRequest", "WebSocket", "EventSource", "navigator.sendBeacon"):
    if forbidden in js:
        fail("offline package contains a network primitive: " + forbidden)
for tool in TOOLS:
    registration = 'api.registerLocalTool({\\n      name: "' + tool + '"'
    if js.count(registration) != 1:
        fail("local page must register exactly one implementation for " + tool)
if 'api.call("local.prayer-wheel.start", {})' not in js:
    fail("manual protected action must return through the Host capability boundary")
if "localStorage" not in js or "next.revision = previous.revision + 1" not in js:
    fail("offline state must be durable with monotonic revision")
if "registerLocalTool" not in js or "fabushi:webmcp-ready" not in js:
    fail("page-local WebMCP registration lifecycle missing")

OUT.mkdir(parents=True, exist_ok=True)
candidate_root = OUT / "candidate"
if candidate_root.exists():
    shutil.rmtree(candidate_root)
candidate_root.mkdir()
files = {}
for path in paths:
    rel = path.relative_to(SRC).as_posix()
    data = path.read_bytes()
    files[rel] = {
        "sha256": hashlib.sha256(data).hexdigest(),
        "bytes": len(data),
        "mime": REQUIRED[rel],
    }
    shutil.copy2(path, candidate_root / rel)

unsigned_manifest = {
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
manifest_bytes = json.dumps(
    unsigned_manifest, ensure_ascii=False, sort_keys=True, separators=(",", ":")
).encode("utf-8")
(candidate_root / "manifest.unsigned.json").write_bytes(manifest_bytes + b"\n")
signing_payload = b"fabushi.fabapp.manifest.v1\x00" + manifest_bytes
(OUT / "signing-payload.bin").write_bytes(signing_payload)

candidate_archive = OUT / "global-dharma-1.1.0-unsigned-candidate.tar.gz"
with tarfile.open(candidate_archive, "w:gz", format=tarfile.PAX_FORMAT) as tar:
    for path in sorted(candidate_root.iterdir()):
        info = tar.gettarinfo(str(path), arcname=path.name)
        info.uid = info.gid = 0
        info.uname = info.gname = ""
        info.mtime = 0
        with path.open("rb") as handle:
            tar.addfile(info, handle)

archive_data = candidate_archive.read_bytes()
evidence = {
    "schemaVersion": 1,
    "status": "unsigned-candidate-not-installable",
    "appId": source["appId"],
    "publisherId": source["publisherId"],
    "version": source["version"],
    "sourceCommit": os.environ.get("GITHUB_SHA"),
    "tools": TOOLS,
    "resources": files,
    "candidateArchive": {
        "path": candidate_archive.name,
        "sha256": hashlib.sha256(archive_data).hexdigest(),
        "bytes": len(archive_data),
    },
    "productionSigning": {
        "required": True,
        "algorithm": "Ed25519",
        "status": "blocked",
        "reason": "trusted Marketplace signing/OIDC owner required; test keys are forbidden",
    },
}
(OUT / "candidate-evidence.json").write_text(
    json.dumps(evidence, ensure_ascii=False, indent=2) + "\n",
    encoding="utf-8",
)
print(json.dumps(evidence, ensure_ascii=False, indent=2))
