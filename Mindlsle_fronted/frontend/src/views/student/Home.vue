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
        <el-card shadow="hover" class="feature-card" @click="$router.push('/student/reports')">
          <div class="feature-icon report-icon">📄</div>
          <div class="feature-title">我的心理报告</div>
          <div class="feature-desc">查看历史报告 · 生成新报告</div>
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
  min-height: 100vh;
  box-sizing: border-box;
  background: linear-gradient(135deg, #fdfbf7 0%, #f0f7ff 100%);
}

.top-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

:deep(.el-card) {
  border-radius: 22px !important;
  border: 1px solid rgba(255, 255, 255, 0.75) !important;
  box-shadow: 0 4px 18px rgba(170, 200, 230, 0.12) !important;
}

:deep(.el-row .el-col:nth-child(1) .el-card__body) {
  background-color: #eaf4ff;
}
:deep(.el-row .el-col:nth-child(2) .el-card__body) {
  background-color: #e8f8f0;
}
:deep(.el-row .el-col:nth-child(3) .el-card__body) {
  background-color: #fff4e4;
}

.feature-card {
  text-align: center;
  cursor: pointer;
  transition: all 0.3s ease;
}
.feature-card:hover {
  transform: translateY(-6px);
}
.feature-card:hover :deep(.el-card) {
  box-shadow: 0 10px 28px rgba(170, 200, 230, 0.20) !important;
}

.feature-icon {
  font-size: 48px;
  margin-bottom: 12px;
}
.feature-title {
  font-size: 18px;
  font-weight: 500;
  margin-bottom: 6px;
  color: #44546a;
}
.feature-desc {
  font-size: 14px;
  color: #718096;
}

.chat-icon   { color: #5b9bd5; }
.hole-icon   { color: #63b980; }
.report-icon { color: #e2a86e; }

:deep(.el-alert--info) {
  border-radius:14px;
  background-color: rgba(255,255,255,0.65) !important;
  border-color:#dbeafe !important;
}
</style>
