// 引用统一配置
import { getAppConfig, getPresetQuestions, getWelcomeMessage } from './settings'

// 获取配置
const presetQuestions = getPresetQuestions()
const welcomeMessage = getWelcomeMessage()

// 默认配置（向后兼容）
export default {
    // 应用配置
    app: {
        name: '医疗评价大模型',
    },

    presetQuestions,
    welcomeMessage
} 