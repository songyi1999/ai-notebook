#!/bin/bash

# AI笔记本项目部署脚本
# 用于初始化项目环境和启动服务

set -e  # 遇到错误立即退出

echo "🚀 开始部署 AI笔记本项目..."

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 打印带颜色的消息
print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# 检查必要的工具
check_requirements() {
    print_info "检查系统要求..."
    
    if ! command -v docker &> /dev/null; then
        print_error "Docker 未安装，请先安装 Docker"
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        print_error "Docker Compose 未安装，请先安装 Docker Compose"
        exit 1
    fi
    
    print_success "系统要求检查通过"
}

# 创建必要的目录
create_directories() {
    print_info "创建必要的目录..."
    
    # 创建notes目录
    if [ ! -d "notes" ]; then
        mkdir -p notes
        print_success "创建 notes/ 目录"
    else
        print_info "notes/ 目录已存在"
    fi
    
    # 创建backend/data目录
    if [ ! -d "backend/data" ]; then
        mkdir -p backend/data
        print_success "创建 backend/data/ 目录"
    else
        print_info "backend/data/ 目录已存在"
    fi
    
    # 创建backend/data的子目录
    mkdir -p backend/data/chroma_db
    mkdir -p backend/data/uploads
    
    print_success "目录创建完成"
}

# 复制配置文件
setup_config_files() {
    print_info "设置配置文件..."
    
    # 复制docker-compose.yml
    if [ ! -f "docker-compose.yml" ]; then
        if [ -f "docker-compose.yml.example" ]; then
            cp docker-compose.yml.example docker-compose.yml
            print_success "创建 docker-compose.yml"
        else
            print_error "docker-compose.yml.example 文件不存在"
            exit 1
        fi
    else
        print_warning "docker-compose.yml 已存在，跳过复制"
    fi
    
    # 复制.env文件
    if [ ! -f ".env" ]; then
        if [ -f "env.example" ]; then
            cp env.example .env
            print_success "创建 .env 文件"
        else
            print_error "env.example 文件不存在"
            exit 1
        fi
    else
        print_warning ".env 文件已存在，跳过复制"
    fi
    
    print_success "配置文件设置完成"
}

# 检查和配置AI服务
check_ai_service() {
    print_info "检查AI服务配置..."
    
    print_warning "请确保您已经配置了以下AI服务之一："
    echo "  1. Ollama (推荐) - http://localhost:11434"
    echo "  2. LM Studio - http://localhost:1234"
    echo "  3. OpenAI API - https://api.openai.com"
    echo "  4. 其他OpenAI兼容的API服务"
    echo ""
    
    read -p "是否已经配置好AI服务？(y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_info "请先配置AI服务，然后重新运行此脚本"
        print_info "参考文档: LOCAL_LLM_SETUP.md"
        exit 1
    fi
}

# 构建和启动服务
build_and_start() {
    print_info "构建和启动Docker服务..."
    
    # 停止可能正在运行的服务
    docker-compose down 2>/dev/null || true
    
    # 构建并启动服务
    if docker-compose up -d --build; then
        print_success "服务启动成功！"
    else
        print_error "服务启动失败，请检查错误信息"
        exit 1
    fi
}

# 等待服务启动
wait_for_services() {
    print_info "等待服务启动..."
    
    # 等待后端服务
    for i in {1..30}; do
        if curl -s http://localhost:8000/health >/dev/null 2>&1; then
            print_success "后端服务已启动"
            break
        fi
        if [ $i -eq 30 ]; then
            print_warning "后端服务启动超时，请检查日志"
            docker-compose logs backend
        fi
        sleep 2
    done
    
    # 等待前端服务
    for i in {1..20}; do
        if curl -s http://localhost:3000 >/dev/null 2>&1; then
            print_success "前端服务已启动"
            break
        fi
        if [ $i -eq 20 ]; then
            print_warning "前端服务启动超时，请检查日志"
            docker-compose logs frontend
        fi
        sleep 2
    done
}

# 显示部署结果
show_results() {
    echo ""
    echo "🎉 部署完成！"
    echo ""
    echo "📱 访问地址："
    echo "  前端界面: http://localhost:3000"
    echo "  后端API:  http://localhost:8000"
    echo "  API文档:  http://localhost:8000/docs"
    echo ""
    echo "🔧 管理命令："
    echo "  查看日志: docker-compose logs -f"
    echo "  停止服务: docker-compose down"
    echo "  重启服务: docker-compose restart"
    echo "  重新构建: docker-compose up -d --build"
    echo ""
    echo "📚 更多帮助："
    echo "  README.md - 项目说明"
    echo "  LOCAL_LLM_SETUP.md - AI服务配置"
    echo "  GETTING_STARTED.md - 快速开始"
    echo ""
}

# 主函数
main() {
    echo "======================================"
    echo "     AI笔记本项目 - 自动部署脚本"
    echo "======================================"
    echo ""
    
    check_requirements
    create_directories
    setup_config_files
    check_ai_service
    build_and_start
    wait_for_services
    show_results
    
    print_success "部署脚本执行完成！"
}

# 错误处理
trap 'print_error "部署过程中发生错误，请检查上面的错误信息"; exit 1' ERR

# 运行主函数
main "$@" 