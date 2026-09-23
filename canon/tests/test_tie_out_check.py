"""The tie-out gate, watched failing before it is trusted passing.

Every check here is exercised twice: once on a document that should sail
through, and once on the same document with one thing broken -- and the broken
run must not merely fail, it must NAME what it caught. A guard nobody has
watched go red is a guard nobody should trust (behaviour 6), and this file
exists because the last pass over these documents fixed nine findings and
introduced seven more.

The three planted defects are not invented. Each is the exact shape of a defect
that was live in `credit-suite`'s delivered covering document on 19 September
2026: a roster adding to 156,767 under a headline of 156,881, a missing "what I
got wrong", and two photographed filings with no ink on them.

The PNG fixtures are written here by hand, in `zlib` and `struct`, rather than
by an image library. That is not purity for its own sake: an encoder borrowed
from the same family as the decoder proves the pair agree with each other and
nothing about the format. These bytes are built from the specification.
"""
from __future__ import annotations

import struct
import sys
import zlib
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import check_tie_out as gate                                    # noqa: E402


# ---------------------------------------------------------------------------
# PNG fixtures, built from the specification
# ---------------------------------------------------------------------------

def _chunk(kind: bytes, body: bytes) -> bytes:
    return (struct.pack(">I", len(body)) + kind + body
            + struct.pack(">I", zlib.crc32(kind + body) & 0xFFFFFFFF))


def rgb_png(pixels, width, height, filter_kind=0) -> bytes:
    """A truecolour, 8-bit PNG. `pixels` is a flat list of (r, g, b).

    `filter_kind` 0 writes the scanlines raw; 2 writes them as the difference
    from the row above, which is the commonest thing a real encoder does and
    the path a decoder gets wrong quietly.
    """
    rows = []
    previous = bytearray(width * 3)
    for y in range(height):
        line = bytearray()
        for x in range(width):
            line += bytes(pixels[y * width + x])
        if filter_kind == 2:
            rows.append(bytes([2]) + bytes((line[i] - previous[i]) & 0xFF
                                           for i in range(len(line))))
        else:
            rows.append(bytes([0]) + bytes(line))
        previous = line
    return (b"\x89PNG\r\n\x1a\n"
            + _chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
            + _chunk(b"IDAT", zlib.compress(b"".join(rows)))
            + _chunk(b"IEND", b""))


def palette_png(indices, palette, width, height, depth=4) -> bytes:
    """A palette PNG at 1, 2 or 4 bits per pixel -- what the strips actually are."""
    per_byte = 8 // depth
    rows = []
    for y in range(height):
        line = bytearray((width + per_byte - 1) // per_byte)
        for x in range(width):
            shift = 8 - depth * (x % per_byte + 1)
            line[x // per_byte] |= (indices[y * width + x] & ((1 << depth) - 1)) << shift
        rows.append(bytes([0]) + bytes(line))
    table = b"".join(bytes(c) for c in palette)
    return (b"\x89PNG\r\n\x1a\n"
            + _chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, depth, 3, 0, 0, 0))
            + _chunk(b"PLTE", table)
            + _chunk(b"IDAT", zlib.compress(b"".join(rows)))
            + _chunk(b"IEND", b""))


def grey_png(width=4, height=4) -> bytes:
    rows = [bytes([0]) + bytes([128] * width) for _ in range(height)]
    return (b"\x89PNG\r\n\x1a\n"
            + _chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 0, 0, 0, 0))
            + _chunk(b"IDAT", zlib.compress(b"".join(rows)))
            + _chunk(b"IEND", b""))


WHITE, RED, INK = (255, 255, 255), (198, 16, 48), (20, 20, 20)


def plain_picture(width=20, height=20) -> bytes:
    """A photographed page with nothing ringed on it."""
    return rgb_png([WHITE if (x + y) % 5 else INK
                    for y in range(height) for x in range(width)],
                   width, height)


def ringed_picture(width=20, height=20) -> bytes:
    """The same page with the row ringed -- 72 red pixels around the edge."""
    pixels = []
    for y in range(height):
        for x in range(width):
            edge = x < 1 or y < 1 or x >= width - 1 or y >= height - 1
            pixels.append(RED if edge else WHITE)
    return rgb_png(pixels, width, height)


def data_uri(png: bytes) -> str:
    import base64
    return "data:image/png;base64," + base64.b64encode(png).decode()


