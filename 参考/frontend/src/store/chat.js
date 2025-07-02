import { defineStore } from 'pinia'
import { generateWelcomeMessage, API_CONFIG } from '../config/settings'
import { welcomeMessage } from '../config'

export const useChatStore = defineStore('chat', {
    state: () => ({
        messages: [{
            id: 0,
            role: 'assistant',
            content: generateWelcomeMessage()
        }],
        loading: false,
        currentStreamingMessage: null
    }),

    actions: {
        async init() {

        },

        async checkQueueStatus() {
            return true
        },

        // 移除思维链内容
        removeThinkContent(content) {
            if (!content) return content;
            return content.replace(/<think>[\s\S]*?<\/think>/g, '').trim();
        },

        // 获取最近的历史记录
        getRecentHistory() {
            // 获取除了欢迎消息和当前问题外的最近3条消息
            return this.messages
                .slice(1) // 跳过欢迎消息
                .slice(-6) // 获取最近6条消息(3轮对话)
                .map(msg => ({
                    role: msg.role,
                    content: msg.role === 'assistant' ? this.removeThinkContent(msg.content) : msg.content
                }));
        },

        // 添加消息到聊天记录
        addMessage(message) {
            this.messages.push({
                ...message,
                timestamp: message.timestamp || new Date().toISOString()
            })
        },

        // 发送消息
        async sendMessage(content) {
            try {
                this.loading = true

                // 添加用户消息
                const userMessage = {
                    role: 'user',
                    content,
                    timestamp: new Date().toISOString()
                }
                this.addMessage(userMessage)

                // 添加助手消息占位符
                const assistantMessage = {
                    role: 'assistant',
                    content: '',
                    timestamp: new Date().toISOString(),
                    isLoading: true
                }
                this.addMessage(assistantMessage)

                // 准备请求数据
                const requestData = {
                    model: 'qwen2.5',
                    messages: this.messages
                        .filter(msg => !msg.isLoading && msg.role !== 'system')
                        .map(msg => ({
                            role: msg.role,
                            content: msg.content
                        })),
                    stream: true
                }

                // 发送流式请求
                const response = await fetch('/api/v1/chat/completions', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(requestData)
                })

                if (!response.ok) {
                    const errorData = await response.json()
                    throw new Error(errorData.detail || '请求失败')
                }

                const reader = response.body.getReader()
                const decoder = new TextDecoder()
                let responseContent = '' // 修复：重命名变量避免与参数冲突

                // 获取最后一条消息（助手消息）
                const lastMessage = this.messages[this.messages.length - 1]

                while (true) {
                    const { done, value } = await reader.read()

                    if (done) break

                    const chunk = decoder.decode(value)
                    const lines = chunk.split('\n')

                    for (const line of lines) {
                        if (line.startsWith('data: ')) {
                            const data = line.slice(6).trim()

                            if (data === '[DONE]') {
                                lastMessage.isLoading = false
                                return
                            }

                            try {
                                const parsed = JSON.parse(data)

                                if (parsed.error) {
                                    throw new Error(parsed.error.message)
                                }

                                if (parsed.choices?.[0]?.delta?.content) {
                                    responseContent += parsed.choices[0].delta.content
                                    lastMessage.content = responseContent
                                }
                            } catch (parseError) {
                                console.warn('解析SSE数据失败:', parseError)
                            }
                        }
                    }
                }

                lastMessage.isLoading = false
            } catch (error) {
                console.error('发送消息失败:', error)

                // 移除加载中的消息
                const loadingIndex = this.messages.findIndex(msg => msg.isLoading)
                if (loadingIndex !== -1) {
                    this.messages.splice(loadingIndex, 1)
                }

                // 添加错误消息
                this.addMessage({
                    role: 'assistant',
                    content: `抱歉，发生了错误：${error.message}`,
                    timestamp: new Date().toISOString(),
                    isError: true
                })

                throw error
            } finally {
                this.loading = false
            }
        },

        // 发送带文档附件的消息
        async sendMessageWithAttachments(content, documents = []) {
            try {
                this.loading = true

                // 构建用户消息内容
                let userContent = content || ''
                if (documents.length > 0) {
                    const docNames = documents.map(doc => doc.name).join(', ')
                    if (userContent) {
                        userContent += `\n\n📎 附件文档: ${docNames}`
                    } else {
                        userContent = `📎 附件文档: ${docNames}`
                    }
                }

                // 添加用户消息
                const userMessage = {
                    role: 'user',
                    content: userContent,
                    timestamp: new Date().toISOString(),
                    hasAttachments: documents.length > 0,
                    attachments: documents.map(doc => ({
                        name: doc.name,
                        size: doc.size,
                        type: doc.type
                    }))
                }
                this.addMessage(userMessage)

                // 如果有文档附件，需要先处理文档
                if (documents.length > 0) {
                    // 添加处理状态消息
                    const processingMessage = {
                        role: 'assistant',
                        content: '📄 正在分析文档内容，请稍等...',
                        timestamp: new Date().toISOString(),
                        isProcessing: true
                    }
                    this.addMessage(processingMessage)

                    // 创建FormData发送文档和消息
                    const formData = new FormData()

                    // 添加文档文件
                    documents.forEach((doc, index) => {
                        formData.append(`files`, doc.file)
                    })

                    // 添加用户问题
                    formData.append('message', content || '')

                    // 添加历史消息上下文
                    const recentHistory = this.getRecentHistory()
                    formData.append('history', JSON.stringify(recentHistory))

                    // 发送到新的文档处理接口
                    const response = await fetch('/api/v1/chat-with-documents', {
                        method: 'POST',
                        body: formData
                    })

                    if (!response.ok) {
                        const errorData = await response.json()
                        throw new Error(errorData.detail || '文档处理失败')
                    }

                    // 移除处理状态消息
                    const processingIndex = this.messages.findIndex(msg => msg.isProcessing)
                    if (processingIndex !== -1) {
                        this.messages.splice(processingIndex, 1)
                    }

                    // 处理流式响应
                    const reader = response.body.getReader()
                    const decoder = new TextDecoder()
                    let responseContent = ''

                    // 添加助手消息占位符
                    const assistantMessage = {
                        role: 'assistant',
                        content: '',
                        timestamp: new Date().toISOString(),
                        isLoading: true,
                        hasDocumentContext: true
                    }
                    this.addMessage(assistantMessage)

                    // 获取最后一条消息（助手消息）
                    const lastMessage = this.messages[this.messages.length - 1]

                    while (true) {
                        const { done, value } = await reader.read()

                        if (done) break

                        const chunk = decoder.decode(value)
                        const lines = chunk.split('\n')

                        for (const line of lines) {
                            if (line.startsWith('data: ')) {
                                const data = line.slice(6).trim()

                                if (data === '[DONE]') {
                                    lastMessage.isLoading = false
                                    return
                                }

                                try {
                                    const parsed = JSON.parse(data)

                                    if (parsed.error) {
                                        throw new Error(parsed.error.message)
                                    }

                                    if (parsed.choices?.[0]?.delta?.content) {
                                        responseContent += parsed.choices[0].delta.content
                                        lastMessage.content = responseContent
                                    }
                                } catch (parseError) {
                                    console.warn('解析SSE数据失败:', parseError)
                                }
                            }
                        }
                    }

                    lastMessage.isLoading = false
                } else {
                    // 没有文档附件，使用原有的发送逻辑
                    await this.sendMessage(content)
                }

            } catch (error) {
                console.error('发送带附件消息失败:', error)

                // 移除加载中的消息
                const loadingIndex = this.messages.findIndex(msg => msg.isLoading || msg.isProcessing)
                if (loadingIndex !== -1) {
                    this.messages.splice(loadingIndex, 1)
                }

                // 添加错误消息
                this.addMessage({
                    role: 'assistant',
                    content: `抱歉，处理您的请求时发生了错误：${error.message}`,
                    timestamp: new Date().toISOString(),
                    isError: true
                })

                throw error
            } finally {
                this.loading = false
            }
        },

        // 添加预设问题处理方法
        async handlePresetQuestion(question) {
            console.log('handlePresetQuestion', question)

            // 检查是否是第7个问题：ATMP项目评价报告查询与下载
            if (question.includes('ATMP项目评价报告查询与下载') || question.includes('报告查询与下载')) {
                // 添加用户消息
                const userMessageId = Date.now()
                this.messages.push({
                    id: userMessageId,
                    role: 'user',
                    content: question,
                    timestamp: new Date()
                })

                // 添加包含下载链接的AI回复
                const aiMessageId = Date.now() + 1
                const downloadResponse = `## 📋 ATMP项目评价报告下载

以下是可供下载的项目评价报告：

---

### 📄 阿尔茨海默病治疗仪器项目初评估
[📥 点击下载报告](./阿尔茨海默病治疗仪器项目初评估.pdf)

### 📄 上消化道癌症AI筛查项目初评估  
[📥 点击下载报告](./上消化道癌症AI筛查项目初评估.pdf)

### 📄 胸腺疫苗(AYP-003)项目初评估
[📥 点击下载报告](./胸腺疫苗(AYP-003)项目初评估.pdf)

---

💡 **说明：** 点击上方链接可直接下载对应的项目评价报告PDF文件。`

                this.messages.push({
                    id: aiMessageId,
                    role: 'assistant',
                    content: downloadResponse,
                    timestamp: new Date(),
                    hasDownloadLinks: true // 标记这条消息包含下载链接
                })
                return
            }

            // 其他问题正常发送到后端处理
            await this.sendMessage(question)
        },

        // 清空聊天记录
        clearMessages() {
            this.messages = [
                {
                    role: 'assistant',
                    content: welcomeMessage,
                    timestamp: new Date().toISOString()
                }
            ]
        }
    }
}) 