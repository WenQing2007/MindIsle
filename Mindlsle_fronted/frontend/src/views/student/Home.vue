<template>
  <div class="student-home">
    <div class="top-bar">
      <el-page-header :content="'你好，' + userName + ' 👋'"></el-page-header>
      <el-button size="small" @click="logout">退出登录</el-button>
    </div>

    <el-row :gutter="20" style="margin-top:20px">
      <el-col :span="8">
        <el-card shadow="hover" class="feature-card" @click="$router.push('/student/chat')">
          <div class="feature-icon chat-icon">💬</div>
          <div class="feature-title">AI 心理陪伴</div>
          <div class="feature-desc">和 MindIsle AI 聊聊你的心情</div>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card shadow="hover" class="feature-card" @click="$router.push('/student/treehole')">
          <div class="feature-icon hole-icon">🌳</div>
          <div class="feature-title">树洞板块</div>
          <div class="feature-desc">匿名发布心事，释放情绪</div>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card shadow="hover" class="feature-card" @click="genReport">
          <div class="feature-icon report-icon">📄</div>
          <div class="feature-title">我的心理报告</div>
          <div class="feature-desc">生成你的个性化心理成长报告</div>
        </el-card>
      </el-col>
    </el-row>

    <el-alert
      style="margin-top:30px"
      type="info"
      :closable="false"
      title="MindIsle 温馨提示：AI 生成内容仅供参考，不构成诊断结论。如遇紧急情况请拨打全国心理援助热线 400-161-9995"
    />
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import axios from 'axios'

const router = useRouter()

const userName = computed(() => {
  return localStorage.getItem('name') || '同学'
})

const logout = () => {
  localStorage.removeItem('token')
  localStorage.removeItem('userType')
  localStorage.removeItem('student_id')
  localStorage.removeItem('name')
  router.push('/student/login')
}

const genReport = async () => {
  const sid = localStorage.getItem('student_id')
  if (!sid) {
    alert("请先重新登录")
    return
  }
  try {
    alert("正在生成报告，请稍候...")
    const res = await axios.post(`/api/report/student/${sid}`)
    const data = res.data
    if (data.code === 200) {
      alert("报告已生成！文件保存在：" + data.data.filepath)
      window.open(`/api/report/download?filepath=${encodeURIComponent(data.data.filepath)}`, '_blank')
    } else {
      alert(data.msg || "生成失败")
    }
  } catch (err) {
    alert("生成失败，请检查后端服务是否启动")
  }
}
</script>

<style scoped>
.student-home {
  padding: 30px;
}
.top-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.feature-card {
  text-align: center;
  cursor: pointer;
  transition: transform .2s;
}
.feature-card:hover {
  transform: translateY(-4px);
}
.feature-icon {
  font-size: 48px;
  margin-bottom: 12px;
}
.feature-title {
  font-size: 18px;
  font-weight: bold;
  margin-bottom: 6px;
  color: #303133;
}
.feature-desc {
  font-size: 13px;
  color: #909399;
}
.chat-icon   { color: #409eff; }
.hole-icon   { color: #67c23a; }
.report-icon { color: #e6a23c; }
</style>