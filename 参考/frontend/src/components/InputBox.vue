<template>
  <div class="input-container">
    <div class="input-box">
      <!-- 上传按钮 -->
      <div class="upload-btn-wrapper">
        <input ref="fileInput" type="file" accept=".jpg,.jpeg,.png,.gif,.bmp,.webp,.pdf,.docx"
          @change="handleFileUpload" style="display: none;" multiple />
        <button class="upload-btn" @click="triggerFileUpload" :disabled="loading" title="上传文件（支持图片、PDF、DOCX）">
          <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none"
            stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path
              d="m21.44 11.05-9.19 9.19a6 6 0 0 1-8.49-8.49l8.57-8.57A4 4 0 1 1 18 8.84l-8.59 8.57a2 2 0 0 1-2.83-2.83l8.49-8.48" />
          </svg>
        </button>
      </div>

      <!-- 输入框 -->
      <div class="input-wrapper">
        <van-field v-model="inputText" type="textarea" placeholder="请输入您的医疗评价相关问题..." rows="1" autosize
          class="message-input" @keypress.enter.prevent="handleSend" @paste="handlePaste" :disabled="loading" />

        <!-- 图片预览区域 -->
        <div v-if="uploadedImages.length > 0" class="image-preview-container">
          <div v-for="(image, index) in uploadedImages" :key="index" class="image-preview-item">
            <img :src="image.url" :alt="image.name" class="preview-image" />
            <button @click="removeImage(index)" class="remove-image-btn" title="删除图片">
              <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none"
                stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <line x1="18" y1="6" x2="6" y2="18"></line>
                <line x1="6" y1="6" x2="18" y2="18"></line>
              </svg>
            </button>
            <div class="image-info">
              <span class="image-name">{{ image.name }}</span>
              <span class="image-size">{{ formatFileSize(image.size) }}</span>
            </div>
          </div>
        </div>

        <!-- 文档附件区域 -->
        <div v-if="uploadedDocuments.length > 0" class="document-attachments-container">
          <div class="attachments-header">
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none"
              stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="m21.44 11.05-9.19 9.19a6 6 0 0 1-8.49-8.49l8.57-8.57A4 4 0 1 1 18 8.84l-8.59 8.57a2 2 0 0 1-2.83-2.83l8.49-8.48" />
            </svg>
            <span>附件文档 ({{ uploadedDocuments.length }})</span>
          </div>
          <div class="document-attachments-list">
            <div v-for="(doc, index) in uploadedDocuments" :key="index" class="document-attachment-item">
              <div class="document-icon">
                <svg v-if="doc.type.includes('pdf')" xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none"
                  stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                  <polyline points="14,2 14,8 20,8" />
                  <line x1="16" y1="13" x2="8" y2="13" />
                  <line x1="16" y1="17" x2="8" y2="17" />
                  <polyline points="10,9 9,9 8,9" />
                </svg>
                <svg v-else xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none"
                  stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                  <polyline points="14,2 14,8 20,8" />
                  <line x1="16" y1="13" x2="8" y2="13" />
                  <line x1="16" y1="17" x2="8" y2="17" />
                </svg>
              </div>
              <div class="document-info">
                <div class="document-name">{{ doc.name }}</div>
                <div class="document-meta">
                  <span class="document-size">{{ formatFileSize(doc.size) }}</span>
                  <span class="document-type">{{ getDocumentTypeDisplay(doc.type) }}</span>
                </div>
              </div>
              <button @click="removeDocument(index)" class="remove-document-btn" title="移除文档">
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none"
                  stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <line x1="18" y1="6" x2="6" y2="18"></line>
                  <line x1="6" y1="6" x2="18" y2="18"></line>
                </svg>
              </button>
            </div>
          </div>
          <div class="attachment-notice">
            <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none"
              stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <circle cx="12" cy="12" r="10" />
              <path d="m9 12 2 2 4-4" />
            </svg>
            <span>文档将随每次提问一起发送，直到您主动删除</span>
          </div>
        </div>
      </div>

      <!-- 发送按钮 -->
      <div class="send-btn-wrapper">
        <button class="send-btn" :class="{ 'has-content': inputText.trim() || uploadedDocuments.length > 0, 'loading': loading }"
          :disabled="(!inputText.trim() && uploadedDocuments.length === 0) || loading" @click="handleSend" 
          :title="loading ? '正在发送...' : '发送消息'">
          <div class="btn-content">
            <svg v-if="!loading" xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24"
              fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M22 2L11 13" />
              <polygon points="22,2 15,22 11,13 2,9" />
            </svg>
            <svg v-else class="loading-icon" xmlns="http://www.w3.org/2000/svg" width="20" height="20"
              viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"
              stroke-linejoin="round">
              <path d="M21 12A9 9 0 1 1 12 3" />
            </svg>
          </div>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useChatStore } from '../store/chat'
