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
        <div style="text-align:right;color:#888;margin-bottom:10px">
          {{ item.author_name }} · {{ item.created_at }}
        </div>

        <!-- 展开收起评论按钮 -->
        <el-button size="small" text @click="toggleComment(item.id)">
          {{ expandCommentId === item.id ? '收起评论' : `💬查看评论(${item.commentList?.length || 0})` }}
        </el-button>

        <!-- 评论区域 -->
        <div v-if="expandCommentId === item.id" class="comment-wrap">
          <el-input
            v-model="commentInputMap[item.id]"
            type="textarea"
            :rows="2"
            placeholder="写下你的评论，匿名发送"
          ></el-input>
          <el-button size="small" type="primary" style="margin-top:8px" @click="handleSubmitComment(item.id)">提交评论</el-button>

          <div class="comment-list" v-if="item.commentList && item.commentList.length">
            <div class="comment-item" v-for="c in item.commentList" :key="c.id">
              <div class="c-text">{{ c.content }}</div>
              <div class="c-meta">{{ c.author_name }} · {{ c.created_at }}</div>
            </div>
          </div>
          <div v-else class="empty-tip">暂无评论，快来抢沙发</div>
        </div>
      </el-card>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { getTreeHoleList, postTreeHole } from '@/api/student'

const newContent = ref('')
const holeList = ref([])

// 当前展开评论的树洞id
const expandCommentId = ref(null)
// 保存各个树洞对应的评论输入框内容
const commentInputMap = ref({})

const loadList = async () => {
  try {
    const res = await getTreeHoleList()
    if (res.code === 200) {
      holeList.value = res.data
      // 模拟：给每条树洞初始化空评论数组，后端返回数据后可以删掉这行
      holeList.value.forEach(post => {
        if (!post.commentList) post.commentList = []
      })
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

// 切换展开/收起评论
const toggleComment = (holeId) => {
  expandCommentId.value = expandCommentId.value === holeId ? null : holeId
  // 真实项目这里调用接口获取该树洞评论
  // if(expandCommentId.value){ await fetchCommentList(holeId) }
}

// 提交评论（模拟）
const handleSubmitComment = (holeId) => {
  const text = commentInputMap.value[holeId]?.trim()
  if (!text) {
    alert('评论不能为空')
    return
  }

  // ==========这里等后端接口写好，替换下面模拟代码==========
  /*
  const res = await postTreeHoleComment({ hole_id: holeId, content:text })
  if(res.code===200){
      commentInputMap.value[holeId] = ''
      await loadList()
  }
  */

  // 模拟新增一条评论，仅看界面效果
  const targetPost = holeList.value.find(p => p.id === holeId)
  if (targetPost) {
    targetPost.commentList.push({
      id: Date.now(),
      content: text,
      author_name: '匿名用户',
      created_at: new Date().toLocaleString()
    })
  }
  commentInputMap.value[holeId] = ''
}

onMounted(() => {
  loadList()
})
</script>

<style scoped>
.treehole {
  width: 100vw;
  min-height: 100vh;
  padding: 30px;
  box-sizing: border-box;
  margin: -30px calc(-50vw + 50%);
  background: linear-gradient(135deg, #fef2f2 0%, #fee2e2 100%);
}

:deep(.el-card) {
  border-radius: 20px !important;
  background-color: rgba(255, 255, 255, 0.72) !important;
  border: 1px solid rgba(255,255,255,0.8) !important;
  box-shadow: 0 4px 16px rgba(220,180,190,0.12) !important;
}

.comment-wrap {
  margin-top:14px;
  padding-top:12px;
  border-top:1px dashed #f8ccd4;
}
.comment-list {
  margin-top:12px;
}
.comment-item {
  background:rgba(255,255,255,0.55);
  border-radius:10px;
  padding:10px 14px;
  margin-bottom:8px;
}
.c-text {
  font-size:14px;
  color:#444;
  line-height:1.5;
}
.c-meta {
  margin-top:4px;
  font-size:12px;
  color:#888;
  text-align:right;
}
.empty-tip {
  margin-top:12px;
  font-size:13px;
  color:#999;
}
</style>
