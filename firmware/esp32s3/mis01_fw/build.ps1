# 编译 / 烧录 MIS-01 ESP32-S3 固件
# 用法：  .\build.ps1                 编译
#         .\build.ps1 flash COM5      经 CH343 串口烧录并打开日志
#         .\build.ps1 <任意 idf.py 参数>
$ErrorActionPreference = 'Stop'
Remove-Item Env:MSYSTEM -ErrorAction SilentlyContinue   # 从 Git Bash 调用时 IDF 会误判为 MSYS
$env:IDF_PATH = 'E:\esp\esp-idf-v5.5.5'
$env:IDF_TOOLS_PATH = 'E:\esp\.espressif'
$env:IDF_GITHUB_ASSETS = 'dl.espressif.cn/github_assets'
. "$env:IDF_PATH\export.ps1" | Out-Null
Set-Location $PSScriptRoot
if ($args.Count -eq 0) { idf.py build; exit $LASTEXITCODE }
if ($args[0] -eq 'flash' -and $args.Count -ge 2) { idf.py -p $args[1] flash monitor; exit $LASTEXITCODE }
idf.py @args
exit $LASTEXITCODE
