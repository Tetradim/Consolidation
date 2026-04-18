# ============================================================
# Trading Bot Windows Installer (PowerShell)
# Run as Administrator
# ============================================================

param(
    [switch]$Uninstall,
    [switch]$SkipPrerequisites
)

$ErrorActionPreference = "Stop"
$script:ExitCode = 0

# ============================================================
# Configuration
# ============================================================
$AppName = "Trading Bot"
$AppVersion = "1.0.0"
$InstallDir = "$env:PROGRAMFILES\Trading Bot"
$StartMenuDir = "$env:APPDATA\Microsoft\Windows\Start Menu\Programs"
$DesktopDir = [Environment]::GetFolderPath("Desktop")
$DataDir = "$env:APPDATA\tradebot"

# Colors for output
function Write-Section($text) {
    Write-Host "`n=== $text ===" -ForegroundColor Cyan
}

function Write-Step($text) {
    Write-Host "[*] $text" -ForegroundColor Yellow
}

function Write-Success($text) {
    Write-Host "[+] $text" -ForegroundColor Green
}

function Write-Error($text) {
    Write-Host "[-] $text" -ForegroundColor Red
    $script:ExitCode = 1
}

# ============================================================
# Prerequisites Check
# ============================================================
function Test-Prerequisites {
    Write-Section "Checking Prerequisites"
    
    # Check Windows version (10 or 11)
    $osVersion = [System.Environment]::OSVersion.Version
    if ($osVersion.Major -lt 10) {
        Write-Error "Windows 10 or higher is required"
        return $false
    }
    Write-Success "Windows version OK"
    
    # Check for PowerShell 5.1+
    if ($PSVersionTable.PSVersion.Major -lt 5) {
        Write-Error "PowerShell 5.1 or higher is required"
        return $false
    }
    Write-Success "PowerShell version OK"
    
    # Check Docker
    try {
        $dockerVersion = docker --version 2>&1
        if ($LASTEXITCODE -ne 0) { throw "Docker not found" }
        Write-Success "Docker installed: $dockerVersion"
    }
    catch {
        Write-Error "Docker is required. Please install from https://docker.com"
        Write-Host "  1. Download Docker Desktop for Windows"
        Write-Host "  2. Run the installer"
        Write-Host "  3. Start Docker Desktop"
        return $false
    }
    
    # Check WSL2 (required for Docker on Windows)
    try {
        $wslStatus = wsl --status 2>&1
        if ($wslStatus -match "not") {
            Write-Error "WSL2 is required for Docker. Run: wsl --install"
            return $false
        }
        Write-Success "WSL2 installed"
    }
    catch {
        Write-Error "WSL2 is required for Docker"
        return $false
    }
    
    # Check disk space (minimum 10GB)
    $drive = Get-PSDrive -Name C
    if ($drive.Free -lt 10GB) {
        Write-Error "Insufficient disk space. Minimum 10GB required"
        return $false
    }
    Write-Success "Disk space OK"
    
    return $true
}

