<template>
  <div class="report-container">
    <h3>我的心理报告</h3>
    <div class="card-wrap">
      <!-- 报告卡片 -->
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
    <el-empty v-if="reportList.length === 0" description="暂无心理报告"></el-empty>

    <!-- 弹窗：查看完整报告 -->
    <el-dialog v-model="dialogVisible" title="报告详情" width="70%">
      <div class="detail-content">{{ currentReport.content }}</div>
      <template #footer>
        <el-button @click="dialogVisible = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { getMyReport } from '@/api/student'

const reportList = ref([])
const dialogVisible = ref(false)
const currentReport = ref({})

// 打开详情弹窗
const openDetail = (row) => {
  currentReport.value = row
  dialogVisible.value = true
}

// 加载我的全部报告
const loadReport = async () => {
  const res = await getMyReport()
  if (res.code === 200) {
    reportList.value = res.data
  }
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
