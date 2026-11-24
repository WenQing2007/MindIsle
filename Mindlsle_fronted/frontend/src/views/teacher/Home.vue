<template>
  <div class="teacher-home">
    <div class="top-bar">
      <el-page-header :content="'老师好，' + userName + ' 👩‍🏫'"></el-page-header>
      <el-button size="small" @click="logout">退出登录</el-button>
    </div>

    <div class="home-banner">
      <div class="banner-text">
        <h2>MindIsle 心屿 · 教师工作台 🌿</h2>
        <p>实时掌握班级心理动态，及时发现风险信号，陪伴每一位学生健康成长。</p>
      </div>
      <div class="banner-emoji">📊</div>
    </div>

    <div class="section-title">📈 今日概览</div>
    <el-row :gutter="16" class="stat-row">
      <el-col :xs="12" :sm="6">
        <el-card shadow="hover" class="stat-card card-stu">
          <div class="stat-num">{{ stats.student_count || 0 }}</div>
          <div class="stat-label">👥 已注册学生</div>
        </el-card>
      </el-col>
      <el-col :xs="12" :sm="6">
        <el-card shadow="hover" class="stat-card card-session">
          <div class="stat-num">{{ stats.session_count || 0 }}</div>
          <div class="stat-label">💬 AI 会话总数</div>
        </el-card>
      </el-col>
      <el-col :xs="12" :sm="6">
        <el-card shadow="hover" class="stat-card card-warn">
          <div class="stat-num warn-critical">{{ warnStats.critical }}</div>
          <div class="stat-label">🔴 红色预警</div>
        </el-card>
      </el-col>
      <el-col :xs="12" :sm="6">
        <el-card shadow="hover" class="stat-card card-warn2">
          <div class="stat-num warn-total">{{ warnStats.total }}</div>
          <div class="stat-label">⚠️ 需关注总计</div>
        </el-card>
      </el-col>
    </el-row>

    <div class="section-title">🛠️ 教师功能</div>
    <el-row :gutter="20" class="feature-row">
      <el-col :xs="24" :sm="12" :md="8">
        <el-card shadow="hover" class="feature-card card-warnlist" @click="$router.push('/teacher/warnlist')">
          <div class="feature-icon">🔔</div>
          <div class="feature-title">风险预警</div>
          <div class="feature-desc">查看有心理风险的学生名单，及时介入干预</div>
          <div class="feature-tag">{{ warnStats.total }} 人需关注</div>
        </el-card>
      </el-col>
      <el-col :xs="24" :sm="12" :md="8">
        <el-card shadow="hover" class="feature-card card-students" @click="$router.push('/teacher/students')">
          <div class="feature-icon">👥</div>
          <div class="feature-title">学生名册</div>
          <div class="feature-desc">浏览所有注册学生的基本信息和心理档案</div>
          <div class="feature-tag">{{ stats.student_count || 0 }} 名学生</div>
        </el-card>
      </el-col>
      <el-col :xs="24" :sm="12" :md="8">
        <el-card shadow="hover" class="feature-card card-reports" @click="$router.push('/teacher/reports')">
          <div class="feature-icon">📄</div>
          <div class="feature-title">报告中心</div>
          <div class="feature-desc">生成成长报告、班级报告、危机处置报告</div>
          <div class="feature-tag">专业生成</div>
        </el-card>
      </el-col>
    </el-row>

    <div class="section-title">📣 最新预警</div>
    <el-card shadow="hover" class="latest-card">
      <el-empty v-if="warnings.length === 0" description="暂无风险预警，班级状态良好 💚"></el-empty>
      <el-timeline v-else>
        <el-timeline-item
          v-for="(w, idx) in warnings.slice(0, 5)"
          :key="idx"
          :timestamp="w.assessed_at"
          placement="top"
          :color="timelineColor(w.risk_level)"
        >
          <div class="tl-content">
            <el-tag :type="tagType(w.risk_level)" effect="dark" size="small">
              {{ w.risk_level_cn }}色预警
            </el-tag>
            <span class="tl-name">{{ w.name }}</span>
            <span class="tl-info">{{ w.school || '' }} · {{ w.grade || '' }}</span>
            <span class="tl-score">风险分 {{ (w.risk_score * 100).toFixed(0) }}</span>
          </div>
          <div v-if="w.indicators" class="tl-indicators">
            关键指标：{{ w.indicators }}
          </div>
        </el-timeline-item>
      </el-timeline>
      <div v-if="warnings.length > 5" class="more-link">
        <el-button link type="primary" @click="$router.push('/teacher/warnlist')">
          查看全部 {{ warnings.length }} 条预警 →
        </el-button>
      </div>
    </el-card>

    <el-alert
      style="margin-top:30px"
      type="warning"
      :closable="false"
      title="⚠️ MindIsle 教师工作台：AI 评估结果仅供参考，红色/橙色预警建议立即联系学校心理干预小组介入。紧急情况请拨打全国心理援助热线 400-161-9995"
    />
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import axios from 'axios'

