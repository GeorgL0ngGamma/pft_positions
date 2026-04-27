# pft_positions

Public v0 specification for machine-readable position snapshots that Task Node agents can consume as shared group state.

This repository defines:
- Canonical schema for a position snapshot (`schema/position-snapshot.v0.schema.json`)
- Provenance and normalization conventions (`schema/README.md`)
- Authoritative executable fixture corpus (`fixtures/`)
- Python reference package and CLI (`pft-positions`)
- Exactly three v0 example payloads:
  - `schema/examples/delta-one.example.json`
  - `schema/examples/option.example.json`
  - `schema/examples/yield.example.json`

The v0 scope is intentionally narrow and implementation-ready so future adapter work (for example, CCXT-based exchange adapters) can plug into stable field names and semantics. v0 instrument categories are `linear`, `option`, and `yield`.

v0 is intentionally limited to position sharing. Trend/contrarian/churn/sentiment/strategy signal components are not part of this schema and can be added in a future version.

## Python reference package

```bash
python3 -m pytest
PYTHONPATH=src python3 -m pft_positions.cli validate fixtures
PYTHONPATH=src python3 -m pft_positions.cli parse fixtures/delta-one.json
PYTHONPATH=src python3 -m pft_positions.cli emit delta-one
```

After installing the package, the same CLI is available as:

```bash
pft-positions validate fixtures
pft-positions parse fixtures/delta-one.json
pft-positions emit delta-one
```

The `validate` command validates JSON syntax, the v0 schema, and `provenance.content_hash`. `parse` is fixture-backed and prints canonical JSON for a valid snapshot. `emit` prints one of the bundled reference fixtures: `delta-one`, `hyperliquid-hlp-child`, `option`, or `yield`.

## Fixture corpus

`fixtures/` is the authoritative executable corpus for package tests and CLI validation. `schema/examples/` remains as documentation examples for the published schema.

Normalized fixtures:

- `fixtures/delta-one.json`
- `fixtures/hyperliquid-hlp-child.json`
- `fixtures/option.json`
- `fixtures/yield.json`

Paired raw fixtures:

- `fixtures/raw/delta-one.raw.json` normalizes to `fixtures/delta-one.json`
- `fixtures/raw/hyperliquid-hlp-child.raw.json` normalizes to `fixtures/hyperliquid-hlp-child.json`
- `fixtures/raw/option.raw.json` normalizes to `fixtures/option.json`
- `fixtures/raw/yield.raw.json` normalizes to `fixtures/yield.json`

The Hyperliquid fixture is a full delta-one/linear test case from public HLP child account `0x010461c14e146ac35fe42271bdc1134ee31c703a`. The raw fixture records the public HLP vault context used to identify whale addresses, including the HLP vault `0xdfc24b077bc1425ad1dea75bcb6f8158e10df303`, child accounts, and top public followers by vault equity. The normalized fixture contains all 190 open positions returned by Hyperliquid `clearinghouseState` at the captured `as_of` timestamp.

## Sharing and ingestion

Snapshots are plain JSON and can be shared in three compatible ways:

- Manual sharing: paste or attach the canonical JSON produced by `pft-positions parse`.
- TaskNode/MCP sharing: send the snapshot JSON through `pft-chatbot-mcp` as `content_type: "application/json"` with TaskNode sharing enabled.
- Adapter sharing: exchange or wallet adapters can publish the normalized snapshot directly, or upload it to existing content storage/IPFS and share the resulting reference through current PostFiat interfaces.

The sharing layer is intentionally outside the v0 schema; the snapshot remains ingestible as a standalone JSON document regardless of transport.

The v0 content hash rule is explicit: compute SHA-256 over canonical JSON bytes after omitting `provenance.content_hash` from the object. Canonical JSON sorts object keys recursively, preserves array order, uses compact separators, and encodes UTF-8 bytes.

Sample validation report for `pft-positions validate fixtures/delta-one.json`:

```json
{
  "valid": true,
  "schema_version": "position-snapshot.v0",
  "errors": [],
  "warnings": [],
  "file": "fixtures/delta-one.json"
}
```

## Validate examples against schema

```bash
npm --prefix test install
npm --prefix test test
```

## Repository layout

```text
schema/
  position-snapshot.v0.schema.json
  README.md
  examples/
    delta-one.example.json
    option.example.json
    yield.example.json
fixtures/
  delta-one.json
  hyperliquid-hlp-child.json
  option.json
  yield.json
  raw/
    delta-one.raw.json
    hyperliquid-hlp-child.raw.json
    option.raw.json
    yield.raw.json
src/
  README.md
  pft_positions/
test/
  package.json
  validate-examples.test.mjs
tests/
  test_reference_package.py
```