# ============================================================
# Install Application
# ============================================================
function Install-Application {
    Write-Section "Installing $AppName v$AppVersion"
    
    # Check prerequisites
    if (-not $SkipPrerequisites) {
        if (-not (Test-Prerequisites)) {
            Write-Error "Prerequisites check failed"
            return $false
        }
    }
    
    # Create installation directory
    Write-Step "Creating installation directory..."
    if (-not (Test-Path $InstallDir)) {
        New-Item -ItemType Directory -Path $InstallDir -Force | Out-Null
    }
    
    # Create subdirectories
    @("data", "logs", "config") | ForEach-Object {
        $dir = Join-Path $InstallDir $_
        if (-not (Test-Path $dir)) {
            New-Item -ItemType Directory -Path $dir -Force | Out-Null
        }
    }
    Write-Success "Directories created"
    
    # Copy application files
    Write-Step "Copying application files..."
    $scriptDir = Split-Path -Parent $MyInvocation.PSCommandPath
    $publishDir = Join-Path $scriptDir "publish"
    
    if (Test-Path $publishDir) {
        Copy-Item -Path "$publishDir\*" -Destination $InstallDir -Recurse -Force
        Write-Success "Application files copied"
    }
    else {
        # Try docker-compose location
        $composeDir = Join-Path $scriptDir "."
        if (Test-Path (Join-Path $composeDir "docker-compose.yml")) {
            Copy-Item -Path "$composeDir\*" -Destination $InstallDir -Recurse -Force -Exclude ".git"
            Write-Success "Application files copied from repository"
        }
        else {
            Write-Error "Cannot find application files"
            return $false
        }
    }
    
    # Create environment file
    Write-Step "Creating configuration file..."
    $envFile = Join-Path $InstallDir ".env"
    $envContent = @"
# Trading Bot Environment Configuration
# Edit these values before starting the bot

# Discord Bot Token (required)
DISCORD_BOT_TOKEN=your-discord-bot-token-here

# Discord Channel IDs (comma separated)
DISCORD_CHANNEL_IDS=123456789

# Database
MONGO_USER=tradebot
MONGO_PASSWORD=tradebot123
DB_NAME=tradebot

# Broker Settings (choose one or more)
# IBKR
IBKR_GATEWAY_URL=https://localhost:5000
IBKR_ACCOUNT_ID=your-account-id

# Alpaca
ALPACA_API_KEY=your-alpaca-key
ALPACA_API_SECRET=your-alpaca-secret
ALPACA_PAPER=true

# Security
SECRET_KEY=$( -join ((65..90) + (97..122) + (48..57) | Get-Random -Count 32 | ForEach-Object {[char]$_}) )

# Debug Mode
DEBUG=false

# API Keys (optional)
ALPHA_VANTAGE_API_KEY=
POLYGON_API_KEY=
"@
    Set-Content -Path $envFile -Value $envContent -Force
    Write-Success "Configuration file created: $envFile"
    
    # Create start script
    Write-Step "Creating start script..."
    $startScript = @"
@echo off
title Trading Bot
cd /d "%~dp0"
echo ============================================
echo   Trading Bot v$AppVersion
echo ============================================
echo.

REM Check Docker is running
docker info >nul 2>&1
if errorlevel 1 (
    echo ERROR: Docker is not running
    echo Please start Docker Desktop and try again
    pause
    exit /b 1
)

echo Starting services...
docker-compose up -d

echo.
echo Waiting for services to be ready...
timeout /t 10 /nobreak >nul

echo.
echo ============================================
echo Trading Bot is running!
echo.
echo Web UI:     http://localhost
echo API:        http://localhost:8000
echo Grafana:    http://localhost:3030
echo.
echo Press any key to stop...
pause >nul

echo Stopping services...
docker-compose down
"@
    Set-Content -Path (Join-Path $InstallDir "start_tradebot.bat") -Value $startScript -Force
    
    # Create stop script
    $stopScript = @"
@echo off
cd /d "%~dp0"
echo Stopping Trading Bot...
docker-compose down
echo Done!
pause
"@
    Set-Content -Path (Join-Path $InstallDir "stop_tradebot.bat") -Value $stopScript -Force
    
    # Create Windows shortcuts
    Write-Step "Creating shortcuts..."
    
    # Start Menu
    $startMenuFolder = Join-Path $StartMenuDir $AppName
    if (-not (Test-Path $startMenuFolder)) {
        New-Item -ItemType Directory -Path $startMenuFolder -Force | Out-Null
    }
    
    # Start shortcut
    $startShortcut = (New-Object -ComObject WScript.Shell).CreateShortcut(
        (Join-Path $startMenuFolder "Start Trading Bot.lnk")
    )
    $startShortcut.TargetPath = Join-Path $InstallDir "start_tradebot.bat"
    $startShortcut.WorkingDirectory = $InstallDir
    $startShortcut.Description = "Start the Trading Bot"
    $startShortcut.Save()
    
    # Stop shortcut
    $stopShortcut = (New-Object -ComObject WScript.Shell).CreateShortcut(
        (Join-Path $startMenuFolder "Stop Trading Bot.lnk")
    )
    $stopShortcut.TargetPath = Join-Path $InstallDir "stop_tradebot.bat"
    $stopShortcut.WorkingDirectory = $InstallDir
    $stopShortcut.Description = "Stop the Trading Bot"
    $stopShortcut.Save()
    
    # Configuration shortcut
    $configShortcut = (New-Object -ComObject WScript.Shell).CreateShortcut(
        (Join-Path $startMenuFolder "Configuration.lnk")
    )
    $configShortcut.TargetPath = Join-Path $InstallDir ".env"
    $configShortcut.Description = "Edit configuration"
    $configShortcut.Save()
    
    # Desktop shortcut
    $desktopShortcut = (New-Object -ComObject WScript.Shell).CreateShortcut(
        (Join-Path $DesktopDir "Trading Bot.lnk")
    )
    $desktopShortcut.TargetPath = Join-Path $InstallDir "start_tradebot.bat"
    $desktopShortcut.WorkingDirectory = $InstallDir
    $desktopShortcut.Description = "Start Trading Bot"
    $desktopShortcut.Save()
    
    Write-Success "Shortcuts created"
    
    # Add to Windows Registry (Uninstall)
    Write-Step "Registering application..."
    $uninstallKey = "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\$AppName"
    if (-not (Test-Path $uninstallKey)) {
        New-Item -Path $uninstallKey -Force | Out-Null
    }
    Set-ItemProperty -Path $uninstallKey -Name "DisplayName" -Value $AppName
    Set-ItemProperty -Path $uninstallKey -Name "DisplayVersion" -Value $AppVersion
    Set-ItemProperty -Path $uninstallKey -Name "Publisher" -Value "Trading Bot"
    Set-ItemProperty -Path $uninstallKey -Name "InstallLocation" -Value $InstallDir
    Set-ItemProperty -Path $uninstallKey -Name "UninstallString" -Value "powershell.exe -ExecutionPolicy Bypass -File `"$InstallDir\install.ps1`" -Uninstall"
    Set-ItemProperty -Path $uninstallKey -Name "NoModify" -Value 1
    Set-ItemProperty -Path $uninstallKey -Name "NoRepair" -Value 1
    Write-Success "Registry entries created"
    
    # Copy installer for uninstall
    Copy-Item -Path $MyInvocation.PSCommandPath -Destination (Join-Path $InstallDir "install.ps1") -Force
    
    # Start services
    Write-Section "Starting Services"
    Write-Step "Starting Docker services..."
    Push-Location $InstallDir
    try {
        docker-compose up -d --build
        Write-Success "Services started"
        
        Write-Host "`nInstallation complete!" -ForegroundColor Green
        Write-Host "========================================" -ForegroundColor Green
        Write-Host "  Web UI:     http://localhost" -ForegroundColor White
        Write-Host "  API:        http://localhost:8000" -ForegroundColor White
        Write-Host "  Grafana:    http://localhost:3030" -ForegroundColor White
        Write-Host "  Prometheus: http://localhost:9090" -ForegroundColor White
        Write-Host "========================================" -ForegroundColor Green
        Write-Host "`nEdit configuration at: $envFile" -ForegroundColor Yellow
    }
    catch {
        Write-Error "Failed to start services: $_"
    }
    finally {
        Pop-Location
    }
    
    return ($script:ExitCode -eq 0)
}

