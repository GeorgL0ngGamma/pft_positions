# Rough Implementation Plan: Canonicalize JSON Before `provenance.content_hash` Verification

Goal: ensure Task Node agents compute the same SHA-256 hash for the same logical snapshot payload, regardless of whitespace, indentation, or key ordering.

## Why This Is Needed

If agents hash raw JSON bytes directly, semantically identical payloads can fail validation due to:
- different object key order
- pretty-printed vs minified JSON
- parser-specific number formatting

`provenance.content_hash` should be verified against a canonical byte representation, not the original transport bytes.

## Canonicalization Approach (v0 recommendation)

Use JSON Canonicalization Scheme (JCS, RFC 8785) semantics, with one practical constraint from this schema: numeric values that matter are already encoded as decimal strings.

Canonicalization steps:
1. Parse JSON into an object model.
2. Remove any transport envelope (hash only the snapshot object defined by schema).
3. Ensure UTF-8 output.
4. Sort all object keys lexicographically (recursive, at every object level).
5. Keep array order unchanged.
6. Serialize with no insignificant whitespace.
7. Normalize escaping using JSON serializer defaults compatible with JCS behavior.
8. Hash canonical bytes with SHA-256, lowercase hex output.

## Verification Flow for Downstream Agents

1. Parse payload.
2. Validate against `position-snapshot.v0` schema.
3. Read expected hash from `provenance.content_hash`.
4. Canonicalize payload using the rules above.
5. Compute `sha256(canonical_bytes)`.
6. Compare computed hex to expected hash (case-insensitive compare is acceptable; store lowercase).
7. Reject or quarantine snapshot on mismatch.

## Producer Guidance

- Producers and consumers must share the exact same canonicalization rules.
- Producers should compute `provenance.content_hash` from canonical JSON bytes at publish time.
- Do not hash pretty-printed output from logs/files.

## Practical Language Notes

- **TypeScript/Node**: use a stable canonical JSON library (JCS-compatible), then `crypto.createHash("sha256")`.
- **Python**: use a JCS implementation (preferred) or strict canonical serializer (`sort_keys=True`, compact separators) as an interim approach.
- **Go/Rust**: prefer dedicated canonical JSON/JCS packages over default encoders.

## Interop Test Vector Plan (rough)

Add cross-language tests with the same fixture:
1. Fixture A: minified JSON.
2. Fixture B: pretty-printed JSON with shuffled key order.
3. Assert both canonicalize to identical bytes.
4. Assert resulting SHA-256 equals fixture's expected `content_hash`.

This prevents false failures and makes `provenance.content_hash` a reliable integrity check for Task Node shared position snapshots.
