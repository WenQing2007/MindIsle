<template>
  <div class="report-container">
    <h3>我的心理报告</h3>
    <!-- 加载骨架 -->
    <el-skeleton :loading="loading" animated>
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
    </el-skeleton>

    <el-empty v-if="!loading && reportList.length === 0" description="暂无心理报告"></el-empty>

    <!-- 弹窗：查看完整报告 -->
    <el-dialog v-model="dialogVisible" title="报告详情" width="70%">
      <div class="detail-content">
        <p><strong>报告类型：</strong>{{ currentReport.report_type }}</p>
        <p><strong>生成时间：</strong>{{ currentReport.created_at }}</p>
        <div style="margin-top:12px;">{{ currentReport.content }}</div>
      </div>
      <template #footer>
        <el-button @click="dialogVisible = false">关闭</el-button>
        <el-button type="primary" @click="exportPdf">导出PDF</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
// import { getMyReport } from '@/api/student'

const reportList = ref([])
const dialogVisible = ref(false)
const currentReport = ref({})
const loading = ref(false)

// 打开详情弹窗
const openDetail = (row) => {
  currentReport.value = row
  dialogVisible.value = true
}

// 加载报告
const loadReport = async () => {
  loading.value = true
  try {
    // ========= mock 假数据，本地调试用 =========
    const mockRes = {
      code: 200,
      data: [
        {
          id: 1,
          report_type: '情绪测评报告',
          title: 'SCL-90心理健康筛查报告',
          created_at: '2026-10-20 14:30',
          content: '本次测评结果显示你的情绪状态整体平稳，偶尔有焦虑倾向。\n建议：规律作息，多进行户外活动，有烦恼可以去AI倾诉聊聊。'
        },
        {
          id: 2,
          report_type: 'AI对话分析报告',
          title: '智能对话心理小结',
          created_at: '2026-10-22 16:10',
          content: '在最近的对话中，你主要压力来源是学业任务较多。\n心理建议：合理拆分任务，不要一次性给自己太高要求。'
        }
      ]
    }
    const res = mockRes

    // ========= 后端通了之后，注释上面mock，启用下面一行 =========
    // const res = await getMyReport()

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

// 导出PDF（先占位，后面装html2pdf再实现函数内容）
const exportPdf = () => {
  ElMessage.info('导出功能待实现')
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
