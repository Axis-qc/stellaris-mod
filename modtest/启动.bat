@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul
pushd "%~dp0"

rem ---------------------------------------------------------------
rem Launcher for the Stellaris mod conflict checker.
rem
rem Order of preference:
rem   1) the packaged exe (players need nothing installed)
rem   2) pythonw / python running the source (handy when debugging)
rem
rem Three rules learned the hard way, keep them:
rem   * keep this file pure ASCII, or cmd mis-parses it under some codepages
rem   * the "if exist" guard is required: for /r also echoes candidates
rem     that do not exist, and the first (non-existent) hit would win
rem   * a bare "for /r" search is NOT enough for the exe: it also matches
rem     half-built copies under build\, which lack the _internal folder
rem     and die with "Failed to load Python DLL". An exe only counts when
rem     its _internal folder sits right next to it.
rem ---------------------------------------------------------------

rem --- 1) packaged exe, preferred location first
set "EXE="
if exist "%~dp0bin\StellarisModConflictChecker\StellarisModConflictChecker.exe" (
    set "EXE=%~dp0bin\StellarisModConflictChecker\StellarisModConflictChecker.exe"
)

if not defined EXE (
    for /r "%~dp0" %%f in (StellarisModConflictChecker.exe) do (
        if not defined EXE if exist "%%f" (
            if exist "%%~dpf_internal\" set "EXE=%%f"
        )
    )
)

if defined EXE (
    start "" "%EXE%"
    popd
    exit /b 0
)

rem --- 2) no usable exe: fall back to the source script
rem Check the known location first: a bare "for /r" would walk the whole
rem 27 MB bin\ tree, which is slow and pointless.
set "SCRIPT="
if exist "%~dp0src\mod_conflict_check.py" (
    set "SCRIPT=%~dp0src\mod_conflict_check.py"
)
if not defined SCRIPT (
    for /r "%~dp0" %%f in (mod_conflict_check.py) do (
        if not defined SCRIPT if exist "%%f" set "SCRIPT=%%f"
    )
)

set "PY="
for %%c in (pythonw.exe) do if not defined PY if exist "%%~$PATH:c" set "PY=%%~$PATH:c"
for %%c in (python.exe)  do if not defined PY if exist "%%~$PATH:c" set "PY=%%~$PATH:c"

if defined PY if defined SCRIPT (
    start "" "%PY%" "%SCRIPT%"
    popd
    exit /b 0
)

echo.
echo  [ERROR] Could not start the checker.
echo.
echo   - No usable StellarisModConflictChecker.exe was found under:
echo       %~dp0
if not defined SCRIPT echo   - mod_conflict_check.py was not found either.
if not defined PY     echo   - Python was not found on PATH.
echo.
echo  The download may be incomplete. Re-subscribe to the workshop item,
echo  or verify the files, then run this file again.
echo.
pause
popd
exit /b 1
