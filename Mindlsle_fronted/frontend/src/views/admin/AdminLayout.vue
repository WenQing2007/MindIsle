<template>
  <el-container class="admin-layout">
    <el-aside width="220px" class="admin-aside">
      <div class="brand">
        <div class="brand-logo">🌿</div>
        <div class="brand-info">
          <div class="brand-text">MindIsle</div>
          <div class="brand-sub">管理后台</div>
        </div>
      </div>
      <el-menu
        :default-active="activeMenu"
        router
        class="admin-menu"
      >
        <el-menu-item index="/admin/dashboard">
          <span class="menu-icon">📊</span><span>数据概览</span>
        </el-menu-item>
        <el-menu-item index="/admin/users">
          <span class="menu-icon">👤</span><span>用户管理</span>
        </el-menu-item>
        <el-menu-item index="/admin/content">
          <span class="menu-icon">📄</span><span>内容管理</span>
        </el-menu-item>
        <el-menu-item index="/admin/logs">
          <span class="menu-icon">📋</span><span>日志管理</span>
        </el-menu-item>
        <el-menu-item index="/admin/config">
          <span class="menu-icon">🛡️</span><span>安全配置</span>
        </el-menu-item>
      </el-menu>
      <div class="aside-footer">
        <div class="footer-hotline">
          <span class="hotline-icon">📞</span>
          <span>危机热线 400-161-9995</span>
        </div>
      </div>
    </el-aside>

    <el-container>
      <el-header class="admin-header">
        <div class="header-left">
          <el-breadcrumb separator="/">
            <el-breadcrumb-item :to="{ path: '/admin/dashboard' }">首页</el-breadcrumb-item>
            <el-breadcrumb-item v-if="pageTitle !== '数据概览'">{{ pageTitle }}</el-breadcrumb-item>
          </el-breadcrumb>
        </div>
        <div class="header-actions">
          <el-tooltip content="帮助文档" placement="bottom">
            <el-button circle>❓</el-button>
          </el-tooltip>
          <el-tag size="default" type="success" effect="light">
            <span class="admin-badge"></span> 管理员
          </el-tag>
          <el-dropdown @command="handleCommand">
            <div class="user-info">
              <el-avatar :size="36" style="background: linear-gradient(135deg, #5cb895, #8dd4b8); color: white;">A</el-avatar>
              <span class="user-name">Admin</span>
              <span class="el-icon--right">▾</span>
            </div>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="logout">🚪 退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
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
  '/admin/dashboard': '数据概览',
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

const handleCommand = (cmd) => {
  if (cmd === 'logout') logout()
}
</script>

<style scoped>
.admin-layout {
  min-height: 100vh;
}
.admin-aside {
  background: linear-gradient(180deg, #2d4a3e 0%, #3d5a4e 100%);
  color: #cfd8e3;
  display: flex;
  flex-direction: column;
  box-shadow: 2px 0 12px rgba(0,0,0,0.08);
}
.brand {
  display: flex;
  align-items: center;
  gap: 12px;
  height: 68px;
  padding: 0 20px;
  border-bottom: 1px solid rgba(255,255,255,0.08);
}
.brand-logo {
  width: 40px;
  height: 40px;
  border-radius: 12px;
  background: linear-gradient(135deg, #5cb895, #8dd4b8);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 22px;
  box-shadow: 0 4px 12px rgba(92,184,149,0.4);
}
.brand-info { display: flex; flex-direction: column; }
.brand-text { color: #fff; font-weight: 700; font-size: 18px; letter-spacing: 1px; }
.brand-sub { color: rgba(255,255,255,0.6); font-size: 12px; letter-spacing: 2px; }

.admin-menu {
  border-right: none !important;
  flex: 1;
  padding: 12px 10px !important;
  background: transparent !important;
}
.admin-menu :deep(.el-menu-item) {
  color: rgba(255,255,255,0.7) !important;
  border-radius: 10px !important;
  margin-bottom: 4px;
  height: 46px;
  line-height: 46px;
  font-weight: 500;
  transition: all 0.25s ease;
}
.admin-menu :deep(.el-menu-item:hover) {
  background: rgba(255,255,255,0.1) !important;
  color: #fff !important;
}
.admin-menu :deep(.el-menu-item.is-active) {
  background: linear-gradient(135deg, #5cb895, #3d9a78) !important;
  color: #fff !important;
  box-shadow: 0 4px 12px rgba(92,184,149,0.4);
}
.menu-icon { margin-right: 10px; font-size: 16px; }

.aside-footer {
  padding: 16px;
  border-top: 1px solid rgba(255,255,255,0.08);
}
.footer-hotline {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: rgba(255,255,255,0.5);
  padding: 10px 14px;
  background: rgba(255,255,255,0.05);
  border-radius: 10px;
}
.hotline-icon { font-size: 16px; }

.admin-header {
  background: #fff;
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid var(--brand-border);
  box-shadow: 0 1px 8px rgba(0,0,0,0.04);
  padding: 0 28px;
  height: 64px;
}
.header-actions { display: flex; align-items: center; gap: 16px; }
.admin-badge {
  display: inline-block;
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--brand-primary);
  margin-right: 4px;
}
.user-info {
  display: flex;
  align-items: center;
  gap: 10px;
  cursor: pointer;
  padding: 4px 12px 4px 4px;
  border-radius: 24px;
  transition: background 0.2s;
}
.user-info:hover { background: var(--brand-bg-soft); }
.user-name { font-weight: 600; color: var(--brand-text); font-size: 14px; }

.admin-main {
  background: var(--brand-bg);
  padding: 24px;
}
</style>