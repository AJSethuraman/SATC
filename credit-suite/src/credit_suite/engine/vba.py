#!/usr/bin/env python3
"""Build a valid `vbaProject.bin` (OLE compound file) from VBA source.

This is the one piece the build environment can't fully verify (it has no
Excel), so it is implemented strictly to [MS-OVBA] and [MS-CFB] and validated
with oletools' olevba parser, which decodes a VBA project the same way Excel
does. Kept isolated in its own module so the embedding choice can change.

It produces a vbaProject.bin containing:
  * PROJECT, PROJECTwm           (project text + module-name map)
  * VBA/dir                      (compressed project records)
  * VBA/_VBA_PROJECT             (minimal version header; Excel recompiles)
  * VBA/<module>                 (compressed module source at offset 0)

Module source is stored uncompiled (MODULEOFFSET=0) so Excel compiles it on
load -- the common, well-tolerated shape for an injected standard module.
"""
from __future__ import annotations

import struct
from math import ceil, log2
from dataclasses import dataclass
from typing import Dict, List, Tuple

# ==========================================================================
# MS-OVBA compression ([MS-OVBA] 2.4.1), WITH copy tokens
# ==========================================================================
# This emitted literals only until 4 September 2026, and that is issue #180: the
# ExtractFiles button did not work in any monitor, in any shipped workbook.
#
# The arithmetic that makes literal-only impossible: a CompressedChunkHeader
# carries the chunk size in 12 bits, capping a chunk at 4098 bytes, while the
# spec requires every NON-FINAL chunk to decompress to exactly 4096. An
# all-literal encoding of 4096 bytes needs 4096 + 512 flag bytes, which does not
# fit. So no literal-only compressor can produce a valid multi-chunk container,
# and every module over ~3.6 KB needs more than one chunk. Both shipped macros
# do.
#
# The previous code worked around that with RawChunks for full 4096-byte
# windows. That round-trips through olevba, which is why the offline bar was
# green for months, and real Excel refuses it -- "An error occurred while loading
# '<module>'", after which the macro is simply absent. Proved by bisecting DOWN
# from a project Excel itself authored: swapping our module stream into it was
# the single change that broke it, and swapping this one in fixed it.
#
# So the matcher is not an optimisation. It is the only way to emit a legal
# stream. (It also compresses ~2x, which is why both macros now fit in a single
# chunk -- pleasant, and NOT the thing that fixes them: a padded 9,962-byte
# module spanning several chunks was verified to load and run in real Excel.)

MAX_CHUNK = 4096


def _copy_token_help(difference: int) -> Tuple[int, int, int, int]:
    """[MS-OVBA] 2.4.1.3.19.1.

    The offset/length bit split depends on how far into the chunk the token
    sits, so the same (offset, length) encodes differently at different
    positions. Getting this wrong produces a stream that decompresses to
    plausible-looking rubbish rather than an error, which is why the tests check
    against the reference decompressor rather than against these numbers.
    """
    bit_count = max(int(ceil(log2(difference))), 4) if difference > 0 else 4
    length_mask = 0xFFFF >> bit_count
    offset_mask = (~length_mask) & 0xFFFF
    maximum_length = (0xFFFF >> bit_count) + 3
    return length_mask, offset_mask, bit_count, maximum_length


def _longest_match(data: bytes, chunk_start: int, at: int,
                   end: int) -> Tuple[int, int]:
    """Longest earlier occurrence WITHIN this chunk. Returns (offset, length).

    Never looks before ``chunk_start``: each chunk decompresses independently,
    so a match reaching into the previous chunk would decode to nonsense.
    """
    difference = at - chunk_start
    if difference == 0:
        return 0, 0
    _lm, _om, _bc, maximum_length = _copy_token_help(difference)
    best_length = 0
    best_offset = 0
    for candidate in range(at - 1, chunk_start - 1, -1):
        length = 0
        while (at + length < end and length < maximum_length
               and data[candidate + length] == data[at + length]):
            length += 1
        if length > best_length:
            best_length, best_offset = length, at - candidate
            if best_length == maximum_length:
                break
    if best_length < 3:                    # a 2-byte match costs as much as it saves
        return 0, 0
    return best_offset, best_length


