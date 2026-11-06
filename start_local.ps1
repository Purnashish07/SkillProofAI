$ErrorActionPreference = 'Stop'

$ProjectRoot = $PSScriptRoot
$BackendDir = Join-Path $ProjectRoot 'backend'
$FrontendDir = Join-Path $ProjectRoot 'frontend'
$VenvDir = Join-Path $ProjectRoot '.venv'
$VenvPython = Join-Path $VenvDir 'Scripts\python.exe'
$Requirements = Join-Path $BackendDir 'requirements.txt'
$RequirementsStamp = Join-Path $VenvDir '.requirements.sha256'

function Stop-WithMessage([string]$Message) {
    Write-Host "[ERROR] $Message" -ForegroundColor Red
    exit 1
}

Write-Host '==========================================================' -ForegroundColor Cyan
Write-Host '  SkillProofAI - Local Development' -ForegroundColor Cyan
Write-Host '==========================================================' -ForegroundColor Cyan

if (-not (Test-Path -LiteralPath $BackendDir -PathType Container)) {
    Stop-WithMessage "Backend folder not found: $BackendDir"
}
if (-not (Test-Path -LiteralPath $FrontendDir -PathType Container)) {
    Stop-WithMessage "Frontend folder not found: $FrontendDir"
}

$PythonCommand = Get-Command python -ErrorAction SilentlyContinue
if (-not $PythonCommand) {
    Stop-WithMessage 'Python 3.10 or newer is required and must be available in PATH.'
}
$PythonVersionOutput = & $PythonCommand.Source --version
if ($LASTEXITCODE -ne 0 -or $PythonVersionOutput -notmatch '^Python\s+(\d+)\.(\d+)\.(\d+)') {
    Stop-WithMessage 'Could not determine the installed Python version.'
}
$PythonMajor = [int]$Matches[1]
$PythonMinor = [int]$Matches[2]
$PythonVersion = $Matches[0].Substring(7)
if ($PythonMajor -lt 3 -or ($PythonMajor -eq 3 -and $PythonMinor -lt 10)) {
    Stop-WithMessage "Python 3.10 or newer is required. Found $PythonVersion."
}
Write-Host "[OK] Python $PythonVersion" -ForegroundColor Green

$NodeCommand = Get-Command node -ErrorAction SilentlyContinue
$NpmCommand = Get-Command npm -ErrorAction SilentlyContinue
if (-not $NodeCommand -or -not $NpmCommand) {
    Stop-WithMessage 'Node.js and npm are required. Install Node.js and reopen PowerShell.'
}
$NodeVersion = & $NodeCommand.Source --version
if ($LASTEXITCODE -ne 0 -or $NodeVersion -notmatch '^v(\d+)\.(\d+)\.') {
    Stop-WithMessage 'Could not determine the installed Node.js version.'
}
$NodeMajor = [int]$Matches[1]
$NodeMinor = [int]$Matches[2]
if ($NodeMajor -lt 20 -or ($NodeMajor -eq 20 -and $NodeMinor -lt 19) -or ($NodeMajor -eq 21) -or ($NodeMajor -eq 22 -and $NodeMinor -lt 12)) {
    Stop-WithMessage "Vite requires Node.js 20.19+ or 22.12+. Found $NodeVersion."
}
$NpmVersion = & $NpmCommand.Source --version
if ($LASTEXITCODE -ne 0) {
    Stop-WithMessage 'npm was found but could not be started.'
}
Write-Host "[OK] Node.js $NodeVersion, npm $NpmVersion" -ForegroundColor Green

if (-not (Test-Path -LiteralPath $VenvPython -PathType Leaf)) {
    Write-Host "[SETUP] Creating project-local virtual environment: $VenvDir" -ForegroundColor Cyan
    & $PythonCommand.Source -m venv $VenvDir
    if ($LASTEXITCODE -ne 0) {
        Stop-WithMessage 'Could not create the local Python virtual environment.'
    }
}

