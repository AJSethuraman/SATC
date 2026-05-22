from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
from pathlib import Path
from queue import Queue
import re
from typing import Any

from categorizer import categorize_file
from excel_report import build_workbook

CHUNK_SIZE = 1024 * 1024
OLD_FILE_YEARS = 7
LARGE_FILE_BYTES = 1024**3


@dataclass
class ScanConfig:
    root_path: Path
    output_file: Path
    filter_mode: str
    extension_text: str
    detect_duplicates: bool = True


def parse_extensions(text: str) -> set[str]:
    vals = [x.strip().lower() for x in re.split(r"[\s,;]+", text.strip()) if x.strip()]
    out: set[str] = set()
    for v in vals:
        if v in {"(none)", "none", "<none>"}:
            out.add("")
        elif v.startswith("."):
            out.add(v)
        else:
            out.add("." + v)
    return out


def should_include(ext: str, mode: str, selected: set[str]) -> bool:
    if mode == "all":
        return True
    if mode == "include":
        return ext in selected
    if mode == "exclude":
        return ext not in selected
    return True


def _dt(ts: float) -> datetime:
    return datetime.fromtimestamp(ts, tz=timezone.utc).astimezone().replace(tzinfo=None)


def _hash_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            chunk = f.read(CHUNK_SIZE)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def _likely_source(top: str) -> str:
    if not top:
        return "Unknown"
    t = top.lower()
    for marker in ["laptop", "desktop", "server", "backup", "pc", "mac", "qnap", "nas"]:
        if marker in t:
            return top
    return "Unknown"