# ---------------------------------------------------------------------------
# A document that conforms, and the knobs to break it with
# ---------------------------------------------------------------------------

def document(headline="156,881", rows=(("TIED", "156,879"), ("DIFFERS", "2")),
             sections=("what-it-found", "what-i-got-wrong",
                       "what-this-does-not-prove"),
             pictures=(True,), role_typo=False):
    marked = "data-tieoutx" if role_typo else gate.ATTR
    body = ["<!doctype html><html><body>",
            '<div class="card"><span %s="headline">%s</span> values delivered'
            "</div>" % (marked, headline)]
    body.append('<table %s="roster">' % gate.ATTR)
    for label, count in rows:
        body.append('<tr><td>%s</td><td %s="count">%s</td></tr>'
                    % (label, gate.ATTR, count))
    body.append("</table>")
    for index, ringed in enumerate(pictures):
        body.append('<img %s="source" alt="filing %d" src="%s">'
                    % (gate.ATTR, index,
                       data_uri(ringed_picture() if ringed else plain_picture())))
    titles = {"what-it-found": "What running this found",
              "what-i-got-wrong": "What I got wrong",
              "what-this-does-not-prove": "What this does not prove"}
    for role in sections:
        body.append('<h2 %s="%s">%s</h2><p>Words.</p>'
                    % (gate.ATTR, role, titles[role]))
    body.append("</body></html>")
    return "\n".join(body)


# ---------------------------------------------------------------------------
# it passes on a document that conforms
# ---------------------------------------------------------------------------

def test_a_conforming_document_is_published():
    report = gate.check(document())
    assert report.ok, report.render()


def test_it_says_what_it_examined_rather_than_just_passing():
    report = gate.check(document())
    assert report.examined["roster rows"] == 2
    assert report.examined["named sections"] == 3
    assert report.examined["marked pictures"] == 1
    assert "2 roster rows" in report.render()


def test_the_gate_returns_quietly_when_the_document_conforms(capsys):
    gate.gate(document())
    assert "adds up" in capsys.readouterr().out


# ---------------------------------------------------------------------------
# a · the roster must sum to the headline
# ---------------------------------------------------------------------------

def test_a_roster_that_does_not_add_up_is_refused():
    """The live defect: a category whose wording changed, whose counter still
    searched for the old string, printing 0 and reading as good news."""
    report = gate.check(document(rows=(("TIED", "156,765"), ("DIFFERS", "2"),
                                       ("not on that filing", "0"))))
    assert not report.ok
    assert any("does not add up" in f and "-114" in f for f in report.findings), \
        report.findings


def test_the_refusal_names_both_numbers_and_the_gap():
    report = gate.check(document(rows=(("TIED", "10"), ("DIFFERS", "1"))))
    text = " ".join(report.findings)
    assert "11" in text and "156,881" in text


def test_a_document_with_no_headline_is_refused():
    html = document().replace('%s="headline"' % gate.ATTR, 'class="headline"')
    report = gate.check(html)
    assert not report.ok
    assert any("headline" in f for f in report.findings)


def test_a_document_with_no_roster_is_refused():
    html = document().replace('%s="roster"' % gate.ATTR, "")
    report = gate.check(html)
    assert not report.ok
    assert any('"roster"' in f for f in report.findings)


def test_an_unmarked_roster_is_not_an_empty_one():
    """Silence must not read as zero. A roster whose rows carry no marks is
    refused, not summed to nothing and compared against the headline."""
    html = document().replace('%s="count"' % gate.ATTR, 'class="n"')
    report = gate.check(html)
    assert any("no" in f and "count" in f for f in report.findings), report.findings


def test_a_mistyped_mark_is_refused_rather_than_ignored():
    report = gate.check(document().replace('%s="roster"' % gate.ATTR,
                                           '%s="rostr"' % gate.ATTR))
    assert not report.ok
    assert any("rostr" in f for f in report.findings)


# ---------------------------------------------------------------------------
# b · the three named sections
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("missing, spoken", [
    ("what-it-found", "what it found"),
    ("what-i-got-wrong", "what I got wrong"),
    ("what-this-does-not-prove", "what this does not prove"),
])
def test_each_missing_section_is_refused_by_name(missing, spoken):
    keep = tuple(r for r, _ in gate.SECTIONS if r != missing)
    report = gate.check(document(sections=keep))
    assert not report.ok
    assert any(spoken in f for f in report.findings), report.findings


