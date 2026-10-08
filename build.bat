@echo off
rem ---------------------------------------------------------------------------
rem build.bat - one command build of the Vid-Trans application and installer.
rem
rem   build.bat            full build: exe, self test, Inno Setup installer
rem   build.bat --fast     skip the self test and the installer verification
rem   build.bat --no-inno  build and test the exe only, no installer
rem   build.bat --test     run the Python test suite (pytest) and exit
rem
rem Requirements: Python 3.11+ with the packages from requirements.txt, and
rem Inno Setup 6 or 7 (ISCC.exe) for the installer step.
rem ---------------------------------------------------------------------------
setlocal
cd /d "%~dp0"

if /i "%~1"=="--test" goto :tests

python -c "import PyQt6, faster_whisper, moviepy, deep_translator, srt" 2>nul
if errorlevel 1 (
    echo Dependencies are missing. Installing them from requirements.txt ...
    python -m pip install -r requirements.txt
    if errorlevel 1 goto :failed
)

python build.py %*
set RC=%ERRORLEVEL%
if not "%RC%"=="0" goto :failed

echo.
echo BUILD OK
echo   application : dist\AccessibleVideoTranscriber\AccessibleVideoTranscriber.exe
echo   installer   : installer_output\AccessibleVideoTranscriber_Setup_*.exe
exit /b 0

:tests
python -m pytest tests -q
exit /b %ERRORLEVEL%

:failed
echo.
echo BUILD FAILED
exit /b 1
