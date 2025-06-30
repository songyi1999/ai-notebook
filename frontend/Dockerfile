FROM nginx:alpine

# 将本地编译后的dist目录复制到nginx静态文件目录
COPY dist /usr/share/nginx/html

# 复制自定义Nginx配置，实现API转发
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"] 