Write-Host "Building CHERENKOV Desktop Launcher..."

# Clean previous builds
if (Test-Path -Path "build") { Remove-Item -Recurse -Force "build" }
if (Test-Path -Path "dist") { Remove-Item -Recurse -Force "dist" }

# Run PyInstaller
pyinstaller --clean cherenkov.spec

Write-Host "Build complete! Executable is in packaging/dist/cherenkov-launcher.exe"
