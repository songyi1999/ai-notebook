<template>
  <div class="app-container">
    <!-- 头部标题栏 -->
    <header class="app-header">
      <div class="header-content">
        <div class="logo-section">
          <div class="logo-icon" v-if="!logoUrl">
            <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path
                d="M12 2C13.1 2 14 2.9 14 4C14 5.1 13.1 6 12 6C10.9 6 10 5.1 10 4C10 2.9 10.9 2 12 2ZM21 9V7L15 1L9 7V9C9 10.1 9.9 11 11 11V16L7.5 15.5C7.1 15.4 6.6 15.25 6.2 15C5.8 14.8 5.5 14.65 5.3 14.5L4.8 14.05C4.25 13.5 4.25 12.75 4.8 12.2C5.35 11.65 6.1 11.65 6.65 12.2L8.5 14.05C8.9 14.45 9.4 14.75 9.9 14.9L12 15.5L14.1 14.9C14.6 14.75 15.1 14.45 15.5 14.05L17.35 12.2C17.9 11.65 18.65 11.65 19.2 12.2C19.75 12.75 19.75 13.5 19.2 14.05L18.7 14.5C18.5 14.65 18.2 14.8 17.8 15C17.4 15.25 16.9 15.4 16.5 15.5L13 16V11C14.1 11 15 10.1 15 9Z"
                fill="currentColor" />
            </svg>
          </div>
          <div class="logo-image" v-else>
            <img :src="logoUrl" alt="Logo" @error="onLogoError" />
          </div>
          <div class="logo-text">
            <h1>{{ modelNameDisplay }}</h1>
            <p>{{ identityPrompt }}</p>
          </div>
        </div>
        <div class="status-indicator">
          <div class="status-dot"></div>
          <span>在线服务</span>
        </div>
      </div>
    </header>

    <!-- 主要内容区域 -->
    <main class="app-main">
      <ChatWindow />
    </main>

    <!-- 输入区域 -->
    <footer class="app-footer">
      <InputBox />
    </footer>

    <!-- 背景装饰 -->
    <div class="background-decoration">
      <div class="decoration-circle circle-1"></div>
      <div class="decoration-circle circle-2"></div>
      <div class="decoration-circle circle-3"></div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useChatStore } from './store/chat'
import { logoUrl as configLogoUrl, identityPrompt as configIdentityPrompt, modelNameDisplay as configModelNameDisplay } from './config'
import ChatWindow from './components/ChatWindow.vue'
import InputBox from './components/InputBox.vue'

const chatStore = useChatStore()
const logoUrl = ref(configLogoUrl)
const identityPrompt = ref(configIdentityPrompt)
const modelNameDisplay = ref(configModelNameDisplay)

// Logo加载失败时的处理
const onLogoError = () => {
  console.warn('Logo加载失败，使用默认图标')
  logoUrl.value = ''
}

onMounted(() => {
  chatStore.init()
})
</script>

<style lang="scss">
.app-container {
  height: 100vh;
  display: flex;
  flex-direction: column;
  position: relative;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  overflow: hidden;
}

.app-header {
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(10px);
  border-bottom: 1px solid rgba(255, 255, 255, 0.2);
  padding: 16px 24px;
  position: relative;
  z-index: 100;
  box-shadow: 0 2px 20px rgba(0, 0, 0, 0.1);

  .header-content {
    max-width: 1200px;
    margin: 0 auto;
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .logo-section {
    display: flex;
    align-items: center;
    gap: 12px;

    .logo-icon {
      width: 48px;
      height: 48px;
      background: linear-gradient(135deg, #667eea, #764ba2);
      border-radius: 12px;
      display: flex;
      align-items: center;
      justify-content: center;
      color: white;
      box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);

      svg {
        width: 24px;
        height: 24px;
      }
    }

    .logo-image {
      width: 48px;
      height: 48px;
      border-radius: 12px;
      overflow: hidden;
      box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);

      img {
        width: 100%;
        height: 100%;
        object-fit: cover;
        object-position: center;
      }
    }

    .logo-text {
      h1 {
        font-size: 24px;
        font-weight: 700;
        color: #2d3748;
        margin: 0;
        line-height: 1.2;
      }

      p {
        font-size: 12px;
        color: #718096;
        margin: 2px 0 0 0;
        font-weight: 500;
        letter-spacing: 0.5px;
      }
    }
  }

  .status-indicator {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 8px 16px;
    background: rgba(72, 187, 120, 0.1);
    border-radius: 20px;
    border: 1px solid rgba(72, 187, 120, 0.2);

    .status-dot {
      width: 8px;
      height: 8px;
      background: #48bb78;
      border-radius: 50%;
      animation: pulse 2s infinite;
    }

    span {
      font-size: 14px;
      color: #48bb78;
      font-weight: 500;
    }
  }
}

.app-main {
  flex: 1;
  position: relative;
  z-index: 10;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.app-footer {
  position: relative;
  z-index: 10;
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(10px);
  border-top: 1px solid rgba(255, 255, 255, 0.2);
  padding: 20px 24px;
}

.background-decoration {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  pointer-events: none;
  overflow: hidden;

  .decoration-circle {
    position: absolute;
    border-radius: 50%;
    background: rgba(255, 255, 255, 0.1);
    animation: float 6s ease-in-out infinite;

    &.circle-1 {
      width: 200px;
      height: 200px;
      top: 10%;
      right: -50px;
      animation-delay: 0s;
    }

    &.circle-2 {
      width: 150px;
      height: 150px;
      bottom: 20%;
      left: -30px;
      animation-delay: 2s;
    }

    &.circle-3 {
      width: 100px;
      height: 100px;
      top: 50%;
      right: 20%;
      animation-delay: 4s;
    }
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

@keyframes float {

  0%,
  100% {
    transform: translateY(0px) rotate(0deg);
  }

  33% {
    transform: translateY(-20px) rotate(120deg);
  }

  66% {
    transform: translateY(10px) rotate(240deg);
  }
}

// 响应式设计
@media (max-width: 768px) {
  .app-header {
    padding: 12px 16px;

    .logo-section {
      .logo-icon {
        width: 40px;
        height: 40px;

        svg {
          width: 20px;
          height: 20px;
        }
      }

      .logo-image {
        width: 40px;
        height: 40px;
      }

      .logo-text {
        h1 {
          font-size: 20px;
        }

        p {
          font-size: 11px;
        }
      }
    }

    .status-indicator {
      padding: 6px 12px;

      span {
        font-size: 13px;
      }
    }
  }

  .app-footer {
    padding: 16px;
  }
}
</style>