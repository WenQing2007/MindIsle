<template>
  <el-tabs v-model="tab" type="border-card">
    <!-- 树洞审核 -->
    <el-tab-pane label="🌳 树洞审核" name="treehole">
      <div class="toolbar">
        <el-radio-group v-model="holeStatus" @change="loadHoles">
          <el-radio-button label="">全部</el-radio-button>
          <el-radio-button label="flagged">待处理</el-radio-button>
          <el-radio-button label="approved">已通过</el-radio-button>
          <el-radio-button label="rejected">已拒绝</el-radio-button>
        </el-radio-group>
        <el-button size="small" @click="loadHoles">🔄 刷新</el-button>
      </div>
      <el-table :data="holes" border stripe v-loading="holeLoading">
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column prop="content" label="内容" min-width="300" show-overflow-tooltip />
        <el-table-column prop="author_name" label="作者" width="110" />
        <el-table-column prop="comment_count" label="评论数" width="80" />
        <el-table-column prop="reviewed_by" label="审核人" width="100" />
        <el-table-column prop="status" label="状态" width="100">
          <template #default="s">
            <el-tag size="small" :type="statusTag(s.row.status)">{{ statusText(s.row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="发布时间" width="160" />
        <el-table-column label="操作" width="220" fixed="right">
          <template #default="s">
            <el-button size="small" type="success" plain @click="review(s.row, 'approved')">通过</el-button>
            <el-button size="small" type="warning" plain @click="review(s.row, 'flagged')">标记</el-button>
            <el-button size="small" type="danger" @click="removeHole(s.row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-tab-pane>

    <!-- 心理资源 -->
    <el-tab-pane label="📚 心理资源" name="resource">
      <div class="toolbar">
        <el-button type="primary" @click="openRes">＋ 发布资源</el-button>
        <el-button size="small" @click="loadRes">🔄 刷新</el-button>
      </div>
      <el-table :data="resources" border stripe v-loading="resLoading">
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column prop="title" label="标题" min-width="200" />
        <el-table-column prop="res_type" label="类型" width="110">
          <template #default="s"><el-tag size="small">{{ resTypeText(s.row.res_type) }}</el-tag></template>
        </el-table-column>
        <el-table-column prop="url" label="链接" min-width="160" show-overflow-tooltip />
        <el-table-column prop="status" label="状态" width="100">
          <template #default="s">
            <el-tag size="small" :type="s.row.status === 'published' ? 'success' : 'info'">
              {{ s.row.status === 'published' ? '已发布' : '下架' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="160" />
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="s">
            <el-button size="small" @click="openRes(s.row)">编辑</el-button>
            <el-button size="small" type="danger" plain @click="removeRes(s.row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-dialog v-model="resDialog" :title="resForm.id ? '编辑资源' : '发布资源'" width="500px">
        <el-form :model="resForm" label-width="70px">
          <el-form-item label="标题"><el-input v-model="resForm.title" /></el-form-item>
          <el-form-item label="类型">
            <el-select v-model="resForm.res_type" style="width:100%">
              <el-option label="文章" value="article" />
              <el-option label="音频" value="audio" />
              <el-option label="视频" value="video" />
              <el-option label="放松训练" value="relax" />
            </el-select>
          </el-form-item>
          <el-form-item label="链接"><el-input v-model="resForm.url" placeholder="可选" /></el-form-item>
          <el-form-item label="简介"><el-input v-model="resForm.content" type="textarea" :rows="3" /></el-form-item>
          <el-form-item label="状态">
            <el-switch v-model="resForm.published" active-text="发布" inactive-text="下架" />
          </el-form-item>
        </el-form>
        <template #footer>
          <el-button @click="resDialog = false">取消</el-button>
          <el-button type="primary" :loading="resSaving" @click="saveRes">保存</el-button>
        </template>
      </el-dialog>
    </el-tab-pane>
  </el-tabs>
</template>

<script setup>
import { ref, onMounted, reactive } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  getAdminTreeholes, reviewTreehole, deleteTreehole,
  getAdminResources, createResource, updateResource, deleteResource
} from '@/api/admin'

const tab = ref('treehole')

// 树洞
const holes = ref([]); const holeStatus = ref(''); const holeLoading = ref(false)
const statusText = (s) => ({ approved: '已通过', rejected: '已拒绝', flagged: '待处理' }[s] || s)
const statusTag = (s) => ({ approved: 'success', rejected: 'danger', flagged: 'warning' }[s] || 'info')
const loadHoles = async () => {
  holeLoading.value = true
  try {
    const res = await getAdminTreeholes(holeStatus.value || undefined)
    if (res.code === 200) holes.value = res.data
  } catch (e) { ElMessage.error('加载树洞失败') } finally { holeLoading.value = false }
}
const review = async (row, status) => {
  const res = await reviewTreehole(row.id, status)
  if (res.code === 200) { ElMessage.success('已处理'); loadHoles() } else ElMessage.error(res.msg || '失败')
}
const removeHole = async (row) => {
  try { await ElMessageBox.confirm('确定删除该树洞吗？', '提示', { type: 'warning' }) } catch { return }
  const res = await deleteTreehole(row.id)
  if (res.code === 200) { ElMessage.success('已删除'); loadHoles() }
}

// 资源
const resources = ref([]); const resLoading = ref(false)
const resDialog = ref(false); const resSaving = ref(false)
const resForm = reactive({ id: null, title: '', res_type: 'article', url: '', content: '', published: true })
const resTypeText = (t) => ({ article: '文章', audio: '音频', video: '视频', relax: '放松' }[t] || t)
const loadRes = async () => {
  resLoading.value = true
  try {
    const res = await getAdminResources()
    if (res.code === 200) resources.value = res.data
  } catch (e) { ElMessage.error('加载资源失败') } finally { resLoading.value = false }
}
const resetRes = () => Object.assign(resForm, { id: null, title: '', res_type: 'article', url: '', content: '', published: true })
const openRes = (row) => {
  resetRes()
  if (row) Object.assign(resForm, { ...row, published: row.status === 'published' })
  resDialog.value = true
}
const saveRes = async () => {
  resSaving.value = true
  try {
    const status = resForm.published ? 'published' : 'unpublished'
    let res
    if (resForm.id) res = await updateResource(resForm.id, { title: resForm.title, res_type: resForm.res_type, url: resForm.url, content: resForm.content, status })
    else res = await createResource({ title: resForm.title, res_type: resForm.res_type, url: resForm.url, content: resForm.content, status })
    if (res.code === 200) { ElMessage.success('保存成功'); resDialog.value = false; loadRes() }
    else ElMessage.error(res.msg || '失败')
  } catch (e) { ElMessage.error('操作失败') } finally { resSaving.value = false }
}
const removeRes = async (row) => {
  try { await ElMessageBox.confirm(`删除资源「${row.title}」？`, '提示', { type: 'warning' }) } catch { return }
  const res = await deleteResource(row.id)
  if (res.code === 200) { ElMessage.success('已删除'); loadRes() }
}

onMounted(loadHoles)
</script>

<style scoped>
.toolbar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px; }
</style>
