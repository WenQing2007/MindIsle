<template>
  <el-container class="admin-layout">
    <el-aside width="220px" class="admin-aside">
      <div class="brand">
        <span class="brand-icon">🌿</span>
        <span class="brand-text">MindIsle 管理后台</span>
      </div>
      <el-menu
        :default-active="activeMenu"
        router
        background-color="#1f2d3d"
        text-color="#cfd8e3"
        active-text-color="#5b8ff9"
        class="admin-menu"
      >
        <el-menu-item index="/admin/users">👤 用户管理</el-menu-item>
        <el-menu-item index="/admin/content">📄 内容管理</el-menu-item>
        <el-menu-item index="/admin/logs">📋 日志管理</el-menu-item>
        <el-menu-item index="/admin/config">🛡️ 安全配置</el-menu-item>
      </el-menu>
    </el-aside>

    <el-container>
      <el-header class="admin-header">
        <div class="header-title">{{ pageTitle }}</div>
        <div class="header-actions">
          <el-tag size="small" type="success" effect="plain">管理员</el-tag>
          <el-button size="small" @click="logout">退出登录</el-button>
        </div>
      </el-header>
      <el-main class="admin-main">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()

const titles = {
  '/admin/users': '用户管理',
  '/admin/content': '内容管理',
  '/admin/logs': '日志管理',
  '/admin/config': '安全配置'
}
const pageTitle = computed(() => titles[route.path] || '后台管理')
const activeMenu = computed(() => route.path)

const logout = () => {
  localStorage.removeItem('token')
  localStorage.removeItem('userType')
  router.push('/admin/login')
}
</script>

<style scoped>
.admin-layout {
  min-height: 100vh;
}
.admin-aside {
  background: #1f2d3d;
  color: #cfd8e3;
  display: flex;
  flex-direction: column;
}
.brand {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  height: 60px;
  color: #fff;
  font-weight: 600;
  font-size: 15px;
  border-bottom: 1px solid rgba(255,255,255,0.08);
}
.brand-icon { font-size: 20px; }
.admin-menu { border-right: none; flex: 1; }
.admin-menu :deep(.el-menu-item.is-active) {
  background: rgba(91, 143, 249, 0.15) !important;
}
.admin-header {
  background: #fff;
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid #eef0f4;
  box-shadow: 0 1px 4px rgba(0,0,0,0.03);
}
.header-title { font-size: 17px; font-weight: 600; color: #33404f; }
.header-actions { display: flex; align-items: center; gap: 10px; }
.admin-main {
  background: #f5f7fa;
  padding: 20px;
}
</style>
