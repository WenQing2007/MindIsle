<template>
  <div class="teacher-page">
    <div class="top-bar">
      <el-page-header content="学生风险预警名单"></el-page-header>
      <div class="top-actions">
        <span class="threshold-label">预警下限</span>
        <el-select v-model="minLevel" size="small" style="width:110px" @change="saveThreshold">
          <el-option label="黄色及以上" value="medium" />
          <el-option label="橙色及以上" value="high" />
          <el-option label="仅红色" value="critical" />
        </el-select>
        <el-button size="small" @click="loadData">🔄 刷新</el-button>
        <el-button size="small" @click="logout">退出登录</el-button>
      </div>
    </div>

    <el-row :gutter="16" style="margin-top:20px">
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-num critical">{{ statCritical }}</div>
          <div class="stat-label">🔴 红色预警</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-num high">{{ statHigh }}</div>
          <div class="stat-label">🟠 橙色预警</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-num medium">{{ statMedium }}</div>
          <div class="stat-label">🟡 黄色预警</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-num">{{ warnings.length }}</div>
          <div class="stat-label">📊 需关注总计</div>
        </el-card>
      </el-col>
    </el-row>

    <el-card style="margin-top:20px">
      <el-table :data="warnings" border v-loading="loading" stripe>
        <el-table-column prop="student_id" label="学号" width="80" />
        <el-table-column prop="name" label="姓名" width="100" />
        <el-table-column prop="school" label="学校" width="120" />
        <el-table-column prop="grade" label="年级/班级" width="120" />
        <el-table-column prop="risk_level_cn" label="风险等级" width="110">
          <template #default="scope">
            <el-tag :type="tagType(scope.row.risk_level)" effect="dark">
              {{ scope.row.risk_level_cn }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="risk_score" label="风险分数" width="100">
          <template #default="scope">
            {{ (scope.row.risk_score * 100).toFixed(0) }}
          </template>
        </el-table-column>
        <el-table-column prop="indicators" label="关键指标" show-overflow-tooltip />
        <el-table-column prop="assessed_at" label="评估时间" width="170" />
        <el-table-column prop="review_status" label="复核状态" width="120">
          <template #default="scope">
            <el-tag size="small" :type="reviewTag(scope.row.review_status)">
              {{ reviewText(scope.row.review_status) }}
            </el-tag>
            <div v-if="scope.row.review_note" class="review-note">{{ scope.row.review_note }}</div>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="300" fixed="right">
          <template #default="scope">
            <el-button size="small" @click="generateReport(scope.row.student_id)">成长报告</el-button>
            <el-button
              v-if="['critical', 'high'].includes(scope.row.risk_level)"
              size="small"
              type="danger"
              plain
              @click="generateCrisisReport(scope.row.student_id, scope.row.name)"
            >
              危机处置
            </el-button>
            <el-button size="small" type="primary" plain @click="openReview(scope.row)">人工复核</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="reviewVisible" title="人工复核" width="460px">
      <div class="review-target" v-if="reviewTarget">
        学生「{{ reviewTarget.name }}」 · {{ reviewTarget.risk_level_cn }}级预警
      </div>
      <el-form label-width="80px" style="margin-top:8px">
        <el-form-item label="处置状态">
          <el-radio-group v-model="reviewForm.status">
            <el-radio value="reviewed">已复核</el-radio>
            <el-radio value="followed_up">已跟进</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="reviewForm.note" type="textarea" :rows="3" placeholder="填写处理情况、介入措施等（留痕）" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="reviewVisible = false">取消</el-button>
        <el-button type="primary" :loading="reviewSaving" @click="submitReview">提交复核</el-button>
      </template>
    </el-dialog>

    <el-alert
      style="margin-top:20px"
      type="warning"
      :closable="false"
      title="⚠️ 红色预警为最高风险等级，请立即联系学校心理干预小组介入。"
    />
  </div>
</template>

<script setup>
import { ref, computed, onMounted, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { getWarnings, getWarningConfig, setWarningConfig, reviewWarning } from '@/api/teacher'
import axios from 'axios'

const router = useRouter()
const warnings = ref([])
const loading = ref(false)
const minLevel = ref('medium')

const reviewVisible = ref(false)
const reviewTarget = ref(null)
const reviewSaving = ref(false)
const reviewForm = reactive({ status: 'reviewed', note: '' })

const statCritical = computed(() => warnings.value.filter(w => w.risk_level === 'critical').length)
const statHigh = computed(() => warnings.value.filter(w => w.risk_level === 'high').length)
const statMedium = computed(() => warnings.value.filter(w => w.risk_level === 'medium').length)

const tagType = (level) => {
  return { critical: 'danger', high: 'warning', medium: '' }[level] || 'info'
}
const reviewText = (s) => ({ pending: '待复核', reviewed: '已复核', followed_up: '已跟进' }[s] || '待复核')
const reviewTag = (s) => ({ pending: 'info', reviewed: 'success', followed_up: 'warning' }[s] || 'info')

const loadConfig = async () => {
  try {
    const res = await getWarningConfig()
    if (res.code === 200) minLevel.value = res.data.min_level
  } catch (e) { /* 忽略 */ }
}

const loadData = async () => {
  loading.value = true
  try {
    const res = await getWarnings()
    if (res.code === 200) warnings.value = res.data
    else ElMessage.error(res.msg || '加载失败')
  } catch (err) {
    ElMessage.error('加载预警数据失败，请检查后端服务是否启动')
  } finally {
    loading.value = false
  }
}

const saveThreshold = async () => {
  try {
    const res = await setWarningConfig(minLevel.value)
    if (res.code === 200) { ElMessage.success('预警阈值已更新'); loadData() }
    else ElMessage.error(res.msg || '更新失败')
  } catch (e) { ElMessage.error('更新阈值失败') }
}

const openReview = (row) => {
  reviewTarget.value = row
  reviewForm.status = 'reviewed'
  reviewForm.note = ''
  reviewVisible.value = true
}

const submitReview = async () => {
  if (!reviewTarget.value) return
  reviewSaving.value = true
  try {
    const res = await reviewWarning(reviewTarget.value.assessment_id, reviewForm.status, reviewForm.note)
    if (res.code === 200) {
      ElMessage.success('复核已记录')
      reviewVisible.value = false
      loadData()
    } else ElMessage.error(res.msg || '提交失败')
  } catch (e) { ElMessage.error('提交复核失败') } finally { reviewSaving.value = false }
}

const generateReport = async (sid) => {
  try {
    const res = await axios.post(`/api/report/student/${sid}`)
    const data = res.data
    if (data.code === 200) {
      alert("报告已生成！文件路径：" + data.data.filepath)
      window.open(`/api/report/download?filepath=${encodeURIComponent(data.data.filepath)}`, '_blank')
    } else {
      alert(data.msg || "生成失败")
    }
  } catch (err) {
    alert("生成报告失败")
  }
}

const generateCrisisReport = async (sid, name) => {
  try {
    const res = await axios.post('/api/report/crisis', { student_id: sid })
    const data = res.data
    if (data.code === 200) {
      alert(`${name || ''} 的危机事件处置报告已生成！\n文件路径：${data.data.filepath}`)
      window.open(`/api/report/download?filepath=${encodeURIComponent(data.data.filepath)}`, '_blank')
    } else {
      alert(data.msg || "生成危机处置报告失败")
    }
  } catch (err) {
    alert("生成危机处置报告失败")
  }
}

const logout = () => {
  localStorage.removeItem('token')
  localStorage.removeItem('userType')
  router.push('/teacher/login')
}

onMounted(() => { loadConfig(); loadData() })
</script>

<style scoped>
.teacher-page {
  padding: 20px 30px;
}
.top-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.top-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}
.threshold-label {
  font-size: 13px;
  color: #909399;
}
.review-note {
  font-size: 11px;
  color: #a0a4ab;
  margin-top: 4px;
  max-width: 110px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.review-target {
  font-size: 14px;
  color: #303133;
  padding: 6px 0;
}
.stat-card {
  text-align: center;
}
.stat-num {
  font-size: 32px;
  font-weight: bold;
  color: #303133;
}
.stat-num.critical { color: #f56c6c; }
.stat-num.high    { color: #f56c1c; }
.stat-num.medium  { color: #e6a23c; }
.stat-label {
  font-size: 13px;
  color: #909399;
  margin-top: 4px;
}
</style>