def _compress_chunk(data: bytes, start: int, end: int) -> Tuple[bytes, int]:
    """Encode one chunk; returns (chunk bytes, decompressed bytes consumed).

    The body is capped at 4096 bytes because the header carries the size in 12
    bits: a longer body wraps at 4095 and the chunk silently claims a size it
    does not have. That is a corrupt stream, not a large one, and it is why the
    encoder stops adding tokens rather than trusting the input to be
    compressible. Incompressible data hits this immediately -- a full window of
    it encodes to 4096 + 512 flag bytes.
    """
    tokens = bytearray()
    flags = 0
    slot = 0
    body = bytearray()
    at = start
    limit = min(end, start + MAX_CHUNK)
    full_window = (limit - start) == MAX_CHUNK
    while at < limit:
        offset, length = _longest_match(data, start, at, limit)
        added = 2 if length >= 3 else 1
        # The +1 is the FlagByte for the group currently being filled. It is not
        # in `body` yet -- it is written when the group of eight closes -- so it
        # must be counted on EVERY token, not only on the one that opens the
        # group. Counting it only at `slot == 0` let the body finish one byte
        # over the cap, and one byte over is enough for the 12-bit size field to
        # wrap: a 4097-byte body announced itself as 3, and the stream decoded
        # into nonsense.
        projected = len(body) + 1 + len(tokens) + added
        if projected > MAX_CHUNK:
            break
        if length >= 3:
            _lm, _om, bit_count, _ml = _copy_token_help(at - start)
            token = ((offset - 1) << (16 - bit_count)) | (length - 3)
            tokens += struct.pack("<H", token)
            flags |= 1 << slot
            at += length
        else:
            tokens.append(data[at])
            at += 1
        slot += 1
        if slot == 8:
            body.append(flags)
            body += tokens
            tokens = bytearray()
            flags = 0
            slot = 0
    if slot:
        body.append(flags)
        body += tokens

    consumed = at - start
    # Ran out of header space before finishing a FULL window: that is what a
    # RawChunk is for, and 4096 is its only legal size. Taking it here also
    # keeps the chunk non-short, which the next chunk depends on.
    if full_window and consumed < MAX_CHUNK:
        header = (4095 & 0x0FFF) | 0x3000                  # flag 0 = raw
        return (struct.pack("<H", header) + data[start:start + MAX_CHUNK],
                MAX_CHUNK)
    if consumed == MAX_CHUNK and len(body) >= MAX_CHUNK:
        header = (4095 & 0x0FFF) | 0x3000
        return struct.pack("<H", header) + data[start:at], consumed
    header = ((len(body) + 2 - 3) & 0x0FFF) | 0x3000 | 0x8000
    return struct.pack("<H", header) + bytes(body), consumed


def compress(data: bytes) -> bytes:
    """CompressedContainer per [MS-OVBA] 2.4.1: 0x01 signature, then chunks."""
    out = bytearray([0x01])
    at = 0
    while at < len(data):
        chunk, consumed = _compress_chunk(data, at, len(data))
        out += chunk
        at += consumed
    return bytes(out)


# ==========================================================================
# 'dir' stream records ([MS-OVBA] 2.3.4.2)
# ==========================================================================
def _rec(rec_id: int, payload: bytes) -> bytes:
    return struct.pack("<HI", rec_id, len(payload)) + payload


def _mbcs(s: str) -> bytes:
    return s.encode("latin-1", "replace")


def _utf16(s: str) -> bytes:
    return s.encode("utf-16-le")


@dataclass
class Module:
    name: str          # module + stream name (kept identical for simplicity)
    source: str        # VBA source text