import { showToast } from 'vant'

const chatStore = useChatStore()
const inputText = ref('')
const loading = ref(false)
const uploadedImages = ref([])
const uploadedDocuments = ref([])
const fileInput = ref(null)

// 支持的文件格式
const ALLOWED_IMAGE_TYPES = ['image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/bmp', 'image/webp']
const ALLOWED_DOCUMENT_TYPES = ['application/pdf', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document']
const ALLOWED_FILE_TYPES = [...ALLOWED_IMAGE_TYPES, ...ALLOWED_DOCUMENT_TYPES]
const MAX_FILE_SIZE = 50 * 1024 * 1024 // 50MB (文档文件可能较大)

// 格式化文件大小
const formatFileSize = (bytes) => {
  if (bytes === 0) return '0 Bytes'
  const k = 1024
  const sizes = ['Bytes', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

// 获取文档类型显示名称
const getDocumentTypeDisplay = (mimeType) => {
  if (mimeType.includes('pdf')) return 'PDF'
  if (mimeType.includes('wordprocessingml')) return 'DOCX'
  return 'DOC'
}

// 处理粘贴事件
const handlePaste = async (event) => {
  const clipboardData = event.clipboardData || window.clipboardData
  const items = clipboardData.items

  for (let item of items) {
    if (item.type.indexOf('image') !== -1) {
      event.preventDefault()
      const file = item.getAsFile()

      if (file) {
        await handleImageFile(file)
      }
    }
  }
}

// 触发文件上传
const triggerFileUpload = () => {
  if (fileInput.value) {
    fileInput.value.click()
  }
}

// 处理文件上传
const handleFileUpload = async (event) => {
  const files = event.target.files
  if (!files || files.length === 0) return

  for (let file of files) {
    await handleFile(file)
  }

  // 清空文件输入框
  if (fileInput.value) {
    fileInput.value.value = ''
  }
}

// 处理单个文件
const handleFile = async (file) => {
  try {
    // 检查文件是否存在
    if (!file.name) {
      showToast('文件无效')
      return
    }

    // 检查文件类型
    if (!ALLOWED_FILE_TYPES.includes(file.type)) {
      showToast(`不支持的文件格式: ${file.name}`)
      return
    }

    // 检查文件大小
    if (file.size > MAX_FILE_SIZE) {
      showToast(`文件过大，最大支持50MB: ${file.name}`)
      return
    }

    const fileType = getFileType(file.type)

    // 如果是图片文件，添加到预览列表
    if (fileType === 'image') {
      await addImageToPreview(file)
      return
    }

    // 如果是文档文件，添加到文档附件列表（不立即发送）
    if (fileType === 'document') {
      await addDocumentToAttachments(file)
      return
    }

  } catch (error) {
    console.error('文件处理失败:', error)
    showToast('文件处理失败，请重试')
  }
}

// 获取文件类型
const getFileType = (mimeType) => {
  if (ALLOWED_IMAGE_TYPES.includes(mimeType)) {
    return 'image'
  } else if (ALLOWED_DOCUMENT_TYPES.includes(mimeType)) {
    return 'document'
  }
  return 'unknown'
}

// 处理图片文件（保持向后兼容）
const handleImageFile = async (file) => {
  // 如果是图片文件，先添加到预览列表
  if (ALLOWED_IMAGE_TYPES.includes(file.type)) {
    await addImageToPreview(file)
  } else {
    // 非图片文件直接处理
    await handleFile(file)
  }
}

// 添加图片到预览列表
const addImageToPreview = async (file) => {
  try {
    // 检查文件大小
    if (file.size > MAX_FILE_SIZE) {
      showToast(`图片文件过大，最大支持50MB: ${file.name}`)
      return
    }

    // 创建图片URL用于预览
    const imageUrl = URL.createObjectURL(file)

    // 添加到预览列表
    uploadedImages.value.push({
      file: file,
      url: imageUrl,
      name: file.name,
      size: file.size,
      type: file.type
    })

    showToast(`图片 ${file.name} 已添加到预览`)
  } catch (error) {
    console.error('添加图片预览失败:', error)
    showToast('添加图片预览失败')
  }
}

// 新增：添加文档到附件列表
const addDocumentToAttachments = async (file) => {
  try {
    // 检查是否已经存在相同的文档
    const existingDoc = uploadedDocuments.value.find(doc => 
      doc.name === file.name && doc.size === file.size
    )
    
    if (existingDoc) {
      showToast(`文档 ${file.name} 已存在于附件列表中`)
      return
    }

    // 添加到文档附件列表
    uploadedDocuments.value.push({
      file: file,
      name: file.name,
      size: file.size,
      type: file.type
    })

    showToast(`文档 ${file.name} 已添加到附件列表`)
  } catch (error) {
    console.error('添加文档附件失败:', error)
    showToast('添加文档附件失败')
  }
}

// 移除图片
const removeImage = (index) => {
  const imageItem = uploadedImages.value[index]
  if (imageItem && imageItem.url) {
    // 释放对象URL以避免内存泄漏
    URL.revokeObjectURL(imageItem.url)
  }
  uploadedImages.value.splice(index, 1)
}

// 新增：移除文档附件
const removeDocument = (index) => {
  const documentItem = uploadedDocuments.value[index]
  uploadedDocuments.value.splice(index, 1)
  showToast(`已移除文档: ${documentItem.name}`)
}

// 发送消息
const handleSend = async () => {
  const text = inputText.value.trim();
  const hasImages = uploadedImages.value.length > 0;
  const hasDocuments = uploadedDocuments.value.length > 0;

  if (!text && !hasImages && !hasDocuments) {
    showToast('请输入问题、添加图片或上传文档');
    return;
  }

  try {
    loading.value = true;

    // 如果有图片需要处理，先处理图片
    if (hasImages) {
      showToast('正在处理图片，请稍等...');

      // 处理每个图片
      for (const imageItem of uploadedImages.value) {
        await processImageFile(imageItem.file);
      }

      // 清空图片预览
      uploadedImages.value.forEach(img => {
        if (img.url) {
          URL.revokeObjectURL(img.url);
        }
      });
      uploadedImages.value = [];
    }

    // 如果有文档附件或文本消息，发送带附件的消息
    if (text || hasDocuments) {
      await chatStore.sendMessageWithAttachments(text, uploadedDocuments.value);
    }

    // 清空输入框（但保留文档附件，直到用户主动删除）
    inputText.value = '';
  } catch (error) {
    console.error('发送消息失败:', error);
    showToast('发送失败，请重试');
  } finally {
    loading.value = false;
  }
};

// 处理图片文件（发送时调用）
const processImageFile = async (file) => {
  try {
    // 创建FormData
    const formData = new FormData();
    formData.append('file', file);

    // 调用文件转换API
    const response = await fetch('/api/v1/upload-and-convert', {
      method: 'POST',
      body: formData
    });

    const result = await response.json();

    if (result.success && result.data) {
      // 直接将转换结果作为聊天消息添加到聊天记录中
      await chatStore.addMessage({
        role: result.data.role,
        content: result.data.content,
        timestamp: new Date().toISOString(),
        isImage: false,
        processingTime: result.data.processing_time,
        originalFilename: result.data.original_filename,
        fileType: result.data.file_type,
        processingType: result.data.processing_type
      });
    } else {
      // 转换失败时也显示错误信息
      if (result.data && result.data.content) {
        await chatStore.addMessage({
          role: result.data.role,
          content: result.data.content,
          timestamp: new Date().toISOString(),
          isError: true,
          originalFilename: result.data.original_filename,
          fileType: result.data.file_type
        });
      }
    }
  } catch (error) {
    console.error('图片处理失败:', error);

    // 添加错误消息到聊天记录
    await chatStore.addMessage({
      role: 'assistant',
      content: `图片处理失败：${error.message || '网络连接错误'}。请检查网络连接后重试。`,
      timestamp: new Date().toISOString(),
      isError: true
    });
  }
};
</script>

<style lang="scss" scoped>
.input-container {
  position: relative;
  max-width: 900px;
  margin: 0 auto;
  width: 100%;
}

.input-box {
  display: flex;
  align-items: flex-end;
  gap: 16px;
  width: 100%;
  padding: 20px;
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(10px);
  border-radius: 24px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.2);
  transition: all 0.3s ease;

  &:hover {
    box-shadow: 0 12px 40px rgba(0, 0, 0, 0.15);
  }

  &:focus-within {
    box-shadow: 0 12px 40px rgba(102, 126, 234, 0.2);
    border-color: rgba(102, 126, 234, 0.3);
  }
}

.input-wrapper {
  flex: 1;
  position: relative;
}

.message-input {
  :deep(.van-field__control) {
    background: transparent;
    border: none;
    font-size: 16px;
    line-height: 1.5;
    color: #2d3748;
    resize: none;
    min-height: 24px;
    max-height: 120px;

    &::placeholder {
      color: #a0aec0;
      font-weight: 400;
    }

    &:focus {
      outline: none;
    }
  }

  :deep(.van-field__body) {
    padding: 0;
  }
}

.upload-btn-wrapper,
.send-btn-wrapper {
  flex-shrink: 0;
}

.upload-btn,
.send-btn {
  width: 48px;
  height: 48px;
  border: none;
  border-radius: 50%;
  cursor: pointer;
  transition: all 0.3s ease;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  background: rgba(102, 126, 234, 0.1);
  color: #667eea;
  box-shadow: 0 2px 8px rgba(102, 126, 234, 0.2);

  &:hover {
    transform: scale(1.05);
    box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
  }

  &:active {
    transform: scale(0.95);
  }

  &:disabled {
    cursor: not-allowed;
    opacity: 0.5;

    &:hover {
      transform: none;
      box-shadow: 0 2px 8px rgba(102, 126, 234, 0.2);
    }
  }
}

.upload-btn {
  background: rgba(76, 175, 80, 0.1);
  color: #4caf50;
  box-shadow: 0 2px 8px rgba(76, 175, 80, 0.2);

  &:hover {
    box-shadow: 0 4px 12px rgba(76, 175, 80, 0.3);
  }

  &:disabled:hover {
    box-shadow: 0 2px 8px rgba(76, 175, 80, 0.2);
  }
}

.send-btn {
  &.has-content {
    background: linear-gradient(135deg, #667eea, #764ba2);
    color: white;
    box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);

    &:hover {
      box-shadow: 0 6px 20px rgba(102, 126, 234, 0.4);
    }
  }

  &.loading {
    background: linear-gradient(135deg, #a0aec0, #718096);
    cursor: not-allowed;

    &:hover {
      transform: none;
      box-shadow: 0 2px 8px rgba(160, 174, 192, 0.2);
    }
  }

  .btn-content {
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .loading-icon {
    animation: spin 1s linear infinite;
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

// 图片预览样式
.image-preview-container {
  margin-top: 12px;
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  max-height: 200px;
  overflow-y: auto;
}

.image-preview-item {
  position: relative;
  border-radius: 8px;
  overflow: hidden;
  border: 1px solid rgba(0, 0, 0, 0.1);
  background: #f8f9fa;
  min-width: 120px;
  max-width: 180px;
}

.preview-image {
  width: 100%;
  height: 80px;
  object-fit: cover;
  display: block;
}

.remove-image-btn {
  position: absolute;
  top: 4px;
  right: 4px;
  width: 24px;
  height: 24px;
  border: none;
  border-radius: 50%;
  background: rgba(0, 0, 0, 0.6);
  color: white;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background-color 0.2s;

  &:hover {
    background: rgba(0, 0, 0, 0.8);
  }
}

.image-info {
  padding: 6px 8px;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.image-name {
  font-size: 12px;
  color: #2d3748;
  font-weight: 500;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.image-size {
  font-size: 10px;
  color: #a0aec0;
}

// 文档附件样式
.document-attachments-container {
  margin-top: 12px;
  padding: 16px;
  background: rgba(102, 126, 234, 0.05);
  border: 1px solid rgba(102, 126, 234, 0.1);
  border-radius: 12px;
  transition: all 0.3s ease;

  &:hover {
    background: rgba(102, 126, 234, 0.08);
    border-color: rgba(102, 126, 234, 0.2);
  }
}

.attachments-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
  color: #667eea;
  font-size: 14px;
  font-weight: 600;

  svg {
    flex-shrink: 0;
  }
}

.document-attachments-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.document-attachment-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  background: rgba(255, 255, 255, 0.8);
  border: 1px solid rgba(0, 0, 0, 0.08);
  border-radius: 8px;
  transition: all 0.2s ease;

  &:hover {
    background: rgba(255, 255, 255, 0.95);
    border-color: rgba(102, 126, 234, 0.2);
    transform: translateY(-1px);
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  }
}

.document-icon {
  flex-shrink: 0;
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(244, 63, 94, 0.1);
  border-radius: 8px;
  color: #f43f5e;

  svg {
    width: 24px;
    height: 24px;
  }
}

.document-info {
  flex: 1;
  min-width: 0;
}

.document-name {
  font-size: 14px;
  font-weight: 500;
  color: #2d3748;
  margin-bottom: 4px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.document-meta {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 12px;
  color: #a0aec0;
}

.document-size {
  font-weight: 500;
}

.document-type {
  padding: 2px 6px;
  background: rgba(102, 126, 234, 0.1);
  color: #667eea;
  border-radius: 4px;
  font-weight: 500;
  font-size: 10px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.remove-document-btn {
  flex-shrink: 0;
  width: 28px;
  height: 28px;
  border: none;
  border-radius: 6px;
  background: rgba(244, 63, 94, 0.1);
  color: #f43f5e;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s ease;

  &:hover {
    background: rgba(244, 63, 94, 0.2);
    transform: scale(1.05);
  }

  &:active {
    transform: scale(0.95);
  }
}

.attachment-notice {
  margin-top: 12px;
  padding: 8px 12px;
  background: rgba(34, 197, 94, 0.1);
  border: 1px solid rgba(34, 197, 94, 0.2);
  border-radius: 6px;
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: #059669;

  svg {
    flex-shrink: 0;
    color: #10b981;
  }
}

// 响应式设计
@media (max-width: 768px) {
  .input-box {
    padding: 16px;
    border-radius: 20px;
    gap: 12px;
  }

  .upload-btn,
  .send-btn {
    width: 44px;
    height: 44px;
  }

  .message-input {
    :deep(.van-field__control) {
      font-size: 16px; // 防止iOS缩放
    }
  }

  .image-preview-container {
    margin-top: 8px;
    gap: 8px;
  }

  .image-preview-item {
    min-width: 100px;
    max-width: 140px;
  }

  .preview-image {
    height: 60px;
  }

  // 文档附件移动端样式
  .document-attachments-container {
    margin-top: 8px;
    padding: 12px;
  }

  .document-attachment-item {
    padding: 10px;
    gap: 10px;
  }

  .document-icon {
    width: 36px;
    height: 36px;

    svg {
      width: 20px;
      height: 20px;
    }
  }

  .document-name {
    font-size: 13px;
  }

  .document-meta {
    gap: 8px;
    font-size: 11px;
  }

  .remove-document-btn {
    width: 26px;
    height: 26px;
  }

  .attachment-notice {
    padding: 6px 10px;
    font-size: 11px;
  }
}
</style>