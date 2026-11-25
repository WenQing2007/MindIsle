<template>
  <div class="login-container">
    <div class="bg-decoration">
      <div class="blob blob-1"></div>
      <div class="blob blob-2"></div>
      <div class="blob blob-3"></div>
    </div>

    <div class="login-wrapper">
      <div class="brand-panel">
        <div class="brand-logo">🌿</div>
        <h1 class="brand-title">MindIsle</h1>
        <p class="brand-subtitle">心屿 · 青少年心理关怀平台</p>
        <div class="brand-features">
          <div class="feature-item"><span class="f-emoji">🎯</span><span>AI 智能心理评估</span></div>
          <div class="feature-item"><span class="f-emoji">🌳</span><span>树洞匿名倾诉</span></div>
          <div class="feature-item"><span class="f-emoji">🛡️</span><span>风险预警守护</span></div>
          <div class="feature-item"><span class="f-emoji">📚</span><span>专业心理资源</span></div>
        </div>
        <div class="brand-footer">v1.0.0 · 管理后台</div>
      </div>

      <div class="login-panel">
        <div class="login-card">
          <div class="card-header">
            <h2>管理员登录</h2>
            <p>欢迎回来，请登录您的管理员账户</p>
          </div>

          <el-form ref="loginFormRef" :model="loginForm" @submit.prevent="handleLogin">
            <el-form-item>
              <el-input v-model="loginForm.username" placeholder="请输入管理员账号" size="large">
                <template #prefix><el-icon><User /></el-icon></template>
              </el-input>
            </el-form-item>
            <el-form-item>
              <el-input v-model="loginForm.password" type="password" placeholder="请输入密码" size="large" show-password @keyup.enter="handleLogin">
                <template #prefix><el-icon><Lock /></el-icon></template>
              </el-input>
            </el-form-item>
            <el-form-item>
              <el-button type="primary" size="large" :loading="loading" class="login-btn" @click="handleLogin">登 录</el-button>
            </el-form-item>
          </el-form>

          <div class="login-tips">
            <el-alert type="info" :closable="false" show-icon title="仅限授权管理员访问，所有操作将被记录" />
          </div>

          <div class="card-footer">
            <span>遇到问题？</span>
            <el-tag type="success" effect="light">联系系统管理员</el-tag>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { User, Lock } from '@element-plus/icons-vue'
import axios from 'axios'

const router = useRouter()
const loginFormRef = ref(null)
const loading = ref(false)
const loginForm = ref({ username: '', password: '' })

const handleLogin = async () => {
  if (!loginForm.value.username || !loginForm.value.password) {
    ElMessage.warning('请输入账号和密码')
    return
  }
  loading.value = true
  try {
    const res = await axios.post('/api/admin/login', loginForm.value)
    const data = res.data
    if (data.code === 200) {
      localStorage.setItem('token', data.data.token)
      localStorage.setItem('userType', 'admin')
      ElMessage.success('登录成功，欢迎回来！')
      router.push('/admin/dashboard')
    } else {
      ElMessage.error(data.msg || '登录失败')
    }
  } catch (err) {
    console.error(err)
    ElMessage.error('请求异常，请检查后端服务是否启动')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-container {
  height: 100vh;
  display: flex;
  justify-content: center;
  align-items: center;
  background: linear-gradient(135deg, #2d4a3e 0%, #3d5a4e 50%, #4a6b5d 100%);
  position: relative;
  overflow: hidden;
}
.bg-decoration { position: absolute; inset: 0; pointer-events: none; }
.blob { position: absolute; border-radius: 50%; filter: blur(80px); opacity: 0.4; }
.blob-1 { width: 400px; height: 400px; background: #5cb895; top: -100px; left: -100px; animation: floatBlob1 12s ease-in-out infinite; }
.blob-2 { width: 350px; height: 350px; background: #8dd4b8; bottom: -80px; right: -80px; animation: floatBlob2 15s ease-in-out infinite; }
.blob-3 { width: 250px; height: 250px; background: #f8b4c0; top: 40%; right: 20%; opacity: 0.2; animation: floatBlob1 10s ease-in-out infinite reverse; }
@keyframes floatBlob1 { 0%, 100% { transform: translate(0,0) scale(1); } 50% { transform: translate(40px,-30px) scale(1.1); } }
@keyframes floatBlob2 { 0%, 100% { transform: translate(0,0) scale(1); } 50% { transform: translate(-30px,40px) scale(1.05); } }

.login-wrapper {
  position: relative;
  z-index: 1;
  display: flex;
  width: 900px;
  min-height: 520px;
  border-radius: 24px;
  overflow: hidden;
  box-shadow: 0 30px 80px rgba(0,0,0,0.3);
}
.brand-panel {
  flex: 1;
  background: linear-gradient(180deg, rgba(92,184,149,0.95) 0%, rgba(61,154,120,0.98) 100%);
  padding: 48px 40px;
  color: #fff;
  display: flex;
  flex-direction: column;
}
.brand-logo {
  font-size: 64px;
  width: 100px; height: 100px;
  background: rgba(255,255,255,0.2);
  border-radius: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 24px;
  backdrop-filter: blur(10px);
}
.brand-title { font-size: 42px; font-weight: 800; margin: 0 0 8px 0; letter-spacing: 2px; }
.brand-subtitle { font-size: 15px; opacity: 0.85; margin: 0 0 40px 0; letter-spacing: 1px; }
.brand-features { display: flex; flex-direction: column; gap: 16px; flex: 1; }
.feature-item {
  display: flex; align-items: center; gap: 12px;
  padding: 10px 16px;
  background: rgba(255,255,255,0.12);
  border-radius: 12px;
  font-size: 14px;
  backdrop-filter: blur(5px);
}
.f-emoji { font-size: 18px; }
.brand-footer { font-size: 12px; opacity: 0.6; letter-spacing: 1px; margin-top: 20px; }

.login-panel { flex: 1; background: #fff; display: flex; align-items: center; justify-content: center; }
.login-card { width: 100%; padding: 48px 44px; }
.card-header { margin-bottom: 36px; }
.card-header h2 { margin: 0 0 8px 0; font-size: 26px; font-weight: 700; color: #2d4a3e; }
.card-header p { margin: 0; font-size: 14px; color: #6b8a7c; }

.login-btn {
  width: 100%; height: 48px; font-size: 16px; letter-spacing: 8px; font-weight: 600;
  border-radius: 12px;
  background: linear-gradient(135deg, #5cb895, #3d9a78) !important;
  border: none !important;
  box-shadow: 0 6px 20px rgba(92,184,149,0.35) !important;
}
.login-btn:hover { transform: translateY(-2px); box-shadow: 0 8px 24px rgba(92,184,149,0.45) !important; }

.login-tips { margin: 8px 0 20px 0; }
.card-footer { text-align: center; margin-top: 20px; font-size: 13px; color: #6b8a7c; display: flex; align-items: center; justify-content: center; gap: 10px; }

@media (max-width: 768px) {
  .login-wrapper { flex-direction: column; width: 95%; }
  .brand-panel { padding: 30px; }
  .login-card { padding: 30px; }
}
</style>