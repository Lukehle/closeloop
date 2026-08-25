# closeloop installer - copies skills and commands into ~/.claude/
# Prompts before overwriting anything that already exists.

$ErrorActionPreference = 'Stop'

$src = Join-Path $PSScriptRoot 'skills'
$dest = if ($env:CLAUDE_SKILLS_DIR) { $env:CLAUDE_SKILLS_DIR } else { Join-Path $HOME '.claude\skills' }
$commandsSrc = Join-Path $PSScriptRoot 'commands'
$commandsDest = if ($env:CLAUDE_COMMANDS_DIR) { $env:CLAUDE_COMMANDS_DIR } else { Join-Path $HOME '.claude\commands' }

if (-not (Test-Path $src)) {
    Write-Error "skills/ not found next to this script."
}
if (-not (Test-Path $dest)) {
    New-Item -ItemType Directory -Force -Path $dest | Out-Null
}
if (-not (Test-Path $commandsDest)) {
    New-Item -ItemType Directory -Force -Path $commandsDest | Out-Null
}

$installed = 0
$skipped = 0

foreach ($dir in Get-ChildItem -Path $src -Directory) {
    $target = Join-Path $dest $dir.Name
    if (Test-Path $target) {
        $reply = Read-Host "Skill `"$($dir.Name)`" already exists. Overwrite? [y/N]"
        if ($reply -notmatch '^[yY]') {
            Write-Host "  skipped $($dir.Name)"
            $skipped++
            continue
        }
        Remove-Item -Recurse -Force $target
    }
    Copy-Item -Recurse -Path $dir.FullName -Destination $target
    Write-Host "  installed $($dir.Name)"
    $installed++
}

foreach ($file in Get-ChildItem -Path $commandsSrc -File -Filter '*.md') {
    $target = Join-Path $commandsDest $file.Name
    if (Test-Path $target) {
        $reply = Read-Host "Command `"$($file.Name)`" already exists. Overwrite? [y/N]"
        if ($reply -notmatch '^[yY]') {
            Write-Host "  skipped command $($file.Name)"
            $skipped++
            continue
        }
        Remove-Item -Force $target
    }
    Copy-Item -Path $file.FullName -Destination $target
    Write-Host "  installed command $($file.Name)"
    $installed++
}

Write-Host ""
Write-Host "closeloop: $installed installed, $skipped skipped"
Write-Host "  skills   -> $dest"
Write-Host "  commands -> $commandsDest"
Write-Host ""
Write-Host "Optional next steps:"
Write-Host "  * Copy docs\CLAUDE.md.template into your finance working folder as CLAUDE.md"
Write-Host "  * Read ENTERPRISE.md before relying on any skill on a managed seat"
Write-Host "  * Hooks are OFF by default - see hooks\README.md to enable them deliberately"
