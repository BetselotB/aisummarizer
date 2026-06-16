@echo off
setlocal enabledelayedexpansion

cd /d "%~dp0\.."

echo ==^> Building frontend
if not exist frontend\node_modules (
  pushd frontend
  call npm ci
  popd
)
pushd frontend
call npm run build
popd

echo ==^> Installing desktop packaging deps
python -m pip install --no-cache-dir -r requirements-desktop.txt

echo ==^> Packaging desktop app
python -m PyInstaller packaging\aisummarizer.spec --noconfirm --clean

set RELEASE_ROOT=%CD%\releases\desktop
if not exist "%RELEASE_ROOT%\windows" mkdir "%RELEASE_ROOT%\windows"
xcopy /E /I /Y "dist\AI Study Guide Generator" "%RELEASE_ROOT%\windows\AI Study Guide Generator\"

echo.
echo Done. Release folder:
echo   %RELEASE_ROOT%\windows

endlocal
