# pft_positions

Public v0 specification for machine-readable position snapshots and exchange adapter for Post Fiat.

## What problem does this solve?

**Observation**: CoinMarketCap Portfolio Snapshot feature integrated in the Task Node is limited to long-only positions, relies on manually created portfolios instead of wallet-synced data, and has a cumbersome upload process — individual position updates require re-uploading an entirely new CSV. 

**Idea**: *Provide a general high resolution position snapshot for postfiat tasknode and AGTI*  

**Value add**:
- Detect user churn from holding coins
- Higher resolution view of positioning 

**Solution Sketch**: 
1) machine-readable position-snapshot  
2) [to be implemented]: exchange adapter (e.g. CCXT-based) connecting to major crypto exchanges via API, pulling live positions and processing them into compliant snapshot format

- **Position Types**: `linear`, `option`, `yield` - crypto & non-crypto
- **Origin**: pulled via exchange adapter, processed to canonical format
              (IBKR support or similar for non-crypto in the future)
- **Origin Type**: internal tasknode user or public source (secondary, e.g. HyperLiquid wallets)    
   
## What this repository provides

- **Canonical JSON Schema** (`schema/position-snapshot.v0.schema.json`) defining the wire-level shape of a position snapshot.
- **Provenance and normalization conventions** (`schema/README.md`) covering collector identity, source evidence, content hashing, decimal-string encoding, and timestamp conventions.
- **Executable fixture corpus** (`fixtures/`) with raw source payloads paired with normalized snapshots, including a full 190-position Hyperliquid public whale case.
- **Python reference package and CLI** (`pft-positions`) for schema validation, canonical JSON emission, and content-hash verification.
- **Three documentation example payloads** covering the v0 instrument categories:
  - `schema/examples/linear.example.json` (Binance + Hyperliquid linear positions)
  - `schema/examples/option.example.json` (Deribit options)
  - `schema/examples/yield.example.json` (Binance staking + Arbitrum vault yield)

## Instrument categories

v0 defines three top-level instrument categories:

| Category | Covers | Detail block |
|---|---|---|
| `linear` | spot, perpetual, future, swap | `linear` |
| `option` | vanilla call/put options | `option` |
| `yield` | staking, lending, vault, liquidity, bond | `yield` |

The `yield.position_kind` enum includes `bond` alongside `staking`, `lending`, `vault`, and `liquidity`. Each category has a matching detail block that becomes required when `instrument_type` is set to that category.

## Scope

v0 is intentionally limited to position sharing. Trend, contrarian, churn, sentiment, and strategy signal components are not part of this schema and can be added in a future version. The scope is narrow and implementation-ready so future adapter work (for example, CCXT-based exchange adapters) can plug into stable field names and semantics.

## Quick start

### Install the Python package

```bash
pip install -e .
```

### Validate fixtures

```bash
pft-positions validate fixtures
```

### Emit a bundled fixture

```bash
pft-positions emit --list
pft-positions emit hyperliquid-hlp-child
```

### Parse a fixture to canonical JSON

```bash
pft-positions parse fixtures/hyperliquid-hlp-child.json
```

### Run the test suite

```bash
python3 -m pytest
npm --prefix tests install
npm --prefix tests test
```

## CLI commands

| Command | Description |
|---|---|
| `pft-positions validate <path>` | Validates JSON syntax, the v0 schema, and `provenance.content_hash` for a file or directory of `.json` files. |
| `pft-positions parse <path>` | Parses, validates, and prints canonical JSON for a single snapshot file. |
| `pft-positions emit <name>` | Prints one of the bundled reference fixtures. Use `--list` to see available names. |

Current bundled fixtures: `linear`, `hyperliquid-hlp-child`, `option`, `yield`.

## Fixture corpus

`fixtures/` is the authoritative executable corpus for package tests and CLI validation. Each normalized fixture has a matching raw source payload in `fixtures/raw/` that documents the upstream API or manual input it was derived from.

### Normalized fixtures

| Fixture | Description |
|---|---|
| `fixtures/linear.json` | Single Binance BTC-USDT perpetual position (didactic example). |
| `fixtures/hyperliquid-hlp-child.json` | Full 190-position snapshot from public Hyperliquid HLP child account `0x010461c14e146ac35fe42271bdc1134ee31c703a`. |
| `fixtures/option.json` | Single Deribit BTC call option position (didactic example). |
| `fixtures/yield.json` | Single Arbitrum USDAI vault yield position (didactic example). |

