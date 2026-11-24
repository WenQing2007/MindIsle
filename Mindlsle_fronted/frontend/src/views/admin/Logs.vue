<template>
  <el-tabs v-model="tab" type="border-card">
    <el-tab-pane label="🔐 登录日志" name="login">
      <div class="toolbar">
        <el-button size="small" @click="loadLogin">🔄 刷新</el-button>
        <span class="tip">最近 {{ loginLogs.length }} 条</span>
      </div>
      <el-table :data="loginLogs" border stripe v-loading="loadingL">
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column prop="username" label="用户名" width="140" />
        <el-table-column prop="role" label="角色" width="100">
          <template #default="s"><el-tag size="small" type="info">{{ s.row.role }}</el-tag></template>
        </el-table-column>
        <el-table-column prop="success" label="结果" width="90">
          <template #default="s">
            <el-tag size="small" :type="s.row.success ? 'success' : 'danger'">{{ s.row.success ? '成功' : '失败' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="detail" label="详情" min-width="200" />
        <el-table-column prop="ip" label="IP" width="140" />
        <el-table-column prop="created_at" label="时间" width="170" />
      </el-table>
    </el-tab-pane>

    <el-tab-pane label="📝 操作日志" name="op">
      <div class="toolbar">
        <el-button size="small" @click="loadOp">🔄 刷新</el-button>
        <span class="tip">最近 {{ opLogs.length }} 条</span>
      </div>
      <el-table :data="opLogs" border stripe v-loading="loadingO">
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column prop="username" label="操作人" width="140" />
        <el-table-column prop="role" label="角色" width="100">
          <template #default="s"><el-tag size="small" type="info">{{ s.row.role }}</el-tag></template>
        </el-table-column>
        <el-table-column prop="action" label="动作" width="160">
          <template #default="s"><el-tag size="small" type="warning" effect="plain">{{ s.row.action }}</el-tag></template>
        </el-table-column>
        <el-table-column prop="detail" label="详情" min-width="220" show-overflow-tooltip />
        <el-table-column prop="created_at" label="时间" width="170" />
      </el-table>
    </el-tab-pane>
  </el-tabs>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { getLoginLogs, getOperationLogs } from '@/api/admin'

const tab = ref('login')
const loginLogs = ref([])
const opLogs = ref([])
const loadingL = ref(false)
const loadingO = ref(false)

const loadLogin = async () => {
  loadingL.value = true
  try { const res = await getLoginLogs(); if (res.code === 200) loginLogs.value = res.data }
  catch (e) { ElMessage.error('加载登录日志失败') } finally { loadingL.value = false }
}
const loadOp = async () => {
  loadingO.value = true
  try { const res = await getOperationLogs(); if (res.code === 200) opLogs.value = res.data }
  catch (e) { ElMessage.error('加载操作日志失败') } finally { loadingO.value = false }
}

onMounted(() => { loadLogin(); loadOp() })
</script>

<style scoped>
.toolbar { display: flex; align-items: center; gap: 12px; margin-bottom: 14px; }
.tip { color: #909399; font-size: 12px; }
</style>
