# 医疗评价大模型前端

基于 Vue 3 + Vite 构建的前端项目。

## 部署说明

### 构建和运行
1. 构建前端
```bash
npm install
npm run build
```

2. 构建镜像
```bash
docker build -t hospital-atmp-frontend .
```

3. 运行容器
```bash
docker run -d  --rm \
  -p 8500:80 \
  --name  hospital-atmp \
  --add-host=host.docker.internal:host-gateway \
  -e API_BASE_URL=http://host.docker.internal:8125/api \
  -e OPENAI_API_KEY=fastgpt-doZD4zQ2tDg6mcVJ0q7yNoXErFKYdn3ViBIcZfu4Apzs9DsekQRQM65nT8Q \
  -e ASR_SERVER_URL=ws://192.168.100.69:10095 \
  hospital-atmp-frontend
```

### 环境变量
- API_BASE_URL: API服务地址（必填）
  - 格式：http://host:port
  - 示例：http://api:8000
- OPENAI_API_KEY: OpenAI API 密钥（必填）
  - 用于API认证
  - 从管理后台获取
- ASR_SERVER_URL: 语音识别服务地址（可选）
  - 格式: ws://host:port
  - 默认值: ws://192.168.100.69:10095
- PRESET_Q1: 预设问题1（可选）
  - 默认值: "CAR-T细胞治疗的适应症和禁忌症有哪些？"
- PRESET_Q2: 预设问题2（可选）
  - 默认值: "基因治疗药物的质量控制要求是什么？"
- PRESET_Q3: 预设问题3（可选）
  - 默认值: "组织工程产品的临床试验设计要点有哪些？"
- WELCOME_MESSAGE: 欢迎消息（可选）
  - 默认值: "欢迎使用医疗评价大模型！我可以回答医疗评价相关的问题。"

### 使用 docker-compose
```yaml
version: '3'
name: hospital-atmp
services:
  frontend:
    build: .
    container_name: hospital-atmp-frontend
    ports:
      - "80:80"
    environment:
      - API_BASE_URL=http://host.docker.internal:8125/api
      - OPENAI_API_KEY=fastgpt-doZD4zQ2tDg6mcVJ0q7yNoXErFKYdn3ViBIcZfu4Apzs9DsekQRQM65nT8Q
      - ASR_SERVER_URL=ws://192.168.100.69:10095
      - PRESET_Q1=CAR-T细胞治疗的适应症和禁忌症有哪些？
      - PRESET_Q2=基因治疗药物的质量控制要求是什么？
      - PRESET_Q3=组织工程产品的临床试验设计要点有哪些？
      - WELCOME_MESSAGE=欢迎使用医疗评价大模型！我可以回答医疗评价相关的问题。
    extra_hosts:
      - "host.docker.internal:host-gateway"
    networks:
      - app-network

networks:
  app-network:
    name: hospital-atmp-network
    driver: bridge

运行: `docker-compose up -d`

## 说明
- 前端通过 nginx 反向代理 API 请求，无需后端配置 CORS
- API 路径为 /v1/，与 OpenAI API 格式兼容
- 支持 SSE (Server-Sent Events) 流式响应
- 支持 WebSocket 连接与语音识别功能
- API 认证通过 nginx 反向代理时自动添加 Authorization Bearer 头


