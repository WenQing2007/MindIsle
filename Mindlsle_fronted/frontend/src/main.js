import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
// 新增ElementPlus导入
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'

const app = createApp(App)
app.use(router)
app.use(ElementPlus) // 挂载
app.mount('#app')

