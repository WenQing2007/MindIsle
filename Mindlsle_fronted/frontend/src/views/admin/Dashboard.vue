<template>
  <div class="dashboard">
    <div class="welcome-banner">
      <div class="banner-left">
        <h2>🌿 MindIsle 管理中心</h2>
        <p>欢迎回来，管理员！这里是系统运行的全景视图。</p>
      </div>
      <div class="banner-right">
        <div class="date-info">{{ today }}</div>
      </div>
    </div>

    <div class="section-title">📈 系统概览</div>
    <el-row :gutter="18" class="stat-row">
      <el-col :xs="12" :sm="6">
        <el-card shadow="hover" class="stat-card card-users" @click="$router.push('/admin/users')">
          <div class="stat-icon">👥</div>
          <div class="stat-body">
            <div class="stat-num">{{ stats.user_count || 0 }}</div>
            <div class="stat-label">注册用户总数</div>
            <div class="stat-sub">学生 {{ stats.student_count || 0 }} · 教师 {{ stats.teacher_count || 0 }}</div>
          </div>
        </el-card>
      </el-col>
      <el-col :xs="12" :sm="6">
        <el-card shadow="hover" class="stat-card card-session" @click="$router.push('/admin/content')">
          <div class="stat-icon">💬</div>
          <div class="stat-body">
            <div class="stat-num">{{ stats.session_count || 0 }}</div>
            <div class="stat-label">AI 会话总数</div>
            <div class="stat-sub">累计心理陪伴对话</div>
          </div>
        </el-card>
      </el-col>
      <el-col :xs="12" :sm="6">
        <el-card shadow="hover" class="stat-card card-treehole" @click="$router.push('/admin/content')">
          <div class="stat-icon">🌳</div>
          <div class="stat-body">
            <div class="stat-num">{{ stats.treehole_count || 0 }}</div>
            <div class="stat-label">树洞帖子</div>
            <div class="stat-sub highlight-pending">待审核 {{ stats.pending_treeholes || 0 }}</div>
          </div>
        </el-card>
      </el-col>
      <el-col :xs="12" :sm="6">
        <el-card shadow="hover" class="stat-card card-warn" @click="$router.push('/admin/config')">
          <div class="stat-icon">⚠️</div>
          <div class="stat-body">
            <div class="stat-num warn-num">{{ warnStats.critical || 0 }}</div>
            <div class="stat-label">风险预警</div>
            <div class="stat-sub">红色 {{ warnStats.critical || 0 }} · 橙色 {{ warnStats.high || 0 }}</div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="18">
      <el-col :xs="24" :lg="14">
        <div class="section-title">🛠️ 管理功能</div>
        <el-row :gutter="14" class="feature-row">
          <el-col :xs="12" :sm="6">
            <div class="feature-card f-users" @click="$router.push('/admin/users')">
              <div class="f-icon">👤</div>
              <div class="f-title">用户管理</div>
              <div class="f-desc">增删改查账号</div>
            </div>
          </el-col>
          <el-col :xs="12" :sm="6">
            <div class="feature-card f-content" @click="$router.push('/admin/content')">
              <div class="f-icon">📄</div>
              <div class="f-title">内容管理</div>
              <div class="f-desc">树洞审核/资源</div>
            </div>
          </el-col>
          <el-col :xs="12" :sm="6">
            <div class="feature-card f-logs" @click="$router.push('/admin/logs')">
              <div class="f-icon">📋</div>
              <div class="f-title">日志管理</div>
              <div class="f-desc">操作/登录记录</div>
            </div>
          </el-col>
          <el-col :xs="12" :sm="6">
            <div class="feature-card f-config" @click="$router.push('/admin/config')">
              <div class="f-icon">🛡️</div>
              <div class="f-title">安全配置</div>
              <div class="f-desc">关键词/热线</div>
            </div>
          </el-col>
        </el-row>

        <div class="section-title">ℹ️ 系统状态</div>
        <el-card shadow="hover" class="sys-card">
          <div class="sys-row">
            <span class="sys-label">AI 引擎</span>
            <el-tag :type="cfg.llm && cfg.llm.enabled ? 'success' : 'info'" effect="light">
              {{ cfg.llm && cfg.llm.enabled ? '已启用' : '模板兜底' }}
            </el-tag>
          </div>
          <div class="sys-row">
            <span class="sys-label">AI 水印</span>
            <span class="sys-value">{{ cfg.ai_watermark || '—' }}</span>
          </div>
          <div class="sys-row">
            <span class="sys-label">危机热线</span>
            <span class="sys-value hotline">{{ cfg.crisis_hotline || '400-161-9995' }}</span>
          </div>
          <div class="sys-row">
            <span class="sys-label">风险关键词</span>
            <span class="sys-value">红 {{ kwStats.red }} · 橙 {{ kwStats.orange }} · 黄 {{ kwStats.yellow }} · 绿 {{ kwStats.green }}</span>
          </div>
        </el-card>
      </el-col>

      <el-col :xs="24" :lg="10">
        <div class="section-title">🔐 最近登录</div>
        <el-card shadow="hover" class="list-card">
          <div v-if="loginLogs.length === 0" class="empty-tip">暂无登录记录</div>
          <div v-else class="log-list">
            <div v-for="log in loginLogs.slice(0, 8)" :key="log.id" class="log-item">
              <div class="log-left">
                <el-tag :type="log.success ? 'success' : 'danger'" size="small" effect="dark" class="log-tag">
                  {{ log.success ? '✓' : '✗' }}
                </el-tag>
                <div class="log-info">
                  <div class="log-user">{{ log.username }}
                    <el-tag size="small" style="margin-left:6px">{{ log.role }}</el-tag>
                  </div>
                  <div class="log-ip">{{ log.ip || '—' }}</div>
                </div>
              </div>
              <div class="log-time">{{ formatTime(log.created_at) }}</div>
            </div>
          </div>
          <div class="more-row">
            <el-button link type="primary" @click="$router.push('/admin/logs')">查看全部日志 →</el-button>
          </div>
        </el-card>

        <div class="section-title">🚨 最新预警</div>
        <el-card shadow="hover" class="list-card">
          <el-empty v-if="warnings.length === 0" description="暂无风险预警 💚" :image-size="60"></el-empty>
          <div v-else class="warn-list">
            <div v-for="(w, i) in warnings.slice(0, 5)" :key="i" class="warn-item">
              <el-tag :type="warnTagType(w.risk_level)" size="small" effect="dark">{{ warnLevelText(w.risk_level) }}</el-tag>
              <span class="warn-name">{{ w.name }}</span>
              <span class="warn-score">风险 {{ (w.risk_score * 100).toFixed(0) }}</span>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-alert
      style="margin-top:24px;border-radius:var(--brand-radius-md)"
      type="warning"
      :closable="false"
      show-icon
      title="管理提示：AI 评估仅供参考，红色/橙色预警建议立即联系学校心理干预小组介入。紧急情况请拨打全国心理援助热线 400-161-9995"
    />
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import axios from 'axios'
import { getAdminConfig, getRiskKeywords } from '@/api/admin'

