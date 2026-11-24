<template>
  <el-row :gutter="16">
    <!-- 左：系统信息 + 危机热线 -->
    <el-col :span="10">
      <el-card shadow="never" class="config-card">
        <template #header>系统配置</template>
        <el-form label-width="90px">
          <el-form-item label="AI 水印">
            <el-input :model-value="cfg.ai_watermark || ''" disabled />
          </el-form-item>
          <el-form-item label="LLM 状态">
            <el-tag :type="cfg.llm && cfg.llm.enabled ? 'success' : 'info'">
              {{ cfg.llm && cfg.llm.enabled ? '已启用' : '未启用（模板兜底）' }}
            </el-tag>
            <div class="hint">{{ cfg.llm && cfg.llm.status_text }}</div>
          </el-form-item>
          <el-form-item label="24h 热线">
            <el-input v-model="hotline" />
          </el-form-item>
          <el-form-item>
            <el-button type="primary" :loading="savingHotline" @click="saveHotline">保存热线</el-button>
          </el-form-item>
        </el-form>
        <el-divider>ACPs 协作日志</el-divider>
        <div class="collab-row">
          <el-button size="small" :loading="collabLoading" @click="loadCollab">🔄 查看最近一次协商日志</el-button>
          <span class="hint">报文：{{ collabCount }}</span>
        </div>
        <el-alert type="info" :closable="false" class="hint" style="margin-top:8px">
          多智能体协商产生的 AIP 报文（讨论 / 交叉校验 / 修订整合 / 一票否决）。无对话时为 0 条。
        </el-alert>
        <el-collapse v-if="collabCount" style="margin-top:10px">
          <el-collapse-item title="查看报文明细">
            <pre class="collab-json">{{ collabJson }}</pre>
          </el-collapse-item>
        </el-collapse>
      </el-card>
    </el-col>

    <!-- 右：风险关键词库 -->
    <el-col :span="14">
      <el-card shadow="never" class="config-card">
        <template #header>
          <div class="card-head">
            <span>风险关键词库</span>
            <div>
              <el-button size="small" @click="seed">同步内置基线</el-button>
              <el-button size="small" type="primary" @click="doAdd">＋ 新增</el-button>
            </div>
          </div>
        </template>

        <div class="add-row">
          <el-select v-model="newLevel" style="width:110px">
            <el-option label="红" value="red" /><el-option label="橙" value="orange" />
            <el-option label="黄" value="yellow" /><el-option label="绿" value="green" />
          </el-select>
          <el-input v-model="newKeyword" placeholder="输入关键词，如：不想活了" @keyup.enter="doAdd" />
          <el-button type="primary" @click="doAdd">添加</el-button>
        </div>

        <el-table :data="keywords" border stripe size="small" v-loading="kwLoading" max-height="520">
          <el-table-column prop="level" label="等级" width="80">
            <template #default="s"><el-tag size="small" :type="levelTag(s.row.level)">{{ levelText(s.row.level) }}</el-tag></template>
          </el-table-column>
          <el-table-column prop="keyword" label="关键词" min-width="160" />
          <el-table-column prop="enabled" label="启用" width="90">
            <template #default="s">
              <el-switch :model-value="!!s.row.enabled" @change="(v) => toggle(s.row, v)" />
            </template>
          </el-table-column>
          <el-table-column label="操作" width="90" fixed="right">
            <template #default="s">
              <el-button size="small" type="danger" link @click="remove(s.row)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
        <el-alert type="warning" :closable="false" style="margin-top:10px" class="hint">
          新增/停用关键词即实时影响风险判定（最高等级优先）；「同步内置基线」会把默认词灌入以便编辑。
        </el-alert>
      </el-card>
    </el-col>
  </el-row>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  getAdminConfig, updateHotline, getRiskKeywords, addRiskKeyword,
  toggleRiskKeyword, deleteRiskKeyword, seedRiskKeywords, getCollaboration
} from '@/api/admin'

const cfg = ref({ ai_watermark: '', llm: {}, crisis_hotline: '' })
const hotline = ref('')
const savingHotline = ref(false)

const keywords = ref([])
const kwLoading = ref(false)
const newLevel = ref('red')
const newKeyword = ref('')

const collabLoading = ref(false)
const collabJson = ref('')
const collabCount = computed(() => collabJson.value ? JSON.parse(collabJson.value).length : 0)

const loadCfg = async () => {
  try {
    const res = await getAdminConfig()
    if (res.code === 200) { cfg.value = res.data; hotline.value = res.data.crisis_hotline }
  } catch (e) { ElMessage.error('加载配置失败') }
}
const saveHotline = async () => {
  savingHotline.value = true
  try {
    const res = await updateHotline(hotline.value.trim())
    if (res.code === 200) { ElMessage.success('热线已更新'); loadCfg() }
    else ElMessage.error(res.msg || '失败')
  } finally { savingHotline.value = false }
}

const levelText = (l) => ({ red: '红', orange: '橙', yellow: '黄', green: '绿' }[l] || l)
const levelTag = (l) => ({ red: 'danger', orange: 'warning', yellow: '', green: 'success' }[l] || 'info')
const loadKw = async () => {
  kwLoading.value = true
  try { const res = await getRiskKeywords(); if (res.code === 200) keywords.value = res.data }
  catch (e) { ElMessage.error('加载关键词失败') } finally { kwLoading.value = false }
}
const doAdd = async () => {
  const kw = newKeyword.value.trim()
  if (!kw) return ElMessage.warning('请输入关键词')
  const res = await addRiskKeyword(newLevel.value, kw)
  if (res.code === 200) { ElMessage.success('已新增'); newKeyword.value = ''; loadKw() }
  else ElMessage.error(res.msg || '失败')
}
const toggle = async (row, v) => {
  const res = await toggleRiskKeyword(row.id, !!v)
  if (res.code === 200) { loadKw() } else ElMessage.error(res.msg || '失败')
}
const remove = async (row) => {
  try { await ElMessageBox.confirm(`删除关键词「${row.keyword}」？`, '提示', { type: 'warning' }) } catch { return }
  const res = await deleteRiskKeyword(row.id)
  if (res.code === 200) { ElMessage.success('已删除'); loadKw() }
}
const seed = async () => {
  const res = await seedRiskKeywords()
  if (res.code === 200) { ElMessage.success(res.msg || '已同步'); loadKw() }
  else ElMessage.error(res.msg || '失败')
}

const loadCollab = async () => {
  collabLoading.value = true
  try {
    const res = await getCollaboration()
    if (res.code === 200) {
      const messages = res.data.messages || []
      collabJson.value = JSON.stringify(messages, null, 2) || '[]'
    }
  } catch (e) { ElMessage.error('加载协作日志失败') } finally { collabLoading.value = false }
}

onMounted(() => { loadCfg(); loadKw() })
</script>

<style scoped>
.config-card { border-radius: 10px; }
.card-head { display: flex; justify-content: space-between; align-items: center; }
.add-row { display: flex; gap: 8px; margin-bottom: 14px; }
.hint { color: #909399; font-size: 12px; line-height: 1.6; margin-top: 4px; }
.collab-row { display: flex; align-items: center; gap: 10px; }
.collab-json { background: #1f2d3d; color: #a8f0c0; padding: 10px; border-radius: 6px; font-size: 11px; max-height: 320px; overflow: auto; white-space: pre-wrap; word-break: break-all; }
</style>
