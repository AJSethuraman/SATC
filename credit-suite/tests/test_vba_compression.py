"""The VBA module stream is a legal [MS-OVBA] container (issue #180).

The ExtractFiles button did not work in any monitor, in any shipped workbook,
because the compressor emitted literals only. That is unrepresentable for more
than one chunk: a CompressedChunkHeader carries the size in 12 bits (capping a
chunk at 4098 bytes) while every NON-FINAL chunk must decompress to exactly
4096, and 4096 literals need 4096 + 512 flag bytes. Both shipped macros are
over the one-chunk limit, so both were broken.

**Why nothing here caught it for months.** `olevba` decompresses the old output
without complaint, so a round-trip test passed. Excel does not. A round-trip
against our own decoder would have been worse than useless -- it would have
agreed with our own bug. So these tests check two independent things:

1. the output round-trips through the REFERENCE decompressor (`oletools`), and
2. the CHUNK STRUCTURE obeys the rule Excel actually enforces, checked by
   parsing the container back apart rather than by trusting the encoder.

Neither can substitute for real Excel, and neither claims to. The real-Excel
acceptance lives in `tools/excel_acceptance.py` and is desk-run; see
`docs/runbook-live-acceptance.md`.
"""
from __future__ import annotations

import random
import struct
from pathlib import Path

import pytest
from oletools.olevba import decompress_stream

from credit_suite.engine import vba

MACROS = sorted((Path(__file__).resolve().parents[1] / "src" / "credit_suite"
                 / "sources").glob("*/macro.bas"))


def roundtrip(data: bytes) -> bytes:
    got = decompress_stream(bytearray(vba.compress(data)))
    return got.encode("latin-1") if isinstance(got, str) else got


def chunks(container: bytes):
    """Parse a CompressedContainer back into (decompressed_size, is_raw) pairs.

    Deliberately a separate implementation from the encoder: a structural check
    written by re-using the encoder's own helpers would only prove the encoder
    agrees with itself.
    """
    assert container[:1] == b"\x01", "missing CompressedContainer signature"
    out = []
    i = 1
    while i < len(container):
        header = struct.unpack_from("<H", container, i)[0]
        size = (header & 0x0FFF) + 3
        is_raw = not (header & 0x8000)
        assert (header & 0x7000) == 0x3000, "bad chunk signature at byte %d" % i
        body = container[i + 2:i + size]
        if is_raw:
            decompressed = len(body)
        else:
            decompressed, j = 0, 0
            while j < len(body):
                flags = body[j]
                j += 1
                for bit in range(8):
                    if j >= len(body):
                        break
                    if flags & (1 << bit):
                        token = struct.unpack_from("<H", body, j)[0]
                        j += 2
                        bit_count = max(4, (decompressed - 1).bit_length()) \
                            if decompressed > 0 else 4
                        length = (token & (0xFFFF >> bit_count)) + 3
                        decompressed += length
                    else:
                        j += 1
                        decompressed += 1
        out.append((decompressed, is_raw))
        i += size
    return out


@pytest.mark.parametrize("macro", MACROS, ids=lambda p: p.parent.name)
def test_every_shipped_macro_round_trips_through_the_reference_decoder(macro):
    source = macro.read_text(encoding="utf-8")
    text = source.replace("\n", "\r\n")
    if not text.endswith("\r\n"):
        text += "\r\n"
    want = text.encode("latin-1", "replace")
    assert roundtrip(want) == want


@pytest.mark.parametrize("size", [0, 1, 7, 8, 9, 4095, 4096, 4097, 8191, 8192, 12000])
def test_round_trips_at_and_around_every_chunk_boundary(size):
    """4096 is where the old encoder switched strategy and where Excel broke."""
    data = (b"Sub Extract()\r\n    Dim i As Long\r\nEnd Sub\r\n" * 400)[:size]
    assert roundtrip(data) == data


