# 使用官方 nginx 镜像作为基础镜像
FROM nginx:alpine

# 设置默认环境变量
ENV PRESET_Q1="创新券可以用来干什么？" \
    PRESET_Q2="创新券申领额度是多少？" \
    PRESET_Q3="谁能申领创新券？" \
    WELCOME_MESSAGE="欢迎使用慧智深度搜索大模型！我可以回答政策相关的问题。"

# 添加环境变量处理脚本
COPY docker-entrypoint.sh /
RUN chmod +x /docker-entrypoint.sh

# 复制 nginx 配置模板
COPY nginx.conf.template /etc/nginx/nginx.conf.template
COPY default.conf.template /etc/nginx/conf.d/default.conf.template

# 复制构建后的前端文件到 nginx 目录
COPY dist/ /usr/share/nginx/html/

# 暴露 80 端口
EXPOSE 80

# 使用 entrypoint 脚本处理环境变量
ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["nginx", "-g", "daemon off;"] 