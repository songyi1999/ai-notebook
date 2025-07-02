<template>
  <div class="chat-window" ref="chatWindow">
    <!-- 欢迎界面 -->
    <div v-if="messages.length === 0" class="welcome-section">
      <div class="welcome-card">
        <div class="welcome-icon">
          <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M20 6L9 17L4 12" stroke="currentColor" stroke-width="2" stroke-linecap="round"
              stroke-linejoin="round" />
          </svg>
        </div>
        <h2>欢迎使用 {{ modelNameDisplay }}</h2>
        <p>{{ welcomeSubtitle }}</p>

        <!-- 预设问题卡片 -->
        <div class="preset-questions">
          <h3>热门问题</h3>
          <div class="questions-grid">
            <div v-for="(question, index) in presetQuestionsList" :key="index" class="question-card"
              @click="handlePresetQuestion(question)">
              <div class="question-icon">
                <svg v-if="index === 0" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                  <path d="M12 2L2 7L12 12L22 7L12 2Z" stroke="currentColor" stroke-width="2" stroke-linecap="round"
                    stroke-linejoin="round" />
                  <path d="M2 17L12 22L22 17" stroke="currentColor" stroke-width="2" stroke-linecap="round"
                    stroke-linejoin="round" />
                  <path d="M2 12L12 17L22 12" stroke="currentColor" stroke-width="2" stroke-linecap="round"
                    stroke-linejoin="round" />
                </svg>
                <svg v-else-if="index === 1" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                  <path d="M14 2H6A2 2 0 0 0 4 4V20A2 2 0 0 0 6 22H18A2 2 0 0 0 20 20V8L14 2Z" stroke="currentColor"
                    stroke-width="2" stroke-linecap="round" stroke-linejoin="round" />
                  <polyline points="14,2 14,8 20,8" stroke="currentColor" stroke-width="2" stroke-linecap="round"
                    stroke-linejoin="round" />
                  <line x1="16" y1="13" x2="8" y2="13" stroke="currentColor" stroke-width="2" stroke-linecap="round"
                    stroke-linejoin="round" />
                  <line x1="16" y1="17" x2="8" y2="17" stroke="currentColor" stroke-width="2" stroke-linecap="round"
                    stroke-linejoin="round" />
                  <polyline points="10,9 9,9 8,9" stroke="currentColor" stroke-width="2" stroke-linecap="round"
                    stroke-linejoin="round" />
                </svg>
                <svg v-else viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                  <path d="M9 11H15M9 15H15M17 3A2 2 0 0 1 19 5V19A2 2 0 0 1 17 21H7A2 2 0 0 1 5 19V5A2 2 0 0 1 7 3H17Z"
                    stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" />
                </svg>
              </div>
              <p>{{ question.displayText }}</p>
            </div>
          </div>
        </div>

        <!-- 功能特点 -->
        <div class="features">
          <div class="feature-item">
            <div class="feature-icon">🧬</div>
            <span>基因治疗专业咨询</span>
          </div>
          <div class="feature-item">
            <div class="feature-icon">🔬</div>
            <span>细胞治疗技术指导</span>
          </div>
          <div class="feature-item">
            <div class="feature-icon">🏥</div>
            <span>临床试验设计建议</span>
          </div>
          <div class="feature-item">
            <div class="feature-icon">📋</div>
            <span>监管法规解读</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 消息列表 -->
    <div v-else class="messages-container" ref="messagesContainer">
      <MessageBubble v-for="message in messages" :key="message.id" :message="message" />

      <!-- 加载指示器 -->
      <div v-if="isLoading" class="loading-indicator">
        <div class="loading-avatar">
          <svg viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
            <circle cx="50" cy="50" r="45" fill="none" stroke="#667eea" stroke-width="6" />
            <circle cx="35" cy="40" r="6" fill="#667eea" />
            <circle cx="65" cy="40" r="6" fill="#667eea" />
            <path d="M 30 65 Q 50 80 70 65" fill="none" stroke="#667eea" stroke-width="6" stroke-linecap="round" />
          </svg>
        </div>
        <div class="loading-text">
          <div class="typing-indicator">
            <span></span>
            <span></span>
            <span></span>
          </div>
          <p>医疗评价助手正在思考中...</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, nextTick, onMounted, computed } from 'vue'
