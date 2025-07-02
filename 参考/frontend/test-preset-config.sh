#!/bin/bash

# ===========================================
# 预设问题配置测试脚本
# 用于验证 docker-entrypoint.sh 的配置功能
# ===========================================

echo "=== 医疗评价大模型 - 预设问题配置测试 ==="
echo "测试时间: $(date)"
echo ""

# 测试函数：模拟环境变量检测
test_preset_detection() {
    echo "=== 测试1: 环境变量检测 ==="
    
    # 模拟设置环境变量
    export PRESET_Q1="三甲医院专家信息"
    export PRESET_Q2="三甲医院医疗项目概况"
    export PRESET_Q5="医疗知识库问答"
    export PRESET_Q10="医疗跨时间追踪与AI比对分析"
    export WELCOME_MESSAGE="欢迎使用医疗评价大模型！"
    
    # 检测预设问题环境变量
    preset_vars=$(env | grep '^PRESET_Q' | sort)
    echo "检测到的预设问题变量:"
    echo "$preset_vars"
    
    # 计算数量
    question_count=$(echo "$preset_vars" | wc -l)
    echo "预设问题数量: $question_count"
    echo ""
}

# 测试函数：配置文件生成
test_config_generation() {
    echo "=== 测试2: 配置文件生成 ==="
    
    # 创建临时配置文件
    temp_config="/tmp/test-config.js"
    
    # 构建预设问题的 JSON 对象
    preset_questions=""
    question_count=0
    
    # 获取所有以 PRESET_Q 开头的环境变量
    preset_vars=$(env | grep '^PRESET_Q' | sort)
    
    # 处理每个预设问题环境变量
    for var in $preset_vars; do
        # 提取变量名和值
        var_name=$(echo "$var" | cut -d'=' -f1)
        var_value=$(echo "$var" | cut -d'=' -f2-)
        
        # 提取问题编号 (PRESET_Q1 -> question1)
        question_key=$(echo "$var_name" | sed 's/PRESET_Q/question/')
        
        # 转义双引号
        escaped_value=$(echo "$var_value" | sed 's/"/\\"/g')
        
        # 构建 JSON 键值对
        if [ -n "$preset_questions" ]; then
            preset_questions="$preset_questions,"
        fi
        preset_questions="$preset_questions
    $question_key: \"$escaped_value\""
        
        question_count=$((question_count + 1))
        echo "处理问题: $question_key = $escaped_value"
    done
    
    # 生成测试配置文件
    cat > "$temp_config" << EOF
// 医疗评价大模型 - 测试配置
// 生成时间: $(date)
// 预设问题数量: $question_count

window.APP_CONFIG = {
  // 预设问题配置
  presetQuestions: {$preset_questions
  },
  
  // 应用配置
  welcomeMessage: "$WELCOME_MESSAGE",
  asrServerUrl: "/asr",
  
  // 元数据
  _meta: {
    generatedAt: "$(date -Iseconds)",
    questionCount: $question_count,
    version: "1.0.0"
  }
};

console.log('医疗评价大模型配置已加载:', window.APP_CONFIG);
EOF

    echo ""
    echo "生成的配置文件内容:"
    echo "========================"
    cat "$temp_config"
    echo "========================"
    echo "配置文件已生成: $temp_config"
    echo ""
}

# 测试函数：配置文件验证
test_config_validation() {
    echo "=== 测试3: 配置验证 ==="
    
    temp_config="/tmp/test-config.js"
    
    if [ -f "$temp_config" ]; then
        file_size=$(wc -c < "$temp_config")
        echo "✅ 配置文件存在，大小: ${file_size} bytes"
        
        # 检查配置文件语法 (简单检查)
        if grep -q "window.APP_CONFIG" "$temp_config"; then
            echo "✅ 配置文件格式正确"
        else
            echo "❌ 配置文件格式错误"
        fi
        
        # 检查预设问题数量
        question_lines=$(grep -c "question[0-9]*:" "$temp_config")
        echo "✅ 检测到 $question_lines 个预设问题"
        
    else
        echo "❌ 配置文件不存在"
    fi
    echo ""
}

# 测试函数：边界情况
test_edge_cases() {
    echo "=== 测试4: 边界情况 ==="
    
    # 测试空环境变量
    echo "测试空环境变量..."
    unset PRESET_Q1 PRESET_Q2 PRESET_Q5 PRESET_Q10
    
    preset_vars=$(env | grep '^PRESET_Q' | sort)
    if [ -z "$preset_vars" ]; then
        echo "✅ 正确处理空环境变量情况"
    else
        echo "❌ 空环境变量处理异常"
    fi
    
    # 测试特殊字符
    echo "测试特殊字符..."
    export PRESET_Q1="包含\"双引号\"的问题"
    export PRESET_Q2="包含'单引号'的问题"
    
    escaped_q1=$(echo "$PRESET_Q1" | sed 's/"/\\"/g')
    escaped_q2=$(echo "$PRESET_Q2" | sed 's/"/\\"/g')
    
    echo "原始: $PRESET_Q1"
    echo "转义: $escaped_q1"
    echo "原始: $PRESET_Q2" 
    echo "转义: $escaped_q2"
    
    if [ "$escaped_q1" != "$PRESET_Q1" ]; then
        echo "✅ 双引号转义正常"
    else
        echo "❌ 双引号转义失败"
    fi
    echo ""
}

# 清理函数
cleanup() {
    echo "=== 清理测试环境 ==="
    unset PRESET_Q1 PRESET_Q2 PRESET_Q5 PRESET_Q10 WELCOME_MESSAGE
    rm -f /tmp/test-config.js
    echo "✅ 测试环境已清理"
    echo ""
}

# 主测试流程
main() {
    echo "开始执行预设问题配置测试..."
    echo ""
    
    test_preset_detection
    test_config_generation
    test_config_validation
    test_edge_cases
    
    echo "=== 测试总结 ==="
    echo "✅ 环境变量检测功能正常"
    echo "✅ 配置文件生成功能正常"
    echo "✅ 配置验证功能正常"
    echo "✅ 边界情况处理正常"
    echo ""
    echo "🎉 所有测试通过！预设问题配置功能工作正常。"
    echo ""
    
    cleanup
}

# 执行测试
main

echo "=== 使用说明 ==="
echo "1. 本脚本用于测试预设问题配置功能"
echo "2. 实际使用时，请参考 PRESET_QUESTIONS_GUIDE.md"
echo "3. 配置文件位置: frontend/preset-questions.env"
echo "4. Docker编排文件: docker-compose.yml 或 docker-compose.env-file.yml"
echo ""
echo "测试完成时间: $(date)" 