param([Parameter(Mandatory = $true)][string]$SetupPath)
$ErrorActionPreference = 'Stop'
$workspace = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$testRoot = [IO.Path]::GetFullPath((Join-Path $workspace 'test-results'))
$destination = [IO.Path]::GetFullPath((Join-Path $testRoot 'installed-qa'))
if (-not $destination.StartsWith($testRoot + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) {
    throw 'Installer test directory is outside the workspace test folder.'
}
$setup = (Resolve-Path -LiteralPath $SetupPath).Path
if (-not $setup.EndsWith('_QA.exe', [StringComparison]::OrdinalIgnoreCase)) {
    throw 'Only the isolated QA installer may be tested automatically.'
}
$registryKey = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\{CE980EF4-4F4A-4EED-A2B7-639C605C9B14}_is1'
if (Test-Path -LiteralPath $registryKey) {
    $existing = (Get-ItemProperty -LiteralPath $registryKey).InstallLocation
    if ([IO.Path]::GetFullPath($existing).TrimEnd('\') -ne $destination.TrimEnd('\')) {
        throw 'A QA installation exists outside this test directory; refusing to replace it.'
    }
}
New-Item -ItemType Directory -Path $testRoot -Force | Out-Null
$desktopLink = Join-Path ([Environment]::GetFolderPath('Desktop')) 'Accessible Media Transcriber QA.lnk'
$startLink = Join-Path ([Environment]::GetFolderPath('Programs')) 'Accessible Media Transcriber QA\Accessible Media Transcriber QA.lnk'
$executable = Join-Path $destination 'AccessibleVideoTranscriber.exe'
$uninstaller = Join-Path $destination 'unins000.exe'
$report = [ordered]@{ fresh_install = $false; upgrade = $false; shortcuts = $false; uninstall = $false }
function Invoke-QASetup([string]$Tasks, [string]$LogName) {
    $arguments = @('/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART', '/CURRENTUSER',
        ('/DIR="' + $destination + '"'), ('/TASKS="' + $Tasks + '"'),
        ('/LOG="' + (Join-Path $testRoot $LogName) + '"'))
    $process = Start-Process -FilePath $setup -ArgumentList $arguments -WindowStyle Hidden -Wait -PassThru
    if ($process.ExitCode -ne 0) { throw "QA Setup exited with $($process.ExitCode)." }
}
try {
    Invoke-QASetup 'startmenuicon,desktopicon,offline,offline\tiny' 'qa-install.log'
    if (-not (Test-Path -LiteralPath $executable)) { throw 'Installed application is missing.' }
    if (-not (Test-Path -LiteralPath (Join-Path $destination 'models\tiny\model.bin'))) { throw 'Selected Tiny model is missing.' }
    if (Test-Path -LiteralPath (Join-Path $destination 'models\base\model.bin')) { throw 'Unselected Base model was installed.' }
    if (-not (Test-Path -LiteralPath $desktopLink) -or -not (Test-Path -LiteralPath $startLink)) { throw 'Selected shortcuts are missing.' }
    $report.fresh_install = $true
    Invoke-QASetup 'startmenuicon,offline,offline\small' 'qa-upgrade.log'
    if (-not (Test-Path -LiteralPath (Join-Path $destination 'models\small\model.bin'))) { throw 'Selected Small model is missing after upgrade.' }
    if ((Get-Content -LiteralPath (Join-Path $destination 'installed-model.ini') -Raw) -notmatch 'model=small') { throw 'Installer model preference was not updated.' }
    if (Test-Path -LiteralPath $desktopLink) { throw 'Deselected Desktop shortcut remains after upgrade.' }
    if (-not (Test-Path -LiteralPath $startLink)) { throw 'Start menu shortcut was lost during upgrade.' }
    $metadata = Get-ItemProperty -LiteralPath $registryKey
    if ($metadata.DisplayName -notmatch 'QA') { throw 'QA installer used a production identity.' }
    $report.upgrade = $true
    $report.shortcuts = $true
    $report.version = $metadata.DisplayVersion
    $report.installed_sha256 = (Get-FileHash -LiteralPath $executable -Algorithm SHA256).Hash
}
finally {
    if (Test-Path -LiteralPath $uninstaller) {
        $process = Start-Process -FilePath $uninstaller -ArgumentList '/VERYSILENT /SUPPRESSMSGBOXES /NORESTART' -WindowStyle Hidden -Wait -PassThru
        if ($process.ExitCode -ne 0) { throw 'QA uninstaller did not finish successfully.' }
    }
}
# A fresh API-only installation must not silently copy an offline model.
try {
    Invoke-QASetup '' 'qa-api-only.log'
    if (-not (Test-Path -LiteralPath $executable)) { throw 'API-only application is missing.' }
    $models = Join-Path $destination 'models'
    if ((Test-Path -LiteralPath $models) -and
        (Get-ChildItem -LiteralPath $models -Filter 'model.bin' -Recurse -File | Select-Object -First 1)) {
        throw 'API-only installation unexpectedly contains an offline model.'
    }
    if (Test-Path -LiteralPath (Join-Path $destination 'installed-model.ini')) {
        throw 'API-only installation incorrectly selects an installed model.'
    }
    if ((Test-Path -LiteralPath $desktopLink) -or (Test-Path -LiteralPath $startLink)) {
        throw 'API-only installation created unselected shortcuts.'
    }
    $report.api_only = $true
}
finally {
    if (Test-Path -LiteralPath $uninstaller) {
        $process = Start-Process -FilePath $uninstaller -ArgumentList '/VERYSILENT /SUPPRESSMSGBOXES /NORESTART' -WindowStyle Hidden -Wait -PassThru
        if ($process.ExitCode -ne 0) { throw 'API-only QA uninstall failed.' }
    }
}
if ((Test-Path -LiteralPath $executable) -or (Test-Path -LiteralPath $registryKey) -or
    (Test-Path -LiteralPath $desktopLink) -or (Test-Path -LiteralPath $startLink)) {
    throw 'QA application, registration, or shortcuts remain after uninstall.'
}
$report.uninstall = $true
$report | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $testRoot 'installer-report.json') -Encoding utf8
$report | ConvertTo-Json