def test_an_empty_heading_does_not_count_as_a_section():
    html = document().replace(">What I got wrong<", "><")
    report = gate.check(html)
    assert any("what I got wrong" in f for f in report.findings), report.findings


# ---------------------------------------------------------------------------
# c · a source image must carry a mark
# ---------------------------------------------------------------------------

def test_an_unringed_photograph_is_refused():
    report = gate.check(document(pictures=(False,)))
    assert not report.ok
    assert any("red mark" in f for f in report.findings), report.findings


def test_one_ringed_picture_among_several_satisfies_the_check():
    assert gate.check(document(pictures=(False, True, False))).ok


def test_a_document_with_no_source_picture_is_refused():
    report = gate.check(document(pictures=()))
    assert any('"source"' in f for f in report.findings), report.findings


def test_a_picture_referenced_by_path_is_refused_not_skipped():
    """The image that failed to embed is indistinguishable from the one that
    did, until somebody opens it. This is the check that opens it."""
    html = document().replace("data:image/png;base64,", "strips/row.png#")
    report = gate.check(html)
    assert any("resolves only on the machine" in f for f in report.findings)


def test_an_image_format_this_cannot_read_is_refused_and_named():
    """The design fork, asserted. There is no dependency to be missing, and an
    image this cannot decode is a refusal rather than a quiet pass."""
    html = document().replace("data:image/png;base64,", "data:image/jpeg;base64,")
    report = gate.check(html)
    assert not report.ok
    assert any("jpeg" in f and "refuses" in f for f in report.findings), \
        report.findings


# ---------------------------------------------------------------------------
# the PNG decoder, against bytes built from the specification
# ---------------------------------------------------------------------------

def test_red_is_counted_in_a_truecolour_png():
    assert gate.red_pixels(ringed_picture(10, 10)) == 36


def test_red_is_counted_through_the_up_filter():
    plain = rgb_png([RED] * 9, 3, 3, filter_kind=0)
    filtered = rgb_png([RED] * 9, 3, 3, filter_kind=2)
    assert plain != filtered
    assert gate.red_pixels(plain) == gate.red_pixels(filtered) == 9


def test_red_is_counted_in_a_four_bit_palette_png():
    """What the delivered strips are: sixteen shades, four bits a pixel."""
    palette = [WHITE, INK, RED] + [(0, 0, 0)] * 13
    indices = [2 if x == 0 else (1 if x == 1 else 0)
               for _ in range(4) for x in range(4)]
    assert gate.red_pixels(palette_png(indices, palette, 4, 4)) == 4


def test_a_greyscale_png_can_never_be_red():
    assert gate.red_pixels(grey_png()) == 0


def test_black_text_on_white_paper_is_not_a_mark():
    assert gate.red_pixels(plain_picture(30, 30)) == 0


def test_a_warm_grey_is_not_red():
    assert gate.red_pixels(rgb_png([(150, 120, 120)] * 4, 2, 2)) == 0


@pytest.mark.parametrize("keep", [40, 45, 60])
def test_a_truncated_png_is_unreadable_rather_than_unmarked(keep):
    """Cut before the pixels, inside the chunk header, and inside the
    compressed stream. None of the three may come back "no red found"."""
    with pytest.raises(gate.Unreadable):
        gate.red_pixels(ringed_picture()[:keep])


def test_something_that_is_not_a_png_is_unreadable():
    with pytest.raises(gate.Unreadable):
        gate.red_pixels(b"GIF89a and then some bytes")


# ---------------------------------------------------------------------------
# the gate refuses rather than warning
# ---------------------------------------------------------------------------

def test_the_gate_raises_rather_than_printing_and_carrying_on(capsys):
    with pytest.raises(SystemExit) as raised:
        gate.gate(document(pictures=(False,)), "the covering document")
    assert "REFUSING" in str(raised.value)
    assert "the covering document" in str(raised.value)
    assert "red mark" in capsys.readouterr().out


def test_the_command_line_reports_a_failing_document(tmp_path, capsys):
    path = tmp_path / "doc.html"
    path.write_text(document(pictures=(False,)), encoding="utf-8")
    assert gate.main([str(path)]) == 1
    assert "red mark" in capsys.readouterr().out


def test_the_command_line_passes_a_conforming_document(tmp_path):
    path = tmp_path / "doc.html"
    path.write_text(document(), encoding="utf-8")
    assert gate.main([str(path)]) == 0
