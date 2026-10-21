# 编译并只显示本工程源文件的 error / warning 和最终结果（调试用）
$out = powershell -NoProfile -ExecutionPolicy Bypass -File "$PSScriptRoot\build.ps1" @args 2>&1 | Out-String -Width 4096
$out -split "`n" | Where-Object { $_ -match '(main[/\][^ ]+:\d+:\d+: (error|warning|note))|undefined reference|Project build complete|binary size|FAILED:|ninja: build stopped' } | Select-Object -Unique