def build_dir_stream(project_name: str, modules: List[Module]) -> bytes:
    out = bytearray()
    # --- PROJECTINFORMATION ---
    out += _rec(0x0001, struct.pack("<I", 0x00000001))            # SYSKIND = Win32
    out += _rec(0x0002, struct.pack("<I", 0x00000409))            # LCID
    out += _rec(0x0014, struct.pack("<I", 0x00000409))            # LCIDINVOKE
    out += _rec(0x0003, struct.pack("<H", 0x04E4))               # CODEPAGE 1252
    out += _rec(0x0004, _mbcs(project_name))                      # PROJECTNAME
    # PROJECTDOCSTRING (empty doc string + unicode)
    out += struct.pack("<HI", 0x0005, 0) + struct.pack("<HI", 0x0040, 0)
    # PROJECTHELPFILEPATH (two empty help files)
    out += struct.pack("<HI", 0x0006, 0) + struct.pack("<HI", 0x003D, 0)
    out += _rec(0x0007, struct.pack("<I", 0))                     # HELPCONTEXT
    out += _rec(0x0008, struct.pack("<I", 0))                     # LIBFLAGS
    # PROJECTVERSION: Id, fixed Reserved=4, VersionMajor(4), VersionMinor(2)
    out += struct.pack("<HI", 0x0009, 4) + struct.pack("<IH", 1, 0)
    # PROJECTCONSTANTS (empty + unicode)
    out += struct.pack("<HI", 0x000C, 0) + struct.pack("<HI", 0x003C, 0)

    # --- PROJECTREFERENCES (registered), in the order real Excel projects
    # store them: VBA + host Excel first (the default, non-removable libraries
    # every module depends on -- MsgBox/vbCrLf live in VBA, Worksheet/xlUp in
    # Excel; omitting them risks a compile error on load), then stdole+Office.
    out += _reference("VBA",
                      "*\\G{000204EF-0000-0000-C000-000000000046}#4.2#9#"
                      "C:\\Program Files\\Common Files\\Microsoft Shared\\VBA"
                      "\\VBA7.1\\VBE7.DLL#Visual Basic For Applications")
    out += _reference("Excel",
                      "*\\G{00020813-0000-0000-C000-000000000046}#1.9#0#"
                      "C:\\Program Files\\Microsoft Office\\Root\\Office16"
                      "\\EXCEL.EXE#Microsoft Excel 16.0 Object Library")
    out += _reference("stdole",
                      "*\\G{00020430-0000-0000-C000-000000000046}#2.0#0#"
                      "C:\\Windows\\System32\\stdole2.tlb#OLE Automation")
    out += _reference("Office",
                      "*\\G{2DF8D04C-5BFA-101B-BDE5-00AA0044DE52}#2.0#0#"
                      "C:\\Program Files\\Common Files\\Microsoft Shared\\OFFICE16"
                      "\\MSO.DLL#Microsoft Office 16.0 Object Library")

    # --- PROJECTMODULES ---
    out += _rec(0x000F, struct.pack("<H", len(modules)))          # module count
    out += _rec(0x0013, struct.pack("<H", 0xFFFF))               # PROJECTCOOKIE
    for m in modules:
        out += _rec(0x0019, _mbcs(m.name))                       # MODULENAME
        out += _rec(0x0047, _utf16(m.name))                      # MODULENAMEUNICODE
        # MODULESTREAMNAME: name, Reserved=0x0032, unicode name
        out += _rec(0x001A, _mbcs(m.name))
        out += struct.pack("<HI", 0x0032, len(_utf16(m.name))) + _utf16(m.name)
        # MODULEDOCSTRING (empty + unicode)
        out += struct.pack("<HI", 0x001C, 0) + struct.pack("<HI", 0x0048, 0)
        out += _rec(0x0031, struct.pack("<I", 0))                # MODULEOFFSET = 0
        out += _rec(0x001E, struct.pack("<I", 0))                # MODULEHELPCONTEXT
        out += _rec(0x002C, struct.pack("<H", 0xFFFF))           # MODULECOOKIE
        out += struct.pack("<HI", 0x0021, 0)                     # MODULETYPE procedural
        out += struct.pack("<HI", 0x002B, 0)                     # MODULE terminator
    out += struct.pack("<HI", 0x0010, 0)                          # dir terminator
    return bytes(out)