$RequirementsHash = (Get-FileHash -LiteralPath $Requirements -Algorithm SHA256).Hash
$InstalledHash = if (Test-Path -LiteralPath $RequirementsStamp) {
    (Get-Content -LiteralPath $RequirementsStamp -Raw).Trim()
} else {
    ''
}
$PythonPackagesReady = $false
if (Test-Path -LiteralPath $VenvPython -PathType Leaf) {
    $PythonImportCheck = & $VenvPython -W ignore -c 'import fastapi, uvicorn, multipart, fitz, reportlab, passlib, jose, email_validator, supabase, httpx, pytest, pytest_asyncio' 2>&1
    $PythonPackagesReady = $LASTEXITCODE -eq 0
}
if ($InstalledHash -ne $RequirementsHash -or -not $PythonPackagesReady) {
    Write-Host '[SETUP] Installing backend dependencies into .venv...' -ForegroundColor Cyan
    & $VenvPython -m pip install --disable-pip-version-check -r $Requirements
    if ($LASTEXITCODE -ne 0) {
        Stop-WithMessage 'Backend dependency installation failed. Review the pip output above.'
    }
    Set-Content -LiteralPath $RequirementsStamp -Value $RequirementsHash -NoNewline
}
Write-Host '[OK] Backend dependencies are ready.' -ForegroundColor Green

$NodeModules = Join-Path $FrontendDir 'node_modules'
if (-not (Test-Path -LiteralPath $NodeModules -PathType Container)) {
    Write-Host '[SETUP] Installing frontend dependencies with npm ci...' -ForegroundColor Cyan
    Push-Location $FrontendDir
    try {
        & $NpmCommand.Source ci
        if ($LASTEXITCODE -ne 0) {
            Stop-WithMessage 'Frontend dependency installation failed. Review the npm output above.'
        }
    } finally {
        Pop-Location
    }
}
Write-Host '[OK] Frontend dependencies are ready.' -ForegroundColor Green

if (-not (Test-Path -LiteralPath (Join-Path $BackendDir '.env'))) {
    Write-Host '[INFO] backend\.env is not present; local development defaults will be used.' -ForegroundColor Yellow
}
if (-not (Test-Path -LiteralPath (Join-Path $FrontendDir '.env'))) {
    Write-Host '[INFO] frontend\.env is not present; Supabase login/registration is disabled. Guest analysis remains available.' -ForegroundColor Yellow
}

$BackendProcess = Start-Process -FilePath $VenvPython `
    -ArgumentList @('-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', '8000', '--reload') `
    -WorkingDirectory $BackendDir -PassThru
$FrontendCommand = Get-Command powershell.exe -ErrorAction SilentlyContinue
if (-not $FrontendCommand) {
    Stop-WithMessage 'Windows PowerShell was not found to launch the frontend console.'
}
$QuotedFrontendDir = "'" + $FrontendDir.Replace("'", "''") + "'"
$FrontendProcess = Start-Process -FilePath $FrontendCommand.Source `
    -ArgumentList @('-NoExit', '-Command', "Set-Location -LiteralPath $QuotedFrontendDir; npm run dev") `
    -WorkingDirectory $FrontendDir -PassThru

Start-Sleep -Seconds 2
if ($BackendProcess.HasExited) {
    Stop-WithMessage 'The backend process exited during startup. Check its console for details.'
}
if ($FrontendProcess.HasExited) {
    Stop-WithMessage 'The frontend process exited during startup. Check its console for details.'
}

Write-Host ''
Write-Host '[STARTING] Backend:  http://127.0.0.1:8000' -ForegroundColor Green
Write-Host '[STARTING] Frontend: http://127.0.0.1:5173' -ForegroundColor Green
Write-Host 'API docs:            http://127.0.0.1:8000/docs' -ForegroundColor Green
Write-Host 'Close the backend and frontend console windows to stop the services.' -ForegroundColor Gray
