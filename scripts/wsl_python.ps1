param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$PythonArguments
)
$taskProjectRoot = Split-Path -Parent $PSScriptRoot
$taskLinuxRoot = '/mnt/' + $taskProjectRoot.Substring(0, 1).ToLowerInvariant() + $taskProjectRoot.Substring(2).Replace('\', '/')
& wsl.exe --distribution Ubuntu-24.04 --user ncm --cd $taskLinuxRoot --exec /home/ncm/.venvs/anytime-ncm/bin/python @PythonArguments
exit $LASTEXITCODE