def _reference(name: str, libid: str) -> bytes:
    """REFERENCENAME + REFERENCEREGISTERED ([MS-OVBA] 2.3.4.2.2)."""
    out = bytearray()
    # REFERENCENAME: Id 0x0016, name, Reserved 0x003E, unicode name
    out += _rec(0x0016, _mbcs(name))
    out += struct.pack("<HI", 0x003E, len(_utf16(name))) + _utf16(name)
    # REFERENCEREGISTERED: Id 0x000D, Size, then SizeOfLibid + Libid + Reserved1(4)+Reserved2(2)
    libid_b = _mbcs(libid)
    body = struct.pack("<I", len(libid_b)) + libid_b + struct.pack("<IH", 0, 0)
    out += struct.pack("<HI", 0x000D, len(body)) + body
    return bytes(out)


def build_module_stream(source: str) -> bytes:
    """MODULEOFFSET = 0, so the stream is just the compressed source."""
    src = source.replace("\n", "\r\n")
    if not src.endswith("\r\n"):
        src += "\r\n"
    return compress(src.encode("latin-1", "replace"))


def build_vba_project_stream() -> bytes:
    """_VBA_PROJECT per [MS-OVBA] 2.3.4.1: Reserved1=0x61CC, Version (ignored
    on read), Reserved2 (1 byte) + Reserved3 (2 bytes) = 7 bytes total. Excel
    rebuilds the performance cache from 'dir' + module source."""
    return struct.pack("<HHBH", 0x61CC, 0xFFFF, 0x00, 0x0000)


# The PROJECTID GUID: the CMG/DPB/GC encryption keys off this string, so the
# ID line and the encryption MUST use the same value.
PROJECT_ID = "{5DD2A1D8-3F1C-4C2B-9B7E-0A1B2C3D4E5F}"


def ovba_encrypt(data: bytes, project_id: str = PROJECT_ID, seed: int = 0xBE) -> str:
    """[MS-OVBA] 2.4.3.1 Data Encryption -> uppercase-hex string for the
    PROJECT stream's CMG/DPB/GC keys. XOR chain keyed on the PROJECTID byte
    sum; payload = ignored bytes + 4-byte LE length + data. Deterministic seed
    keeps builds reproducible (any seed byte is legal)."""
    proj_key = sum(project_id.encode("latin-1")) & 0xFF
    version_enc = seed ^ 0x02                      # Version is always 2
    proj_key_enc = seed ^ proj_key
    out = bytearray([seed, version_enc, proj_key_enc])
    enc2, enc1, unenc1 = version_enc, proj_key_enc, proj_key

    def push(byte):
        nonlocal enc2, enc1, unenc1
        byte_enc = byte ^ ((enc2 + unenc1) & 0xFF)
        out.append(byte_enc)
        enc2, enc1, unenc1 = enc1, byte_enc, byte

    for i in range(1, ((seed & 6) >> 1) + 1):      # IgnoredLength filler bytes
        push(i & 0xFF)
    for byte in struct.pack("<I", len(data)) + data:
        push(byte)
    return out.hex().upper()


def ovba_decrypt(hex_str: str, project_id: str = PROJECT_ID) -> bytes:
    """[MS-OVBA] 2.4.3.2 Data Decryption -- the inverse, used by the tests to
    prove the keys parse exactly the way Excel/VBE will read them."""
    blob = bytes.fromhex(hex_str)
    seed, version_enc, proj_key_enc = blob[0], blob[1], blob[2]
    if seed ^ version_enc != 0x02:
        raise ValueError("bad Version (must decrypt to 2)")
    proj_key = sum(project_id.encode("latin-1")) & 0xFF
    if seed ^ proj_key_enc != proj_key:
        raise ValueError("ProjKey does not match the PROJECTID")
    enc2, enc1, unenc1 = version_enc, proj_key_enc, proj_key
    decoded = bytearray()
    for byte_enc in blob[3:]:
        byte = byte_enc ^ ((enc2 + unenc1) & 0xFF)
        decoded.append(byte)
        enc2, enc1, unenc1 = enc1, byte_enc, byte
    ignored = (seed & 6) >> 1
    body = bytes(decoded[ignored:])
    length = struct.unpack("<I", body[:4])[0]
    data = body[4:4 + length]
    if len(data) != length:
        raise ValueError("truncated payload")
    return data