def run_scan(config: ScanConfig, events: Queue[dict]) -> None:
    errors: list[dict[str, str]] = []
    records: list[dict[str, Any]] = []
    selected_exts = parse_extensions(config.extension_text) if config.filter_mode != "all" else set()

    files_scanned = 0
    files_hashed = 0

    try:
        events.put({"type": "progress", "phase": "Metadata Scan", "message": "Scanning file metadata..."})
        for path in config.root_path.rglob("*"):
            try:
                if path.is_symlink() or not path.is_file():
                    continue
                ext = path.suffix.lower()
                if not should_include(ext, config.filter_mode, selected_exts):
                    continue
                st = path.stat()
                rel_parts = path.relative_to(config.root_path).parts
                top = rel_parts[0] if rel_parts else ""
                modified = _dt(st.st_mtime)
                rec = {
                    "full_path": str(path), "folder_path": str(path.parent), "file_name": path.name, "extension": ext,
                    "category": categorize_file(ext, str(path).lower()), "size_bytes": st.st_size,
                    "size_mb": round(st.st_size / (1024**2), 2), "size_gb": round(st.st_size / (1024**3), 2),
                    "created_date": _dt(st.st_ctime), "modified_date": modified, "accessed_date": _dt(st.st_atime),
                    "top_level_folder": top, "parent_folder": path.parent.name, "likely_source": _likely_source(top),
                    "hash": "", "duplicate_group_id": "", "duplicate_confidence": "Not checked",
                    "recommended_action": "No Action", "reason_flagged": "", "scan_error": "",
                }
                records.append(rec)
                files_scanned += 1
                if files_scanned % 100 == 0:
                    events.put({"type": "progress", "phase": "Metadata Scan", "files_scanned": files_scanned, "files_hashed": files_hashed, "duplicate_groups": 0, "errors": len(errors)})
            except Exception as ex:
                errors.append({"full_path": str(path), "error_type": type(ex).__name__, "error_message": str(ex), "stage": "Metadata Scan"})

        dup_groups = {}
        total_dup_groups = 0
        if config.detect_duplicates:
            events.put({"type": "progress", "phase": "Hashing", "message": "Hashing duplicate-size candidates...", "files_scanned": files_scanned, "files_hashed": files_hashed, "errors": len(errors)})
            by_size: dict[int, list[dict[str, Any]]] = {}
            for r in records:
                by_size.setdefault(r["size_bytes"], []).append(r)
            dup_id = 1
            for _, group in sorted(by_size.items(), key=lambda kv: kv[0]):
                if len(group) < 2:
                    continue
                by_hash: dict[str, list[dict[str, Any]]] = {}
                for r in group:
                    try:
                        r["hash"] = _hash_file(Path(r["full_path"]))
                        r["duplicate_confidence"] = "Not duplicate"
                        files_hashed += 1
                    except Exception as ex:
                        r["scan_error"] = f"Hash failed: {ex}"
                        errors.append({"full_path": r["full_path"], "error_type": type(ex).__name__, "error_message": str(ex), "stage": "Hashing"})
                        continue
                    by_hash.setdefault(r["hash"], []).append(r)
                for h, hgroup in by_hash.items():
                    if len(hgroup) > 1:
                        gid = f"DUP-{dup_id:06d}"
                        dup_id += 1
                        total_dup_groups += 1
                        dup_groups[gid] = hgroup
                        for r in hgroup:
                            r["duplicate_group_id"] = gid
                            r["duplicate_confidence"] = "Exact hash match"
                events.put({"type": "progress", "phase": "Hashing", "files_scanned": files_scanned, "files_hashed": files_hashed, "duplicate_groups": total_dup_groups, "errors": len(errors)})

        now = datetime.now()
        old_cutoff = now.replace(year=now.year - OLD_FILE_YEARS)
        for r in records:
            reason = ""
            if r["duplicate_group_id"]:
                r["recommended_action"] = "Review Duplicate"
                reason = "Exact duplicate based on size and SHA-256 hash"
            elif r["category"] in {"Backup/Image", "Virtual Machine"}:
                r["recommended_action"] = "Review Backup File"
                reason = "Backup-like or disk-image file type" if r["category"] == "Backup/Image" else "Virtual machine file type"
            elif r["size_bytes"] > LARGE_FILE_BYTES:
                r["recommended_action"] = "Review Large File"
                reason = "Large file over 1 GB"
            elif r["modified_date"] and r["modified_date"] < old_cutoff:
                r["recommended_action"] = "Review Old File"
                reason = f"File not modified in more than {OLD_FILE_YEARS} years"
            r["reason_flagged"] = reason

        potential_recoverable = sum((len(v)-1) * v[0]["size_bytes"] for v in dup_groups.values())
        modified_dates = [r["modified_date"] for r in records if r.get("modified_date")]
        scan_meta = {
            "scan_root": str(config.root_path),
            "output_file": str(config.output_file),
            "scan_date": now.strftime("%Y-%m-%d %H:%M:%S"),
            "file_type_mode": config.filter_mode,
            "extension_filter": ", ".join(sorted(selected_exts)) if selected_exts else "(all)",
            "duplicate_detection": config.detect_duplicates,
            "total_files": len(records),
            "total_size_gb": round(sum(r["size_bytes"] for r in records)/(1024**3), 2),
            "total_duplicate_groups": len(dup_groups),
            "total_duplicate_files": sum(len(v) for v in dup_groups.values()),
            "potential_recoverable_gb": round(potential_recoverable/(1024**3), 2),
            "files_skipped_error": len(errors),
            "largest_file_gb": round(max((r["size_bytes"] for r in records), default=0)/(1024**3), 2),
            "oldest_modified": min(modified_dates).strftime("%Y-%m-%d %H:%M:%S") if modified_dates else "",
            "newest_modified": max(modified_dates).strftime("%Y-%m-%d %H:%M:%S") if modified_dates else "",
        }

        events.put({"type": "progress", "phase": "Export", "message": "Writing Excel report...", "files_scanned": files_scanned, "files_hashed": files_hashed, "duplicate_groups": len(dup_groups), "errors": len(errors)})
        build_workbook(records, errors, scan_meta, config.output_file)
        events.put({"type": "done", "output_file": str(config.output_file)})
    except PermissionError as ex:
        msg = f"Permission denied while writing report. Is the output workbook open? Details: {ex}"
        errors.append({"full_path": str(config.output_file), "error_type": type(ex).__name__, "error_message": str(ex), "stage": "Export"})
        events.put({"type": "error", "message": msg})
    except Exception as ex:
        events.put({"type": "error", "message": f"Unexpected scan error: {type(ex).__name__}: {ex}"})
