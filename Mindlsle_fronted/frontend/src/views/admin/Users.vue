<template>
  <div class="admin-card">
    <div class="toolbar">
      <el-radio-group v-model="roleFilter" @change="load">
        <el-radio-button label="">全部</el-radio-button>
        <el-radio-button label="student">学生</el-radio-button>
        <el-radio-button label="teacher">教师</el-radio-button>
        <el-radio-button label="admin">管理员</el-radio-button>
      </el-radio-group>
      <el-button type="primary" @click="openCreate">＋ 新建账号</el-button>
    </div>

    <el-table :data="rows" border stripe v-loading="loading">
      <el-table-column prop="id" label="ID" width="70" />
      <el-table-column prop="username" label="用户名" width="140" />
      <el-table-column prop="display_name" label="姓名/昵称" width="140" />
      <el-table-column prop="role" label="角色" width="100">
        <template #default="s">
          <el-tag :type="roleTag(s.row.role)" size="small">{{ roleText(s.row.role) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="school" label="学校" min-width="120" />
      <el-table-column prop="grade" label="年级/班级" min-width="120" />
      <el-table-column prop="created_at" label="创建时间" width="170" />
      <el-table-column label="操作" width="220" fixed="right">
        <template #default="s">
          <el-button size="small" @click="openEdit(s.row)">编辑</el-button>
          <el-button size="small" type="danger" plain @click="remove(s.row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="dialogVisible" :title="form.id ? '编辑账号' : '新建账号'" width="460px">
      <el-form :model="form" label-width="90px">
        <el-form-item label="角色">
          <el-select v-model="form.role" :disabled="!!form.id" style="width:100%">
            <el-option label="学生" value="student" />
            <el-option label="教师" value="teacher" />
            <el-option label="管理员" value="admin" />
          </el-select>
        </el-form-item>
        <el-form-item label="用户名">
          <el-input v-model="form.username" :disabled="!!form.id" placeholder="至少3个字符" />
        </el-form-item>
        <el-form-item label="密码">
          <el-input v-model="form.password" type="password" :placeholder="form.id ? '留空则不修改' : '至少6个字符'" show-password />
        </el-form-item>
        <template v-if="!form.id && form.role === 'student'">
          <el-form-item label="姓名"><el-input v-model="form.name" /></el-form-item>
          <el-form-item label="性别">
            <el-select v-model="form.gender" style="width:100%">
              <el-option label="男" value="男" /><el-option label="女" value="女" />
            </el-select>
          </el-form-item>
          <el-form-item label="年龄"><el-input-number v-model="form.age" :min="6" :max="18" /></el-form-item>
          <el-form-item label="学校"><el-input v-model="form.school" /></el-form-item>
          <el-form-item label="年级/班级"><el-input v-model="form.grade" /></el-form-item>
        </template>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="save">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, reactive } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  getAdminUsers, createAdminUser, updateAdminUser, deleteAdminUser
} from '@/api/admin'

const roleFilter = ref('')
const rows = ref([])
const loading = ref(false)
const dialogVisible = ref(false)
const saving = ref(false)
const form = reactive({ id: null, role: 'student', username: '', password: '', name: '', gender: '男', age: 12, school: '', grade: '' })

const roleText = (r) => ({ student: '学生', teacher: '教师', admin: '管理员' }[r] || r)
const roleTag = (r) => ({ student: 'primary', teacher: 'warning', admin: 'danger' }[r] || 'info')

const load = async () => {
  loading.value = true
  try {
    const res = await getAdminUsers(roleFilter.value || undefined)
    if (res.code === 200) rows.value = res.data
  } catch (e) { ElMessage.error('加载用户失败') } finally { loading.value = false }
}

const resetForm = () => {
  Object.assign(form, { id: null, role: 'student', username: '', password: '', name: '', gender: '男', age: 12, school: '', grade: '' })
}
const openCreate = () => { resetForm(); dialogVisible.value = true }
const openEdit = (row) => {
  resetForm()
  Object.assign(form, { id: row.id, role: row.role, username: row.username })
  dialogVisible.value = true
}

const save = async () => {
  saving.value = true
  try {
    let res
    if (form.id) {
      const payload = {}
      if (form.password) payload.password = form.password
      if (form.role) payload.role = form.role
      res = await updateAdminUser(form.id, payload)
    } else {
      res = await createAdminUser({ ...form })
    }
    if (res.code === 200) {
      ElMessage.success(res.msg || '成功')
      dialogVisible.value = false
      load()
    } else ElMessage.error(res.msg || '失败')
  } catch (e) { ElMessage.error('操作失败') } finally { saving.value = false }
}

const remove = async (row) => {
  try {
    await ElMessageBox.confirm(`确定删除账号「${row.username}」吗？`, '提示', { type: 'warning' })
  } catch { return }
  const res = await deleteAdminUser(row.id)
  if (res.code === 200) { ElMessage.success('已删除'); load() }
  else ElMessage.error(res.msg || '删除失败')
}

onMounted(load)
</script>

<style scoped>
.toolbar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px; }
.admin-card { background: #fff; border-radius: 10px; padding: 18px; }
</style>
