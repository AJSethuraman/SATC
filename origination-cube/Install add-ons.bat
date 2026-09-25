@echo off
echo Installing the two add-ons the Origination Cube needs: openpyxl and PyYAML.
py -m pip install --user openpyxl PyYAML || python -m pip install --user openpyxl PyYAML
echo.
echo Done. Close this window and double-click "Origination Cube.pyw".
pause
