<template>
  <div class="app-root">
    <router-view v-slot="{ Component }">
      <transition name="page-fade" mode="out-in">
        <component :is="Component" />
      </transition>
    </router-view>

    <div class="global-watermark">
      <span>🌿 AI 生成内容仅供参考，不构成医疗诊断。如遇紧急情况请拨打 <b>400‑161‑9995</b></span>
    </div>
  </div>
</template>

<script setup>
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
  text-align: center;
  padding: 8px 16px;
  background: rgba(92, 184, 149, 0.08);
  color: var(--brand-text-muted);
  font-size: 12px;
  z-index: 999;
  backdrop-filter: blur(4px);
  border-top: 1px solid var(--brand-border);
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
