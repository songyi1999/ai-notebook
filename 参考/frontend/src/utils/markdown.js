import MarkdownIt from 'markdown-it'
import hljs from 'highlight.js'

const md = new MarkdownIt({
    html: true,
    linkify: true,
    typographer: true,
    highlight: function (str, lang) {
        if (lang && hljs.getLanguage(lang)) {
            try {
                return hljs.highlight(str, { language: lang }).value
            } catch (__) { }
        }
        return '' // 使用默认的转义
    }
})

export function markdownToHtml(text) {
    return md.render(text)
} 