const stats = ref({})
const cfg = ref({ ai_watermark: '', llm: {}, crisis_hotline: '' })
const keywords = ref([])
const loginLogs = ref([])
const warnings = ref([])

const warnStats = computed(() => ({
  critical: warnings.value.filter(w => w.risk_level === 'critical').length,
  high: warnings.value.filter(w => w.risk_level === 'high').length,
  medium: warnings.value.filter(w => w.risk_level === 'medium').length,
}))

const kwStats = computed(() => {
  const s = { red: 0, orange: 0, yellow: 0, green: 0 }
  keywords.value.forEach(k => { if (k.enabled) s[k.level] = (s[k.level] || 0) + 1 })
  return s
})

const today = computed(() => {
  const d = new Date()
  const weeks = ['日', '一', '二', '三', '四', '五', '六']
  return `${d.getFullYear()} 年 ${d.getMonth() + 1} 月 ${d.getDate()} 日 · 星期${weeks[d.getDay()]}`
})

const warnTagType = (l) => ({ critical: 'danger', high: 'warning', medium: '' })[l] || 'info'
const warnLevelText = (l) => ({ critical: '红色预警', high: '橙色预警', medium: '黄色关注' })[l] || l

const formatTime = (t) => {
  if (!t) return ''
  try {
    return new Date(t).toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
  } catch { return t }
}

