@echo off
echo Installing the three add-ons the Origination Cube needs: numpy, openpyxl and PyYAML.
py -m pip install --user --upgrade numpy openpyxl PyYAML || python -m pip install --user --upgrade numpy openpyxl PyYAML
echo.
echo Done. Close this window and double-click "Origination Cube.pyw".
pause
