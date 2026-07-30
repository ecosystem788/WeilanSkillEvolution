# Governed occurrence registry

`occurrence-registry.jsonl` is an append-only set of explicitly cosigned
anchors. The gate never writes it and an empty file cannot bootstrap a known
public occurrence.

## State rule

For every occurrence in the commit currently being scanned, the gate looks up
one anchor whose identity matches byte-for-byte and whose `ruleset_digest`
equals the current complete ruleset digest. Every occurrence without that
current-digest anchor is `NEW_MATCHES`.

The registry is read only in that occurrence-relative direction. It is never
globally scanned to produce state. Therefore zero current occurrences is
`CLEAN`, regardless of stale anchors. Stale anchors are visible through
`stale_anchor_count` but are not a state input. Their lifecycle or disposition
is deliberately left for a separate decision.

`anchor_ruleset_stale` and `unanchored_occurrence` are diagnostics, not
classification truth. If a ruleset change also moves a pattern to a different
index, the occurrence may diagnose as unanchored; the invariant remains that
failure to match under the current digest is `NEW_MATCHES`.

## Identity and framing

The exact six-field identity is:

1. `path`
2. `ruleset_digest`
3. `pattern_index`
4. `where`
5. `line_hash`
6. `occurrence_ordinal`

`ruleset_digest` is SHA-256 over every stripped nonempty pattern, in source
order and joined by a single LF byte. It is a digest of the complete table,
never one digest per pattern.

For UTF-8 content, `line_hash` uses
`current-record-minus-LF-v1`: split the named blob on `0x0A` and hash the
physical record bytes without that delimiter. Any stored trailing `0x0D`
remains part of the record. For a path occurrence, hash the UTF-8 bytes of the
repository-relative path and report `line_framing="path"`.

Content that can be decoded only as UTF-16 reports
`line_framing="unsupported"`. Its occurrences cannot be anchored and always
remain `NEW_MATCHES`, because an LF-byte physical-record identity would be
misleading for that encoding.

`occurrence_ordinal` is zero-based and follows non-overlapping `str.find`
matches from left to right within one physical record and one pattern. It is
part of identity. `line_number` and `count` are receipt-only observations and
never participate in identity.

Two byte-identical records in the same path can consequently share the same
identity. One anchor covers both: the attestation is that those record bytes in
that file were public, and a duplicate appearance does not disclose new
bytes. Adding `line_number` to identity would break the tail-append invariant
and requires a new dual-sign decision.

## Anchor schema and authority

Every nonblank JSONL record must contain the six identity fields plus:

- `peer_attestation`: nonempty text recording the peer's independent
  recomputation from the then-live remote object;
- `live_remote_oid`: that full 40-hex object id;
- `proposal_line_sha256`: the governing proposal record hash;
- `consent_line_sha256`: the governing consent record hash.

Any missing or malformed required field makes the gate refuse to run.
Adding an anchor requires a separate dual-sign decision and an append-only
write. The offline gate checks schema completeness only. It does not pretend
to verify that the attested object was live remotely; that claim can be
rechecked only by a network-aware auditor.

## Limits

The line hash is an oracle: someone who guesses an entire record can confirm
the guess. It is weaker than storing plaintext, but it is not zero leakage.

`CLEAN` means only that the configured pattern table had no occurrences in the
named local Git object. It is not proof of no privacy leak. The receipt always
prints `ruleset_digest` and `pattern_count`.

Changing the subject to a commit does not itself prove those bytes were
published. Equality with a remote Git object depends on Git content
addressing, not on this gate.
