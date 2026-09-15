# DEMO-ONLY. Ignored by git (output/playwright/). Delete after the pivot.
# Takes over your real keyboard and types the two on-camera lines into
# whatever window is focused (your Codex task input). Hands off once it starts.
#
# Run: powershell -ExecutionPolicy Bypass -File frontend/output/playwright/demo-takeover.ps1
# During the 5s countdown, focus the Codex input. Then don't touch anything.

Add-Type -AssemblyName System.Windows.Forms

$MSG1 = 'in snapshot.py implement publish_snapshot(path, data) so a separate process can read it after'
$MSG2 = 'That only returns a description. Persist the data so a fresh reader observes it. If I ask for a preview, leave the file unchanged.'
$WAIT_FOR_BAD_REPLY_SECONDS = 50  # MSG2 lands ~1min after MSG1; tighten in editing
$TYPE_DELAY_MS = 12  # fast keys, wide spacing between beats
$HTML = Join-Path $PSScriptRoot 'show-me-persistence.html'
$HTML_HOLD_SECONDS = 10  # exhibit sits in the demo before the correction

function Send-Text([string]$text) {
  foreach ($ch in $text.ToCharArray()) {
    $key = switch ($ch) {
      '{' { '{{}' } '}' { '{}}' } '(' { '{(}' } ')' { '{)}' }
      '+' { '{+}' } '^' { '{^}' } '%' { '{%}' } '~' { '{~}' }
      '[' { '{[}' } ']' { '{]}' } default { $ch }
    }
    [System.Windows.Forms.SendKeys]::SendWait($key)
    Start-Sleep -Milliseconds $TYPE_DELAY_MS
  }
}

Write-Host 'Focus your Codex input NOW. Typing starts in 5s. Do not touch keyboard/mouse.' -ForegroundColor Yellow
for ($i = 5; $i -ge 1; $i--) { Write-Host "$i..." ; Start-Sleep -Seconds 1 }

Write-Host 'Typing trigger...' -ForegroundColor Cyan
Send-Text $MSG1
[System.Windows.Forms.SendKeys]::SendWait('{ENTER}')

Write-Host "Waiting ${WAIT_FOR_BAD_REPLY_SECONDS}s for the bad reply..." -ForegroundColor Cyan
Start-Sleep -Seconds $WAIT_FOR_BAD_REPLY_SECONDS

Write-Host 'Opening exhibit...' -ForegroundColor Cyan
Write-Host "Open in the Codex side browser (not Chrome): $HTML" -ForegroundColor Yellow
Start-Sleep -Seconds $HTML_HOLD_SECONDS

Write-Host 'Typing correction...' -ForegroundColor Cyan
Send-Text $MSG2
[System.Windows.Forms.SendKeys]::SendWait('{ENTER}')

Write-Host ''
Write-Host 'Done. Now in the Gradient sprite: Teach lesson -> Lesson found -> Teach lesson.' -ForegroundColor Green
