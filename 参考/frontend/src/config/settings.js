/**
 * 前端统一配置文件
 * 整合所有预设问题、欢迎消息、API配置等
 */

// 默认预设问题配置
export const DEFAULT_PRESET_QUESTIONS = {
    question1: '三甲医院专家信息',
    question2: '三甲医院ATMP项目概况',
    question3: '三甲医院ATMP项目自动化评价',
    question4: '三甲医院ATMP项目专家反馈',
    question5: 'ATMP知识库问答',
    question6: '三甲医院ATMP项目评价信息上报',
    question7: 'ATMP项目评价报告查询与下载',
    question8: 'ATMP跨主体追踪与AI比对分析',
    question9: 'ATMP跨区域追踪与AI比对分析',
    question10: 'ATMP跨时间追踪与AI比对分析'
}

// 应用基础配置
export const APP_CONFIG = {
    name: '医疗评价大模型',
    description: 'Medical Evaluation AI Model',
    version: '1.0.0'
}

// 默认欢迎消息
export const DEFAULT_WELCOME_MESSAGE = '欢迎使用医疗评价大模型！我可以回答ATMP相关的问题。'

// 默认Logo配置
export const DEFAULT_LOGO_URL = ''

// 默认模型显示名称
export const DEFAULT_MODEL_NAME_DISPLAY = '医疗评价大模型'

// 默认身份提示
export const DEFAULT_IDENTITY_PROMPT = '医疗评价AI助手'

// 默认欢迎语副标题
export const DEFAULT_WELCOME_SUBTITLE = '我是您的专业AI助手，随时可以为您服务'

// API配置
export const API_CONFIG = {
    isDev: import.meta.env.DEV || process.env.NODE_ENV === 'development',
    baseURL: import.meta.env.DEV ? 'http://localhost:8125' : '',
    endpoints: {
        chat: '/api/v1/chat/completions',
        health: '/api/v1/health'
    }
}

// 获取运行时配置的预设问题
export const getPresetQuestions = () => {
    // 优先级：window.APP_CONFIG > 环境变量 > 默认配置
    if (typeof window !== 'undefined' && window.APP_CONFIG?.presetQuestions) {
        return window.APP_CONFIG.presetQuestions
    }

    // 从环境变量获取
    const envQuestions = {}
    for (let i = 1; i <= 10; i++) {
        const envKey = `VITE_PRESET_Q${i}`
        const envValue = import.meta.env[envKey]
        if (envValue) {
            envQuestions[`question${i}`] = envValue
        }
    }

    // 合并默认配置和环境变量配置
    return { ...DEFAULT_PRESET_QUESTIONS, ...envQuestions }
}

// 获取欢迎消息
export const getWelcomeMessage = () => {
    if (typeof window !== 'undefined' && window.APP_CONFIG?.welcomeMessage) {
        return window.APP_CONFIG.welcomeMessage
    }
    return import.meta.env.VITE_WELCOME_MESSAGE || DEFAULT_WELCOME_MESSAGE
}

// 获取Logo URL
export const getLogoUrl = () => {
    if (typeof window !== 'undefined' && window.APP_CONFIG?.logoUrl) {
        return window.APP_CONFIG.logoUrl
    }
    return import.meta.env.VITE_LOGO_URL || DEFAULT_LOGO_URL
}

// 获取身份提示
export const getIdentityPrompt = () => {
    if (typeof window !== 'undefined' && window.APP_CONFIG?.identityPrompt) {
        return window.APP_CONFIG.identityPrompt
    }
    return import.meta.env.VITE_IDENTITY_PROMPT || DEFAULT_IDENTITY_PROMPT
}

// 获取模型显示名称
export const getModelNameDisplay = () => {
    if (typeof window !== 'undefined' && window.APP_CONFIG?.modelNameDisplay) {
        return window.APP_CONFIG.modelNameDisplay
    }
    return import.meta.env.VITE_MODEL_NAME_DISPLAY || DEFAULT_MODEL_NAME_DISPLAY
}

// 获取欢迎语副标题
export const getWelcomeSubtitle = () => {
    if (typeof window !== 'undefined' && window.APP_CONFIG?.welcomeSubtitle) {
        return window.APP_CONFIG.welcomeSubtitle
    }
    return import.meta.env.VITE_WELCOME_SUBTITLE || DEFAULT_WELCOME_SUBTITLE
}

// 获取完整的应用配置
export const getAppConfig = () => {
    return {
        ...APP_CONFIG,
        presetQuestions: getPresetQuestions(),
        welcomeMessage: getWelcomeMessage(),
        logoUrl: getLogoUrl(),
        identityPrompt: getIdentityPrompt(),
        modelNameDisplay: getModelNameDisplay(),
        welcomeSubtitle: getWelcomeSubtitle(),
        api: API_CONFIG
    }
}

// 生成动态欢迎消息（包含预设问题）
export const generateWelcomeMessage = () => {
    const welcomeMsg = getWelcomeMessage()
    const questions = getPresetQuestions()

    // 动态生成问题列表，添加序号和正确排序
    const questionEntries = Object.entries(questions)
        .filter(([key, value]) => key.startsWith('question') && value && value.trim())
        .sort(([a], [b]) => {
            // 按问题编号排序 (question1, question2, ...)
            const numA = parseInt(a.replace('question', ''))
            const numB = parseInt(b.replace('question', ''))
            return numA - numB
        })

    // 如果没有预设问题，只返回欢迎消息
    if (questionEntries.length === 0) {
        return welcomeMsg
    }

    // 生成带序号的可点击问题列表，每个问题单独一行
    const questionList = questionEntries
        .map(([key, value], index) => `${index + 1}、[${value}](#${key})`)
        .join('\n\n') // 使用双换行符确保每个问题单独一行

    return `${welcomeMsg}

您可以点击以下问题快速开始：

${questionList}

或者直接输入您感兴趣的问题。`
}

// 导出默认配置对象（向后兼容）
export default {
    app: APP_CONFIG,
    presetQuestions: getPresetQuestions(),
    welcomeMessage: getWelcomeMessage(),
    logoUrl: getLogoUrl(),
    identityPrompt: getIdentityPrompt(),
    modelNameDisplay: getModelNameDisplay(),
    welcomeSubtitle: getWelcomeSubtitle(),
    api: API_CONFIG
} 