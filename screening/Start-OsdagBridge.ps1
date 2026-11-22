param(
    [string]$SessionName = (Get-Date -Format 'yyyyMMdd-HHmmss'),
    [string]$CondaExe = "$env:USERPROFILE\miniconda3\Scripts\conda.exe"
)

$ErrorActionPreference = 'Continue'
if ($SessionName -notmatch '^[a-zA-Z0-9_-]+$') {
    throw 'Use letters, digits, underscores, or hyphens for SessionName.'
}
if (-not (Test-Path -LiteralPath $CondaExe)) {
    throw "Conda executable not found: $CondaExe"
}

$repoRoot = Split-Path -Parent $PSScriptRoot
$sessionDir = Join-Path $PSScriptRoot "evidence\$SessionName"
if (Test-Path -LiteralPath $sessionDir) {
    throw "Session already exists; choose a new SessionName: $sessionDir"
}
New-Item -ItemType Directory -Path $sessionDir -ErrorAction Stop | Out-Null

Push-Location $repoRoot
try {
    & $CondaExe run --no-capture-output -n osdagbridge-env python -u -m osdagbridge.desktop 2>&1 |
        Tee-Object -FilePath (Join-Path $sessionDir 'console.log')
    $appExitCode = $LASTEXITCODE
} finally {
    Pop-Location
}
exit $appExitCode
