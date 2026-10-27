<template>
  <div class="home-layout">
    <!-- 侧边导航 -->
    <el-aside width="220px" class="aside">
      <el-menu router default-active="/student/home" class="menu">
        <el-menu-item index="/student/home">首页</el-menu-item>
        <el-menu-item index="/student/treehole">树洞广场</el-menu-item>
        <el-menu-item index="/student/report">我的心理报告</el-menu-item>
      </el-menu>
    </el-aside>
    <!-- 右侧主内容区域 -->
    <el-main class="main">
      <el-page-header content="MindIsle 首页"></el-page-header>
      <el-card style="margin-top:20px;width:600px;">
        <template #header>
          <div>项目主页</div>
        </template>
        <p>Vue3 + Vite + ElementPlus 前端项目</p>
      </el-card>
    </el-main>
  </div>
</template>

<script setup>
</script>

<style scoped>
.home-layout {
  display: flex;
  height: calc(100vh - 20px);
}
.aside {
  background-color: #fff;
  border-right: 1px solid #eee;
  padding-top: 20px;
}
.menu {
  border-right: none;
}
.main {
  padding: 20px;
}
</style>

