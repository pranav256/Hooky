# Hooky Windows launcher
$HookyArgs = @($args)

$ErrorActionPreference = "Stop"
$Root = $PSScriptRoot

$Python = $null
$PythonCandidates = @()
if ($env:VIRTUAL_ENV) {
    $PythonCandidates += Join-Path $env:VIRTUAL_ENV "Scripts\python.exe"
}
$PythonCandidates += @(
    (Join-Path $Root ".venv\Scripts\python.exe"),
    (Join-Path $Root "venv\Scripts\python.exe")
)
foreach ($candidate in $PythonCandidates) {
    if (Test-Path -LiteralPath $candidate -PathType Leaf) {
        $Python = $candidate
        break
    }
}
if ($null -eq $Python) {
    Write-Error "No project Python environment found (.venv or venv). Run .\setup.ps1 first." -ErrorAction Continue
    exit 1
}

$startInfo = New-Object System.Diagnostics.ProcessStartInfo
$startInfo.FileName = $Python
$startInfo.WorkingDirectory = $Root
$startInfo.UseShellExecute = $false
$nativeArgs = @("-m", "hooky") + $HookyArgs
if ($null -ne $startInfo.PSObject.Properties["ArgumentList"]) {
    foreach ($argument in $nativeArgs) {
        $startInfo.ArgumentList.Add([string] $argument)
    }
} else {
    $quotedArgs = foreach ($argument in $nativeArgs) {
        '"' + (([string] $argument) -replace '(\\*)"', '$1$1\"' -replace '(\\+)$', '$1$1') + '"'
    }
    $startInfo.Arguments = $quotedArgs -join " "
}

try {
    $process = [System.Diagnostics.Process]::Start($startInfo)
    try {
        $process.WaitForExit()
        $exitCode = $process.ExitCode
    } finally {
        $process.Dispose()
    }
} catch {
    Write-Error -Message $_.Exception.Message -ErrorAction Continue
    exit 1
}
exit $exitCode
