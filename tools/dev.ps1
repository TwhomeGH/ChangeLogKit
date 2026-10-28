# PowerShell wrapper for tools/dev.py. Logic lives in Python.
param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]] $Rest
)

$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
& python (Join-Path $here "dev.py") @Rest
exit $LASTEXITCODE
