# DeepSeek Harness 桌面版一键打包脚本
# 用法：在项目目录下运行  .\build.ps1
python -m PyInstaller --noconfirm --clean --onefile --windowed --name DeepSeekHarness --icon icon.ico --collect-all webview dsh_launcher.py
Write-Output ""
Write-Output "打包完成：dist\DeepSeekHarness.exe"