def test_round_trips_incompressible_data():
    """Random bytes force the raw/compressed decision and the size ceiling.

    The size is chosen, not arbitrary. 4096 + 4000 makes the FINAL chunk short
    (4000 bytes) *and* incompressible, so its encoded body still exceeds 4096 --
    the one shape where "is this big?" and "is this exactly a full chunk?" give
    different answers. A round 9,000 bytes leaves a 808-byte tail that never
    reaches the ceiling, so the raw-chunk guard is never exercised and a mutation
    that drops the size check survives. It did.
    """
    random.seed(20260904)
    data = bytes(random.randrange(256) for _ in range(4096 + 4000))
    assert roundtrip(data) == data


@pytest.mark.parametrize("macro", MACROS, ids=lambda p: p.parent.name)
def test_no_non_final_chunk_is_short(macro):
    """THE #180 RULE. Every chunk but the last must decompress to exactly 4096.

    This is the assertion that would have failed on the shipped code, and no
    round-trip test could have: `olevba` decodes a short non-final chunk
    happily, and Excel refuses the whole project.
    """
    text = macro.read_text(encoding="utf-8").replace("\n", "\r\n")
    padded = (text + "' pad\r\n" * 2000).encode("latin-1", "replace")
    parsed = chunks(vba.compress(padded))
    assert len(parsed) > 1, "the padding was meant to force several chunks"
    for index, (decompressed, _raw) in enumerate(parsed[:-1]):
        assert decompressed == vba.MAX_CHUNK, (
            "chunk %d of %d decompresses to %d, not 4096 -- Excel refuses the "
            "project and the macro silently disappears (#180)"
            % (index, len(parsed), decompressed)
        )


def test_the_compressor_actually_uses_copy_tokens():
    """Without a matcher the encoder cannot reach 4096 in a non-final chunk, so
    'it compresses' is load-bearing rather than an efficiency nicety."""
    data = b"Sub Extract()\r\n" * 2000
    out = vba.compress(data)
    assert len(out) < len(data) // 4, (
        "highly repetitive source barely shrank (%d -> %d): the copy-token "
        "matcher is not firing" % (len(data), len(out))
    )


@pytest.mark.parametrize("size", [1, 3640, 3641, 4095, 4096, 4097, 8096, 12000])
def test_no_chunk_claims_a_size_the_header_cannot_hold(size):
    """CompressedChunkSize is 12 bits, so a chunk tops out at 4098 bytes.

    Written after the encoder produced a 4,097-byte body at 4,095 bytes of
    incompressible input: the size field wrapped, the chunk announced itself as
    3 bytes long, and the reference decoder walked off into the next chunk's
    bytes. A round-trip test caught it at one size and missed it at others,
    because a corrupt length sometimes still decodes to something. This asserts
    the ceiling directly instead of hoping a decode notices.
    """
    random.seed(size)
    data = bytes(random.randrange(256) for _ in range(size))
    container = vba.compress(data)
    i = 1
    while i < len(container):
        header = struct.unpack_from("<H", container, i)[0]
        chunk_size = (header & 0x0FFF) + 3
        assert (header & 0x7000) == 0x3000, "bad signature at byte %d" % i
        assert chunk_size <= 4098, (
            "chunk at byte %d claims %d bytes; the 12-bit size field caps a "
            "chunk at 4098 and anything larger wraps into a corrupt stream"
            % (i, chunk_size))
        i += chunk_size
    assert i == len(container), "chunk walk overran the container by %d bytes" % (
        i - len(container))


def test_a_stream_over_the_mini_cutoff_still_round_trips():
    """The regular-sector pool is the case that never once worked before the
    fix, so it gets its own test rather than being implied by the sweep."""
    data = (b"' unique line %08d\r\n" % i for i in range(3000))
    blob = b"".join(data)
    stream = vba.compress(blob)
    assert len(stream) >= 4096, "meant to exceed the mini-stream cutoff"
    assert roundtrip(blob) == blob
