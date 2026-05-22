from __future__ import annotations

CATEGORY_MAP: dict[str, set[str]] = {
    "Excel": {".xlsx", ".xls", ".xlsm", ".xlsb", ".csv"},
    "Word": {".docx", ".doc", ".rtf"},
    "PDF": {".pdf"},
    "Image": {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tif", ".tiff", ".heic", ".webp"},
    "Video": {".mp4", ".mov", ".avi", ".mkv", ".wmv", ".m4v", ".mpg", ".mpeg"},
    "Audio": {".mp3", ".wav", ".aac", ".flac", ".m4a", ".wma"},
    "Archive": {".zip", ".rar", ".7z", ".tar", ".gz", ".bz2"},
    "Email": {".pst", ".ost", ".msg", ".eml", ".mbox"},
    "Database": {".db", ".sqlite", ".sqlite3", ".mdb", ".accdb", ".sql"},
    "Backup/Image": {".bak", ".backup", ".tib", ".vhd", ".vhdx", ".img", ".iso", ".dmg"},
    "Virtual Machine": {".vmdk", ".vdi", ".vmx", ".ova", ".ovf"},
    "Executable/Installer": {".exe", ".msi", ".bat", ".cmd", ".app", ".pkg", ".deb", ".rpm"},
    "Text/Code": {".txt", ".md", ".py", ".js", ".ts", ".html", ".css", ".json", ".xml", ".yaml", ".yml", ".ini", ".cfg", ".log"},
    "Temporary/System": {".tmp", ".temp", ".cache", ".lnk", ".ds_store"},
}


def categorize_file(extension: str, lower_path: str = "") -> str:
    ext = (extension or "").lower()
    if ext in {".vhd", ".vhdx", ".img", ".iso", ".dmg"} or any(x in lower_path for x in ["backup", "image"]):
        if ext in CATEGORY_MAP["Virtual Machine"]:
            return "Virtual Machine"
        if ext in CATEGORY_MAP["Backup/Image"]:
            return "Backup/Image"
    for category, exts in CATEGORY_MAP.items():
        if ext in exts:
            return category
    return "Other"
