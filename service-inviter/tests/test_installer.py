"""The installer: built from this source, and what it does to Trade Inviter.

PowerShell and cmd are not available where these run, so these read the script;
the install itself has to be watched on Windows.
"""
import base64
import io
import re
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).parent.parent
BAT = ROOT / "Install-ServiceInviter.bat"


def _ps():
    text = BAT.read_bytes().decode()
    return text[text.index("#PS-BEGIN"):]


def test_the_committed_installer_is_built_from_this_source():
    r = subprocess.run([sys.executable, "build.py", "--check"], cwd=ROOT, capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr


def test_the_installer_carries_exactly_this_addon():
    b64 = re.search(r"\$b64 = @'\r\n(.*?)\r\n'@", BAT.read_bytes().decode(), re.S).group(1)
    z = zipfile.ZipFile(io.BytesIO(base64.b64decode(re.sub(r"\s", "", b64))))
    for name in ("ServiceInviter.toc", "Services.lua", "ServiceInviter.lua"):
        src = (ROOT / "ServiceInviter" / name).read_bytes().replace(b"\r\n", b"\n")
        assert z.read(f"ServiceInviter/{name}") == src


def test_it_removes_trade_inviter_from_addons():
    ps = _ps()
    assert "$old = Join-Path $dest 'TradeInviter'" in ps
    assert "Remove-Item -LiteralPath $old -Recurse -Force" in ps
    assert "Move-Item" not in ps


def test_it_no_longer_claims_settings_were_copied():
    assert "already copied" not in _ps()


def test_its_own_path_is_quoted_safely_for_powershell():
    head = BAT.read_bytes().decode().split("#PS-BEGIN")[0]
    assert "set \"SELF=%SELF:'=''%\"" in head
    assert "'%~f0'" not in head
