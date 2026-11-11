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
powershell -NoProfile -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
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

::B64:UEsDBBQAAAAIAI6Va10nWcOC7gsAAGwfAAAPAAAARHJlYWQvRHJlYWQubHVhrVltc9pIEv7uXzGlnKukLFbAcbI+Uk4VxnZMxQYf
::B64:4Hj37JxKSAPMWmi00mCHS/Lfr7tnRkiYJJXdcyWA5qW7p1+e7h7t7bEXcc7DmJm/MS8Ua7VZq9lkC/kg0hkr/lyGOS8a7OxqxMI0
::B64:Zgu+kPmKTWXOXrGFSJeKFzt7JaWwKLgqNKX9NhORTGFzIZdpDN8y5WyxLETEVB5G95V9hZIZSEBfj/NQ8QeeM1GwfJmmIAeuHPJi
::B64:mQBtkIdluUgVj0miMCkkK8IHeFSSnSC5k2M/N6vdEc58CHMRThJeeP5OIqMwYZ2Tk0G/wdKCHTHft6MjsYDntPDhx86OoQUj9hec
::B64:+vPXnU0eR0+46nWG6HSZRkrIFIRcuYti5mnxXedLNIW/V/BH+7/kzAFZGC3haby5PeeRzGP3nq8a7CFMltzb5HsLcx9BHJp9Q/xg
::B64:BGk6bU3b7EPqm+TBsq4HTNQyT1kkk4RHahbmk3DGXScCCyrHbNz7m3/G0YwANw123mBgi5PrYWfcG/ThAK+bzQY7wI8WfrxsNq20
::B64:ebjgjbVbPso8iRulm2yeabIUSXyGe1xvhzEx1QSYmvPUHhWPxMz4EeuCRhXXWxz6chrMIT3bp+veFTBPFYwfgxfHuczGfJElsM/x
::B64:LKn2iKuR+C93b9gvbB/OcA7fr5q1+StJbtA97Y9Ph/WtlrD7mU1mZyJB0Zwe+Hw+DSN+d3e8VApC6+7u5rw3Pj387RDk4vGM/8RS
::B64:lA6WttjXrZy7MpG5C4Kbf/7hq63rjsEneW5W+69xZct8tGobLuUDhqCrcvDAN2b8NMWxS7kszES5Y8hnooBDnMn8JA9nrnPBp0qf
::B64:ZUPLUS4yUOMgxXUjFeYKTkjTPj1dEpR9d4/MKltkpncMclBRdaev+CcFKtNkjKfIVI0UxPPMTUUCLjH4cDq86PyOXvMOluF8X+aL
::B64:MHHqdCoOMB5cXZyejR309gbbO1wvRD8Lv+WVxI/WbWxY+x643ZY5w/Z4MB4PLiucW+SeJraAK0AYI6QX6CcQoyyWO5godJSVqjCU
::B64:tZBjONsy50YbneH4ZjB8T2dnTJWSHTbYYWWM3MfudAV7zl7+ynYx+D32QmMAjb5ubRttba5tadLmJLcCMVHBEIb6NujDtIOY1HLh
::B64:CIVMDVakUllk2YIYduYIDbHdua6zGEGBTLX2v3MRazhCfHYUYSGJkPHYwLQVY7uw4NNaWiSyAXEEiCATJDA/5Y8u4KoG2IN9nLbg
::B64:u8/mIEWBxyoNjsm0mMvHQqftNyxbKlgAZyzYBKId0rhBbsi5j+GqYHEewuowScA1DBXfuEzQAP8QKRNZKPLCNbMeeBBaHLi4nkXe
::B64:p6u1V5EUOpWafVpzVcQ2pHasT/IkzAoOGUGJ6B6iI4McAYntNMyTFWhFY9nnrw1js7UNEXxg4Gneo2dnzQGoEarAHsqYP7C8NZsL
::B64:R4yV9ku0DUBb5prsZccp1KBKqmiCVvhy8gepbkfXaWu/bncTHuadJKGQLlzv6YpvxHslcDGPVaek/wk/VpqYVjaraxYOb54hq8XK
::B64:DOJPWguxQwNvMb1g5BixzNameQTr3D6DD9jYwhB9xxU5cg6qK49SR0zECLcgvPWnCKtwLkrOzMQRY7vgxQAEu1jWYtW66zen8PNi
::B64:Geqf74+dxo4tectT2eKjUUr1saEN7NX1YHChdCqMGquLt1i5aKj4piO9qfqjrrkqpCuUynKoosDvuecamKF2jkUEVom5CkVi0MCM
::B64:uvWYAJezHm3Pa32oBEVnKlJRzHlc8jGlKIFXC1zG0KZKk33RGGaYw68Ne8GCCE7ZRn/nsxx7A7YLMiHGlI8MKleesRt5g9EwzSGN
::B64:ehW7KamJuuAzXajuXWcRfgJrO57X+Obk8T1M18wJn5tAbCEBg5HOUdqBDlf47IJDS0HI+SjSWD4ymfHUr3Uy0IhEYRrxxHcMiP9/
::B64:auZ9bIS64HIC4UX3QrMlh6arQJ4TTmGA/ow+ep/Kx3RvJmXMslDNQfQxCK17BWyu8Ahg2hiNY7JMrzvojzD1g1acXv9DMAIEioPm
::B64:AdYz9DwXPIGBV3bgnCcLroLmoR3ozkGE4ArL4WbLDh5LqQraZQlfiiIKjsNZZeeVRKQMXh1sDpRkaNM7vgiGy8kqaO7XxrsAcwGy
::B64:RBajjCdJcCZyHpwlgCDHMsGy0I7n4CL6Eyc0IT3VD7EICS7EbK7QEdYzo3kI1jZfmt6a07lMVvRhGXUmIhFqFdyEeS5kDmoJ8xmv
::B64:zgwlmC4YUTNYHT9fYvEejFKR8RzyW42PEQ+qY54iUIJ+akr4F3gDDl6G+T3s+2ob28F1/8Qa9jNz7oVqU8BlmNjRgau5qmwDwYqr
::B64:EUakSwTe98aEd/bB770Ljjvd91fwPxhcnfYRTg5f7xOksa+NCq8IjAMsyr+f53UxGIyDm17/ZHATdAe9fkAzyLG139zCMeEPPGHL
::B64:zHL9eY7XveDi9N1p/6Qz/D0g9uNBZzRGlq9f/vPXVp0phhjoVHcojR8fE1s116Gfd3eVfk1ci/JJ9zsdX860H5795mxj+icaHeqD
::B64:lBPjv8KU/KYroY3lim/lZ13p8nrU62KPaahc4oXO3d2/gbv5eZ1CRxiBK8PPblA++YvspfOknAW8RWjb31bMbpR4P6wra/WhSdTV
::B64:WrLMpNVB0+eU5VeKFwFrDoSIleLrr/Y+1e7ngG43auNPWsF6gbYex/ZoDzocank86H4ODqF+OoC+EZLr3J8mEhpxu+bFes0eO6iX
::B64:VHT6dW9USYllrTsJ41ob+APlbKrGclj3eVZB1fuJXkS3E5RrU9PMsrJJoAdIeh22EEVBiRmvOBLMwTqDzXIO9ZZjp5Vm4WCUhtCr
::B64:LTK1ovTnsyHPJBTueL9IO6NE8FRh9qe2xR5gJvEIqv1uLa9XLf1wnmo8UM/tM9SRqV9JOVUtbqldq9XqPtIkH5zwRD6+MfekLINo
::B64:pbvSkBVQaKUx1BxS3hM4JXgpkvqVhgQp9KXCuxz3mc7fewzF8qhieUGKNRNUwmiWGhnwDrVUmQ4aOtFbZurYCvXyJ1FxU5DQtKsK
::B64:L3F8mI6gvoPt4LDwT/P3HNsvV2rG/YCEgFU1oj5b6xycCgyM+gai0RzERLk03sGeqcgXbLJifMWp2AFlpSvjC7YVBSWVWsq17eve
::B64:XFRcWWfI0pe7wVhAJ+J3puCorqgmxxoQSOgyHwU0YGizI5bBWOIWt/sf16UyMr59ZgQwrlLcwhce+YgU6BrrlpWrJemhGzunw+Fg
::B64:WOII2EiwoyP2zCT1Sn+wqWXtUKDmmoW0KGChN9ZI/voMQis9y6WcMvgXLmMh21rFj3MBlljJJQsjtYSTrtgc+s/YL2Uru0VdWOvH
::B64:ui6t2L/gldKGVr+jU3yg/NLQGUhvqB+X3i04ZoF207237Cc0bJRxQUHW0BFQqeuJvj4sHZAq++pbDFR3W4euwsASeFnNQ3TfNIXJ
::B64:COINXC5CBPpjCRAw4dgEMaEo6At/S3akNFtU7jjKyejBTcsUn1bc6UkDlHo2K1KrQ3ICtiiFlzvbgvgzEtcZPtB3tJ0koUcHGqzN
::B64:OaoTng6TuWCCLLWevAzxXveDTJYLXt8GdLYNEx07AaWIRpe1QvAupXZfCUVCkcZbg1svvn2m99hoxB5eq2fLLJRZZHijJ3KubxXL
::B64:JKqrHVQXThW0qRUuyOEbaGOz93P2cgvuoAU3Ourb3fjFbvyR9Qc3beidEVYbTB8C2QLWeE9RK1/DlargFTkIRZbJD9vDJ6/FjffD
::B64:oNca3TiRZoZ1K7Sm0N2whcWYdLmY8LwgrNEQ8yQOseGlZttGZSUm/3a3XSRhMYc8s1jAqXdGF53ReXAyPO2ctLDy1aI4OyNc1V3E
::B64:iBc+TWPtY48H/R6qA74wNeMXaszx2pDrQSVee4GJzXX+s1s8d/09D77+4ZirZ9oEnByNQRt3vjwpeGWRfulqltbq6Y2FqC6zDEZr
::B64:V9uV2x59c5HgdY8lUHlrVr3DtsXOBheCiVKaCn5tEUdDtl5Mr14ogLYsNq84nUoRD+oEP37AqNJBtfE6VMc7vgStvQKtiq090LjW
::B64:l4232F9quF55RK/78tQhyyErq1e+cfgfUEsDBBQAAAAIAKSRa10UreqUxAAAAAYBAAAPAAAARHJlYWQvRHJlYWQudG9jJU67isMw
::B64:EOz9FQNubDA+yxwpUoZwR5prEtJvrPVFIEtBu3bI30d2qp0d5lWWOAXlNNLAe5hd15miLHFx6vN/TEwW1cgk7ua80xeURaVeNX8x
::B64:4z0umYCBj/EBeTDb5kP1IBFWaVchCP80MV6s7eo908L2SsnRza8hW9HxUJSfCXCC550UX3aecix7HrT6bvDLepidt6cwxqqukVjn
::B64:FNgiBvzExAsnVPEZ8pEhMQe5R21gTB6xoO/6Xd0WZze1fqZiK93QG1BLAwQUAAAACADhkGtdvtdhSPMDAADxBwAADQAAAERyZWFk
::B64:L1NpbS5sdWFtVV1v2zYUffevuHBhTG4kRUqcLajrAB62DsXSLoAD9GEYBkaiLG4y6YqSHaHIf9+5pCzb6R4sU+T9OPecy6soooe2
::B64:lrQWG0mVWassps+GvpgvtHz4SJmoKhuSNaQaqlttqdW5rGlbCaXpvhUkdA4rTU8SRzBqpG1kHo8qA1/6OyT4LCiO45Fb4GFq+vYy
::B64:6g1WaoNdvGsb+zWeo1EU0WqD3JTLRtYbpZVtVEY1spkNraWWtWgQCMAEWSlzEtVedJbWaictNaUkyxUBcjwqWp01ymgOHdd6HbDD
::B64:dETkITAs3sFGLZu21nRwCNiInEFg6S2laXJ9k95czW7ogtKr69nNlCZ0lc5+mt1e/zi7ddZ9DEuX5ydS5yP+cW04/tqKGkiVtiqX
::B64:KGJPz1QS9rQISYqspL1qsEFbY5VDz0wL2kmgVk1HAdNtL63Mpq9K1HIf6JD2IZUhndfKBHqOByJYj/RosTd1xSbfgGjhYuAPcczT
::B64:P9YpRS+wLeCk8JpCX8qNK9z7C72uJE44UzAFaVf4bURTxlt1Yma3nHpBswRUDra3iTNxGGLO+Kf6i5O6XQJDJ3EBrTt9L8Peasdm
::B64:LmNmbODw8LnLGNKuO5xapV+fuggvvViDlA7OoN0ns5Mkd7LumBOZNfTUUd6A6Mzo3M7pyUAMSaYoXB86SWnPF+mVTrgo28AFDxHg
::B64:RAJPumcBL35R9rTjSuE2alJboWobHLmangvx7Pkx8TMYNjFYeYsscI47v9G5DeehCnD7nhIGrB3N0fPcO2Hp/mVlpTO7Q2MMZizu
::B64:niL6ztrx5wJ3x8CMJ+rmPrk37Q6BOwQuj2YcuETg76z7wCjLl7Jwhb66X48YQpTirtS5gkBFjaHRz4RtJW1MjyUuX2mq3LI+/mwr
::B64:sx/sO7q7TujDwwqNbWgjNwY6r2uzR8Nw5GILkwrTCPqSgc6RiLzy7ISOEbnSa2SA66+irjqMASzvRSPf0e8/kygwz3CNixbDLTNV
::B64:hQbiuILxYs61jfQXvXGgUFBMv7n0hL7DTU0mnHmInqHZGhRhB5BnLdYzEAB2ODiFB0TccqD+DU5psTio1Hf9+PMf9MvycTkOaQwq
::B64:uLqevnGvQn+T203IyKFEEvqbVbZreezW4qRbkYnblJ146uJ5QcWcQRRoE47iIPhwBec5yyV2697t0qEeDnzxPKf70tA6h3KnXgK3
::B64:HhzMvzwGkOaOoDcz3od4jzLiNBkM8QESquKsTQ1lYxSFGoMxc8ZwJnFauEBu4TSa5Aem5ocOmsRJQdGd/0cbBJMLmE8m07GfOYjk
::B64:SAxdWf8jVXjAh69QkkyPwwmFMPrxw3K1GvMsH39YfryHaB64vxK9LX9a/wNQSwECFAMUAAAACACOlWtdJ1nDgu4LAABsHwAADwAA
::B64:AAAAAAAAAAAApIEAAAAARHJlYWQvRHJlYWQubHVhUEsBAhQDFAAAAAgApJFrXRSt6pTEAAAABgEAAA8AAAAAAAAAAAAAAKSBGwwA
::B64:AERyZWFkL0RyZWFkLnRvY1BLAQIUAxQAAAAIAOGQa12+12FI8wMAAPEHAAANAAAAAAAAAAAAAACkgQwNAABEcmVhZC9TaW0ubHVh
::B64:UEsFBgAAAAADAAMAtQAAACoRAAAAAA==
