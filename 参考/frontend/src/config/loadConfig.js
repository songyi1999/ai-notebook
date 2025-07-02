// 如果前端应用直接启动(不是通过config.js加载配置)
if (!window.APP_CONFIG) {
    window.APP_CONFIG = {
        presetQuestions: {
            question1: '创新券可以用来干什么？',
            question2: '创新券申领额度是多少？',
            question3: '谁能申领创新券？'
        },
        welcomeMessage: '欢迎使用慧智深度搜索大模型！我可以回答政策相关的问题。'
    };
    console.log('Using default APP_CONFIG');
} else {
    console.log('Using external APP_CONFIG');
} 