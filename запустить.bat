@echo off
echo.
echo  === Obnovlenie kataloga bota ===
echo.
echo  Polozhite Excel/CSV fajly v papku prices\
echo  Nazhite lyubuyu klavishu dlya zapuska...
echo.
pause >nul

echo.
echo  [1/2] Import prajs-fajlov...
echo  --------------------------------
python import_excel.py
if errorlevel 1 (
    echo.
    echo  OSHIBKA: Import ne udalsya. Deplo otmenyon.
    pause
    exit /b 1
)

echo.
echo  [2/2] Zagruzka kataloga na server...
echo  --------------------------------
python deploy_catalog.py
if errorlevel 1 (
    echo.
    echo  OSHIBKA: Deplo ne udalsya.
    pause
    exit /b 1
)

echo.
pause
