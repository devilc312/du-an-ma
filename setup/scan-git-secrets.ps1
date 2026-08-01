param(
    [Parameter(Mandatory = $false)]
    [string[]] $Roots = @("$HOME\code"),

    [Parameter(Mandatory = $false)]
    [string] $GitleaksPath = "gitleaks",

    [Parameter(Mandatory = $false)]
    [switch] $IncludeHistory
)

$ErrorActionPreference = "Stop"

$repositories = foreach ($root in $Roots) {
    if (-not (Test-Path -LiteralPath $root)) {
        Write-Warning "Skip missing root: $root"
        continue
    }

    if (Test-Path -LiteralPath (Join-Path $root ".git")) {
        Get-Item -LiteralPath $root
    }

    Get-ChildItem -LiteralPath $root -Directory -Force -Recurse -ErrorAction SilentlyContinue |
        Where-Object { $_.Name -eq ".git" } |
        ForEach-Object { $_.Parent }
}

$repositories = @($repositories | Sort-Object FullName -Unique)
if ($repositories.Count -eq 0) {
    Write-Host "No Git repositories found under the requested roots."
    exit 0
}

$failed = @()
foreach ($repository in $repositories) {
    Write-Host "Scanning $($repository.FullName)"
    $mode = if ($IncludeHistory) { "git" } else { "dir" }
    & $GitleaksPath $mode $repository.FullName --redact=100 --no-banner --log-level warn
    if ($LASTEXITCODE -ne 0) {
        $failed += $repository.FullName
    }
}

if ($failed.Count -gt 0) {
    Write-Error "Gitleaks found potential secrets or failed in: $($failed -join ', ')"
    exit 1
}

Write-Host "Secret scan passed for $($repositories.Count) repository/repositories in $mode mode."
