<template>
  <div class="app-root">
    <router-view v-slot="{ Component }">
      <transition name="page-fade" mode="out-in">
        <component :is="Component" />
      </transition>
    </router-view>

    <div class="global-watermark">
      <span class="wm-left">🌿 AI 生成内容仅供参考，不构成医疗诊断。如遇紧急情况请拨打 <b>400‑161‑9995</b></span>
      <router-link
        v-if="showAdminLink"
        to="/admin/login"
        class="wm-admin"
        title="管理后台（需管理员账号）"
      >管理后台</router-link>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()
const showAdminLink = computed(() => {
  // 未登录或正在登录页时不展示，避免干扰；已登录任意角色都展示入口
  if (!localStorage.getItem('token')) return false
  const p = route.path
  return !(p.includes('/login') || p.includes('/register'))
})
</script>

<style>
/* 覆盖Element Plus全局背景变量，所有页面生效 */
:root {
  --el-bg-color: transparent !important;
}

html,
body {
  margin: 0;
  padding: 0;
  min-height: 100vh;
  background: linear-gradient(135deg, #fdfbf7 0%, #f0f7ff 100%) !important;
}

#app {
  min-height: 100vh;
  background: transparent !important;
}

/* 干掉el-container、el-main默认白色 */
.el-container,
.el-main {
  background-color: transparent !important;
}

.app-root {
  min-height: 100vh;
  padding-bottom: 28px;
  position: relative;
}

.global-watermark {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 20px;
  text-align: center;
  padding: 8px 16px;
  background: rgba(92, 184, 149, 0.08);
  color: var(--brand-text-muted);
  font-size: 12px;
  z-index: 999;
  backdrop-filter: blur(4px);
  border-top: 1px solid var(--brand-border);
}

.wm-admin {
  color: var(--brand-primary-dark);
  text-decoration: none;
  font-weight: 500;
  padding: 3px 12px;
  border: 1px solid var(--brand-border);
  border-radius: 20px;
  background: rgba(255, 255, 255, 0.55);
  transition: all 0.2s ease;
  white-space: nowrap;
}

.wm-admin:hover {
  background: var(--brand-primary, #5b8ff9);
  color: #fff;
  border-color: transparent;
}

.wm-admin:visited {
  color: inherit;
}

.global-watermark b {
  color: var(--brand-primary-dark);
}

.page-fade-enter-active,
.page-fade-leave-active {
  transition: opacity 0.25s ease, transform 0.25s ease;
}

.page-fade-enter-from {
  opacity: 0;
  transform: translateY(8px);
}

.page-fade-leave-to {
  opacity: 0;
  transform: translateY(-8px);
}
</style>
