<template>
  <div class="message-bubble" :class="{ 'is-user': message.role === 'user' }">
    <!-- AI头像放在左边 -->
    <div v-if="message.role === 'assistant'" class="avatar ai-avatar">
      <div class="avatar-gradient">
        <svg viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
          <circle cx="50" cy="50" r="45" fill="none" stroke="currentColor" stroke-width="6" />
          <circle cx="35" cy="40" r="6" fill="currentColor" />
          <circle cx="65" cy="40" r="6" fill="currentColor" />
          <path d="M 30 65 Q 50 80 70 65" fill="none" stroke="currentColor" stroke-width="6" stroke-linecap="round" />
        </svg>
      </div>
    </div>

    <!-- 用户头像放在右边 -->
    <div v-else class="avatar user-avatar">
      <div class="avatar-gradient">
        <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
          <path d="M20 21V19A4 4 0 0 0 16 15H8A4 4 0 0 0 4 19V21" stroke="currentColor" stroke-width="2"
            stroke-linecap="round" stroke-linejoin="round" />
          <circle cx="12" cy="7" r="4" stroke="currentColor" stroke-width="2" />
        </svg>
      </div>
    </div>

    <div class="message-content">
      <div class="message-card">
        <div class="text" v-if="message.role === 'assistant'" @click="handleLinkClick">
          <!-- 思考中状态 -->
          <div v-if="isThinking" class="thinking-status">
            <div class="thinking-icon">
              <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M9.09 9A3 3 0 0 1 15 9M21 12A9 9 0 1 1 3 12A9 9 0 0 1 21 12Z" stroke="currentColor"
                  stroke-width="2" stroke-linecap="round" stroke-linejoin="round" />
                <path d="M8 15H8.01M12 15H12.01M16 15H16.01" stroke="currentColor" stroke-width="2"
                  stroke-linecap="round" stroke-linejoin="round" />
              </svg>
            </div>
            <span>深度思考中...</span>
          </div>

          <!-- 思维链部分 -->
          <div v-if="hasThinkContent" class="think-chain">
            <div class="think-header" @click.stop="toggleThinkChain">
              <div class="think-icon">
                <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                  <path d="M9 18L15 12L9 6" stroke="currentColor" stroke-width="2" stroke-linecap="round"
                    stroke-linejoin="round" :class="{ 'rotated': showThinkChain }" />
                </svg>
              </div>
              <span>思维链</span>
              <div class="expand-hint">{{ showThinkChain ? '收起' : '展开' }}</div>
            </div>
            <div v-show="showThinkChain" class="think-content" v-html="thinkContent"></div>
          </div>

          <!-- 最终回答部分 -->
          <div class="final-answer" v-html="finalContent"></div>

          <!-- 相关文件列表 -->
          <div v-if="hasFiles" class="files-section">
            <div class="files-header">
              <div class="files-icon">
                <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                  <path d="M14 2H6A2 2 0 0 0 4 4V20A2 2 0 0 0 6 22H18A2 2 0 0 0 20 20V8L14 2Z" stroke="currentColor"
                    stroke-width="2" stroke-linecap="round" stroke-linejoin="round" />
                  <polyline points="14,2 14,8 20,8" stroke="currentColor" stroke-width="2" stroke-linecap="round"
                    stroke-linejoin="round" />
                </svg>
              </div>
              <span>相关政策文件</span>
            </div>
            <div class="files-list">
              <div v-for="file in files" :key="file" class="file-item" @click="handleFileClick(file)">
                <div class="file-icon">
                  <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <path d="M14 2H6A2 2 0 0 0 4 4V20A2 2 0 0 0 6 22H18A2 2 0 0 0 20 20V8L14 2Z" stroke="currentColor"
                      stroke-width="2" stroke-linecap="round" stroke-linejoin="round" />
                    <polyline points="14,2 14,8 20,8" stroke="currentColor" stroke-width="2" stroke-linecap="round"
                      stroke-linejoin="round" />
                  </svg>
                </div>
                <span class="file-name">{{ file }}</span>
                <div class="view-icon">
                  <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <path d="M1 12S5 4 12 4S23 12 23 12S19 20 12 20S1 12 1 12Z" stroke="currentColor" stroke-width="2"
                      stroke-linecap="round" stroke-linejoin="round" />
                    <circle cx="12" cy="12" r="3" stroke="currentColor" stroke-width="2" />
                  </svg>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div class="text user-text" v-else>
          <!-- 解析并显示文本和图片 -->
          <div v-if="parsedUserMessage.text" class="user-message-text">
            {{ parsedUserMessage.text }}
          </div>
          <div v-if="parsedUserMessage.images.length > 0" class="user-message-images">
            <!-- 图片数量提示 -->
            <div v-if="parsedUserMessage.images.length > 1" class="images-count-tip">
              <span>📷 {{ parsedUserMessage.images.length }} 张图片</span>
            </div>
            
            <!-- 图片缩略图列表 -->
            <div class="images-grid">
              <div 
                v-for="(imageUrl, index) in parsedUserMessage.images" 
                :key="index" 
                class="user-image-item"
                @click="handleImagePreview(imageUrl)"
              >
                <img 
                  :src="imageUrl" 
                  :alt="`用户上传图片 ${index + 1}`" 
                  class="user-image"
                  @error="handleImageError($event, index)"
                  @load="handleImageLoad($event, index)"
                />
                <div class="image-index">{{ index + 1 }}</div>
              </div>
            </div>
          </div>
        </div>

        <!-- 操作按钮 -->
        <div v-if="message.role === 'assistant'" class="message-actions">
          <button class="action-btn" @click="handleCopy" title="复制内容">
            <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
              <rect x="9" y="9" width="13" height="13" rx="2" ry="2" stroke="currentColor" stroke-width="2" />
              <path d="M5 15H4A2 2 0 0 1 2 13V4A2 2 0 0 1 4 2H13A2 2 0 0 1 15 4V5" stroke="currentColor"
                stroke-width="2" />
            </svg>
          </button>
        </div>
      </div>

      <div class="time" v-if="message.timestamp">{{ formattedTime }}</div>
    </div>
  </div>

  <!-- 文件内容对话框 -->
  <van-dialog v-model:show="showFileContent" :title="currentFileName" class="file-content-dialog" width="90%"
    :show-confirm-button="false">
    <template #title>
      <div class="dialog-header">
        <span>{{ currentFileName }}</span>
        <van-icon name="cross" class="close-icon" @click="showFileContent = false" />
      </div>
    </template>
    <div class="file-content" v-if="fileContent">
      <pre>{{ fileContent }}</pre>
    </div>
    <div v-else class="loading-content">
      <div class="loading-spinner">
        <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
          <path d="M21 12A9 9 0 1 1 12 3" stroke="currentColor" stroke-width="2" stroke-linecap="round"
            stroke-linejoin="round" />
        </svg>
      </div>
      <span>加载中...</span>
    </div>
  </van-dialog>

  <!-- 图片预览对话框 -->
  <van-dialog v-model:show="showImagePreview" class="image-preview-dialog" width="95%" :show-confirm-button="false">
    <template #title>
      <div class="dialog-header">
        <span>图片预览</span>
        <van-icon name="cross" class="close-icon" @click="showImagePreview = false" />
      </div>
    </template>
    <div class="image-preview-content">
      <img :src="previewImageUrl" alt="预览图片" class="preview-full-image" />
    </div>
  </van-dialog>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { showToast, Dialog } from 'vant'
