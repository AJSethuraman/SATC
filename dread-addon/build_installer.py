"""Builds dist/Install-Dread.bat: one double-click file that carries the addon inside it and
copies it into the Forever AddOns folder. Run again after any change to Dread/.

    python build_installer.py
"""
import base64, io, os, zipfile

TARGET = r"C:\Program Files (x86)\World of Warcraft\_forever_\Interface\AddOns"

HEAD = r"""@echo off
setlocal
set "ADDONS=__TARGET__"
title Install Dread

rem Program Files needs administrator rights. Ask for them and run this file again.
net session >nul 2>&1
if errorlevel 1 (
  echo Asking for administrator permission to write to Program Files...
  powershell -NoProfile -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
  exit /b
)

if not exist "%ADDONS%" (
  echo Could not find: %ADDONS%
  echo Edit the ADDONS line at the top of this file to your AddOns folder, then run it again.
  pause
  exit /b 1
)

echo Installing Dread into %ADDONS%\Dread ...
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
 "$ErrorActionPreference='Stop';" ^
 "$b64 = (Get-Content -LiteralPath '%~f0' | Where-Object { $_.StartsWith('::B64:') } | ForEach-Object { $_.Substring(6) }) -join '';" ^
 "$zip = Join-Path $env:TEMP 'Dread.zip';" ^
 "[IO.File]::WriteAllBytes($zip, [Convert]::FromBase64String($b64));" ^
 "$old = Join-Path '%ADDONS%' 'Dread'; if (Test-Path -LiteralPath $old) { Remove-Item -LiteralPath $old -Recurse -Force };" ^
 "Expand-Archive -LiteralPath $zip -DestinationPath '%ADDONS%' -Force;" ^
 "Remove-Item -LiteralPath $zip;" ^
 "Get-ChildItem -LiteralPath (Join-Path '%ADDONS%' 'Dread') | Select-Object -ExpandProperty Name"
if errorlevel 1 (
  echo.
  echo Something went wrong. Copy the message above and send it over.
  pause
  exit /b 1
)
echo.
echo Done. In WoW, type /reload and then /dread
pause
exit /b 0

"""

def main():
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(os.listdir("Dread")):
            z.write(os.path.join("Dread", f), "Dread/" + f)
    b64 = base64.b64encode(buf.getvalue()).decode()
    lines = [b64[i:i + 100] for i in range(0, len(b64), 100)]
    text = HEAD.replace("__TARGET__", TARGET) + "\n".join("::B64:" + l for l in lines) + "\n"
    os.makedirs("dist", exist_ok=True)
    with open("dist/Install-Dread.bat", "w", newline="") as fh:
        fh.write(text.replace("\n", "\r\n"))
    with open("dist/Dread.zip", "wb") as fh:
        fh.write(buf.getvalue())
    print("wrote dist/Install-Dread.bat and dist/Dread.zip")

if __name__ == "__main__":
    main()