const loadAll = async () => {
  try {
    const [healthRes, cfgRes, kwRes, logRes, warnRes] = await Promise.allSettled([
      axios.get('/health'),
      getAdminConfig(),
      getRiskKeywords(),
      axios.get('/api/admin/logs/login?limit=8'),
      axios.get('/api/teacher/warnings')
    ])
    if (healthRes.status === 'fulfilled' && healthRes.value.data?.code === 200) {
      stats.value = healthRes.value.data.data?.stats || {}
    }
    if (cfgRes.status === 'fulfilled' && cfgRes.value.code === 200) cfg.value = cfgRes.value.data
    if (kwRes.status === 'fulfilled' && kwRes.value.code === 200) keywords.value = kwRes.value.data || []
    if (logRes.status === 'fulfilled') {
      const d = logRes.value.data
      if (d?.code === 200) loginLogs.value = d.data || []
    }
    if (warnRes.status === 'fulfilled') {
      const d = warnRes.value.data
      if (d?.code === 200) warnings.value = d.data || []
    }
  } catch (e) {}
}

onMounted(loadAll)
</script>

<style scoped>
.dashboard { min-height: 100%; }

.welcome-banner {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 28px 32px;
  margin-bottom: 10px;
  border-radius: var(--brand-radius-xl);
  background: linear-gradient(135deg, #eaf5ef 0%, #f0f9f4 50%, #fdfaf4 100%);
  border: 1px solid var(--brand-border);
  box-shadow: var(--brand-shadow);
}
.banner-left h2 { margin: 0 0 6px 0; font-size: 22px; color: var(--brand-text); font-weight: 700; }
.banner-left p { margin: 0; color: var(--brand-text-soft); font-size: 14px; }
.date-info {
  padding: 10px 18px;
  background: rgba(255,255,255,0.7);
  border-radius: 12px;
  color: var(--brand-text-soft);
  font-size: 13px;
  font-weight: 500;
}

.section-title { font-size: 16px; font-weight: 600; color: var(--brand-text); margin: 28px 4px 14px 4px; }

.stat-row { margin-bottom: 4px; }
.stat-card {
  cursor: pointer;
  transition: all 0.3s ease;
  border-radius: var(--brand-radius-lg) !important;
  border: 1px solid var(--brand-border) !important;
  overflow: hidden;
}
.stat-card:hover { transform: translateY(-4px); box-shadow: var(--brand-shadow-lg) !important; }
.stat-card :deep(.el-card__body) { display: flex; gap: 16px; padding: 22px !important; }
.stat-icon {
  width: 54px; height: 54px;
  border-radius: 14px;
  display: flex; align-items: center; justify-content: center;
  font-size: 26px; flex-shrink: 0;
}
.card-users .stat-icon { background: linear-gradient(135deg, #a8c8e0, #c5dced); }
.card-session .stat-icon { background: linear-gradient(135deg, #8dd4b8, #b5e5cd); }
.card-treehole .stat-icon { background: linear-gradient(135deg, #f5e6d3, #faf0e4); }
.card-warn .stat-icon { background: linear-gradient(135deg, #f8b4c0, #fcd5de); }

.card-users :deep(.el-card__body)    { background: linear-gradient(135deg, #f4f9fc 0%, #fafdff 100%); }
.card-session :deep(.el-card__body)  { background: linear-gradient(135deg, #f0faf4 0%, #fdfaf4 100%); }
.card-treehole :deep(.el-card__body) { background: linear-gradient(135deg, #fdf8f0 0%, #fdfaf4 100%); }
.card-warn :deep(.el-card__body)     { background: linear-gradient(135deg, #fdf0f2 0%, #fff5f7 100%); }

.stat-body { flex: 1; }
.stat-num { font-size: 30px; font-weight: 700; color: var(--brand-text); line-height: 1.1; }
.warn-num { color: #e07a7a; }
.stat-label { font-size: 14px; color: var(--brand-text); margin-top: 4px; font-weight: 500; }
.stat-sub { font-size: 12px; color: var(--brand-text-muted); margin-top: 4px; }
.highlight-pending { color: #e8a86a; font-weight: 500; }

.feature-row .el-col { margin-bottom: 14px; }
.feature-card {
  padding: 20px 16px;
  border-radius: var(--brand-radius-lg);
  text-align: center;
  cursor: pointer;
  transition: all 0.3s ease;
  border: 1px solid var(--brand-border);
  background: #fff;
}
.feature-card:hover { transform: translateY(-4px); box-shadow: var(--brand-shadow-lg); }
.f-icon { font-size: 36px; margin-bottom: 8px; }
.f-title { font-size: 15px; font-weight: 600; color: var(--brand-text); margin-bottom: 4px; }
.f-desc { font-size: 12px; color: var(--brand-text-muted); }

.f-users   { background: linear-gradient(135deg, #f4f9fc, #fafdff); }
.f-content { background: linear-gradient(135deg, #f0faf4, #fdfaf4); }
.f-logs    { background: linear-gradient(135deg, #f5f5f7, #fafafa); }
.f-config  { background: linear-gradient(135deg, #fdf0f2, #fff5f7); }

.sys-card { border-radius: var(--brand-radius-lg) !important; }
.sys-row {
  display: flex; justify-content: space-between; align-items: center;
  padding: 12px 0;
  border-bottom: 1px dashed var(--brand-border);
}
.sys-row:last-child { border-bottom: none; }
.sys-label { color: var(--brand-text-soft); font-size: 14px; }
.sys-value { color: var(--brand-text); font-weight: 500; font-size: 14px; }
.sys-value.hotline { color: var(--brand-primary-dark); font-weight: 600; }

.list-card { border-radius: var(--brand-radius-lg) !important; }
.empty-tip { color: var(--brand-text-muted); text-align: center; padding: 30px; font-size: 13px; }
.log-list { display: flex; flex-direction: column; gap: 2px; }
.log-item {
  display: flex; justify-content: space-between; align-items: center;
  padding: 12px 10px; border-radius: 10px; transition: background 0.2s;
}
.log-item:hover { background: var(--brand-bg-soft); }
.log-left { display: flex; gap: 10px; align-items: center; }
.log-tag { width: 24px; height: 24px; padding: 0; font-size: 11px; border-radius: 50%; }
.log-info { display: flex; flex-direction: column; }
.log-user { font-size: 14px; font-weight: 500; color: var(--brand-text); }
.log-ip { font-size: 12px; color: var(--brand-text-muted); }
.log-time { font-size: 12px; color: var(--brand-text-muted); }
.more-row { text-align: center; margin-top: 10px; padding-top: 8px; border-top: 1px solid var(--brand-border); }

.warn-list { display: flex; flex-direction: column; gap: 8px; }
.warn-item {
  display: flex; align-items: center; gap: 10px;
  padding: 10px 12px;
  background: var(--brand-bg-soft);
  border-radius: 10px;
}
.warn-name { font-weight: 500; color: var(--brand-text); flex: 1; }
.warn-score { font-size: 13px; color: #e07a7a; font-weight: 600; }
</style>
