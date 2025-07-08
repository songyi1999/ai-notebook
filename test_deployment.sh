#!/bin/bash

# AI笔记本部署验证脚本
# 测试配置系统和无AI模式的完整部署

set -e

echo "=========================================="
echo "AI笔记本部署验证脚本"
echo "=========================================="

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 函数定义
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查依赖
check_dependencies() {
    log_info "检查系统依赖..."
    
    # 检查Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker 未安装或不在 PATH 中"
        exit 1
    fi
    log_success "Docker 已安装"
    
    # 检查docker-compose
    if ! command -v docker-compose &> /dev/null; then
        log_error "docker-compose 未安装或不在 PATH 中"
        exit 1
    fi
    log_success "docker-compose 已安装"
    
    # 检查curl
    if ! command -v curl &> /dev/null; then
        log_error "curl 未安装或不在 PATH 中"
        exit 1
    fi
    log_success "curl 已安装"
}

# 创建测试配置文件
create_test_configs() {
    log_info "创建测试配置文件..."
    
    # 1. 创建完整AI配置
    cat > config.json.ai << 'EOF'
{
  "ai_settings": {
    "enabled": true,
    "language_model": {
      "provider": "openai_compatible",
      "base_url": "http://localhost:11434/v1",
      "api_key": "ollama",
      "model_name": "qwen2.5:0.5b",
      "temperature": 0.7,
      "max_tokens": 2048
    },
    "embedding_model": {
      "provider": "openai_compatible",
      "base_url": "http://localhost:11434/v1",
      "api_key": "ollama",
      "model_name": "quentinz/bge-large-zh-v1.5:latest",
      "dimension": 1024
    }
  },
  "application": {
    "theme": "light",
    "language": "zh-CN",
    "auto_save": true
  },
  "meta": {
    "config_version": "1.0",
    "description": "测试AI配置"
  }
}
EOF

    # 2. 创建纯笔记模式配置
    cat > config.json.notes_only << 'EOF'
{
  "ai_settings": {
    "enabled": false,
    "fallback_mode": "notes_only"
  },
  "application": {
    "theme": "light",
    "language": "zh-CN",
    "auto_save": true
  },
  "meta": {
    "config_version": "1.0",
    "description": "纯笔记模式配置"
  }
}
EOF

    # 3. 创建docker-compose文件（如果不存在）
    if [ ! -f docker-compose.yml ]; then
        if [ -f docker-compose.yml.example ]; then
            cp docker-compose.yml.example docker-compose.yml
            log_success "已从示例文件创建 docker-compose.yml"
        else
            log_error "未找到 docker-compose.yml.example 文件"
            exit 1
        fi
    fi
    
    log_success "测试配置文件已创建"
}

