import { ref, computed, onMounted } from 'vue'
import { presetQuestions } from '../config'

// 动态获取预设问题
const getPresetQuestions = () => {
if (typeof window !== 'undefined' && window.APP_CONFIG?.presetQuestions) {
return window.APP_CONFIG.presetQuestions;
}
return presetQuestions;
}

// const questions = ref(presetQuestions)
const questions = ref(getPresetQuestions())

// 监听配置变化
onMounted(() => {
// 如果配置已加载但组件已渲染,强制更新
if (typeof window !== 'undefined' && window.APP_CONFIG?.presetQuestions) {
questions.value = window.APP_CONFIG.presetQuestions;
}
})

<template>
  <div class="preset-questions-container">
    <div class="questions-header">
      <div class="header-icon">
        <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
          <path
            d="M9.09 9C9.3251 8.33167 9.78915 7.76811 10.4 7.40913C11.0108 7.05016 11.7289 6.91894 12.4272 7.03871C13.1255 7.15849 13.7588 7.52152 14.2151 8.06353C14.6713 8.60553 14.9211 9.29152 14.92 10C14.92 12 11.92 13 11.92 13"
            stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" />
          <circle cx="12" cy="17" r="1" fill="currentColor" />
          <circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="2" />
        </svg>
      </div>
      <div class="header-text">
        <h3>常见问题</h3>
        <p>选择一个问题快速开始对话</p>
      </div>
    </div>

    <div class="questions-grid">
      <div v-for="(question, index) in questions" :key="index" class="question-card" :class="`card-${(index % 4) + 1}`"
        @click="$emit('selectQuestion', question.text)">
        <div class="card-icon">
          <component :is="question.icon" />
        </div>
        <div class="card-content">
          <h4>{{ question.title }}</h4>
          <p>{{ question.description }}</p>
        </div>
        <div class="card-arrow">
          <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M7 17L17 7" stroke="currentColor" stroke-width="2" stroke-linecap="round"
              stroke-linejoin="round" />
            <path d="M7 7H17V17" stroke="currentColor" stroke-width="2" stroke-linecap="round"
              stroke-linejoin="round" />
          </svg>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { defineEmits } from 'vue'

// 定义事件
const emit = defineEmits(['selectQuestion'])

// 预设问题数据
const questions = [
  {
    title: "三甲医院专家信息",
    description: "查询三甲医院的医疗领域专家信息",
    text: "请提供三甲医院医疗领域的专家信息",
    icon: "ClinicalIcon"
  },
  {
    title: "三甲医院医疗项目概况",
    description: "了解三甲医院医疗项目的总体情况",
    text: "介绍一下三甲医院医疗项目的概况",
    icon: "GeneIcon"
  },
  {
    title: "三甲医院医疗项目自动化评价",
    description: "对三甲医院的医疗项目进行自动化评价",
    text: "如何对三甲医院的医疗项目进行自动化评价？",
    icon: "TissueIcon"
  },
  {
    title: "三甲医院医疗项目专家反馈",
    description: "查看专家对三甲医院医疗项目的反馈",
    text: "我想查询三甲医院医疗项目的专家反馈",
    icon: "RegulationIcon"
  },
  {
    title: "医疗知识库问答",
    description: "从医疗知识库中获取问题的答案",
    text: "请从医疗知识库中回答：什么是医疗质量评价？",
    icon: "QualityIcon"
  },
  {
    title: "三甲医院医疗项目评价信息上报",
    description: "上报三甲医院医疗项目的评价信息",
    text: "如何上报三甲医院医疗项目的评价信息？",
    icon: "CellIcon"
  },
  {
    title: "医疗项目评价报告查询与下载",
    description: "查询并下载医疗项目的评价报告",
    text: "在哪里可以查询和下载医疗项目评价报告？",
    icon: "GeneIcon"
  },
  {
    title: "医疗跨主体追踪与AI比对分析",
    description: "对不同主体的医疗项目进行追踪和AI比对分析",
    text: "如何实现医疗项目的跨主体追踪与AI比对分析？",
    icon: "TissueIcon"
  },
  {
    title: "医疗跨区域追踪与AI比对分析",
    description: "对不同区域的医疗项目进行追踪和AI比对分析",
    text: "如何实现医疗项目的跨区域追踪与AI比对分析？",
    icon: "RegulationIcon"
  },
  {
    title: "医疗跨时间追踪与AI比对分析",
    description: "对不同时间的医疗项目进行追踪和AI比对分析",
    text: "如何实现医疗项目的跨时间追踪与AI比对分析？",
    icon: "QualityIcon"
  }
]
</script>

