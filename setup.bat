@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

:: AI笔记本项目部署脚本 (Windows版本)
:: 用于初始化项目环境和启动服务

echo 🚀 开始部署 AI笔记本项目...
echo ======================================
echo      AI笔记本项目 - 自动部署脚本
echo ======================================
echo.

:: 检查Docker是否安装
echo ℹ️  检查系统要求...
docker --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Docker 未安装，请先安装 Docker Desktop
    pause
    exit /b 1
)

docker-compose --version >nul 2>&1
if %errorlevel% neq 0 (
    docker compose version >nul 2>&1
    if !errorlevel! neq 0 (
        echo ❌ Docker Compose 未安装，请先安装 Docker Compose
        pause
        exit /b 1
    )
)
echo ✅ 系统要求检查通过

:: 创建必要的目录
echo ℹ️  创建必要的目录...
if not exist "notes" (
    mkdir notes
    echo ✅ 创建 notes\ 目录
) else (
    echo ℹ️  notes\ 目录已存在
)

if not exist "backend\data" (
    mkdir backend\data
    echo ✅ 创建 backend\data\ 目录
) else (
    echo ℹ️  backend\data\ 目录已存在
)

:: 创建子目录
if not exist "backend\data\chroma_db" mkdir backend\data\chroma_db
if not exist "backend\data\uploads" mkdir backend\data\uploads
echo ✅ 目录创建完成

:: 复制配置文件
echo ℹ️  设置配置文件...
if not exist "docker-compose.yml" (
    if exist "docker-compose.yml.example" (
        copy docker-compose.yml.example docker-compose.yml >nul
        echo ✅ 创建 docker-compose.yml
    ) else (
        echo ❌ docker-compose.yml.example 文件不存在
        pause
        exit /b 1
    )
) else (
    echo ⚠️  docker-compose.yml 已存在，跳过复制
)

if not exist ".env" (
    if exist "env.example" (
        copy env.example .env >nul
        echo ✅ 创建 .env 文件
    ) else (
        echo ❌ env.example 文件不存在
        pause
        exit /b 1
    )
) else (
    echo ⚠️  .env 文件已存在，跳过复制
)
echo ✅ 配置文件设置完成

:: 检查AI服务配置
echo ℹ️  检查AI服务配置...
echo ⚠️  请确保您已经配置了以下AI服务之一：
echo   1. Ollama (推荐) - http://localhost:11434
echo   2. LM Studio - http://localhost:1234
echo   3. OpenAI API - https://api.openai.com
echo   4. 其他OpenAI兼容的API服务
echo.
set /p choice="是否已经配置好AI服务？(y/n): "
if /i not "%choice%"=="y" (
    echo ℹ️  请先配置AI服务，然后重新运行此脚本
    echo ℹ️  参考文档: LOCAL_LLM_SETUP.md
    pause
    exit /b 1
)

:: 构建和启动服务
echo ℹ️  构建和启动Docker服务...
docker-compose down >nul 2>&1

echo ℹ️  正在构建和启动服务，请稍候...
docker-compose up -d --build
if %errorlevel% neq 0 (
    echo ❌ 服务启动失败，请检查错误信息
    pause
    exit /b 1
)
echo ✅ 服务启动成功！

:: 等待服务启动
echo ℹ️  等待服务启动...
timeout /t 10 /nobreak >nul

:: 检查后端服务
for /l %%i in (1,1,15) do (
    curl -s http://localhost:8000/health >nul 2>&1
    if !errorlevel! equ 0 (
        echo ✅ 后端服务已启动
        goto :frontend_check
    )
    timeout /t 2 /nobreak >nul
)
echo ⚠️  后端服务启动超时，请检查日志

:frontend_check
:: 检查前端服务
for /l %%i in (1,1,10) do (
    curl -s http://localhost:3000 >nul 2>&1
    if !errorlevel! equ 0 (
        echo ✅ 前端服务已启动
        goto :show_results
    )
    timeout /t 2 /nobreak >nul
)
echo ⚠️  前端服务启动超时，请检查日志

:show_results
:: 显示部署结果
echo.
echo 🎉 部署完成！
echo.
echo 📱 访问地址：
echo   前端界面: http://localhost:3000
echo   后端API:  http://localhost:8000
echo   API文档:  http://localhost:8000/docs
echo.
echo 🔧 管理命令：
echo   查看日志: docker-compose logs -f
echo   停止服务: docker-compose down
echo   重启服务: docker-compose restart
echo   重新构建: docker-compose up -d --build
echo.
echo 📚 更多帮助：
echo   README.md - 项目说明
echo   LOCAL_LLM_SETUP.md - AI服务配置
echo   GETTING_STARTED.md - 快速开始
echo.
echo ✅ 部署脚本执行完成！

pause 