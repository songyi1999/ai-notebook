/**
 * MessageBubble组件测试
 * 测试图片缩略图显示功能
 */

import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia } from 'pinia'
import MessageBubble from '../../src/components/MessageBubble.vue'

// Mock vant组件
vi.mock('vant', () => ({
    showToast: vi.fn(),
    Dialog: vi.fn()
}))

// Mock moment
vi.mock('moment', () => ({
    default: vi.fn(() => ({
        format: vi.fn(() => '10:30')
    }))
}))

// Mock markdown-it
vi.mock('markdown-it', () => ({
    default: vi.fn(() => ({
        render: vi.fn((text) => `<p>${text}</p>`)
    }))
}))

// Mock chat store
const mockChatStore = {
    handlePresetQuestion: vi.fn()
}

vi.mock('../../src/store/chat', () => ({
    useChatStore: () => mockChatStore
}))

describe('MessageBubble 图片缩略图显示功能', () => {
    let wrapper
    const pinia = createPinia()

    // 创建包含图片的用户消息
    const createUserMessageWithImages = (text, images) => ({
        id: '1',
        role: 'user',
        content: text + (images.length > 0 ? '\n\n图片:\n' + images.join('\n') : ''),
        timestamp: new Date().toISOString()
    })

    // 创建不包含图片的用户消息
    const createUserMessageWithoutImages = (text) => ({
        id: '1',
        role: 'user',
        content: text,
        timestamp: new Date().toISOString()
    })

    // 创建AI消息
    const createAssistantMessage = (content) => ({
        id: '2',
        role: 'assistant',
        content: content,
        timestamp: new Date().toISOString()
    })

    afterEach(() => {
        if (wrapper) {
            wrapper.unmount()
        }
    })

    it('应该解析单张图片的用户消息', () => {
        const message = createUserMessageWithImages('请分析这张图片', [
            '/api/v1/files/image1.jpg'
        ])

        wrapper = mount(MessageBubble, {
            props: { message },
            global: {
                plugins: [pinia]
            }
        })

        const vm = wrapper.vm
        expect(vm.parsedUserMessage.text).toBe('请分析这张图片')
        expect(vm.parsedUserMessage.images).toEqual(['/api/v1/files/image1.jpg'])
    })

    it('应该解析多张图片的用户消息', () => {
        const message = createUserMessageWithImages('请分析这些图片', [
            '/api/v1/files/image1.jpg',
            '/api/v1/files/image2.png',
            'https://example.com/image3.gif'
        ])

        wrapper = mount(MessageBubble, {
            props: { message },
            global: {
                plugins: [pinia]
            }
        })

        const vm = wrapper.vm
        expect(vm.parsedUserMessage.text).toBe('请分析这些图片')
        expect(vm.parsedUserMessage.images).toHaveLength(3)
        expect(vm.parsedUserMessage.images).toEqual([
            '/api/v1/files/image1.jpg',
            '/api/v1/files/image2.png',
            'https://example.com/image3.gif'
        ])
    })

    it('应该正确处理没有图片的用户消息', () => {
        const message = createUserMessageWithoutImages('这是一个普通的文本消息')

        wrapper = mount(MessageBubble, {
            props: { message },
            global: {
                plugins: [pinia]
            }
        })

        const vm = wrapper.vm
        expect(vm.parsedUserMessage.text).toBe('这是一个普通的文本消息')
        expect(vm.parsedUserMessage.images).toEqual([])
    })

    it('应该显示图片缩略图', async () => {
        const message = createUserMessageWithImages('请看这张图片', [
            '/api/v1/files/test-image.jpg'
        ])

        wrapper = mount(MessageBubble, {
            props: { message },
            global: {
                plugins: [pinia]
            }
        })

        // 检查是否显示图片容器
        const imageContainer = wrapper.find('.user-message-images')
        expect(imageContainer.exists()).toBe(true)

        // 检查是否显示图片缩略图
        const imageItem = wrapper.find('.user-image-item')
        expect(imageItem.exists()).toBe(true)

        // 检查图片元素
        const image = wrapper.find('.user-image')
        expect(image.exists()).toBe(true)
        expect(image.attributes('src')).toBe('/api/v1/files/test-image.jpg')
        expect(image.attributes('alt')).toBe('用户上传图片 1')
    })

    it('应该显示多张图片的数量提示', async () => {
        const message = createUserMessageWithImages('请分析这些图片', [
            '/api/v1/files/image1.jpg',
            '/api/v1/files/image2.png',
            '/api/v1/files/image3.gif'
        ])

        wrapper = mount(MessageBubble, {
            props: { message },
            global: {
                plugins: [pinia]
            }
        })

        // 检查图片数量提示
        const countTip = wrapper.find('.images-count-tip')
        expect(countTip.exists()).toBe(true)
        expect(countTip.text()).toContain('3 张图片')

        // 检查是否显示所有图片
        const imageItems = wrapper.findAll('.user-image-item')
        expect(imageItems).toHaveLength(3)

        // 检查图片序号
        const imageIndexes = wrapper.findAll('.image-index')
        expect(imageIndexes).toHaveLength(3)
        expect(imageIndexes[0].text()).toBe('1')
        expect(imageIndexes[1].text()).toBe('2')
        expect(imageIndexes[2].text()).toBe('3')
    })

    it('单张图片不应该显示数量提示', async () => {
        const message = createUserMessageWithImages('请看这张图片', [
            '/api/v1/files/single-image.jpg'
        ])

        wrapper = mount(MessageBubble, {
            props: { message },
            global: {
                plugins: [pinia]
            }
        })

        // 单张图片不应该显示数量提示
        const countTip = wrapper.find('.images-count-tip')
        expect(countTip.exists()).toBe(false)

        // 但应该显示图片
        const imageItem = wrapper.find('.user-image-item')
        expect(imageItem.exists()).toBe(true)
    })

    it('应该处理图片预览点击事件', async () => {
        const message = createUserMessageWithImages('请看这张图片', [
            '/api/v1/files/preview-test.jpg'
        ])

        wrapper = mount(MessageBubble, {
            props: { message },
            global: {
                plugins: [pinia]
            }
        })

        const vm = wrapper.vm
        const imageItem = wrapper.find('.user-image-item')

        // 模拟点击图片
        await imageItem.trigger('click')

        // 检查预览状态
        expect(vm.showImagePreview).toBe(true)
        expect(vm.previewImageUrl).toBe('/api/v1/files/preview-test.jpg')
    })

    it('应该处理图片加载错误', async () => {
        const message = createUserMessageWithImages('图片加载测试', [
            '/api/v1/files/error-image.jpg'
        ])

        wrapper = mount(MessageBubble, {
            props: { message },
            global: {
                plugins: [pinia]
            }
        })

        const vm = wrapper.vm
        const image = wrapper.find('.user-image')

        // 模拟图片加载错误
        const mockEvent = {
            target: {
                src: '/api/v1/files/error-image.jpg',
                style: {}
            }
        }

        vm.handleImageError(mockEvent, 0)

        // 检查错误处理
        expect(mockEvent.target.style.opacity).toBe('0.5')
        expect(mockEvent.target.style.filter).toBe('grayscale(100%)')
    })

    it('应该处理图片加载成功', async () => {
        const message = createUserMessageWithImages('图片加载测试', [
            '/api/v1/files/success-image.jpg'
        ])

        wrapper = mount(MessageBubble, {
            props: { message },
            global: {
                plugins: [pinia]
            }
        })

        const vm = wrapper.vm

        // 模拟图片加载成功
        const mockEvent = {
            target: {
                src: '/api/v1/files/success-image.jpg',
                style: {}
            }
        }

        vm.handleImageLoad(mockEvent, 0)

        // 检查成功处理
        expect(mockEvent.target.style.opacity).toBe('1')
        expect(mockEvent.target.style.filter).toBe('none')
    })

    it('不应该为AI消息显示图片缩略图', () => {
        const message = createAssistantMessage('这是AI的回复消息')

        wrapper = mount(MessageBubble, {
            props: { message },
            global: {
                plugins: [pinia]
            }
        })

        // AI消息不应该显示图片容器
        const imageContainer = wrapper.find('.user-message-images')
        expect(imageContainer.exists()).toBe(false)

        // 应该显示AI消息内容
        const aiContent = wrapper.find('.text')
        expect(aiContent.exists()).toBe(true)
    })

    it('应该过滤无效的图片URL', () => {
        const message = {
            id: '1',
            role: 'user',
            content: '请分析图片\n\n图片:\n/api/v1/files/valid.jpg\n\ninvalid-url\n\nhttps://example.com/valid.png',
            timestamp: new Date().toISOString()
        }

        wrapper = mount(MessageBubble, {
            props: { message },
            global: {
                plugins: [pinia]
            }
        })

        const vm = wrapper.vm
        // 应该只包含有效的图片URL
        expect(vm.parsedUserMessage.images).toEqual([
            '/api/v1/files/valid.jpg',
            'https://example.com/valid.png'
        ])
    })
}) 