def build_project_stream(project_name: str, modules: List[Module]) -> bytes:
    # Properly encrypted per [MS-OVBA] 2.4.3 (a malformed 2-byte value here
    # triggers the VBE's "invalid key 'DPB'" prompt in real Excel):
    # protection state = none, password = none, visibility = visible.
    cmg = ovba_encrypt(struct.pack("<I", 0), seed=0xBE)
    dpb = ovba_encrypt(bytes([0x00]), seed=0xD2)
    gc = ovba_encrypt(bytes([0xFF]), seed=0x91)
    lines = [
        f'ID="{PROJECT_ID}"',
    ]
    for m in modules:
        lines.append(f"Module={m.name}")
    lines += [
        f'Name="{project_name}"',
        'HelpContextID="0"',
        'VersionCompatible32="393222000"',
        f'CMG="{cmg}"',
        f'DPB="{dpb}"',
        f'GC="{gc}"',
        "",
        "[Host Extender Info]",
        "&H00000001={3832D640-CF90-11CF-8E43-00A0C911005A};VBE;&H00000000",
        "",
        "[Workspace]",
    ]
    for m in modules:
        lines.append(f"{m.name}=0, 0, 0, 0, C")
    return ("\r\n".join(lines) + "\r\n").encode("latin-1", "replace")


def build_projectwm_stream(modules: List[Module]) -> bytes:
    out = bytearray()
    for m in modules:
        out += _mbcs(m.name) + b"\x00" + _utf16(m.name) + b"\x00\x00"
    out += b"\x00\x00"
    return bytes(out)


# ==========================================================================
# CFB (compound file) writer ([MS-CFB])
# ==========================================================================
SECTOR = 512
MINI_SECTOR = 64
MINI_CUTOFF = 4096
FREESECT = 0xFFFFFFFF
ENDOFCHAIN = 0xFFFFFFFE
FATSECT = 0xFFFFFFFD
NOSTREAM = 0xFFFFFFFF


@dataclass
class DirEntry:
    name: str
    obj_type: int           # 1 storage, 2 stream, 5 root
    data: bytes = b""
    children: List[int] = None
    left: int = NOSTREAM
    right: int = NOSTREAM
    child: int = NOSTREAM
    start_sector: int = 0
    size: int = 0
    color: int = 1          # black


def _cfb_name_key(name: str):
    # CFB ordering: by UTF-16 length (incl. terminator), then case-insensitive.
    return (len(name) + 1, name.upper())


def _build_bst(entries: List[DirEntry], ids: List[int]) -> int:
    """Balanced BST over child ids sorted by CFB name key; returns root id."""
    ids = sorted(ids, key=lambda i: _cfb_name_key(entries[i].name))

    def build(lo, hi):
        if lo > hi:
            return NOSTREAM
        mid = (lo + hi) // 2
        node = ids[mid]
        entries[node].left = build(lo, mid - 1)
        entries[node].right = build(mid + 1, hi)
        return node

    return build(0, len(ids) - 1)


