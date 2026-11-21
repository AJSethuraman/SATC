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


def test_the_addon_has_room_for_more_top_level_names():
    """WoW's Lua 5.1 refuses a file with more than 200 local names at its top level, and the addon
    then does not load at all. 2.0.13's banner work hit exactly that (12 Nov 2026), caught only
    because the tests load the file. Keep at least 10 spare."""
    from lupa import lua51
    from conftest import ADDON
    src = ADDON.read_text() + "\n" + "\n".join(f"local _spare{i} = {i}" for i in range(10)) + "\n"
    lua51.LuaRuntime().compile(src)   # raises if the limit is crossed


def test_the_toc_is_whole():
    """2.5.2 to 2.5.4 shipped an empty .toc (a script truncated it), and the game listed the
    addon as Incompatible. The owner's screenshot, 13 Nov 2026."""
    toc = (ROOT / "ServiceInviter" / "ServiceInviter.toc").read_text()
    assert "## Interface:" in toc and "## Version:" in toc
    assert "Services.lua" in toc and "ServiceInviter.lua" in toc
    version = re.search(r"## Version: (\S+)", toc).group(1)
    first = (ROOT / "ServiceInviter" / "ServiceInviter.lua").read_text().splitlines()[0]
    assert first.endswith("v" + version)