import moment from 'moment'
import MarkdownIt from 'markdown-it'
import { useChatStore } from '../store/chat'
import { presetQuestions } from '../config'
import axios from 'axios'
import { isDev } from '../config'

const chatStore = useChatStore()
const md = new MarkdownIt()
const showThinkChain = ref(false)

const props = defineProps({
  message: {
    type: Object,
    required: true
  }
})

// 处理链接点击
const handleLinkClick = (e) => {
  if (e.target.tagName === 'A') {
    // 检查是否是下载链接
    if (e.target.href && e.target.href.includes('.pdf')) {
      // 下载链接，不阻止默认行为，让浏览器处理下载
      console.log('点击下载链接:', e.target.href);
      return;
    }

    // 检查是否点击了预设问题链接
    if (e.target.hash) {
      e.preventDefault();
      const questionId = e.target.hash.substring(1); // 移除 # 符号

      // 从统一配置获取所有问题
      const allQuestions = window.APP_CONFIG?.presetQuestions || presetQuestions;

      // 获取问题内容
      const question = allQuestions[questionId];
      if (question) {
        chatStore.handlePresetQuestion(question);
      }
    }
  }
}

// 解析思维链内容
const parseThinkContent = (content) => {
  const thinkMatch = content.match(/<think>([\s\S]*?)<\/think>/)
  if (thinkMatch) {
    return {
      thinkContent: thinkMatch[1].trim(),
      finalContent: content.replace(/<think>[\s\S]*?<\/think>/, '').trim()
    }
  }
  return {
    thinkContent: '',
    finalContent: content
  }
}

