// 引用统一配置
import {
    getPresetQuestions,
    getWelcomeMessage,
    getLogoUrl,
    getIdentityPrompt,
    getModelNameDisplay,
    getWelcomeSubtitle,
    API_CONFIG
} from './settings'
import appConfig from './app.config'

// 当前配置
export const isDev = API_CONFIG.isDev

// 导出配置
export const presetQuestions = getPresetQuestions()

// 导出欢迎消息
export const welcomeMessage = getWelcomeMessage()

// 导出Logo URL
export const logoUrl = getLogoUrl()

// 导出身份提示
export const identityPrompt = getIdentityPrompt()

// 导出模型显示名称
export const modelNameDisplay = getModelNameDisplay()

// 导出欢迎语副标题
export const welcomeSubtitle = getWelcomeSubtitle()

// 导出完整应用配置（向后兼容）
export { appConfig as default } 