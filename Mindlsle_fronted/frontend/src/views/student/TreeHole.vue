<template>
  <div class="treehole">
    <el-page-header content="树洞广场" @back="$router.push('/student/home')"></el-page-header>
    <el-card style="margin-top:20px">
      <el-input v-model="newContent" type="textarea" :rows="4" placeholder="写下你的心事，匿名发布"></el-input>
      <el-button type="primary" style="margin-top:10px" @click="submitPost">发布树洞</el-button>
    </el-card>

    <div style="margin-top:20px">
      <el-card v-for="item in holeList" :key="item.id" style="margin-bottom:15px">
        <p>{{ item.content }}</p>
        <div style="text-align:right;color:#888">{{ item.author_name }} · {{ item.created_at }}</div>
      </el-card>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { getTreeHoleList, postTreeHole } from '@/api/student'

const newContent = ref('')
const holeList = ref([])

const loadList = async () => {
  try {
    const res = await getTreeHoleList()
    if (res.code === 200) {
      holeList.value = res.data
    }
  } catch (err) {
    console.error("获取树洞失败", err)
  }
}

const submitPost = async () => {
  if (!newContent.value) {
    alert("内容不能为空")
    return
  }
  try {
    const res = await postTreeHole({ content: newContent.value })
    if (res.code === 200) {
      newContent.value = ''
      await loadList()
    } else {
      alert(res.msg || "发布失败")
    }
  } catch (err) {
    alert("发布失败，请检查后端服务是否启动")
  }
}

onMounted(() => {
  loadList()
})
</script>

<style scoped>
.treehole {
  padding: 30px;
}
</style>