const isThinking = computed(() => {
  if (!props.message.content) return false
  return props.message.content.includes('<think>') && !props.message.content.includes('</think>')
})

const hasThinkContent = computed(() => {
  const { thinkContent } = parseThinkContent(props.message.content || '')
  return !!thinkContent
})

const thinkContent = computed(() => {
  const { thinkContent } = parseThinkContent(props.message.content || '')
  return md.render(thinkContent)
})

// 解析文件列表
const parseFiles = (content) => {
  const fileMatch = content.match(/<file>(.*?)<\/file>/)
  if (fileMatch) {
    // 去除空格并过滤空字符串
    return fileMatch[1].split(',')
      .map(f => f.trim())
      .filter(f => f)
  }
  return []
}

// 是否有文件
const hasFiles = computed(() => {
  return files.value.length > 0
})

// 文件列表
const files = computed(() => {
  if (!props.message.content) return []
  const { finalContent } = parseThinkContent(props.message.content || '')
  console.log('解析文件列表:', {
    content: props.message.content,
    finalContent,
    files: parseFiles(finalContent)
  })
  return parseFiles(finalContent)
})

const toggleThinkChain = () => {
  showThinkChain.value = !showThinkChain.value
}

// 格式化时间
const formattedTime = computed(() => {
  if (!props.message.timestamp) return ''
  return moment(props.message.timestamp).format('HH:mm')
})

const handleCopy = async () => {
  try {
    await navigator.clipboard.writeText(props.message.content)
    showToast('复制成功')
  } catch (error) {
    console.error('复制失败:', error)
    showToast('复制失败')
  }
}

// 添加文件内容相关的状态
const showFileContent = ref(false)
const fileContent = ref('')
const currentFileName = ref('')

// 图片预览相关
const showImagePreview = ref(false)
const previewImageUrl = ref('')

// 解析用户消息中的文本和图片
const parsedUserMessage = computed(() => {
  if (props.message.role !== 'user' || !props.message.content) {
    return { text: '', images: [] }
  }
  
  const content = props.message.content
  
  // 查找图片部分 - 支持多种格式
  const imageMatch = content.match(/图片:\n(.*?)(?=\n\n|$)/s)
  let text = content
  let images = []
  
  if (imageMatch) {
    // 提取图片URLs，过滤空行和无效URL
    const imageUrls = imageMatch[1].split('\n')
      .map(url => url.trim())
      .filter(url => url && (url.startsWith('http') || url.startsWith('/api/v1/files/')))
    images = imageUrls
    
    // 移除图片部分，保留文本
    text = content.replace(/\n\n图片:\n.*$/s, '').trim()
  }
  
  // 如果没有找到"图片:"格式，尝试查找直接的图片URL
  if (images.length === 0) {
    const urlPattern = /(https?:\/\/[^\s]+\.(jpg|jpeg|png|gif|bmp|webp)|\/api\/v1\/files\/[^\s]+)/gi
    const urlMatches = content.match(urlPattern)
    if (urlMatches) {
      images = urlMatches
      // 从文本中移除图片URL
      text = content.replace(urlPattern, '').replace(/\s+/g, ' ').trim()
    }
  }
  
  return { text, images }
})

// 图片预览处理
const handleImagePreview = (imageUrl) => {
  previewImageUrl.value = imageUrl
  showImagePreview.value = true
}

