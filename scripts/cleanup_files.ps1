[CmdletBinding()]
param(
    [int]$RetentionDays = 35,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"

if ($RetentionDays -lt 1) {
    Write-Error "RetentionDays must be a positive integer."
    exit 2
}

# scripts\cleanup_files.ps1 -> project root
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$Cutoff = (Get-Date).AddDays(-$RetentionDays)
$EligibleCount = 0

function Remove-OldPpiFiles {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Directory,

        [Parameter(Mandatory = $true)]
        [string]$Filter
    )

    if (-not (Test-Path -LiteralPath $Directory -PathType Container)) {
        return
    }

    Get-ChildItem -LiteralPath $Directory -File -Filter $Filter -ErrorAction Stop |
        Where-Object { $_.LastWriteTime -lt $Cutoff } |
        ForEach-Object {
            $script:EligibleCount++

            if ($DryRun) {
                Write-Host "Would delete: $($_.FullName)"
            }
            else {
                Write-Host "Deleting: $($_.FullName)"
                Remove-Item -LiteralPath $_.FullName -Force -ErrorAction Stop
            }
        }
}

try {
    # Timestamped per-run logs are disposable after the retention period.
    Remove-OldPpiFiles `
        -Directory (Join-Path $Root "logs\runs") `
        -Filter "*.log"

    # Timestamped TIDAL matched/unmatched reports are disposable after the retention period.
    # Keep the legacy '=' pattern so reports created before CP025 still age out.
    Remove-OldPpiFiles `
        -Directory (Join-Path $Root "reports") `
        -Filter "tidal-matched=*.csv"

    Remove-OldPpiFiles `
        -Directory (Join-Path $Root "reports") `
        -Filter "tidal-matched-*.csv"

    Remove-OldPpiFiles `
        -Directory (Join-Path $Root "reports") `
        -Filter "tidal-unmatched-*.csv"

    if ($DryRun) {
        Write-Host "Dry run complete: $EligibleCount file(s) eligible for deletion."
    }
    else {
        Write-Host "Housekeeping complete: $EligibleCount file(s) deleted."
    }

    exit 0
}
catch {
    Write-Error "PPI file housekeeping failed: $($_.Exception.Message)"
    exit 1
}