import { storeToRefs } from 'pinia'
import { useChatStore } from '../store/chat'
import MessageBubble from './MessageBubble.vue'
import { getPresetQuestions } from '../config/settings'
import { modelNameDisplay, welcomeSubtitle } from '../config'

const chatWindow = ref(null)
const messagesContainer = ref(null)
const chatStore = useChatStore()
const { messages, isLoading } = storeToRefs(chatStore)

// 预设问题列表 - 从统一配置获取所有问题，并添加序号
const presetQuestionsList = computed(() => {
  const questions = getPresetQuestions()
  return Object.entries(questions)
    .filter(([key, value]) => key.startsWith('question') && value && value.trim())
    .sort(([a], [b]) => {
      // 按问题编号排序 (question1, question2, ...)
      const numA = parseInt(a.replace('question', ''))
      const numB = parseInt(b.replace('question', ''))
      return numA - numB
    })
    .map(([key, value], index) => ({
      id: key,
      text: value,
      displayText: `${index + 1}、${value}`, // 添加序号显示
      number: index + 1
    }))
})

// 处理预设问题点击
const handlePresetQuestion = (question) => {
  // 传递原始问题文本，不包含序号
  chatStore.handlePresetQuestion(question.text)
}

// 监听消息变化,自动滚动到底部
watch(messages, () => {
  nextTick(() => {
    scrollToBottom()
  })
}, { deep: true })

const scrollToBottom = () => {
  const container = messagesContainer.value || chatWindow.value
  if (container) {
    container.scrollTop = container.scrollHeight
  }
}
</script>

<style lang="scss" scoped>
.chat-window {
  flex: 1;
  overflow-y: auto;
  padding: 0;
  background: transparent;
  display: flex;
  flex-direction: column;
  height: 100%;

  // 自定义滚动条
  &::-webkit-scrollbar {
    width: 6px;
  }

  &::-webkit-scrollbar-track {
    background: rgba(255, 255, 255, 0.1);
    border-radius: 3px;
  }

  &::-webkit-scrollbar-thumb {
    background: rgba(255, 255, 255, 0.3);
    border-radius: 3px;

    &:hover {
      background: rgba(255, 255, 255, 0.5);
    }
  }
}

.messages-container {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 16px;

  // 自定义滚动条
  &::-webkit-scrollbar {
    width: 6px;
  }

  &::-webkit-scrollbar-track {
    background: rgba(255, 255, 255, 0.1);
    border-radius: 3px;
  }

  &::-webkit-scrollbar-thumb {
    background: rgba(255, 255, 255, 0.3);
    border-radius: 3px;

    &:hover {
      background: rgba(255, 255, 255, 0.5);
    }
  }
}

.welcome-section {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100%;
  padding: 40px 20px;
}

