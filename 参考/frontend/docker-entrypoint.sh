#!/bin/sh

# ===========================================
# 医疗评价大模型 - Docker 启动脚本
# 功能：自动检测和配置任意数量的预设问题
# ===========================================

echo "=== 医疗评价大模型前端容器启动 ==="
echo "启动时间: $(date)"

# 显示关键环境变量用于调试
echo ""
echo "=== 环境变量检查 ==="
echo "API_BASE_URL=$API_BASE_URL"
echo "OPENAI_API_KEY=${OPENAI_API_KEY:0:20}..." # 只显示前20个字符
echo "ASR_SERVER_URL=$ASR_SERVER_URL"
echo "WELCOME_MESSAGE=$WELCOME_MESSAGE"
echo "LOGO_URL=$LOGO_URL"
echo "IDENTITY_PROMPT=$IDENTITY_PROMPT"
echo "MODEL_NAME_DISPLAY=$MODEL_NAME_DISPLAY"
echo "WELCOME_SUBTITLE=$WELCOME_SUBTITLE"

# 替换 Nginx 配置文件中的环境变量
echo ""
echo "=== 配置 Nginx ==="
envsubst '$API_BASE_URL $OPENAI_API_KEY $ASR_SERVER_URL' < /etc/nginx/nginx.conf.template > /etc/nginx/nginx.conf
envsubst '$API_BASE_URL $OPENAI_API_KEY $ASR_SERVER_URL' < /etc/nginx/conf.d/default.conf.template > /etc/nginx/conf.d/default.conf

echo "Nginx 配置文件已生成"

# 自动检测所有预设问题环境变量
echo ""
echo "=== 检测预设问题 ==="

# 获取所有以 PRESET_Q 开头的环境变量
preset_vars=$(env | grep '^PRESET_Q' | sort)
echo "检测到的预设问题变量:"
echo "$preset_vars"

# 构建预设问题的 JSON 对象
preset_questions=""
question_count=0

# 处理每个预设问题环境变量
for var in $preset_vars; do
    # 提取变量名和值
    var_name=$(echo "$var" | cut -d'=' -f1)
    var_value=$(echo "$var" | cut -d'=' -f2-)
    
    # 提取问题编号 (PRESET_Q1 -> question1)
    question_key=$(echo "$var_name" | sed 's/PRESET_Q/question/')
    
    # 转义双引号和换行符
    escaped_value=$(echo "$var_value" | sed 's/"/\\"/g' | sed 's/$/\\n/' | tr -d '\n' | sed 's/\\n$//')
    
    # 构建 JSON 键值对
    if [ -n "$preset_questions" ]; then
        preset_questions="$preset_questions,"
    fi
    preset_questions="$preset_questions
    $question_key: \"$escaped_value\""
    
    question_count=$((question_count + 1))
    echo "  $question_key: $escaped_value"
done

echo "总共检测到 $question_count 个预设问题"

# 如果没有检测到预设问题，使用默认问题
if [ $question_count -eq 0 ]; then
    echo "未检测到预设问题，使用默认配置"
    preset_questions='
    question1: "三甲医院专家信息",
    question2: "三甲医院医疗项目概况",
    question3: "三甲医院医疗项目自动化评价"'
fi

# 处理欢迎消息
welcome_message="${WELCOME_MESSAGE:-欢迎使用医疗评价大模型！我可以回答医疗评价相关的问题。}"
escaped_welcome=$(echo "$welcome_message" | sed 's/"/\\"/g')

# 处理Logo URL
logo_url="${LOGO_URL:-}"
escaped_logo_url=$(echo "$logo_url" | sed 's/"/\\"/g')

# 处理身份提示
identity_prompt="${IDENTITY_PROMPT:-医疗评价AI助手}"
escaped_identity_prompt=$(echo "$identity_prompt" | sed 's/"/\\"/g')

# 处理模型显示名称
model_name_display="${MODEL_NAME_DISPLAY:-医疗评价大模型}"
escaped_model_name_display=$(echo "$model_name_display" | sed 's/"/\\"/g')

# 处理欢迎语副标题
welcome_subtitle="${WELCOME_SUBTITLE:-我是您的专业AI助手，随时可以为您服务}"
escaped_welcome_subtitle=$(echo "$welcome_subtitle" | sed 's/"/\\"/g')

# 生成运行时配置文件
echo ""
echo "=== 生成应用配置 ==="

cat > /usr/share/nginx/html/config.js << EOF
// 医疗评价大模型 - 运行时配置
// 生成时间: $(date)
// 预设问题数量: $question_count

window.APP_CONFIG = {
  // 预设问题配置
  presetQuestions: {$preset_questions
  },
  
  // 应用配置
  welcomeMessage: "$escaped_welcome",
  logoUrl: "$escaped_logo_url",
  identityPrompt: "$escaped_identity_prompt",
  modelNameDisplay: "$escaped_model_name_display",
  welcomeSubtitle: "$escaped_welcome_subtitle",
  asrServerUrl: "/asr",
  
  // 元数据
  _meta: {
    generatedAt: "$(date -Iseconds)",
    questionCount: $question_count,
    version: "1.0.0"
  }
};

// 调试信息
console.log('医疗评价大模型配置已加载:', window.APP_CONFIG);
console.log('预设问题数量:', $question_count);
EOF

echo "应用配置文件已生成: /usr/share/nginx/html/config.js"

# 输出生成的配置内容用于调试
echo ""
echo "=== 生成的配置内容 ==="
echo "--- config.js ---"
cat /usr/share/nginx/html/config.js
echo "--- 配置文件结束 ---"

# 验证生成的配置文件
echo ""
echo "=== 配置验证 ==="
if [ -f "/usr/share/nginx/html/config.js" ]; then
    file_size=$(wc -c < /usr/share/nginx/html/config.js)
    echo "✅ 配置文件生成成功，大小: ${file_size} bytes"
else
    echo "❌ 配置文件生成失败"
    exit 1
fi

# 检查 Nginx 配置是否正确
echo ""
echo "=== Nginx 配置验证 ==="
if nginx -t 2>/dev/null; then
    echo "✅ Nginx 配置验证通过"
else
    echo "❌ Nginx 配置验证失败"
    nginx -t
    exit 1
fi

echo ""
echo "=== 启动完成 ==="
echo "前端服务配置完成，准备启动 Nginx"
echo "访问地址: http://localhost:8088"
echo "API 代理: $API_BASE_URL"
echo "预设问题: $question_count 个"
echo ""

# 执行传入的命令 (通常是 nginx)
exec "$@" 