def write_vba_project(modules: List[Module], project_name: str = "VBAProject") -> bytes:
    # ---- assemble the logical streams/storages ----
    project = build_project_stream(project_name, modules)
    projectwm = build_projectwm_stream(modules)
    dir_stream = compress(build_dir_stream(project_name, modules))
    vba_proj = build_vba_project_stream()

    # Directory entries (index 0 = Root).
    entries: List[DirEntry] = []

    def add(name, obj_type, data=b""):
        entries.append(DirEntry(name=name, obj_type=obj_type, data=data,
                                size=len(data)))
        return len(entries) - 1

    root = add("Root Entry", 5)
    vba_storage = add("VBA", 1)
    i_project = add("PROJECT", 2, project)
    i_projectwm = add("PROJECTwm", 2, projectwm)
    i_dir = add("dir", 2, dir_stream)
    i_vbap = add("_VBA_PROJECT", 2, vba_proj)
    module_ids = []
    for m in modules:
        module_ids.append(add(m.name, 2, build_module_stream(m.source)))

    # tree wiring
    entries[root].child = vba_storage  # will be overwritten below to BST root
    root_children = [vba_storage, i_project, i_projectwm]
    entries[root].child = _build_bst(entries, root_children)
    vba_children = [i_dir, i_vbap] + module_ids
    entries[vba_storage].child = _build_bst(entries, vba_children)

    # ---- split streams: regular (>=4096) vs mini (<4096) ----
    stream_ids = [i_project, i_projectwm, i_dir, i_vbap] + module_ids
    mini_ids = [i for i in stream_ids if 0 < entries[i].size < MINI_CUTOFF]
    reg_ids = [i for i in stream_ids if entries[i].size >= MINI_CUTOFF]

    # ---- build the mini stream + miniFAT ----
    mini_stream = bytearray()
    minifat: List[int] = []
    for i in mini_ids:
        data = entries[i].data
        n = (len(data) + MINI_SECTOR - 1) // MINI_SECTOR
        start = len(minifat)
        entries[i].start_sector = start
        for k in range(n):
            minifat.append(start + k + 1 if k < n - 1 else ENDOFCHAIN)
        padded = data + b"\x00" * (n * MINI_SECTOR - len(data))
        mini_stream += padded
    mini_stream = bytes(mini_stream)

    # ---- lay out regular sectors ----
    # Sector plan (all in the FAT): [regular streams][mini-stream container]
    #   [miniFAT][directory][FAT]. We compute counts, then chain them.
    fat: List[int] = []
    file_sectors: List[bytes] = []   # parallel to fat indices

    def alloc(data: bytes) -> int:
        """Append data as a chain of 512-byte sectors; return first sector id."""
        if not data:
            return ENDOFCHAIN
        n = (len(data) + SECTOR - 1) // SECTOR
        start = len(fat)
        for k in range(n):
            seg = data[k * SECTOR:(k + 1) * SECTOR]
            seg = seg + b"\x00" * (SECTOR - len(seg))
            file_sectors.append(seg)
            fat.append(start + k + 1 if k < n - 1 else ENDOFCHAIN)
        return start

    # regular streams
    for i in reg_ids:
        entries[i].start_sector = alloc(entries[i].data)
    # mini stream container -> owned by Root entry
    if mini_stream:
        entries[root].start_sector = alloc(mini_stream)
        entries[root].size = len(mini_stream)
    else:
        entries[root].start_sector = ENDOFCHAIN
        entries[root].size = 0

    # miniFAT
    if minifat:
        minifat_bytes = b"".join(struct.pack("<I", x) for x in minifat)
        minifat_bytes += b"\xff" * (((len(minifat_bytes) + SECTOR - 1) // SECTOR) * SECTOR - len(minifat_bytes))
        minifat_start = alloc(minifat_bytes)
        minifat_count = len(minifat_bytes) // SECTOR
    else:
        minifat_start, minifat_count = ENDOFCHAIN, 0

    # directory
    dir_bytes = bytearray()
    for e in entries:
        dir_bytes += _encode_dir_entry(e)
    # pad to a whole number of sectors (with free entries = zeros but type 0)
    while len(dir_bytes) % SECTOR != 0:
        dir_bytes += _empty_dir_entry()
    dir_start = alloc(bytes(dir_bytes))
    dir_sectors = len(dir_bytes) // SECTOR

    # ---- FAT sectors: the FAT itself must be representable ----
    # Reserve FAT sectors and mark them FATSECT. Iterate until stable.
    n_fat_sectors = 1
    while True:
        total_sectors = len(fat) + n_fat_sectors
        entries_per_fat = SECTOR // 4
        need = (total_sectors + entries_per_fat - 1) // entries_per_fat
        if need <= n_fat_sectors:
            break
        n_fat_sectors = need

    fat_start = len(fat)
    for k in range(n_fat_sectors):
        fat.append(FATSECT)
        file_sectors.append(b"")   # placeholder; filled after FAT finalized

    # pad FAT to full sectors with FREESECT
    entries_per_fat = SECTOR // 4
    total_fat_entries = n_fat_sectors * entries_per_fat
    while len(fat) < total_fat_entries:
        fat.append(FREESECT)
    fat_bytes = b"".join(struct.pack("<I", x) for x in fat)
    # write FAT sector payloads
    for k in range(n_fat_sectors):
        file_sectors[fat_start + k] = fat_bytes[k * SECTOR:(k + 1) * SECTOR]

    # ---- DIFAT (header holds up to 109 FAT sector locations) ----
    difat = [FREESECT] * 109
    for k in range(n_fat_sectors):
        difat[k] = fat_start + k

    # ---- header ----
    header = bytearray()
    header += b"\xD0\xCF\x11\xE0\xA1\xB1\x1A\xE1"      # signature
    header += b"\x00" * 16                              # CLSID
    header += struct.pack("<HH", 0x003E, 0x0003)       # minor / major (v3)
    header += struct.pack("<H", 0xFFFE)                # byte order
    header += struct.pack("<HH", 0x0009, 0x0006)       # sector shift 512 / mini 64
    header += b"\x00" * 6                               # reserved
    header += struct.pack("<I", 0)                      # num dir sectors (v3 = 0)
    header += struct.pack("<I", n_fat_sectors)          # num FAT sectors
    header += struct.pack("<I", dir_start)              # first dir sector
    header += struct.pack("<I", 0)                      # transaction sig
    header += struct.pack("<I", MINI_CUTOFF)            # mini stream cutoff
    header += struct.pack("<I", minifat_start)          # first miniFAT sector
    header += struct.pack("<I", minifat_count)          # num miniFAT sectors
    header += struct.pack("<I", ENDOFCHAIN)            # first DIFAT sector
    header += struct.pack("<I", 0)                      # num DIFAT sectors
    header += b"".join(struct.pack("<I", x) for x in difat)
    assert len(header) == SECTOR, len(header)

    return bytes(header) + b"".join(file_sectors)


_ZERO_TIME = b"\x00" * 8


def _encode_dir_entry(e: DirEntry) -> bytes:
    name16 = e.name.encode("utf-16-le")
    name16 = name16[:62]
    name_field = name16 + b"\x00\x00"
    name_field += b"\x00" * (64 - len(name_field))
    name_len = len(e.name) * 2 + 2 if e.name else 0
    out = bytearray()
    out += name_field
    out += struct.pack("<H", name_len)
    out += struct.pack("<B", e.obj_type)
    out += struct.pack("<B", e.color)
    out += struct.pack("<I", e.left)
    out += struct.pack("<I", e.right)
    out += struct.pack("<I", e.child)
    out += b"\x00" * 16                                  # CLSID
    out += struct.pack("<I", 0)                          # state bits
    out += _ZERO_TIME + _ZERO_TIME                       # ctime / mtime
    out += struct.pack("<I", e.start_sector if e.size or e.obj_type in (1, 5) else 0)
    out += struct.pack("<Q", e.size)
    assert len(out) == 128, len(out)
    return bytes(out)


def _empty_dir_entry() -> bytes:
    out = bytearray(b"\x00" * 64)
    out += struct.pack("<H", 0)
    out += struct.pack("<B", 0)            # type unknown/unallocated
    out += struct.pack("<B", 0)
    out += struct.pack("<I", NOSTREAM)     # left
    out += struct.pack("<I", NOSTREAM)     # right
    out += struct.pack("<I", NOSTREAM)     # child
    out += b"\x00" * 16
    out += struct.pack("<I", 0)
    out += _ZERO_TIME + _ZERO_TIME
    out += struct.pack("<I", 0)
    out += struct.pack("<Q", 0)
    assert len(out) == 128, len(out)
    return bytes(out)


if __name__ == "__main__":
    import os
    here = os.path.dirname(os.path.abspath(__file__))
    src = open(os.path.join(here, "macro.bas"), encoding="utf-8").read()
    mods = [Module(name="FREDDashboard", source=src)]
    blob = write_vba_project(mods)
    out = os.path.join(here, "build", "vbaProject.bin")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "wb") as fh:
        fh.write(blob)
    print(f"wrote {out}: {len(blob)} bytes")