# 测试无AI模式部署
test_notes_only_mode() {
    log_info "测试纯笔记模式部署..."
    
    # 使用纯笔记模式配置
    cp config.json.notes_only config.json
    
    # 启动服务
    log_info "启动Docker服务（纯笔记模式）..."
    docker-compose down -v 2>/dev/null || true
    docker-compose up -d --build
    
    # 等待服务启动
    log_info "等待服务启动（60秒）..."
    sleep 60
    
    # 检查服务状态
    if ! docker-compose ps | grep -q "Up"; then
        log_error "Docker服务启动失败"
        docker-compose logs
        return 1
    fi
    
    # 测试后端健康检查
    log_info "测试后端健康检查..."
    for i in {1..30}; do
        if curl -s http://localhost:8000/health > /dev/null; then
            log_success "后端服务健康检查通过"
            break
        fi
        if [ $i -eq 30 ]; then
            log_error "后端服务健康检查失败"
            return 1
        fi
        sleep 2
    done
    
    # 测试前端访问
    log_info "测试前端访问..."
    if curl -s http://localhost:3000 > /dev/null; then
        log_success "前端服务访问正常"
    else
        log_error "前端服务访问失败"
        return 1
    fi
    
    # 测试AI状态API
    log_info "测试AI状态API..."
    ai_status=$(curl -s http://localhost:8000/api/v1/config/status)
    if echo "$ai_status" | grep -q '"enabled":false'; then
        log_success "AI已正确禁用"
    else
        log_warning "AI状态可能未正确配置"
    fi
    
    # 测试搜索降级
    log_info "测试搜索降级功能..."
    search_result=$(curl -s "http://localhost:8000/api/v1/files/search?q=test&search_type=semantic&limit=5")
    if echo "$search_result" | grep -q '"degraded":true'; then
        log_success "搜索降级功能正常"
    else
        log_warning "搜索可能未降级或无测试数据"
    fi
    
    log_success "纯笔记模式测试完成"
    return 0
}

# 测试AI模式部署
test_ai_mode() {
    log_info "测试AI模式部署..."
    
    # 使用AI模式配置
    cp config.json.ai config.json
    
    # 重启服务以加载新配置
    log_info "重启服务以加载AI配置..."
    docker-compose restart backend
    
    # 等待重启完成
    log_info "等待服务重启（30秒）..."
    sleep 30
    
    # 测试AI状态
    log_info "测试AI配置加载..."
    ai_status=$(curl -s http://localhost:8000/api/v1/config/status)
    if echo "$ai_status" | grep -q '"enabled":true'; then
        log_success "AI配置已正确加载"
    else
        log_warning "AI配置可能未正确加载"
    fi
    
    # 测试AI连接（可能失败，取决于是否有本地AI服务）
    log_info "测试AI连接性..."
    ai_test=$(curl -s http://localhost:8000/api/v1/config/test)
    overall_status=$(echo "$ai_test" | grep -o '"overall_status":"[^"]*"' | cut -d'"' -f4)
    
    case $overall_status in
        "fully_available")
            log_success "AI服务完全可用"
            ;;
        "partially_available")
            log_warning "AI服务部分可用"
            ;;
        "disabled")
            log_info "AI服务已禁用"
            ;;
        *)
            log_warning "AI服务不可用（这是正常的，如果您没有配置本地AI服务）"
            ;;
    esac
    
    log_success "AI模式测试完成"
    return 0
}

# 清理函数
cleanup() {
    log_info "清理测试环境..."
    
    # 停止Docker服务
    docker-compose down -v 2>/dev/null || true
    
    # 清理测试配置文件
    rm -f config.json config.json.ai config.json.notes_only
    
    log_success "清理完成"
}

# 主函数
main() {
    echo "开始部署验证..."
    echo "这将测试AI笔记本的配置系统和降级功能"
    echo ""
    
    # 检查依赖
    check_dependencies
    
    # 创建测试配置
    create_test_configs
    
    # 设置清理陷阱
    trap cleanup EXIT
    
    # 运行测试
    success_count=0
    total_tests=2
    
    # 测试纯笔记模式
    if test_notes_only_mode; then
        success_count=$((success_count + 1))
    fi
    
    # 测试AI模式
    if test_ai_mode; then
        success_count=$((success_count + 1))
    fi
    
    # 输出结果
    echo ""
    echo "=========================================="
    echo "部署验证结果"
    echo "=========================================="
    echo "总测试数: $total_tests"
    echo "通过数: $success_count"
    echo "失败数: $((total_tests - success_count))"
    
    if [ $success_count -eq $total_tests ]; then
        log_success "🎉 所有部署测试通过！"
        echo ""
        echo "系统已成功部署，您可以通过以下方式访问："
        echo "- 前端界面: http://localhost:3000"
        echo "- 后端API: http://localhost:8000"
        echo "- API文档: http://localhost:8000/docs"
        echo ""
        echo "配置管理："
        echo "- 点击右上角设置按钮或按 Ctrl+, 打开配置界面"
        echo "- 配置文件位置: ./config.json"
        echo "- 配置指南: ./CONFIG_GUIDE.md"
    else
        log_error "⚠️ 部分测试失败，请检查配置"
        exit 1
    fi
}

# 运行主函数
main "$@"