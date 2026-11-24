<template>
  <div class="student-home">
    <div class="top-bar">
      <el-page-header :content="'你好，' + userName + ' 👋'"></el-page-header>
      <el-button size="small" @click="logout">退出登录</el-button>
    </div>

    <div class="home-banner">
      <div class="banner-text">
        <h2>欢迎来到 心屿 🌿</h2>
        <p>在这里，你可以倾诉烦恼、放松身心、认识自己。我们陪你一起成长。</p>
      </div>
      <div class="banner-emoji">🏝️</div>
    </div>

    <div class="section-title">💚 情绪陪伴</div>
    <el-row :gutter="20" class="feature-row">
      <el-col :xs="24" :sm="12" :md="8">
        <el-card shadow="hover" class="feature-card card-chat" @click="$router.push('/student/chat')">
          <div class="feature-icon">💬</div>
          <div class="feature-title">AI 心理陪伴</div>
          <div class="feature-desc">和 MindIsle AI 聊聊你的心情，文字或语音都可以</div>
          <div class="feature-tag">24 小时在线</div>
        </el-card>
      </el-col>
      <el-col :xs="24" :sm="12" :md="8">
        <el-card shadow="hover" class="feature-card card-hole" @click="$router.push('/student/treehole')">
          <div class="feature-icon">🌳</div>
          <div class="feature-title">树洞广场</div>
          <div class="feature-desc">匿名发布心事，在这里没有人认识你</div>
          <div class="feature-tag">温暖治愈</div>
        </el-card>
      </el-col>
      <el-col :xs="24" :sm="12" :md="8">
        <el-card shadow="hover" class="feature-card card-breath" @click="$router.push('/student/breath')">
          <div class="feature-icon">🌬️</div>
          <div class="feature-title">呼吸花园</div>
          <div class="feature-desc">跟随引导呼吸，让身心慢慢平静下来</div>
          <div class="feature-tag">放松训练</div>
        </el-card>
      </el-col>
    </el-row>

    <div class="section-title">🌱 自我探索</div>
    <el-row :gutter="20" class="feature-row">
      <el-col :xs="24" :sm="12" :md="8">
        <el-card shadow="hover" class="feature-card card-assess" @click="$router.push('/student/assessment')">
          <div class="feature-icon">📝</div>
          <div class="feature-title">测评小站</div>
          <div class="feature-desc">PHQ-9、GAD-7 等专业量表，了解自己的心理状态</div>
          <div class="feature-tag">科学测评</div>
        </el-card>
      </el-col>
      <el-col :xs="24" :sm="12" :md="8">
        <el-card shadow="hover" class="feature-card card-scenario" @click="$router.push('/student/scenario')">
          <div class="feature-icon">🎭</div>
          <div class="feature-title">情景演练</div>
          <div class="feature-desc">模拟真实场景，练习应对焦虑、沟通等技巧</div>
          <div class="feature-tag">角色扮演</div>
        </el-card>
      </el-col>
      <el-col :xs="24" :sm="12" :md="8">
        <el-card shadow="hover" class="feature-card card-resource" @click="$router.push('/student/resources')">
          <div class="feature-icon">📚</div>
          <div class="feature-title">心理资源</div>
          <div class="feature-desc">科普文章、冥想音频、解压小技巧</div>
          <div class="feature-tag">持续更新</div>
        </el-card>
      </el-col>
    </el-row>

    <div class="section-title">📄 我的报告</div>
    <el-row :gutter="20" class="feature-row">
      <el-col :xs="24" :sm="12" :md="8">
        <el-card shadow="hover" class="feature-card card-report" @click="$router.push('/student/reports')">
          <div class="feature-icon">📄</div>
          <div class="feature-title">心理报告</div>
          <div class="feature-desc">查看历次心理报告，或生成一份新的</div>
          <div class="feature-tag">专属档案</div>
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

.home-banner {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 28px 32px;
  margin: 10px 0 30px 0;
  border-radius: 20px;
  background: linear-gradient(135deg, #eaf5ef 0%, #f0f9ff 100%);
  border: 1px solid rgba(92, 184, 149, 0.15);
}

.banner-text h2 {
  margin: 0 0 8px 0;
  font-size: 22px;
  color: var(--brand-text);
}

.banner-text p {
  margin: 0;
  color: var(--brand-text-soft);
  font-size: 14px;
}

.banner-emoji {
  font-size: 60px;
  animation: floatSoft 3s ease-in-out infinite;
}

.section-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--brand-text);
  margin: 28px 4px 14px 4px;
}

.feature-row {
  margin-top: 0;
}

.feature-row .el-col {
  margin-bottom: 16px;
}

.feature-card {
  text-align: center;
  cursor: pointer;
  transition: all 0.3s ease;
  height: 100%;
  min-height: 180px;
  position: relative;
  overflow: hidden;
}

.feature-card:hover {
  transform: translateY(-6px);
}

.feature-card:hover :deep(.el-card) {
  box-shadow: 0 10px 28px rgba(170, 200, 230, 0.20) !important;
}

.feature-icon {
  font-size: 44px;
  margin-bottom: 10px;
}

.feature-title {
  font-size: 17px;
  font-weight: 600;
  margin-bottom: 6px;
  color: var(--brand-text);
}

.feature-desc {
  font-size: 13px;
  color: var(--brand-text-soft);
  margin-bottom: 10px;
  line-height: 1.5;
}

.feature-tag {
  display: inline-block;
  font-size: 11px;
  padding: 2px 12px;
  border-radius: 20px;
  background: rgba(255, 255, 255, 0.6);
  color: var(--brand-text-soft);
}

.card-chat :deep(.el-card__body)   { background: linear-gradient(135deg, #eaf4ff 0%, #f0f9ff 100%); }
.card-hole :deep(.el-card__body)   { background: linear-gradient(135deg, #e8f8f0 0%, #f0faf4 100%); }
.card-breath :deep(.el-card__body) { background: linear-gradient(135deg, #f0f8ff 0%, #e6f4ff 100%); }
.card-assess :deep(.el-card__body) { background: linear-gradient(135deg, #fff4e4 0%, #fff7ec 100%); }
.card-scenario :deep(.el-card__body){ background: linear-gradient(135deg, #f5efff 0%, #faf4ff 100%); }
.card-resource :deep(.el-card__body){ background: linear-gradient(135deg, #eaf5f0 0%, #f2faf4 100%); }
.card-report :deep(.el-card__body) { background: linear-gradient(135deg, #fff8f0 0%, #fffaf5 100%); }

.card-chat .feature-icon   { color: #5b9bd5; }
.card-hole .feature-icon   { color: #63b980; }
.card-breath .feature-icon { color: #7ab8d8; }
.card-assess .feature-icon { color: #e2a86e; }
.card-scenario .feature-icon{ color: #b08cd8; }
.card-resource .feature-icon{ color: #6fb89a; }
.card-report .feature-icon { color: #d89a6a; }

:deep(.el-alert--info) {
  border-radius: 14px;
  background-color: rgba(255, 255, 255, 0.65) !important;
  border-color: #dbeafe !important;
}
</style>