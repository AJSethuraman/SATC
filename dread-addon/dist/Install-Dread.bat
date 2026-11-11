@echo off
setlocal
set "ADDONS=C:\Program Files (x86)\World of Warcraft\_forever_\Interface\AddOns"
title Install Dread

rem No parenthesised blocks anywhere in this file: the ")" in "(x86)" ends a block early and
rem closes the window with a syntax error. Everything branches with goto instead.

net session >nul 2>&1
if errorlevel 1 goto elevate
if not exist "%ADDONS%" goto nofolder

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
if errorlevel 1 goto failed
echo.
echo Done. In WoW, type /reload and then /dread
goto finish

:elevate
echo Asking for administrator permission to write to Program Files...
powershell -NoProfile -Command "Start-Process -FilePath cmd.exe -ArgumentList '/k','\"%~f0\"' -Verb RunAs"
exit /b

:nofolder
echo Could not find: %ADDONS%
echo Edit the ADDONS line at the top of this file to your AddOns folder, then run it again.
goto finish

:failed
echo.
echo Something went wrong. Copy the message above and send it over.

:finish
echo.
pause
exit /b

::B64:UEsDBBQAAAAIAOmTa11BmOw7pAsAAKEeAAAPAAAARHJlYWQvRHJlYWQubHVhrVl7c9pIEv/fn2JKOVdJWayA42R9pJwqjO2Yig0+
::B64:wPHu2TmVkAaYtdBopcEOl+S7X3fPSIwwSSq7R9mA5tGv+fVr2NtjL+KchzEzrzEvFGu1WavZZAv5INIZK/5chjkvGuzsasTCNGYL
::B64:vpD5ik1lzl6xhUiXihc7exWlsCi4KjSl/TYTkUxhcyGXaQyfMuVssSxExFQeRvfWvkLJDCSgj8d5qPgDz5koWL5MU5ADVw55sUyA
::B64:NsjDslykisckUZgUkhXhAzwqyU6Q3Mmxn5vV7ghnPoS5CCcJLzx/J5FRmLDOycmg32BpwY6Y75ejI7GA57Tw4cvOjqEFI+U30Prz
::B64:151NHkdPuOp1huh0mUZKyBSEXLmLYuZp8V3nSzSF1yt40f4vOXNAFkZLeBpvbs95JPPYveerBnsIkyX3NvnewtxHEIdm3xA/GEGa
::B64:TlvTNvuQ+iZ5OFnXAyZqmacskknCIzUL80k4464TwQkqx2zc+5svAzQjwE2DnTcYnMXJ9bAz7g36oMDrZrPBDvCthW8vm81S2jxc
::B64:8MYalo8yT+JGBZNNnSZLkcRnuMf1dhgTU02AqTlPS1VRJWbGj1gXLKq43uLQh9NgDtm5fLruXQHzVMH4MaA4zmU25ossgX2OV5Jq
::B64:j7gaif9y94b9wvZBh3P4fNWszV9JgkH3tD8+Hda3loTdz2wyOxMJiub0APP5NIz43d3xUilwrbu7m/Pe+PTwt0OQi8cz/hNLUTpY
::B64:2mJft3LuykTmLghu/vzDV1vXHQMmeW5W+69xZcu8tWobLuUDuqCrckDgGzN+muLYpVwWZqLaMeQzUYASZzI/ycOZ61zwqdK6bFg5
::B64:ykUGZhykuG6kwlyBhjTt09MlhbLv7pGZtUVmescgBxPZO33FPykwmSZjkCJTNVLgzzM3FQlAYvDhdHjR+R1R8w6W4Xxf5oswcep0
::B64:LACMB1cXp2djB9HeYHuH64WIs/BbqCR+tG5jwxp7ALstc4bt8WA8HlxanFsET+NbwBVCGKNILxAn4KMsljuYKLSXVaYwlLWQY9Bt
::B64:mXNjjc5wfDMYvifdGVOVZIcNdmiNEXzKna5gz9nLX9kuOr/HXugYQKOvW9tGW5trW5q00eRWYExUMISuvi30YdrBmNRyQYVCpiZW
::B64:pFKVkWVLxChnjvAgtoPrOosxKNBRrfF3LmIdjjA+O4piIYmQ8diE6VKM7cICprW0SGQjxFFABJkggfkpf3QhruoAe7BvecBcPtJq
::B64:TZonYVZwCKNKRPcAqQwCK2SD0zBPVkBKB4DPXxtG0bXi6LEw8DRZ0LOz5gDUyBVhD6WZH5ir1NUNGixW+jBRIYgHmWtCfjlO+ITS
::B64:gomUiSwUeaFX+HLyR+GViLXB0O4mPMw7SUJ+ULje0xXfcBIL7Rj87Snpf8K3lSamEcLqlgXlzTOkgliZQfxKawFwNPAWYzLCzYhl
::B64:tjbNI5zO7TN4g40txPU7ruj0czBdpUo9zKBjuQUFKX+KsQj0oozGDPgY24USDLxnF2tBLPV2/eYUvl4sQ/31/bHT2CnrxEqrMmM3
::B64:Kqk+NvQBe3U7GGeqQIV1W2mLt5jutX99E0hvbDzqQsUibVGqagjLgN+D5zqaQcEZiwhOJeYqFIlxITPq1n0CIFciutS3xFAVSZyp
::B64:SEUx53HFx9Rv5PEtgIyhTeUZ+6Id3zCHbxvnBQsi0LKNeOezHAtqtgsyTSANV48Myj2esRt5g94wzSH3eNa5KamJuoCZLpTErrMI
::B64:P8FpO57X+Obk8T1M144T3jejVxkS0BlJj+ocSLnCZxcc6nA8FfYo0lg+Mpnx1K+V/1C9R2Ea8cR3TOT7/xSa+9g9dAFyAsOLbiBm
::B64:Sw6dSoE8J5zcAPGMGL1P5WO6N5MyZlmo5iD6GITWBTZ2JKgCHG2Mh2NCc6876I8wX4JVnF7/QzCCCBQHzQMsAuh5LngCA6/KgXOe
::B64:LLgKmoflQHcOIgRXWEM2W+XgsZSqoF0l4UtRRMFxOLN2XkmMlMGrg82BigxtescXwXA5WQXN/dp4F8JcgCyRxSjjSRKciZwHZwlE
::B64:kGOZYC1VjucAEf2OE5qQnuqHmLmDCzGbKwTCemY0D+G0zYemt+Z0LpMVvZWMOhORCLUKbsI8FzIHs4T5jNszQwlHF4yog7LHz5dY
::B64:8QajVGQ8h/xW42PEg5KSpxgowT41I/wL0ICDl2F+D/u+lt3g4Lp/Uh7sZ+bcC9Umh8vgnwBs56qqd4JTXI3QI10i8L43pnhXPvi9
::B64:d8Fxp/v+Cv6DwdVpH8PJ4et9Cmnsa8PiFcHhAIvq9fO8LgaDcXDT658MboLuoNcPaAY5tvabWzgm0HgnbJmVXH+e43UvuDh9d9o/
::B64:6Qx/D4j9eNAZjZHl65f//LVVZ4ouBjbVZX3jx2pif+M69PXuzmpyxLWonnST0PHlTOPw7DdnG9M/8dChPkg5Mf4rTAk3XQm9H1d8
::B64:K78SSpfXo14XGzND5RJvQe7u/g3czdfrFNqoCKAMX7tB9eQvspfOkxoQ4i2Gtv1tFeBGiYchGcooZdVHptDB4gjKb12OmthuErWu
::B64:H+j2Zp1J7UHTHFTlV4rd85oDRUSr+PqrDYPdMhzQlUBt/En/VC/Q1uPYU+xBW0B9ggctw8Eh1E8H0GxBcp3700RC91quebFes8cO
::B64:6iUVab9uKKyUWNW6kzCu9U4/MM6maUoO6+aoNJDd1Pciaukp16amA6Tl5bEzBkmvwxaiKCgx471AgjlYZ7BZzqHecspppVk46KUh
::B64:NDiLTK0o/flsyDMJhTteytHOKBE8VZj9C99SYCZRBdV+t5bXs0s/nKcaD8xz+wxtZOpXMo5txS21q12t7iNNwuCEJ/LxjblcZBl4
::B64:K10whqyAQiuNoeaQ8p6CU4I3CalvNSRIoS8VXoC4z3T+3mMolkcVywsyrJmgEkaz1JEBLx4rk2mnIY3eMlPHWtSrr0TFTUFC0+Mp
::B64:vPnwYTqC+g62A2DhT/P3nLLJtGrG/YCEgFU1oj5b2xxABQeM9gai0RzERLl0vIM9U5Ev2GTF+IpTsQPGSlcGCyYooJEqK+X67Oto
::B64:Liwo6wxZYbkbjAV0In5nCkB1hZ0ca4FAQpf5KKABwzM7YhmMJW5xu/9xXSoj49tnRgADleIWPlDlIzKga063qlxLkh7C2DkdDgfD
::B64:Ko7AGQl2dMSemaRu9QebVtaAAjPXTkiLAif0pjwkf62D0EbPcimnDP7CZSxkW5v4cS7gJFZyycJILUHTFZtD/xn7lWxVt6gLa/1Y
::B64:t2Up9i94D7Nh1e/YFB8ovzR0BtIb6urShbxjFmiY7r1lP2FhY4wLcrKG9gCrrif6WllSkCp7++ofzd3WrqvQsQTe8PIQ4ZumMBmB
::B64:vwHkIoxAfywhBEw4NkFMKHL6wt+SHSnNFtYdRzUZPbhpleJTC05PGqDUK7MitTokJ8QWpWBRsc2JPyNxneEDfbHZSRJ6dKDB2pyj
::B64:OuHpMB0XTNBJrScvQ7wM/SCT5YLXtwGdbcNEp5yAUkRHl7VB8C6ldskHRUKRxludWy++fab3lN6IPbw2z5ZZKLPo4I2dCFzfKpZJ
::B64:VFcDVBdOVrSpFS7I4RvRpszez9nLLXEHT3Cjo77djV/sxh9Zf3DTht4Zw2qDaSWQLcQa72nUytfhSlnxigBCnmXyw3b3yWt+4/3Q
::B64:6bVFNzTSzLBuhdYUuhu2KGNMulxMeF5QrNEh5okfYsNLzXbplZZP/u1uu0jCYg55ZrEArXdGF53ReXAyPO2ctLDy1aI4OyNc1V3E
::B64:GC98msbap1QP+j00B3xgasYPtJjjtSHXg0m89gITm+v8Z7d47vp7Hnz8wzH3tbQJODk6Bm1clPKk4NYi/UulWVqrpzcWornMMhit
::B64:3Qdbtz365iLB656SgPVTk33xWxY7G1woTFTSWPFrizg6ZOvF9HsFOdCWxeZ3Qccq4sGcgOMH9CrtVBu/IWp/x18Oa78b2mJrBBpo
::B64:fdn46fdLLa5bj4i6L08BWQ2VsnrVNf3/AFBLAwQUAAAACACkkWtdFK3qlMQAAAAGAQAADwAAAERyZWFkL0RyZWFkLnRvYyVOu4rD
::B64:MBDs/RUDbmwwPsscKVKGcEeaaxLSb6z1RSBLQbt2yN9HdqqdHeZVljgF5TTSwHuYXdeZoixxcerzf0xMFtXIJO7mvNMXlEWlXjV/
::B64:MeM9LpmAgY/xAXkw2+ZD9SARVmlXIQj/NDFerO3qPdPC9krJ0c2vIVvR8VCUnwlwguedFF92nnIsex60+m7wy3qYnbenMMaqrpFY
::B64:5xTYIgb8xMQLJ1TxGfKRITEHuUdtYEwesaDv+l3dFmc3tX6mYivd0BtQSwMEFAAAAAgA4ZBrXb7XYUjzAwAA8QcAAA0AAABEcmVh
::B64:ZC9TaW0ubHVhbVVdb9s2FH33r7hwYUxuJEVKnC2o6wAetg7F0i6AA/RhGAZGoixuMumKkh2hyH/fuaQs2+keLFPk/Tj3nMurKKKH
::B64:tpa0FhtJlVmrLKbPhr6YL7R8+EiZqCobkjWkGqpbbanVuaxpWwml6b4VJHQOK01PEkcwaqRtZB6PKgNf+jsk+CwojuORW+Bhavr2
::B64:MuoNVmqDXbxrG/s1nqNRFNFqg9yUy0bWG6WVbVRGNbKZDa2llrVoEAjABFkpcxLVXnSW1monLTWlJMsVAXI8KlqdNcpoDh3Xeh2w
::B64:w3RE5CEwLN7BRi2bttZ0cAjYiJxBYOktpWlyfZPeXM1u6ILSq+vZzZQmdJXOfprdXv84u3XWfQxLl+cnUucj/nFtOP7aihpIlbYq
::B64:lyhiT89UEva0CEmKrKS9arBBW2OVQ89MC9pJoFZNRwHTbS+tzKavStRyH+iQ9iGVIZ3XygR6jgciWI/0aLE3dcUm34Bo4WLgD3HM
::B64:0z/WKUUvsC3gpPCaQl/KjSvc+wu9riROOFMwBWlX+G1EU8ZbdWJmt5x6QbMEVA62t4kzcRhizvin+ouTul0CQydxAa07fS/D3mrH
::B64:Zi5jZmzg8PC5yxjSrjucWqVfn7oIL71Yg5QOzqDdJ7OTJHey7pgTmTX01FHegOjM6NzO6clADEmmKFwfOklpzxfplU64KNvABQ8R
::B64:4EQCT7pnAS9+Ufa040rhNmpSW6FqGxy5mp4L8ez5MfEzGDYxWHmLLHCOO7/RuQ3noQpw+54SBqwdzdHz3Dth6f5lZaUzu0NjDGYs
::B64:7p4i+s7a8ecCd8fAjCfq5j65N+0OgTsELo9mHLhE4O+s+8Aoy5eycIW+ul+PGEKU4q7UuYJARY2h0c+EbSVtTI8lLl9pqtyyPv5s
::B64:K7Mf7Du6u07ow8MKjW1oIzcGOq9rs0fDcORiC5MK0wj6koHOkYi88uyEjhG50mtkgOuvoq46jAEs70Uj39HvP5MoMM9wjYsWwy0z
::B64:VYUG4riC8WLOtY30F71xoFBQTL+59IS+w01NJpx5iJ6h2RoUYQeQZy3WMxAAdjg4hQdE3HKg/g1OabE4qNR3/fjzH/TL8nE5DmkM
::B64:Kri6nr5xr0J/k9tNyMihRBL6m1W2a3ns1uKkW5GJ25SdeOrieUHFnEEUaBOO4iD4cAXnOcslduve7dKhHg588Tyn+9LQOodyp14C
::B64:tx4czL88BpDmjqA3M96HeI8y4jQZDPEBEqrirE0NZWMUhRqDMXPGcCZxWrhAbuE0muQHpuaHDprESUHRnf9HGwSTC5hPJtOxnzmI
::B64:5EgMXVn/I1V4wIevUJJMj8MJhTD68cNytRrzLB9/WH68h2geuL8SvS1/Wv8DUEsBAhQDFAAAAAgA6ZNrXUGY7DukCwAAoR4AAA8A
::B64:AAAAAAAAAAAAAKSBAAAAAERyZWFkL0RyZWFkLmx1YVBLAQIUAxQAAAAIAKSRa10UreqUxAAAAAYBAAAPAAAAAAAAAAAAAACkgdEL
::B64:AABEcmVhZC9EcmVhZC50b2NQSwECFAMUAAAACADhkGtdvtdhSPMDAADxBwAADQAAAAAAAAAAAAAApIHCDAAARHJlYWQvU2ltLmx1
::B64:YVBLBQYAAAAAAwADALUAAADgEAAAAAA=
