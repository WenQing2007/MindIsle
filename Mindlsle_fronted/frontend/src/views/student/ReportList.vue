<template>
  <div class="report-container">
    <div class="top-bar">
      <h3>我的心理报告</h3>
      <div>
        <el-button size="small" type="primary" @click="genNewReport">✨ 生成新报告</el-button>
        <el-button size="small" @click="loadReport">🔄 刷新</el-button>
      </div>
    </div>

    <el-skeleton :loading="loading" animated>
      <div class="card-wrap">
        <el-card
          v-for="item in reportList"
          :key="item.id"
          class="report-card"
          shadow="hover"
          @click="openDetail(item)"
        >
          <template #header>
            <el-tag>{{ item.report_type }}</el-tag>
          </template>
          <div class="card-title">{{ item.title }}</div>
          <div class="card-time">{{ item.created_at }}</div>
        </el-card>
      </div>
    </el-skeleton>

    <el-empty v-if="!loading && reportList.length === 0" description="暂无心理报告"></el-empty>

    <el-dialog v-model="dialogVisible" title="报告详情" width="70%">
      <div class="detail-content">
        <p><strong>报告类型：</strong>{{ currentReport.report_type }}</p>
        <p><strong>报告标题：</strong>{{ currentReport.title }}</p>
        <p><strong>生成时间：</strong>{{ currentReport.created_at }}</p>
        <div style="margin-top:12px;">{{ currentReport.content }}</div>
      </div>
      <template #footer>
        <el-button @click="dialogVisible = false">关闭</el-button>
        <el-button type="primary" @click="exportPdf">下载 PDF</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import axios from 'axios'
import { getReportList, getReportDetail } from '@/api/student'

const reportList = ref([])
const dialogVisible = ref(false)
const currentReport = ref({})
const loading = ref(false)

const loadReport = async () => {
  const sid = localStorage.getItem('student_id')
  if (!sid) {
    ElMessage.warning('请先重新登录')
    return
  }
  loading.value = true
  try {
    const res = await getReportList(sid)
    if (res.code === 200) {
      reportList.value = res.data
    } else {
      ElMessage.warning('获取报告失败：' + res.msg)
    }
  } catch (err) {
    console.error(err)
    ElMessage.error('网络错误，获取报告列表失败')
  } finally {
    loading.value = false
  }
}

const openDetail = async (row) => {
  try {
    const res = await getReportDetail(row.id)
    if (res.code === 200) {
      currentReport.value = res.data
      dialogVisible.value = true
    } else {
      currentReport.value = row
      dialogVisible.value = true
    }
  } catch (err) {
    console.error(err)
    currentReport.value = row
    dialogVisible.value = true
  }
}

const genNewReport = async () => {
  const sid = localStorage.getItem('student_id')
  if (!sid) {
    ElMessage.warning('请先重新登录')
    return
  }
  ElMessage.info('正在生成报告，请稍候...')
  try {
    const res = await axios.post(`/api/report/student/${sid}`)
    const data = res.data
    if (data.code === 200) {
      ElMessage.success('报告已生成！')
      setTimeout(() => loadReport(), 500)
    } else {
      ElMessage.error(data.msg || '生成失败')
    }
  } catch (err) {
    console.error(err)
    ElMessage.error('生成报告失败')
  }
}

const exportPdf = () => {
  const path = currentReport.value.file_path
  if (!path) {
    ElMessage.warning('该报告没有 PDF 文件')
    return
  }
  window.open(`/api/report/download?filepath=${encodeURIComponent(path)}`, '_blank')
}

onMounted(() => {
  loadReport()
})
</script>

<style scoped>
.report-container {
  max-width: 900px;
  margin: 0 auto;
  padding: 20px;
}
.top-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.card-wrap {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 18px;
  margin-top: 20px;
}
.report-card {
  cursor: pointer;
  transition: 0.3s;
}
.report-card:hover {
  transform: translateY(-4px);
}
.card-title {
  font-size: 16px;
  font-weight: 500;
  margin: 8px 0;
}
.card-time {
  font-size: 13px;
  color: #888;
}
.detail-content {
  white-space: pre-wrap;
  line-height: 1.8;
  font-size: 15px;
}
</style>