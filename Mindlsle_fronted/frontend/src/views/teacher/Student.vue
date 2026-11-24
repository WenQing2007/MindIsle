<template>
  <div class="students-page">
    <div class="top-bar">
      <el-page-header @back="$router.back()" content="学生名册"></el-page-header>
      <el-button size="small" @click="$router.push('/teacher/home')">返回工作台</el-button>
    </div>

    <el-card style="margin-top:20px">
      <el-input
        v-model="keyword"
        placeholder="搜索姓名/学校/年级..."
        clearable
        style="width:300px;margin-bottom:16px"
      >
        <template #prefix>🔍</template>
      </el-input>

      <el-table :data="filteredStudents" stripe border v-loading="loading">
        <el-table-column prop="id" label="学号" width="80" />
        <el-table-column prop="name" label="姓名" width="120" />
        <el-table-column prop="gender" label="性别" width="80">
          <template #default="scope">
            {{ scope.row.gender === '男' ? '👨' : scope.row.gender === '女' ? '👩' : '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="age" label="年龄" width="80" />
        <el-table-column prop="school" label="学校" width="180" />
        <el-table-column prop="grade" label="年级/班级" width="140" />
        <el-table-column prop="created_at" label="注册时间" width="180" />
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import axios from 'axios'

const loading = ref(false)
const keyword = ref('')
const students = ref([])

const filteredStudents = computed(() => {
  const k = keyword.value.trim().toLowerCase()
  if (!k) return students.value
  return students.value.filter(s =>
    (s.name || '').toLowerCase().includes(k) ||
    (s.school || '').toLowerCase().includes(k) ||
    (s.grade || '').toLowerCase().includes(k)
  )
})

const loadData = async () => {
  loading.value = true
  try {
    const res = await axios.get('/api/students')
    if (res.data.code === 200) students.value = res.data.data
  } catch (e) {
    alert('加载学生列表失败：' + e.message)
  } finally {
    loading.value = false
  }
}

onMounted(loadData)
</script>

<style scoped>
.students-page { padding: 20px 30px; }
.top-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>
