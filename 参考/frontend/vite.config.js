import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import Components from 'unplugin-vue-components/vite'
import { VantResolver } from '@vant/auto-import-resolver'
import { isDev } from './config'
export default defineConfig({
    plugins: [
        vue(),
        Components({
            resolvers: [VantResolver()]
        })
    ],
    server: {
        proxy: {
            '/v1': {
                target: 'http://localhost:8000',
                changeOrigin: true
            }
        }
    }
}) 