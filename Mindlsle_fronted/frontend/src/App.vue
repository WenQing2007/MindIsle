<template>
  <router-view />
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
</style>