### Paired raw fixtures

| Raw fixture | Normalizes to |
|---|---|
| `fixtures/raw/linear.raw.json` | `fixtures/linear.json` |
| `fixtures/raw/hyperliquid-hlp-child.raw.json` | `fixtures/hyperliquid-hlp-child.json` |
| `fixtures/raw/option.raw.json` | `fixtures/option.json` |
| `fixtures/raw/yield.raw.json` | `fixtures/yield.json` |

### Hyperliquid whale test case

The Hyperliquid fixture demonstrates that public wallet positions can be normalized into the snapshot format without private credentials:

- **Source API**: `POST https://api.hyperliquid.xyz/info` with `{ "type": "clearinghouseState", "user": "0x010461c14e146ac35fe42271bdc1134ee31c703a" }`
- **Whale identification**: Derived from the public HLP vault `0xdfc24b077bc1425ad1dea75bcb6f8158e10df303` via `vaultDetails`, which exposes child accounts and top public followers by vault equity.
- **Coverage**: All 190 open perp positions in the selected HLP child account, normalized as `instrument_type: "linear"`.
- **Raw provenance**: The raw fixture records the HLP vault context, child account list, and top followers for traceability.

## Sharing and ingestion

Snapshots are plain JSON and can be shared in three compatible ways:

| Method | How it works |
|---|---|
| **Manual sharing** | Paste or attach the canonical JSON produced by `pft-positions parse`. |
| **TaskNode/MCP sharing** | Send the snapshot JSON through `pft-chatbot-mcp` as `content_type: "application/json"` with TaskNode sharing enabled. |
| **Adapter sharing** | Exchange or wallet adapters publish the normalized snapshot directly, or upload it to existing content storage/IPFS and share the resulting reference through current PostFiat interfaces. |

The sharing layer is intentionally outside the v0 schema; the snapshot remains ingestible as a standalone JSON document regardless of transport.

## Content hash

`provenance.content_hash` is computed by:

1. Parsing the snapshot JSON.
2. Omitting `provenance.content_hash` from the object.
3. Serializing canonical JSON with recursive object-key sorting, compact separators, preserved array order, and UTF-8 encoding.
4. Computing lowercase SHA-256 hex over those canonical bytes.

This avoids circular hashing and makes validation deterministic across whitespace and object key ordering differences.

Sample validation report for `pft-positions validate fixtures/linear.json`:

```json
{
  "valid": true,
  "schema_version": "position-snapshot.v0",
  "errors": [],
  "warnings": [],
  "file": "fixtures/linear.json"
}
```

## PostFiat ecosystem context

This repository is designed to interoperate with the broader PostFiat tooling:

| Repository | Role |
|---|---|
| [`pft-chatbot-mcp`](https://github.com/postfiatorg/pft-chatbot-mcp) | MCP server for Task Node message transport, encrypted content, IPFS storage, and bot registry. Snapshots can be shared as `application/json` message content or attachments. |
| [`postfiatd`](https://github.com/postfiatorg/postfiatd) | XRPL-family ledger daemon. Snapshot JSON should be shared through content/message infrastructure rather than embedded directly in ledger memos. |
| [`pftl-snap`](https://github.com/postfiatorg/pftl-snap) | MetaMask Snap for PFTL wallet management, memo transactions, and user-client context. |
| [`explorer`](https://github.com/postfiatorg/explorer) | PFTL block explorer for transaction and memo display conventions. |
| [`dynamic-unl-scoring`](https://github.com/postfiatorg/dynamic-unl-scoring) | AI-driven validator scoring service demonstrating PostFiat deployment, IPFS, and agent workflow patterns. |
| [`validator-history-service`](https://github.com/postfiatorg/validator-history-service) | Ingestion/API service conventions and network environment patterns. |

## Repository layout

```text
schema/
  position-snapshot.v0.schema.json
  README.md
  examples/
    linear.example.json
    option.example.json
    yield.example.json
fixtures/
  linear.json
  hyperliquid-hlp-child.json
  option.json
  yield.json
  raw/
    linear.raw.json
    hyperliquid-hlp-child.raw.json
    option.raw.json
    yield.raw.json
src/
  README.md
  pft_positions/
tests/
  test_reference_package.py
  validate-examples.test.mjs
  package.json
  package-lock.json
```
