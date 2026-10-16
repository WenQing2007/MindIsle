<template>
  <div class="treehole">
    <el-page-header content="树洞广场" @back="$router.push('/student/home')"></el-page-header>
    <el-card style="margin-top:20px">
      <el-input v-model="newPost" type="textarea" :rows="4" placeholder="写下你的心事，匿名发布"></el-input>
      <el-button type="primary" style="margin-top:10px">发布树洞</el-button>
    </el-card>

    <div style="margin-top:20px">
      <el-card v-for="item in holeList" :key="item.id" style="margin-bottom:15px">
        <p>{{ item.content }}</p>
        <div style="text-align:right;color:#888">匿名用户</div>
      </el-card>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { getTreeHoleList, postTreeHole } from '@/api/student'
import { useRouter } from 'vue-router'
const router = useRouter()

const newContent = ref('')
const holeList = ref([])

// 获取树洞列表
const loadList = async () => {
  try {
    const res = await getTreeHoleList()
    if(res.code === 200){
      holeList.value = res.data
    }
  } catch (err) {
    console.error("获取树洞失败", err)
  }
}

// 发布树洞
const submitPost = async () => {
  if(!newContent.value){
    alert("内容不能为空")
    return
  }
  try{
    const res = await postTreeHole({content: newContent.value})
    if(res.code ===200){
      newContent.value = ''
      await loadList() //发布成功，刷新列表
    }else{
      alert(res.msg)
    }
  }catch(err){
    alert("发布失败")
  }
}

onMounted(()=>{
  loadList()
})
</script>

<style scoped>
.treehole{
  padding:30px;
}
</style>