// 图片加载错误处理
const handleImageError = (event, index) => {
  console.error(`图片加载失败 (${index + 1}):`, event.target.src)
  // 可以在这里添加重试逻辑或显示默认图片
  event.target.style.opacity = '0.5'
  event.target.style.filter = 'grayscale(100%)'
}

// 图片加载成功处理
const handleImageLoad = (event, index) => {
  console.log(`图片加载成功 (${index + 1}):`, event.target.src)
  event.target.style.opacity = '1'
  event.target.style.filter = 'none'
}

// 修改文件点击处理函数
const handleFileClick = async (filename) => {
  try {
    currentFileName.value = filename
    showFileContent.value = true
    fileContent.value = ''  // 清空之前的内容

    // 获取文件ID (从文件名中提取)
    const fileId = filename.replace('.txt', '')

    // 发起请求获取文件内容
    const response = await axios({
      url: isDev ?
        `http://localhost:8000/v1/files/${fileId}/content` :
        `/v1/files/${fileId}/content`,
      method: 'GET'
    })

    if (response.data.status === 'success') {
      fileContent.value = response.data.data
    } else {
      showToast('获取文件内容失败')
    }
  } catch (error) {
    console.error('获取文件内容失败:', error)
    if (error.response?.status === 404) {
      showToast('文件不存在')
    } else {
      showToast('获取文件内容失败')
    }
    showFileContent.value = false
  }
}

// 修改finalContent计算属性
const finalContent = computed(() => {
  if (props.message.thinking) {
    return 'AI正在思考...'
  }
  const { finalContent } = parseThinkContent(props.message.content || '')
  // 先移除file标签，再渲染markdown
  return md.render(finalContent.replace(/<file>.*?<\/file>/g, ''))
})

const messageElement = ref(null)

onMounted(() => {
  // 添加事件监听器
  if (messageElement.value) {
    messageElement.value.addEventListener('click', handleLinkClick);
  }
});

onUnmounted(() => {
  // 移除事件监听器
  if (messageElement.value) {
    messageElement.value.removeEventListener('click', handleLinkClick);
  }
});
</script>

