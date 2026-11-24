<template>
  <div class="reports-page">
    <div class="top-bar">
      <el-page-header @back="$router.back()" content="报告中心"></el-page-header>
      <el-button size="small" @click="$router.push('/teacher/home')">返回工作台</el-button>
    </div>

    <div class="section-title">📋 生成报告</div>
    <el-row :gutter="20">
      <el-col :xs="24" :sm="12" :md="8">
        <el-card shadow="hover" class="feature-card" @click="showStudentDialog = true">
          <div class="feature-icon">🧑‍🎓</div>
          <div class="feature-title">学生成长报告</div>
          <div class="feature-desc">选择一名学生，生成其个体心理成长报告 PDF</div>
        </el-card>
      </el-col>
      <el-col :xs="24" :sm="12" :md="8">
        <el-card shadow="hover" class="feature-card" @click="showClassDialog = true">
          <div class="feature-icon">🏫</div>
          <div class="feature-title">班级汇总报告</div>
          <div class="feature-desc">按班级维度汇总全体学生的心理状态画像</div>
        </el-card>
      </el-col>
      <el-col :xs="24" :sm="12" :md="8">
        <el-card shadow="hover" class="feature-card danger" @click="showCrisisDialog = true">
          <div class="feature-icon">🚨</div>
          <div class="feature-title">危机处置报告</div>
          <div class="feature-desc">针对橙/红预警学生生成危机事件处置报告</div>
        </el-card>
      </el-col>
    </el-row>

    <el-dialog v-model="showStudentDialog" title="选择学生" width="500px">
      <el-input v-model="studentKeyword" placeholder="搜索学生姓名..." style="margin-bottom:12px" />
      <el-table :data="filteredStudents" height="300" highlight-current-row @current-change="pickStudent">
        <el-table-column prop="id" label="学号" width="80" />
        <el-table-column prop="name" label="姓名" width="120" />
        <el-table-column prop="school" label="学校" />
        <el-table-column prop="grade" label="年级" />
      </el-table>
      <template #footer>
        <el-button @click="showStudentDialog = false">取消</el-button>
        <el-button type="primary" :disabled="!pickedStudent" @click="genStudentReport">生成报告</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="showClassDialog" title="生成班级汇总报告" width="420px">
      <el-form label-width="100px">
        <el-form-item label="班级名称">
          <el-input v-model="className" placeholder="例：高二(1)班" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showClassDialog = false">取消</el-button>
        <el-button type="primary" :disabled="!className" @click="genClassReport">生成报告</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="showCrisisDialog" title="危机处置报告" width="500px">
      <el-alert type="warning" :closable="false" title="仅显示最近有橙/红预警的学生" style="margin-bottom:12px" />
      <el-table :data="crisisStudents" height="300" highlight-current-row @current-change="pickStudent">
        <el-table-column prop="student_id" label="学号" width="80" />
        <el-table-column prop="name" label="姓名" width="120" />
        <el-table-column prop="risk_level_cn" label="风险等级" width="100">
          <template #default="scope">
            <el-tag :type="tagType(scope.row.risk_level)" effect="dark" size="small">
              {{ scope.row.risk_level_cn }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="assessed_at" label="评估时间" />
      </el-table>
      <template #footer>
        <el-button @click="showCrisisDialog = false">取消</el-button>
        <el-button type="danger" :disabled="!pickedStudent" @click="genCrisisReport">生成危机处置报告</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import axios from 'axios'

const showStudentDialog = ref(false)
const showClassDialog = ref(false)
const showCrisisDialog = ref(false)
const studentKeyword = ref('')
const className = ref('')
const pickedStudent = ref(null)
const students = ref([])
const warnings = ref([])

const filteredStudents = computed(() => {
  const k = studentKeyword.value.trim().toLowerCase()
  if (!k) return students.value
  return students.value.filter(s => (s.name || '').toLowerCase().includes(k))
})

const crisisStudents = computed(() =>
  warnings.value.filter(w => ['critical', 'high'].includes(w.risk_level))
)

const tagType = (level) => ({ critical: 'danger', high: 'warning' })[level] || 'info'

const loadStudents = async () => {
  try {
    const res = await axios.get('/api/students')
    if (res.data.code === 200) students.value = res.data.data
  } catch (e) {}
}
const loadWarnings = async () => {
  try {
    const res = await axios.get('/api/teacher/warnings')
    if (res.data.code === 200) warnings.value = res.data.data
  } catch (e) {}
}

const pickStudent = (row) => { pickedStudent.value = row }

const genStudentReport = async () => {
  try {
    const sid = pickedStudent.value.id
    const res = await axios.post(`/api/report/student/${sid}`)
    if (res.data.code === 200) {
      showStudentDialog.value = false
      alert('✅ 成长报告已生成！正在下载...')
      window.open(`/api/report/download?filepath=${encodeURIComponent(res.data.data.filepath)}`, '_blank')
    } else {
      alert('❌ ' + (res.data.msg || '生成失败'))
    }
  } catch (e) { alert('❌ 生成失败') }
}

const genClassReport = async () => {
  try {
    const res = await axios.post('/api/report/class', null, { params: { class_name: className.value } })
    if (res.data.code === 200) {
      showClassDialog.value = false
      alert('✅ 班级报告已生成！正在下载...')
      window.open(`/api/report/download?filepath=${encodeURIComponent(res.data.data.filepath)}`, '_blank')
    } else {
      alert('❌ ' + (res.data.msg || '生成失败'))
    }
  } catch (e) { alert('❌ 生成失败') }
}

const genCrisisReport = async () => {
  try {
    const sid = pickedStudent.value.student_id
    const res = await axios.post('/api/report/crisis', { student_id: sid })
    if (res.data.code === 200) {
      showCrisisDialog.value = false
      alert('✅ 危机处置报告已生成！正在下载...')
      window.open(`/api/report/download?filepath=${encodeURIComponent(res.data.data.filepath)}`, '_blank')
    } else {
      alert('❌ ' + (res.data.msg || '生成失败'))
    }
  } catch (e) { alert('❌ 生成失败') }
}

onMounted(() => { loadStudents(); loadWarnings() })
</script>

<style scoped>
.reports-page { padding: 20px 30px; }
.top-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.section-title { font-size: 16px; font-weight: 600; color: #2c3e50; margin: 20px 4px 14px 4px; }
.feature-card { text-align: center; cursor: pointer; transition: all 0.3s ease; height: 100%; min-height: 160px; }
.feature-card:hover { transform: translateY(-6px); }
.feature-icon { font-size: 40px; margin-bottom: 8px; }
.feature-title { font-size: 16px; font-weight: 600; margin-bottom: 6px; color: #2c3e50; }
.feature-desc { font-size: 13px; color: #606266; line-height: 1.5; }
.feature-card.danger :deep(.el-card__body) { background: linear-gradient(135deg, #ffe8e8 0%, #fff0f0 100%); }
</style>