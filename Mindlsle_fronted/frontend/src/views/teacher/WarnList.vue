<template>
  <div class="teacher-page">
    <div class="top-bar">
      <el-page-header content="学生风险预警名单"></el-page-header>
      <div>
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
        <el-table-column label="操作" width="120" fixed="right">
          <template #default="scope">
            <el-button size="small" @click="generateReport(scope.row.student_id)">生成报告</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-alert
      style="margin-top:20px"
      type="warning"
      :closable="false"
      title="⚠️ 红色预警为最高风险等级，请立即联系学校心理干预小组介入。"
    />
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import axios from 'axios'

const router = useRouter()
const warnings = ref([])
const loading = ref(false)

const statCritical = computed(() => warnings.value.filter(w => w.risk_level === 'critical').length)
const statHigh = computed(() => warnings.value.filter(w => w.risk_level === 'high').length)
const statMedium = computed(() => warnings.value.filter(w => w.risk_level === 'medium').length)

const tagType = (level) => {
  return { critical: 'danger', high: 'warning', medium: '' }[level] || 'info'
}

const loadData = async () => {
  loading.value = true
  try {
    const res = await axios.get('/api/teacher/warnings')
    const data = res.data
    if (data.code === 200) {
      warnings.value = data.data
    }
  } catch (err) {
    alert("加载预警数据失败，请检查后端服务是否启动")
  } finally {
    loading.value = false
  }
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

const logout = () => {
  localStorage.removeItem('token')
  localStorage.removeItem('userType')
  router.push('/teacher/login')
}

onMounted(loadData)
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