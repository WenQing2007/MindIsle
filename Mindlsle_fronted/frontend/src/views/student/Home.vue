<template>
  <div class="student-home">
    <el-page-header content="MindIsle 学生主页"></el-page-header>
    <el-row :gutter="20" style="margin-top:20px">
      <el-col :span="8">
        <el-card shadow="hover">
          <div style="font-size:18px;text-align:center">树洞板块</div>
          <el-button type="primary" @click="$router.push('/student/treehole')" style="margin-top:10px">进入树洞</el-button>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card shadow="hover">
          <div style="font-size:18px;text-align:center">心理测评</div>
          <el-button type="success" style="margin-top:10px">开始测评</el-button>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card shadow="hover">
          <div style="font-size:18px;text-align:center">预约咨询</div>
          <el-button type="warning" style="margin-top:10px">预约咨询师</el-button>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
</script>

<style scoped>
.student-home {
  padding: 30px;
}
</style>