const router = useRouter()
const stats = ref({})
const warnings = ref([])
const userName = computed(() => localStorage.getItem('name') || '老师')

const warnStats = computed(() => ({
  total: warnings.value.length,
  critical: warnings.value.filter(w => w.risk_level === 'critical').length,
  high: warnings.value.filter(w => w.risk_level === 'high').length,
}))

const tagType = (level) => ({ critical: 'danger', high: 'warning', medium: '' })[level] || 'info'
const timelineColor = (level) => ({ critical: '#f56c6c', high: '#f56c1c', medium: '#e6a23c' })[level] || '#67c23a'

const loadStats = async () => {
  try {
    const res = await axios.get('/health')
    if (res.data.code === 200) stats.value = res.data.data.stats
  } catch (e) {}
}

const loadWarnings = async () => {
  try {
    const res = await axios.get('/api/teacher/warnings')
    if (res.data.code === 200) warnings.value = res.data.data
  } catch (e) {}
}

const logout = () => {
  localStorage.removeItem('token')
  localStorage.removeItem('userType')
  localStorage.removeItem('name')
  router.push('/teacher/login')
}

onMounted(() => { loadStats(); loadWarnings() })
</script>

<style scoped>
.teacher-home {
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
  background: linear-gradient(135deg, #eaf0f9 0%, #f0f9ff 100%);
  border: 1px solid rgba(91, 155, 213, 0.2);
}
.banner-text h2 { margin: 0 0 8px 0; font-size: 22px; color: #2c3e50; }
.banner-text p { margin: 0; color: #606266; font-size: 14px; }
.banner-emoji { font-size: 60px; animation: floatSoft 3s ease-in-out infinite; }
@keyframes floatSoft {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-8px); }
}
.section-title { font-size: 16px; font-weight: 600; color: #2c3e50; margin: 28px 4px 14px 4px; }
.stat-row .el-col { margin-bottom: 16px; }
.stat-card { text-align: center; transition: all 0.3s ease; cursor: pointer; }
.stat-card:hover { transform: translateY(-4px); }
.stat-num { font-size: 32px; font-weight: 700; color: #2c3e50; }
.warn-critical { color: #f56c6c; }
.warn-total { color: #e6a23c; }
.stat-label { font-size: 13px; color: #909399; margin-top: 4px; }
.card-stu :deep(.el-card__body)     { background: linear-gradient(135deg, #eaf4ff 0%, #f0f9ff 100%); }
.card-session :deep(.el-card__body) { background: linear-gradient(135deg, #e8f8f0 0%, #f0faf4 100%); }
.card-warn :deep(.el-card__body)    { background: linear-gradient(135deg, #fff0f0 0%, #fff5f5 100%); }
.card-warn2 :deep(.el-card__body)   { background: linear-gradient(135deg, #fff8e4 0%, #fffbe8 100%); }
.feature-row .el-col { margin-bottom: 16px; }
.feature-card { text-align: center; cursor: pointer; transition: all 0.3s ease; height: 100%; min-height: 180px; }
.feature-card:hover { transform: translateY(-6px); }
.feature-icon { font-size: 44px; margin-bottom: 10px; }
.feature-title { font-size: 17px; font-weight: 600; margin-bottom: 6px; color: #2c3e50; }
.feature-desc { font-size: 13px; color: #606266; margin-bottom: 10px; line-height: 1.5; }
.feature-tag { display: inline-block; font-size: 11px; padding: 2px 12px; border-radius: 20px; background: rgba(255,255,255,0.6); color: #909399; }
.card-warnlist :deep(.el-card__body) { background: linear-gradient(135deg, #ffe8e8 0%, #fff0f0 100%); }
.card-students :deep(.el-card__body) { background: linear-gradient(135deg, #eaf4ff 0%, #f0f9ff 100%); }
.card-reports :deep(.el-card__body)  { background: linear-gradient(135deg, #fff4e4 0%, #fff7ec 100%); }
.card-warnlist .feature-icon { color: #f56c6c; }
.card-students .feature-icon { color: #5b9bd5; }
.card-reports  .feature-icon { color: #e2a86e; }
.latest-card { padding: 6px 8px; }
.tl-content { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.tl-name { font-weight: 600; color: #2c3e50; font-size: 15px; }
.tl-info { color: #909399; font-size: 13px; }
.tl-score { color: #f56c6c; font-size: 13px; font-weight: 600; margin-left: auto; }
.tl-indicators { margin-top: 4px; font-size: 12px; color: #909399; }
.more-link { text-align: center; margin-top: 10px; }
:deep(.el-alert--warning) { border-radius: 14px; background-color: rgba(255,255,255,0.65) !important; }
</style>