<style lang="scss" scoped>
.preset-questions-container {
  padding: 32px 24px;
  max-width: 1000px;
  margin: 0 auto;
}

.questions-header {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 32px;
  text-align: left;

  .header-icon {
    width: 56px;
    height: 56px;
    background: var(--gradient-primary);
    border-radius: 16px;
    display: flex;
    align-items: center;
    justify-content: center;
    color: white;
    box-shadow: 0 8px 25px rgba(102, 126, 234, 0.3);
    flex-shrink: 0;

    svg {
      width: 28px;
      height: 28px;
    }
  }

  .header-text {
    flex: 1;

    h3 {
      font-size: 24px;
      font-weight: 700;
      color: var(--text-primary);
      margin: 0 0 4px 0;
      line-height: 1.2;
    }

    p {
      font-size: 16px;
      color: var(--text-muted);
      margin: 0;
      font-weight: 400;
    }
  }
}

.questions-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 20px;
}

.question-card {
  position: relative;
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(10px);
  border-radius: 20px;
  padding: 24px;
  cursor: pointer;
  transition: all 0.3s ease;
  border: 1px solid rgba(255, 255, 255, 0.2);
  overflow: hidden;

  &::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 4px;
    background: var(--gradient-primary);
    opacity: 0;
    transition: opacity 0.3s ease;
  }

  &:hover {
    transform: translateY(-4px);
    box-shadow: 0 12px 40px rgba(0, 0, 0, 0.15);

    &::before {
      opacity: 1;
    }

    .card-arrow {
      transform: translate(4px, -4px);
      opacity: 1;
    }

    .card-icon {
      transform: scale(1.1);
    }
  }

  &:active {
    transform: translateY(-2px);
  }

  // 不同卡片的主题色
  &.card-1 {
    &::before {
      background: linear-gradient(90deg, #667eea, #764ba2);
    }
  }

  &.card-2 {
    &::before {
      background: linear-gradient(90deg, #48bb78, #38a169);
    }
  }

  &.card-3 {
    &::before {
      background: linear-gradient(90deg, #ff6b6b, #ee5a52);
    }
  }

  &.card-4 {
    &::before {
      background: linear-gradient(90deg, #ed8936, #dd6b20);
    }
  }

  .card-icon {
    width: 48px;
    height: 48px;
    background: rgba(102, 126, 234, 0.1);
    border-radius: 12px;
    display: flex;
    align-items: center;
    justify-content: center;
    color: var(--primary-color);
    margin-bottom: 16px;
    transition: all 0.3s ease;

    svg {
      width: 24px;
      height: 24px;
    }
  }

  .card-content {
    flex: 1;

    h4 {
      font-size: 18px;
      font-weight: 600;
      color: var(--text-primary);
      margin: 0 0 8px 0;
      line-height: 1.3;
    }

    p {
      font-size: 14px;
      color: var(--text-secondary);
      margin: 0;
      line-height: 1.5;
    }
  }

  .card-arrow {
    position: absolute;
    top: 20px;
    right: 20px;
    width: 24px;
    height: 24px;
    color: var(--text-light);
    opacity: 0.6;
    transition: all 0.3s ease;

    svg {
      width: 100%;
      height: 100%;
    }
  }
}

// 图标组件
.card-icon {
  svg {
    width: 24px;
    height: 24px;
  }
}

// 响应式设计
@media (max-width: 768px) {
  .preset-questions-container {
    padding: 24px 16px;
  }

  .questions-header {
    margin-bottom: 24px;

    .header-icon {
      width: 48px;
      height: 48px;

      svg {
        width: 24px;
        height: 24px;
      }
    }

    .header-text {
      h3 {
        font-size: 20px;
      }

      p {
        font-size: 14px;
      }
    }
  }

  .questions-grid {
    grid-template-columns: 1fr;
    gap: 16px;
  }

  .question-card {
    padding: 20px;

    .card-content {
      h4 {
        font-size: 16px;
      }

      p {
        font-size: 13px;
      }
    }
  }
}

@media (max-width: 480px) {
  .questions-grid {
    grid-template-columns: 1fr;
  }

  .question-card {
    padding: 16px;

    .card-icon {
      width: 40px;
      height: 40px;
      margin-bottom: 12px;

      svg {
        width: 20px;
        height: 20px;
      }
    }
  }
}
</style>