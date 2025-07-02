# 医疗评价大模型

## 项目架构

### 整体架构
```
前端(Vue3) <--> Nginx反向代理 <--> FastAPI后端 <--> LangChain <--> 向量数据库(FAISS)
                                                        ↓
                                                  大语言模型(OpenAI)
```

### 数据流


1. 对话流程:
   - 用户发送问题
   - 意图识别(医疗评价/其他)
   - 根据意图选择不同的模型
   - 结合上下文生成回答
   - 支持流式输出

## 技术栈

### 后端
- Python 3.8+
- FastAPI: Web框架
- LangChain 0.3.21: 大模型开发框架
  - langchain-openai 0.3.9: OpenAI集成  
- Pydantic: 数据验证
- Uvicorn: ASGI服务器

### 前端
- Vue 3: 前端框架 
- Vite: 构建工具
- Nginx: 反向代理
- SSE: 流式响应
- WebSocket: 语音识别

### 模型与API
- 基础模型(意图识别): qwen2.5:1.5b
- 对话模型(带思维链): deepseek-r1:1.5b
- 医疗评价模型(专用): atmp
- OpenAI API兼容格式
- 支持流式输出

## 目录结构

```
Code/
├── readme.md                # 项目说明文档
├── requirements.txt         # Python依赖包列表

├── main.py                 # 数据导入主程序入口
├── config.py               # 配置文件
└── api/                    # API服务模块
    ├── main.py            # FastAPI应用主入口
    │

    │
    ├── agents/            # 智能体模块
    │   └── base.py        # 智能体基础实现
    │   
    └── routers/           # 路由模块
        └── chat.py        # 聊天路由处理模块
```

## 核心模块说明



### 1. 智能体 (base.py)
- 意图识别:
  - 使用轻量模型快速分类
  - 支持医疗评价/其他二类
- 对话生成:
  - 支持流式输出
  - 结合检索结果和上下文
  - 支持历史对话
- 错误处理和日志

### 2. 聊天路由 (chat.py)
- OpenAI API兼容格式
- 支持流式/非流式响应
- 历史对话管理
- 错误处理

## 配置说明

### 1. 环境变量
可以通过环境变量或 `.env` 文件配置以下参数：
```bash
# API配置
OPENAI_API_KEY=your_api_key  # OpenAI API密钥
OPENAI_BASE_URL=your_api_base_url  # API基础URL

# 模型配置
MODELNAME=qwen2.5:1.5b  # 基础模型，不带思维链
MODELNAME_WITH_CHAIN=deepseek-r1:1.5b  # 带思维链模型


# 其他配置
TEMPERATURE=0.7  # 生成温度
MAX_TOKENS=4000  # 最大token数
```

### 2. 统一配置文件 (config.py)
所有配置都统一在 `config.py` 中管理，使用 pydantic 进行配置验证：

```python
class Settings(BaseSettings):
    # 应用基础配置
    PROJECT_NAME: str = "医疗评价大模型"
    API_V1_STR: str = "/api/v1"
    
    # 模型配置
    MODELNAME: str = "qwen2.5:1.5b"
    MODELNAME_WITH_CHAIN: str = "deepseek-r1:1.5b"
    TEMPERATURE: float = 0.7
    MAX_TOKENS: int = 4000
    
    class Config:
        case_sensitive = True
        env_file = ".env"
```

### 3. 配置优先级
1. 环境变量
2. .env 文件
3. 代码中的默认值



## 开发指南

### 1. 环境准备
```bash
# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux
venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt
```


### 2. 启动服务
```bash
# 开发模式
cd Code && uvicorn api.main:app --reload --port 8125

# 生产模式
cd Code && uvicorn api.main:app --host 0.0.0.0 --port 8125
```

### 3. API文档
- Swagger UI: http://localhost:8125/docs
- ReDoc: http://localhost:8125/redoc

## 部署说明

### Docker部署
1. 构建镜像:
```bash
docker build -t hospital-atmp-assistant .
```

2. 运行容器:
```bash
docker run -d \
  -p 8125:8125 \
  -v $(pwd)/data:/app/data \
  -e OPENAI_API_KEY=your_key \
  -e OPENAI_BASE_URL=your_url \
  hospital-atmp-assistant
```

### Docker Compose
```yaml
version: '3'
services:
  backend:
    build: .
    ports:
      - "8125:8125"
    volumes:
      - ./data:/app/data
    environment:
      - OPENAI_API_KEY=your_key
      - OPENAI_BASE_URL=your_url
```

## 测试

### 单元测试
```bash
pytest tests/
```



### base.py
```python
class LawAgent:
    async def get_streaming_answer(self, question: str, history: Optional[List] = None) -> AsyncGenerator:
        """获取流式回答"""
        
    async def get_answer(self, question: str, history: Optional[List] = None) -> str:
        """获取完整回答"""
```

## 变量说明

### 全局变量
```python

MODELNAME: str  # 基础模型名称
MODELNAME_WITH_CHAIN: str  # 带思维链模型名称
LAWMODEL: str  # 法律案例专用微调模型名称
TEMPERATURE: float  # 生成温度

```

### 环境变量
```bash
OPENAI_API_KEY  # OpenAI API密钥
OPENAI_BASE_URL  # OpenAI API地址
LOG_LEVEL  # 日志级别
```