<style lang="scss" scoped>
.message-bubble {
  display: flex;
  margin-bottom: 24px;
  align-items: flex-start;
  gap: 16px;
  animation: fadeInUp 0.3s ease-out;

  &.is-user {
    flex-direction: row-reverse;

    .message-card {
      background: linear-gradient(135deg, #667eea, #764ba2);
      color: white;

      .user-text {
        color: white;
      }
    }
  }
}

.avatar {
  width: 48px;
  height: 48px;
  border-radius: 50%;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);

  .avatar-gradient {
    width: 100%;
    height: 100%;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    position: relative;
    overflow: hidden;
  }

  &.ai-avatar .avatar-gradient {
    background: linear-gradient(135deg, #667eea, #764ba2);
    color: white;
  }

  &.user-avatar .avatar-gradient {
    background: linear-gradient(135deg, #48bb78, #38a169);
    color: white;
  }

  svg {
    width: 24px;
    height: 24px;
    z-index: 1;
  }
}

.message-content {
  flex: 1;
  max-width: calc(100% - 80px);
  position: relative;
}

.message-card {
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(10px);
  border-radius: 20px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
  border: 1px solid rgba(255, 255, 255, 0.2);
  overflow: hidden;
  position: relative;
  transition: all 0.3s ease;

  &:hover {
    box-shadow: 0 8px 30px rgba(0, 0, 0, 0.12);
    transform: translateY(-1px);
  }
}

.text {
  padding: 20px 24px;
  word-wrap: break-word;
  line-height: 1.6;
  font-size: 15px;
  color: #2d3748;
}

.user-text {
  color: #2d3748;
  font-weight: 500;
}

.thinking-status {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px 20px;
  background: rgba(102, 126, 234, 0.05);
  border-radius: 12px;
  margin-bottom: 16px;
  border: 1px solid rgba(102, 126, 234, 0.1);

  .thinking-icon {
    width: 24px;
    height: 24px;
    color: #667eea;
    animation: pulse 2s infinite;

    svg {
      width: 100%;
      height: 100%;
    }
  }

  span {
    color: #667eea;
    font-weight: 500;
    font-size: 14px;
  }
}

.think-chain {
  margin-bottom: 20px;
  border: 1px solid rgba(102, 126, 234, 0.2);
  border-radius: 12px;
  overflow: hidden;
  background: rgba(102, 126, 234, 0.02);

  .think-header {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 12px 16px;
    background: rgba(102, 126, 234, 0.05);
    cursor: pointer;
    transition: all 0.2s ease;
    border-bottom: 1px solid rgba(102, 126, 234, 0.1);

    &:hover {
      background: rgba(102, 126, 234, 0.08);
    }

    .think-icon {
      width: 20px;
      height: 20px;
      color: #667eea;
      transition: transform 0.2s ease;

      svg path.rotated {
        transform: rotate(90deg);
        transform-origin: center;
      }
    }

    span {
      font-weight: 600;
      color: #667eea;
      font-size: 14px;
    }

    .expand-hint {
      margin-left: auto;
      font-size: 12px;
      color: #718096;
      font-weight: 400;
    }
  }

  .think-content {
    padding: 16px;
    background: rgba(255, 255, 255, 0.5);
    font-size: 14px;
    line-height: 1.5;
    color: #4a5568;
    animation: fadeIn 0.3s ease;
  }
}

.final-answer {
  font-size: 15px;
  line-height: 1.6;
  color: #2d3748;
}

.time {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.7);
  margin-top: 8px;
  text-align: right;
  font-weight: 400;

  .is-user & {
    text-align: left;
  }
}

.files-section {
  margin-top: 20px;
  border-top: 1px solid rgba(0, 0, 0, 0.05);
  padding-top: 16px;

  .files-header {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 12px;

    .files-icon {
      width: 20px;
      height: 20px;
      color: #667eea;

      svg {
        width: 100%;
        height: 100%;
      }
    }

    span {
      font-weight: 600;
      color: #2d3748;
      font-size: 14px;
    }
  }

  .files-list {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .file-item {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 12px 16px;
    background: rgba(102, 126, 234, 0.03);
    border: 1px solid rgba(102, 126, 234, 0.1);
    border-radius: 10px;
    cursor: pointer;
    transition: all 0.2s ease;

    &:hover {
      background: rgba(102, 126, 234, 0.08);
      border-color: rgba(102, 126, 234, 0.2);
      transform: translateX(4px);
    }

    .file-icon {
      width: 20px;
      height: 20px;
      color: #667eea;
      flex-shrink: 0;

      svg {
        width: 100%;
        height: 100%;
      }
    }

    .file-name {
      flex: 1;
      font-size: 14px;
      color: #4a5568;
      font-weight: 500;
    }

    .view-icon {
      width: 18px;
      height: 18px;
      color: #718096;
      opacity: 0.6;
      transition: opacity 0.2s ease;

      svg {
        width: 100%;
        height: 100%;
      }
    }

    &:hover .view-icon {
      opacity: 1;
    }
  }
}

.message-actions {
  display: flex;
  justify-content: flex-end;
  padding: 12px 16px;
  border-top: 1px solid rgba(0, 0, 0, 0.05);
  background: rgba(0, 0, 0, 0.01);

  .action-btn {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 32px;
    height: 32px;
    border: none;
    background: rgba(102, 126, 234, 0.1);
    border-radius: 8px;
    cursor: pointer;
    transition: all 0.2s ease;
    color: #667eea;

    &:hover {
      background: rgba(102, 126, 234, 0.2);
      transform: scale(1.05);
    }

    svg {
      width: 16px;
      height: 16px;
    }
  }
}

// 文件对话框样式
.file-content-dialog {
  .dialog-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 16px 20px;
    border-bottom: 1px solid rgba(0, 0, 0, 0.1);

    span {
      font-weight: 600;
      color: #2d3748;
    }

    .close-icon {
      cursor: pointer;
      color: #718096;
      font-size: 20px;

      &:hover {
        color: #4a5568;
      }
    }
  }

  .file-content {
    padding: 20px;
    max-height: 60vh;
    overflow-y: auto;

    pre {
      background: #f8f9fa;
      border-radius: 8px;
      padding: 16px;
      font-size: 13px;
      line-height: 1.5;
      color: #2d3748;
      white-space: pre-wrap;
      word-wrap: break-word;
    }
  }

  .loading-content {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 12px;
    padding: 40px 20px;
    color: #718096;

    .loading-spinner {
      width: 20px;
      height: 20px;
      animation: spin 1s linear infinite;

      svg {
        width: 100%;
        height: 100%;
      }
    }

    span {
      font-size: 14px;
    }
  }
}

// 深色模式适配
.text :deep(pre) {
  margin: 16px 0;
  padding: 16px;
  border-radius: 8px;
  background: #1a1a1a;
  color: #fff;
  overflow-x: auto;
  font-family: Monaco, Consolas, Courier New, monospace;
  font-size: 13px;
  line-height: 1.5;
}

.text :deep(code) {
  font-family: Monaco, Consolas, Courier New, monospace;
  font-size: 0.9em;
  background: rgba(102, 126, 234, 0.1);
  padding: 2px 6px;
  border-radius: 4px;
  color: #667eea;
}

.text :deep(a) {
  color: #667eea;
  text-decoration: none;
  cursor: pointer;
  font-weight: 500;

  &:hover {
    text-decoration: underline;
  }

  // 下载链接特殊样式
  &[href*=".pdf"] {
    display: inline-flex;
    align-items: center;
    gap: 10px;
    padding: 12px 20px;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white !important;
    border-radius: 12px;
    font-weight: 600;
    text-decoration: none;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    margin: 8px 0;
    font-size: 14px;
    box-shadow: 0 4px 15px rgba(102, 126, 234, 0.25);
    border: 1px solid rgba(255, 255, 255, 0.1);
    position: relative;
    overflow: hidden;

    &::before {
      content: "";
      position: absolute;
      top: 0;
      left: -100%;
      width: 100%;
      height: 100%;
      background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.2), transparent);
      transition: left 0.6s;
    }

    &:hover {
      background: linear-gradient(135deg, #5a67d8 0%, #6b46c1 100%);
      transform: translateY(-2px);
      box-shadow: 0 8px 25px rgba(102, 126, 234, 0.35);
      text-decoration: none;

      &::before {
        left: 100%;
      }
    }

    &:active {
      transform: translateY(-1px);
      box-shadow: 0 6px 20px rgba(102, 126, 234, 0.3);
    }

    // 下载图标效果
    &::after {
      content: "📥";
      font-size: 16px;
      filter: drop-shadow(0 1px 2px rgba(0, 0, 0, 0.1));
    }
  }
}

