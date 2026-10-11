# Global Dharma offline .fabapp package

Status: IN PROGRESS
Updated: 2026-10-11

## Purpose

Make `global-dharma` the first production offline-first Marketplace Mini App package consumed by the canonical Fabushi Mini App host. The package must contain its own free UI, local state, and page-owned WebMCP tools. It must not depend on the legacy remote Global Dharma MCP service to render or execute free local functions.

This Spec owns Marketplace package source and package metadata only. iOS Host/WebKit/session/entitlement enforcement remains owned by `fabushi-ios/fabushi-ios`; service entitlement/payment remains owned by the canonical backend/commerce repositories.

## Authority and migration facts

- Canonical Marketplace repository: `bhrumom/fabushi-marketplace`.
- Legacy `bhrumom/fabushi` package `global-dharma@1.0.0` is provenance only.
- The legacy 1.0.0 archive contains only `fabushi-miniapp.json` and `index.html`, declares a remote MCP URL, permits HTTPS network connections, and does not register local WebMCP tools or persist real local business state.
- New package version is `1.1.0`; the old immutable 1.0.0 asset must not be overwritten.

## Package contract

Source directory:

`marketplace/packages/global-dharma/1.1.0/src/`

Generated artifact:

`global-dharma-1.1.0.fabapp` (canonical OMA-001 catalog package consumed by the strict iOS `.fabapp` verifier). The historical `fabushi.miniapp.package.v1` tar manifest is migration provenance only and is not the new package contract.

Required files:

- `manifest.json` — generated/pinned strict catalog manifest v1
- `index.html`
- `style.css`
- `app.js`

The package must contain no remote CSS, JS, images, fonts, or Wasm for its free path. CSP must use `connect-src 'none'`.

## Offline business state

The package owns one durable local state document in the account-scoped WebKit data store:

- schemaVersion
- revision (monotonic integer)
- freeActionCount
- prayerWheelStartCount
- lastAction
- updatedAt

Every mutation increments revision exactly once and synchronously updates both persisted storage and visible UI. Reload must recover the same revision and values.

The Web page may use `localStorage` because the iOS Host provides an account-scoped persistent `WKWebsiteDataStore`. The page must not receive Fabushi account tokens, Keychain access, or arbitrary files.

## WebMCP tools

The running page registers the following tools through `window.__fabushiWebMcp.registerLocalTool`:

| Tool | Kind | Network | Host approval / entitlement |
|---|---|---|---|
| `offline.capabilities` | read | none | read-only |
| `offline.state.read` | read | none | read-only |
| `offline.practice.record` | mutation | none | mutation approval |
| `local.prayer-wheel.start` | protected mutation | entitlement check only in Host | mutation approval + fresh entitlement |

The page never performs entitlement or payment requests itself. The iOS Host must reject `local.prayer-wheel.start` unless current server-authoritative entitlement allows the exact capability. Free tools must not inherit that network preflight.

## WebMCP lifecycle

- Register only after the Fabushi bridge announces ready.
- Registration must be per page load and automatically disappear when the WebView/session is disposed.
- Tool execution returns the state revision produced/read by the actual page.
- Manual UI actions and WebMCP calls operate on the same state object.
- No remote fallback may be advertised as local execution.

## Marketplace metadata

The release metadata must advertise the exact four local tools above so the iOS Host grant envelope can intersect with page registration. Tool permissions must distinguish read-only from mutation/protected mutation.

The strict `manifest.json` fields are exactly those accepted by the iOS verifier: `manifestVersion`, `packageClass`, `appId`, `publisherId`, `version`, `displayName`, `entrypoint`, `runtime`, `minHostApi`, `offlineCore`, `requestedCapabilities`, `networkPolicy`, `files`, and `signature`. For Global Dharma: `runtime="web"`, `offlineCore=true`, and `networkPolicy={"mode":"deny","allowedOrigins":[]}`.

`files` is generated from the exact resource bytes and contains SHA-256, byte count and MIME for every resource. Catalog installation is fail-closed unless the manifest carries an Ed25519 signature from the trusted publisher/key registered by the Host. The signing payload is the verifier's `fabushi.fabapp.manifest.v1\\0` domain separator plus canonical manifest JSON with `signature` removed.

The package source is immutable by version. Resource digests, final manifest, package digest/size and production signature are produced on GitHub Actions/trusted release infrastructure only and then pinned in Marketplace release metadata. No local or persistent-device packaging is permitted. A PR build may produce an unsigned candidate manifest/resource bundle for inspection, but it must never be named or accepted as a production `.fabapp`.

## GitHub Actions

A dedicated workflow must:

1. checkout exact source;
2. validate source identity/version/entry/runtime and strict manifest-v1 inputs;
3. reject remote URL references and reject CSP/network capability on the free path;
4. validate required local WebMCP registrations;
5. calculate every resource SHA-256/bytes/MIME and generate the unsigned strict manifest candidate;
6. on an authorized protected release, obtain the trusted Ed25519 signature through the platform trusted signer/OIDC path and create final `manifest.json`;
7. build the deterministic `.fabapp`, then verify archive entries, manifest signature, SHA-256 and byte size;
8. upload the archive plus machine-readable release metadata/provenance as Actions artifacts;
9. when expected digest/size are pinned, fail closed on mismatch.

Until the trusted Marketplace signing/OIDC owner is available, steps 6-9 for a production-signed package are BLOCKED; source-contract CI must still run and pass without inventing a test signer.

No local build/package/test may substitute for this evidence.

## Acceptance

- GD-PKG-01: deterministic package generated by Actions from exact source.
- GD-PKG-02: archive contains all required local resources and no remote runtime dependency for free functions.
- GD-PKG-03: `offline.capabilities`, `offline.state.read`, `offline.practice.record`, and `local.prayer-wheel.start` registrations are statically validated.
- GD-PKG-04: manual free mutation and WebMCP mutation share one persisted revision state implementation.
- GD-PKG-05: Marketplace release metadata pins exact version, SHA-256, size, entry and tool grant envelope.
- GD-PKG-06: backend catalog consumption of this canonical Marketplace release is separately verified; package construction alone does not imply production catalog rollout.

## Compliance record

| Criterion | Status | Evidence |
|---|---|---|
| Spec exists before package implementation | passed | this file |
| 1.1.0 source package | pending | |
| Actions-only source candidate packaging | pending | |
| Trusted catalog Ed25519 signing | blocked | canonical trusted Marketplace signing/OIDC owner not yet available; no test key may substitute |
| Local free WebMCP tools | pending | |
| Protected capability declared | pending | |
| Digest/size pinned | pending | |
| Backend catalog consumes canonical release | blocked | must verify/update backend integration |
| iOS live same-instance execution | out-of-scope here | owned by iOS PR #3 |
