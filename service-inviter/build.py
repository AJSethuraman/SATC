"""Build Install-ServiceInviter.bat: the installer template with the addon zipped inside it.

    python build.py           write it
    python build.py --check   fail if the committed .bat is not what the source builds

The zip is built with fixed timestamps and LF line endings, so the same source always
gives the same installer, on any machine.
"""
import base64
import io
import sys
import zipfile
from pathlib import Path

HERE = Path(__file__).parent
ADDON = HERE / "ServiceInviter"
TEMPLATE = HERE / "installer.template.bat"
OUT = HERE / "Install-ServiceInviter.bat"
FILES = ["ServiceInviter.toc", "ServiceInviter.lua"]


def build() -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for name in FILES:
            info = zipfile.ZipInfo(f"ServiceInviter/{name}", date_time=(2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            text = (ADDON / name).read_bytes().replace(b"\r\n", b"\n")
            z.writestr(info, text)
    b64 = base64.b64encode(buf.getvalue()).decode()
    payload = "\n".join(b64[i:i + 76] for i in range(0, len(b64), 76))
    template = TEMPLATE.read_bytes().decode().replace("\r\n", "\n")
    assert template.count("{PAYLOAD}") == 1
    return template.replace("{PAYLOAD}", payload).replace("\n", "\r\n").encode()


if __name__ == "__main__":
    want = build()
    if "--check" in sys.argv:
        have = OUT.read_bytes().replace(b"\r\n", b"\n") if OUT.exists() else b""
        if have != want.replace(b"\r\n", b"\n"):
            sys.exit(f"{OUT.name} is stale: run python build.py")
        print(f"{OUT.name} matches the source")
    else:
        OUT.write_bytes(want)
        print(f"wrote {OUT.name} ({len(want):,} bytes)")
