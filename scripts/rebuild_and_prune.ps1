# scripts/rebuild_and_prune.ps1
# ------------------------------------------------------------
# 目的: Windows 开发环境一键重启 Docker 服务并自动清理旧镜像
# 使用: .\scripts\rebuild_and_prune.ps1
# ------------------------------------------------------------

param(
    [switch]$PruneAll  # 若传入 -PruneAll 将执行 docker system prune -a -f
)

function Invoke-Safe($cmd) {
    Write-Host "▶ $cmd" -ForegroundColor Cyan
    & $cmd
    if ($LASTEXITCODE -ne 0) { throw "命令失败: $cmd" }
}

try {
    $ErrorActionPreference = 'Stop'

    Write-Host "➡ 停止并删除旧容器..." -ForegroundColor Yellow
    Invoke-Safe "docker-compose down --remove-orphans"

    Write-Host "🚀 重新构建并启动服务..." -ForegroundColor Yellow
    Invoke-Safe "docker-compose up -d --build"

    if ($PruneAll) {
        Write-Host "🧹 深度清理所有未使用资源 (docker system prune -a -f)..." -ForegroundColor Yellow
        Invoke-Safe "docker system prune -a -f"
    } else {
        Write-Host "🧹 清理悬挂(dangling)镜像 (docker image prune -f)..." -ForegroundColor Yellow
        Invoke-Safe "docker image prune -f"
    }

    Write-Host "✅ Docker 服务已重启且旧镜像已清理完毕" -ForegroundColor Green
}
catch {
    Write-Error "❌ 执行失败: $_"
    exit 1
} 