// 下载区域美化
.text :deep(h2) {
  color: #2d3748;
  border-bottom: 2px solid #667eea;
  padding-bottom: 8px;
  margin-bottom: 20px;
  font-size: 18px;
  font-weight: 700;
}

.text :deep(h3) {
  color: #4a5568;
  margin: 16px 0 8px 0;
  font-size: 16px;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 8px;
}

.text :deep(hr) {
  border: none;
  height: 1px;
  background: linear-gradient(90deg, transparent, #e2e8f0, transparent);
  margin: 20px 0;
}

@keyframes fadeInUp {
  from {
    opacity: 0;
    transform: translateY(20px);
  }

  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes fadeIn {
  from {
    opacity: 0;
  }

  to {
    opacity: 1;
  }
}

@keyframes pulse {

  0%,
  100% {
    opacity: 1;
  }

  50% {
    opacity: 0.5;
  }
}

@keyframes spin {
  from {
    transform: rotate(0deg);
  }

  to {
    transform: rotate(360deg);
  }
}

// 用户消息图片样式
.user-message-images {
  margin-top: 12px;
  padding: 8px 0;
}

.images-count-tip {
  margin-bottom: 8px;
  
  span {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    padding: 4px 8px;
    background: rgba(102, 126, 234, 0.1);
    border-radius: 12px;
    font-size: 12px;
    color: #667eea;
    font-weight: 500;
  }
}

.images-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}

.user-image-item {
  position: relative;
  border-radius: 12px;
  overflow: hidden;
  cursor: pointer;
  transition: all 0.3s ease;
  border: 2px solid rgba(102, 126, 234, 0.1);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  background: #f8f9fa;
  
  &:hover {
    transform: scale(1.05) translateY(-2px);
    border-color: rgba(102, 126, 234, 0.4);
    box-shadow: 0 8px 25px rgba(102, 126, 234, 0.2);
  }
  
  // 添加图片加载状态
  &::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: linear-gradient(45deg, #f0f0f0 25%, transparent 25%, transparent 75%, #f0f0f0 75%, #f0f0f0),
                linear-gradient(45deg, #f0f0f0 25%, transparent 25%, transparent 75%, #f0f0f0 75%, #f0f0f0);
    background-size: 20px 20px;
    background-position: 0 0, 10px 10px;
    opacity: 0.5;
    z-index: 1;
  }
  
  // 添加预览图标覆盖层
  &::after {
    content: '🔍';
    position: absolute;
    top: 8px;
    right: 8px;
    width: 24px;
    height: 24px;
    background: rgba(0, 0, 0, 0.6);
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 12px;
    opacity: 0;
    transition: opacity 0.3s ease;
    z-index: 3;
  }
  
  &:hover::after {
    opacity: 1;
  }
}

.image-index {
  position: absolute;
  bottom: 6px;
  left: 6px;
  width: 20px;
  height: 20px;
  background: rgba(102, 126, 234, 0.9);
  color: white;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  font-weight: 600;
  z-index: 3;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
}

.user-image {
  width: 150px;
  height: 150px;
  object-fit: cover;
  display: block;
  border-radius: 10px;
  position: relative;
  z-index: 2;
  transition: opacity 0.3s ease;
  
  // 图片加载完成后隐藏背景纹理
  &:not([src=""]) + &::before {
    opacity: 0;
  }
  
  // 图片加载失败时的样式
  &[alt]:after {
    content: "🖼️ 图片加载失败";
    position: absolute;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    color: #999;
    font-size: 12px;
    text-align: center;
    z-index: 2;
  }
}

// 图片预览对话框样式
.image-preview-dialog {
  .image-preview-content {
    padding: 0;
    text-align: center;
    background: #000;
    border-radius: 8px;
    overflow: hidden;
  }

  .preview-full-image {
    width: 100%;
    height: auto;
    max-height: 70vh;
    object-fit: contain;
  }

  .dialog-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0 8px;
    
    .close-icon {
      font-size: 20px;
      cursor: pointer;
      color: #666;
      
      &:hover {
        color: #333;
      }
    }
  }
}

// 响应式设计
@media (max-width: 768px) {
  .message-bubble {
    gap: 12px;
    margin-bottom: 20px;
  }

  .avatar {
    width: 40px;
    height: 40px;

    svg {
      width: 20px;
      height: 20px;
    }
  }

  .message-content {
    max-width: calc(100% - 68px);
  }

  .message-card {
    border-radius: 16px;
  }

  .text {
    padding: 16px 20px;
    font-size: 14px;
  }

  .thinking-status {
    padding: 12px 16px;
    margin-bottom: 12px;

    .thinking-icon {
      width: 20px;
      height: 20px;
    }

    span {
      font-size: 13px;
    }
  }

  .files-section {
    .file-item {
      padding: 10px 12px;

      .file-name {
        font-size: 13px;
      }
    }
  }

  // 移动端图片样式调整
  .user-message-images {
    margin-top: 8px;
    gap: 8px;
    padding: 4px 0;
  }

  .user-image-item {
    &::after {
      width: 20px;
      height: 20px;
      font-size: 10px;
      top: 6px;
      right: 6px;
    }
  }

  .image-index {
    width: 18px;
    height: 18px;
    font-size: 10px;
    bottom: 4px;
    left: 4px;
  }

  .images-count-tip span {
    font-size: 11px;
    padding: 3px 6px;
  }

  .user-image {
    width: 100px;
    height: 100px;
    border-radius: 8px;
  }

  .image-preview-dialog {
    .preview-full-image {
      max-height: 60vh;
    }
  }
}
</style>