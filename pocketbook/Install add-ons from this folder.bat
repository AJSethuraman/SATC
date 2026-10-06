@echo off
rem For a bank machine pip cannot reach the internet from: installs the add-ons from the add-ons folder
rem beside this file (unzip "PocketBook add-ons.zip" in the same place as PocketBook.zip). Nothing is downloaded.
echo Installing numpy, openpyxl, PyYAML and scikit-learn from the add-ons folder beside this file.
py -m pip install --user --no-index --find-links "%~dp0add-ons" numpy openpyxl PyYAML scikit-learn || python -m pip install --user --no-index --find-links "%~dp0add-ons" numpy openpyxl PyYAML scikit-learn
echo.
echo If a line above starts "ERROR", take a picture of this window. Otherwise close it and double-click "PocketBook.pyw".
pause
