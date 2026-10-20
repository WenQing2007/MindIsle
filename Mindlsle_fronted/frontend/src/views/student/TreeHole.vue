<template>
  <div class="treehole-container">
    <!-- 发布心事表单 -->
    <el-card class="publish-card" shadow="hover">
      <el-input
        v-model="form.content"
        type="textarea"
        rows="4"
        placeholder="写下你的心事..."
        maxlength="500"
      ></el-input>
      <div class="publish-row">
        <el-checkbox v-model="form.is_anonymous">匿名发布</el-checkbox>
        <el-button type="primary" :loading="loading" @click="submitTreehole">
          发布
        </el-button>
      </div>
    </el-card>

    <!-- 标签切换：广场 / 我的树洞 -->
    <el-tabs v-model="activeTab" type="card" class="mt-4" @change="switchTab">
      <el-tab-pane label="树洞广场" name="square"></el-tab-pane>
      <el-tab-pane label="我的树洞" name="my"></el-tab-pane>
    </el-tabs>

    <!-- 树洞列表 -->
    <div class="list-wrap">
      <el-card v-for="item in treeholeList" :key="item.id" class="tree-item" shadow="hover">
        <div class="item-content">{{ item.content }}</div>
        <div class="item-footer">
          <span v-if="item.student_id">用户{{ item.student_id }}</span>
          <span v-else>匿名用户</span>
          <span class="time">{{ item.created_at }}</span>
        </div>
      </el-card>
      <el-empty v-if="treeholeList.length === 0" description="暂无内容"></el-empty>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { createTreehole, getTreeholeList, getMyTreehole } from '@/api/student'

// 标签
const activeTab = ref('square')
// 加载状态
const loading = ref(false)
// 表单
const form = reactive({
  content: '',
  is_anonymous: 1 // 默认开启匿名：1开启，0关闭
})
// 树洞列表
const treeholeList = ref([])

// 切换标签加载对应数据
const switchTab = async () => {
  if (activeTab.value === 'square') {
    await loadSquare()
  } else {
    await loadMyTreehole()
  }
}

// 加载广场全部树洞
const loadSquare = async () => {
  const res = await getTreeholeList()
  if (res.code === 200) treeholeList.value = res.data
}

// 加载我发布的树洞
const loadMyTreehole = async () => {
  const res = await getMyTreehole()
  if (res.code === 200) treeholeList.value = res.data
}

// 提交发布
const submitTreehole = async () => {
  if (!form.content.trim()) {
    ElMessage.warning('内容不能为空')
    return
  }
  loading.value = true
  try {
    await createTreehole(form)
    ElMessage.success('发布成功')
    form.content = ''
    // 刷新列表
    switchTab()
  } catch (err) {
    ElMessage.error('发布失败')
  } finally {
    loading.value = false
  }
}

// 页面初始化加载广场
onMounted(() => {
  loadSquare()
})
</script>

<style scoped>
.treehole-container {
  max-width: 800px;
  margin: 0 auto;
  padding: 20px;
}
.publish-card {
  margin-bottom: 20px;
}
.publish-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 12px;
}
.tree-item {
  margin-bottom: 16px;
}
.item-content {
  font-size: 15px;
  line-height: 1.6;
  margin-bottom: 10px;
}
.item-footer {
  display: flex;
  justify-content: space-between;
  color: #999;
  font-size: 13px;
}
.mt-4 {
  margin-top: 16px;
}
</style>