.welcome-card {
  max-width: 800px;
  width: 100%;
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(20px);
  border-radius: 24px;
  padding: 48px 40px;
  text-align: center;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.2);

  .welcome-icon {
    width: 80px;
    height: 80px;
    background: linear-gradient(135deg, #667eea, #764ba2);
    border-radius: 20px;
    display: flex;
    align-items: center;
    justify-content: center;
    margin: 0 auto 24px;
    color: white;
    box-shadow: 0 10px 30px rgba(102, 126, 234, 0.3);

    svg {
      width: 40px;
      height: 40px;
    }
  }

  h2 {
    font-size: 32px;
    font-weight: 700;
    color: #2d3748;
    margin: 0 0 16px 0;
    background: linear-gradient(135deg, #667eea, #764ba2);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
  }

  >p {
    font-size: 18px;
    color: #718096;
    margin: 0 0 40px 0;
    line-height: 1.6;
  }
}

.preset-questions {
  margin-bottom: 40px;

  h3 {
    font-size: 20px;
    font-weight: 600;
    color: #2d3748;
    margin: 0 0 24px 0;
  }

  .questions-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 12px;
    max-height: 400px;
    overflow-y: auto;

    // 自定义滚动条
    &::-webkit-scrollbar {
      width: 6px;
    }

    &::-webkit-scrollbar-track {
      background: rgba(102, 126, 234, 0.1);
      border-radius: 3px;
    }

    &::-webkit-scrollbar-thumb {
      background: rgba(102, 126, 234, 0.3);
      border-radius: 3px;

      &:hover {
        background: rgba(102, 126, 234, 0.5);
      }
    }
  }

  .question-card {
    background: rgba(255, 255, 255, 0.7);
    border: 2px solid rgba(102, 126, 234, 0.1);
    border-radius: 16px;
    padding: 20px;
    cursor: pointer;
    transition: all 0.3s ease;
    text-align: left;
    display: flex;
    align-items: flex-start;
    gap: 12px;

    &:hover {
      background: rgba(102, 126, 234, 0.05);
      border-color: rgba(102, 126, 234, 0.3);
      transform: translateY(-2px);
      box-shadow: 0 8px 25px rgba(102, 126, 234, 0.15);
    }

    .question-icon {
      width: 40px;
      height: 40px;
      background: linear-gradient(135deg, #667eea, #764ba2);
      border-radius: 10px;
      display: flex;
      align-items: center;
      justify-content: center;
      color: white;
      flex-shrink: 0;

      svg {
        width: 20px;
        height: 20px;
      }
    }

    p {
      font-size: 14px;
      color: #4a5568;
      margin: 0;
      line-height: 1.5;
      font-weight: 500;
    }
  }
}

.features {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 16px;

  .feature-item {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 16px;
    background: rgba(102, 126, 234, 0.05);
    border-radius: 12px;
    border: 1px solid rgba(102, 126, 234, 0.1);

    .feature-icon {
      font-size: 24px;
      width: 40px;
      height: 40px;
      display: flex;
      align-items: center;
      justify-content: center;
      background: rgba(255, 255, 255, 0.8);
      border-radius: 10px;
    }

    span {
      font-size: 14px;
      color: #4a5568;
      font-weight: 500;
    }
  }
}

.messages-container {
  max-width: 900px;
  margin: 0 auto;
  padding: 24px 16px;
}

.loading-indicator {
  display: flex;
  align-items: flex-start;
  gap: 16px;
  padding: 20px;
  margin: 16px 0;
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(10px);
  border-radius: 20px;
  border: 1px solid rgba(255, 255, 255, 0.2);
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);

  .loading-avatar {
    width: 40px;
    height: 40px;
    border-radius: 50%;
    background: rgba(102, 126, 234, 0.1);
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;

    svg {
      width: 24px;
      height: 24px;
      animation: pulse 2s infinite;
    }
  }

  .loading-text {
    flex: 1;

    .typing-indicator {
      display: flex;
      gap: 4px;
      margin-bottom: 8px;

      span {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background: #667eea;
        animation: typing 1.4s infinite ease-in-out;

        &:nth-child(1) {
          animation-delay: 0.0s;
        }

        &:nth-child(2) {
          animation-delay: 0.2s;
        }

        &:nth-child(3) {
          animation-delay: 0.4s;
        }
      }
    }

    p {
      margin: 0;
      font-size: 14px;
      color: #718096;
    }
  }
}

@keyframes typing {

  0%,
  60%,
  100% {
    transform: translateY(0);
    opacity: 0.5;
  }

  30% {
    transform: translateY(-10px);
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

// 响应式设计
@media (max-width: 768px) {
  .welcome-card {
    padding: 32px 24px;
    border-radius: 20px;

    .welcome-icon {
      width: 60px;
      height: 60px;

      svg {
        width: 30px;
        height: 30px;
      }
    }

    h2 {
      font-size: 24px;
    }

    >p {
      font-size: 16px;
    }
  }

  .preset-questions {
    .questions-grid {
      grid-template-columns: 1fr;
    }

    .question-card {
      padding: 16px;

      .question-icon {
        width: 36px;
        height: 36px;

        svg {
          width: 18px;
          height: 18px;
        }
      }
    }
  }

  .features {
    grid-template-columns: 1fr;

    .feature-item {
      padding: 12px;

      .feature-icon {
        width: 36px;
        height: 36px;
        font-size: 20px;
      }

      span {
        font-size: 13px;
      }
    }
  }

  .messages-container {
    padding: 16px 12px;
  }
}
</style>