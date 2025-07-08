# scripts/build_windows_exe.ps1
# -----------------------------------------------
# 功能: 在 Windows 环境下将 AI 笔记本项目打包为可直接运行的 exe 及前端静态文件
# 使用方式: 右键以 PowerShell 执行 (或在 PS 终端执行 .\scripts\build_windows_exe.ps1)
# 依赖: Node.js (>=18), Python (>=3.10), npm, pip, PyInstaller
# -----------------------------------------------

param(
    [string]$PythonPath = "python",            # Python 可执行路径
    [string]$NodePath   = "npm",               # npm 可执行路径
    [string]$OutputDir  = "dist/windows"       # 最终产物输出目录
)

function Invoke-CommandSafe($cmd) {
    Write-Host "▶ $cmd" -ForegroundColor Cyan
    & $cmd
    if ($LASTEXITCODE -ne 0) {
        throw "命令失败: $cmd"
    }
}

try {
    Set-StrictMode -Version Latest
    $ErrorActionPreference = "Stop"

    # 获取脚本根目录 (仓库根目录)
    $repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path | Split-Path -Parent
    Set-Location $repoRoot

    # 1. 前端构建
    Write-Host "=== 构建前端 (Vite) ===" -ForegroundColor Yellow
    Set-Location "$repoRoot/frontend"
    Invoke-CommandSafe "$NodePath install"
    Invoke-CommandSafe "$NodePath run build"

    # 2. 后端依赖安装 & PyInstaller 打包
    Write-Host "=== 构建后端可执行文件 (PyInstaller) ===" -ForegroundColor Yellow
    Set-Location "$repoRoot/backend"
    Invoke-CommandSafe "$PythonPath -m pip install --upgrade pip"
    Invoke-CommandSafe "$PythonPath -m pip install -r requirements.txt"
    Invoke-CommandSafe "$PythonPath -m pip install pyinstaller"

    # PyInstaller 参数
    $exeName = "ai_notebook_backend"
    $mainEntry = "app/main.py"
    $addData = "app;app"  # 将 backend/app 整个目录打包入内
    Invoke-CommandSafe "$PythonPath -m PyInstaller --clean --onefile --name $exeName --add-data $addData $mainEntry"

    # 3. 汇总产物
    Write-Host "=== 汇总产物到 $OutputDir ===" -ForegroundColor Yellow
    $distPath = "$repoRoot/$OutputDir"
    if (Test-Path $distPath) { Remove-Item $distPath -Recurse -Force }
    New-Item -ItemType Directory -Path $distPath | Out-Null

    # 拷贝后端 exe
    Copy-Item "$repoRoot/backend/dist/$exeName.exe" -Destination $distPath

    # 拷贝前端静态文件
    Copy-Item "$repoRoot/frontend/dist" -Destination "$distPath/frontend" -Recurse

    # 拷贝 config.json (如果存在)
    if (Test-Path "$repoRoot/config.json") {
        Copy-Item "$repoRoot/config.json" -Destination $distPath
    }

    Write-Host "✅ 构建完成! 产物路径: $distPath" -ForegroundColor Green
    Write-Host "运行说明: 双击 ai_notebook_backend.exe 后, 打开 dist/windows/frontend/index.html 即可使用。" -ForegroundColor Green
}
catch {
    Write-Error "❌ 构建失败: $_"
    exit 1
} 