# ============================================================
# Uninstall Application
# ============================================================
function Uninstall-Application {
    Write-Section "Uninstalling $AppName"
    
    # Stop services
    Write-Step "Stopping services..."
    Push-Location $InstallDir
    try {
        docker-compose down -v 2>$null
        Write-Success "Services stopped"
    }
    catch { }
    Pop-Location
    
    # Remove shortcuts
    Write-Step "Removing shortcuts..."
    $startMenuFolder = Join-Path $StartMenuDir $AppName
    if (Test-Path $startMenuFolder) {
        Remove-Item -Path $startMenuFolder -Recurse -Force
    }
    $desktopShortcut = Join-Path $DesktopDir "Trading Bot.lnk"
    if (Test-Path $desktopShortcut) {
        Remove-Item -Path $desktopShortcut -Force
    }
    Write-Success "Shortcuts removed"
    
    # Remove installation directory
    Write-Step "Removing files..."
    if (Test-Path $InstallDir) {
        Remove-Item -Path $InstallDir -Recurse -Force
    }
    Write-Success "Files removed"
    
    # Remove registry entries
    Write-Step "Removing registry entries..."
    $uninstallKey = "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\$AppName"
    if (Test-Path $uninstallKey) {
        Remove-Item -Path $uninstallKey -Recurse -Force
    }
    Write-Success "Registry cleaned"
    
    # Ask about user data
    $removeData = Read-Host "Remove user data and database? (y/N)"
    if ($removeData -eq "y" -or $removeData -eq "Y") {
        if (Test-Path $DataDir) {
            Remove-Item -Path $DataDir -Recurse -Force
            Write-Success "User data removed"
        }
    }
    
    Write-Host "`nUninstallation complete!" -ForegroundColor Green
}

# ============================================================
# Main
# ============================================================
function Main {
    Write-Host "`n========================================" -ForegroundColor Cyan
    Write-Host "  $AppName Installer v$AppVersion" -ForegroundColor Cyan
    Write-Host "========================================`n" -ForegroundColor Cyan
    
    if ($Uninstall) {
        Uninstall-Application
    }
    else {
        Install-Application
    }
    
    exit $script:ExitCode
}

# Run
Main