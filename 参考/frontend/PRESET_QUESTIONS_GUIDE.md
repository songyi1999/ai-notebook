# 预设问题配置指南

## 概述

医疗评价大模型支持灵活的预设问题配置，可以自动检测和加载任意数量的预设问题。系统提供了两种配置方式，满足不同场景的需求。

## 🚀 核心特性

- ✅ **自动检测**：自动扫描所有 `PRESET_Q*` 环境变量
- ✅ **任意数量**：支持配置任意数量的预设问题 (1-N个)
- ✅ **智能排序**：按照问题编号自动排序显示
- ✅ **错误容忍**：跳过空值或无效的问题配置
- ✅ **实时生成**：容器启动时动态生成配置文件
- ✅ **调试友好**：详细的启动日志和配置验证

## 📋 配置方式

### 方式1: 使用配置文件 (推荐)

**优点**: 配置集中、易于管理、支持注释、适合生产环境

1. **编辑配置文件**: `frontend/preset-questions.env`
```bash
# 预设问题配置
PRESET_Q1=三甲医院专家信息
PRESET_Q2=三甲医院医疗项目概况
PRESET_Q3=三甲医院医疗项目自动化评价
# ... 更多问题
```

2. **使用配置文件**: `docker-compose.env-file.yml`
```yaml
services:
  frontend:
    env_file:
      - ./frontend/preset-questions.env
    environment:
      - API_BASE_URL=http://api:8000
      # 其他非预设问题的环境变量
```

3. **启动服务**:
```bash
docker-compose -f docker-compose.env-file.yml up -d
```

### 方式2: 直接定义环境变量

**优点**: 配置直观、便于快速调试、适合开发环境

```yaml
services:
  frontend:
    environment:
      - PRESET_Q1=三甲医院专家信息
      - PRESET_Q2=三甲医院医疗项目概况
      - PRESET_Q3=三甲医院医疗项目自动化评价
      - PRESET_Q4=三甲医院医疗项目专家反馈
      # ... 更多问题
```

## 🔧 配置规则

### 环境变量命名规范

- **格式**: `PRESET_Q[数字]`
- **示例**: `PRESET_Q1`, `PRESET_Q2`, `PRESET_Q10`, `PRESET_Q15`
- **编号**: 支持任意正整数，可以不连续
- **排序**: 系统会按数字大小自动排序

### 问题内容要求

- **长度**: 建议控制在50字以内，便于界面显示
- **字符**: 支持中文、英文、数字、标点符号
- **格式**: 纯文本，不支持HTML或Markdown
- **转义**: 系统会自动处理引号转义

### 配置示例

```bash
# ✅ 正确的配置
PRESET_Q1=三甲医院专家信息
PRESET_Q2=医疗项目概况查询
PRESET_Q5=医疗质量评价标准
PRESET_Q10=医疗安全风险评估

# ❌ 错误的配置
PRESET_1=问题内容           # 缺少Q
PRESET_QA=问题内容          # 编号不是数字
PRESET_Q=问题内容           # 缺少编号
```

## 🎯 使用场景

### 开发环境
- 使用 `docker-compose.yml` (直接定义环境变量)
- 便于快速修改和测试
- 配置直观，易于调试

### 生产环境
- 使用 `docker-compose.env-file.yml` + `preset-questions.env`
- 配置集中管理，便于维护
- 支持配置文件版本控制
- 敏感信息可以单独管理

### 多环境部署
- 不同环境使用不同的配置文件
- `preset-questions.dev.env` (开发环境)
- `preset-questions.prod.env` (生产环境)
- `preset-questions.test.env` (测试环境)

## 🛠️ 操作指南

### 添加新问题

1. **方式1** (配置文件):
```bash
# 编辑 frontend/preset-questions.env
echo "PRESET_Q11=新的医疗评价问题" >> frontend/preset-questions.env
```

2. **方式2** (环境变量):
```yaml
# 在 docker-compose.yml 中添加
- PRESET_Q11=新的医疗评价问题
```

3. **重启服务**:
```bash
docker-compose restart frontend
```

### 修改现有问题

1. **编辑配置文件或docker-compose.yml**
2. **重启前端服务**:
```bash
docker-compose restart frontend
```

### 删除问题

1. **删除对应的环境变量**
2. **重启服务**

### 调整问题顺序

通过修改问题编号来调整显示顺序：
```bash
# 原来的顺序
PRESET_Q1=问题A
PRESET_Q2=问题B
PRESET_Q3=问题C

# 调整后的顺序 (B放到第一位)
PRESET_Q1=问题B
PRESET_Q2=问题A  
PRESET_Q3=问题C
```

## 🔍 调试和验证

### 查看启动日志

```bash
# 查看前端容器启动日志
docker-compose logs frontend

# 实时查看日志
docker-compose logs -f frontend
```

### 验证生成的配置

```bash
# 进入容器查看生成的配置文件
docker exec hospital-atmp-frontend cat /usr/share/nginx/html/config.js

# 检查环境变量
docker exec hospital-atmp-frontend env | grep PRESET_Q
```

### 浏览器调试

打开浏览器开发者工具，在控制台中查看：
```javascript
// 查看加载的配置
console.log(window.APP_CONFIG);

// 查看预设问题
console.log(window.APP_CONFIG.presetQuestions);

// 查看问题数量
console.log(window.APP_CONFIG._meta.questionCount);
```

## 📝 最佳实践

### 1. 问题设计原则
- **简洁明了**: 问题表述清晰，避免歧义
- **用户导向**: 从用户角度设计问题
- **分类合理**: 按功能或场景分类组织
- **数量适中**: 建议5-15个问题，避免过多

### 2. 配置管理
- **版本控制**: 将配置文件纳入版本控制
- **环境隔离**: 不同环境使用不同配置
- **备份机制**: 定期备份重要配置
- **文档同步**: 配置变更及时更新文档

### 3. 测试验证
- **功能测试**: 验证问题点击和响应
- **界面测试**: 检查问题显示和布局
- **兼容测试**: 测试不同设备和浏览器
- **性能测试**: 验证大量问题的性能表现

## 🚨 故障排除

### 常见问题

1. **问题不显示**
   - 检查环境变量名是否正确 (`PRESET_Q[数字]`)
   - 查看容器启动日志
   - 验证配置文件语法

2. **问题顺序错乱**
   - 检查编号是否为纯数字
   - 确认没有重复的编号

3. **特殊字符显示异常**
   - 检查字符编码设置
   - 避免使用特殊的控制字符

4. **配置不生效**
   - 确认已重启容器
   - 检查配置文件路径
   - 验证环境变量优先级

### 日志关键字

查看日志时关注以下关键字：
- `检测到的预设问题变量`
- `总共检测到 X 个预设问题`
- `配置文件生成成功`
- `✅` 或 `❌` 状态标识

## 📚 相关文件

- `frontend/docker-entrypoint.sh` - 启动脚本和配置生成逻辑
- `frontend/preset-questions.env` - 预设问题配置文件
- `docker-compose.yml` - 主要的容器编排文件
- `docker-compose.env-file.yml` - 使用配置文件的编排文件
- `frontend/public/config.js` - 生成的运行时配置文件

---

**📞 技术支持**: 如有问题，请查看项目文档或提交Issue 