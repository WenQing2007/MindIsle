<template>
  <div class="treehole-page">
    <el-page-header @back="$router.push('/student/home')">
      <template #content>
        <span class="page-title">🌳 树洞广场</span>
      </template>
    </el-page-header>

    <el-card class="compose-card" shadow="never">
      <div class="compose-header">
        <span class="compose-icon">✍️</span>
        <span class="compose-hint">写下你的心事，这里没有人认识你</span>
      </div>
      <el-input
        v-model="newContent"
        type="textarea"
        :rows="4"
        placeholder="今天发生了什么？把它悄悄告诉树洞吧..."
        maxlength="500"
        show-word-limit
      ></el-input>
      <div class="compose-footer">
        <el-button type="primary" class="btn-soft" @click="submitPost" :loading="submitting">
          🌿 匿名发布
        </el-button>
      </div>
    </el-card>

    <div class="hole-list" v-if="holeList.length > 0">
      <el-card
        v-for="item in holeList"
        :key="item.id"
        class="hole-card"
        shadow="hover"
      >
        <div class="hole-body">
          <p class="hole-content">{{ item.content }}</p>
          <div class="hole-meta">
            <span class="hole-author">🌱 {{ item.author_name }}</span>
            <span class="hole-time">{{ formatTime(item.created_at) }}</span>
          </div>
        </div>

        <div class="hole-actions">
          <el-button
            link
            type="primary"
            class="toggle-comments"
            @click="toggleComments(item.id)"
          >
            💬 评论 <span class="comment-count">{{ commentMap[item.id]?.length || 0 }}</span>
            <span class="arrow" :class="{ open: expandedId === item.id }">▾</span>
          </el-button>
        </div>

        <div v-if="expandedId === item.id" class="comments-section">
          <div class="comments-divider"><span>🍃 温暖回复</span></div>

          <div v-if="loadingComments[item.id]" class="comments-loading">
            <el-skeleton :rows="2" animated />
          </div>

          <div v-else-if="(commentMap[item.id] || []).length === 0" class="comments-empty">
            <span>还没有人回复，做第一个温暖 TA 的人吧 🌿</span>
          </div>

          <div v-else class="comment-list">
            <div
              v-for="c in commentMap[item.id]"
              :key="c.id"
              class="comment-item"
            >
              <div class="comment-avatar">🌿</div>
              <div class="comment-body">
                <div class="comment-meta">
                  <span class="comment-author">{{ c.author_name }}</span>
                  <span class="comment-time">{{ formatTime(c.created_at) }}</span>
                </div>
                <div class="comment-content">{{ c.content }}</div>
              </div>
            </div>
          </div>

          <div class="comment-input-row">
            <el-input
              v-model="commentText[item.id]"
              size="small"
              placeholder="送一句温暖的话..."
              @keydown.enter.exact.prevent="submitComment(item.id)"
            ></el-input>
            <el-button
              type="primary"
              size="small"
              class="btn-soft"
              @click="submitComment(item.id)"
              :loading="submittingComment[item.id]"
            >
              发送
            </el-button>
          </div>
        </div>
      </el-card>
    </div>

    <el-empty v-else description="树洞还很安静，来写下第一条吧 🌱" />
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { getTreeHoleList, postTreeHole, getTreeHoleComments, postTreeHoleComment } from '@/api/student'

const newContent = ref('')
const holeList = ref([])
const submitting = ref(false)

const expandedId = ref(null)
const commentMap = reactive({})
const commentText = reactive({})
const loadingComments = reactive({})
const submittingComment = reactive({})

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
  if (!newContent.value.trim()) return
  submitting.value = true
  try {
    const res = await postTreeHole({ content: newContent.value.trim() })
    if (res.code === 200) {
      newContent.value = ''
      await loadList()
    } else {
      alert(res.msg || "发布失败")
    }
  } catch (err) {
    alert("发布失败，请检查后端服务是否启动")
  } finally {
    submitting.value = false
  }
}

const toggleComments = async (holeId) => {
  if (expandedId.value === holeId) {
    expandedId.value = null
    return
  }
  expandedId.value = holeId
  if (!commentMap[holeId]) {
    await loadComments(holeId)
  }
}

const loadComments = async (holeId) => {
  loadingComments[holeId] = true
  try {
    const res = await getTreeHoleComments(holeId)
    if (res.code === 200) {
      commentMap[holeId] = res.data
    } else {
      commentMap[holeId] = []
    }
  } catch (err) {
    commentMap[holeId] = []
  } finally {
    loadingComments[holeId] = false
  }
}

const submitComment = async (holeId) => {
  const text = (commentText[holeId] || '').trim()
  if (!text || submittingComment[holeId]) return
  submittingComment[holeId] = true
  try {
    const res = await postTreeHoleComment({ hole_id: holeId, content: text })
    if (res.code === 200) {
      commentText[holeId] = ''
      await loadComments(holeId)
    } else {
      alert(res.msg || "评论失败")
    }
  } catch (err) {
    alert("评论失败，请检查后端服务")
  } finally {
    submittingComment[holeId] = false
  }
}

const formatTime = (iso) => {
  if (!iso) return ''
  try {
    const d = new Date(iso.replace(' ', 'T'))
    const now = new Date()
    const diff = Math.floor((now - d) / 1000)
    if (diff < 60) return '刚刚'
    if (diff < 3600) return Math.floor(diff / 60) + ' 分钟前'
    if (diff < 86400) return Math.floor(diff / 3600) + ' 小时前'
    return d.toLocaleDateString('zh-CN')
  } catch {
    return iso
  }
}

onMounted(() => {
  loadList()
})
</script>

<style scoped>
.treehole-page {
  padding: 30px;
  max-width: 780px;
  margin: 0 auto;
}

.page-title {
  font-size: 22px;
  font-weight: 600;
  color: var(--brand-primary-dark);
}

.compose-card {
  margin-bottom: 24px;
  border-radius: var(--brand-radius-lg) !important;
  background: linear-gradient(135deg, var(--brand-bg-soft) 0%, var(--brand-cream) 100%) !important;
  border: 1px solid var(--brand-border) !important;
}

.compose-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
  color: var(--brand-text-soft);
  font-size: 14px;
}

.compose-icon {
  font-size: 18px;
}

.compose-hint {
  font-style: italic;
}

.compose-footer {
  margin-top: 14px;
  text-align: right;
}

.btn-soft {
  background: linear-gradient(135deg, var(--brand-primary) 0%, var(--brand-primary-dark) 100%) !important;
  border: none !important;
  border-radius: 20px !important;
  padding: 8px 22px !important;
  box-shadow: 0 4px 12px rgba(92, 184, 149, 0.28) !important;
}

.btn-soft:hover {
  transform: translateY(-1px);
  box-shadow: 0 6px 16px rgba(92, 184, 149, 0.38) !important;
}

.hole-list {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.hole-card {
  border-radius: var(--brand-radius-lg) !important;
  transition: box-shadow 0.25s ease !important;
}

.hole-card:hover {
  box-shadow: var(--brand-shadow-lg) !important;
}

.hole-body {
  padding-bottom: 4px;
}

.hole-content {
  font-size: 15px;
  line-height: 1.8;
  color: var(--brand-text);
  margin: 0 0 14px 0;
  white-space: pre-wrap;
  word-break: break-word;
}

.hole-meta {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 13px;
  color: var(--brand-text-muted);
}

.hole-author {
  color: var(--brand-accent);
  font-weight: 500;
}

.hole-time {
  color: var(--brand-text-muted);
}

.hole-actions {
  margin-top: 8px;
  padding-top: 12px;
  border-top: 1px dashed var(--brand-border);
}

.toggle-comments {
  font-size: 13px !important;
  color: var(--brand-primary) !important;
  padding: 0 !important;
}

.toggle-comments:hover {
  color: var(--brand-primary-dark) !important;
}

.comment-count {
  display: inline-block;
  min-width: 18px;
  height: 18px;
  line-height: 18px;
  padding: 0 5px;
  background: var(--brand-primary-light);
  color: white;
  border-radius: 10px;
  font-size: 11px;
  margin-left: 2px;
  text-align: center;
}

.arrow {
  display: inline-block;
  margin-left: 4px;
  transition: transform 0.25s ease;
}

.arrow.open {
  transform: rotate(180deg);
}

.comments-section {
  margin-top: 14px;
  padding-top: 14px;
  border-top: 1px solid var(--brand-border);
  animation: fadeIn 0.25s ease;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(-6px); }
  to { opacity: 1; transform: translateY(0); }
}

.comments-divider {
  text-align: center;
  margin-bottom: 14px;
}

.comments-divider span {
  display: inline-block;
  padding: 3px 14px;
  background: var(--brand-bg-soft);
  color: var(--brand-primary-dark);
  font-size: 12px;
  border-radius: 12px;
}

.comments-loading {
  padding: 8px 0;
}

.comments-empty {
  text-align: center;
  padding: 18px;
  color: var(--brand-text-muted);
  font-size: 13px;
}

.comment-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-bottom: 14px;
}

.comment-item {
  display: flex;
  gap: 10px;
  padding: 10px 12px;
  background: var(--brand-bg);
  border-radius: var(--brand-radius-md);
  transition: background 0.2s;
}

.comment-item:hover {
  background: var(--brand-bg-soft);
}

.comment-avatar {
  width: 30px;
  height: 30px;
  border-radius: 50%;
  background: linear-gradient(135deg, var(--brand-primary-light) 0%, var(--brand-primary) 100%);
  color: white;
  text-align: center;
  line-height: 30px;
  font-size: 14px;
  flex-shrink: 0;
}

.comment-body {
  flex: 1;
  min-width: 0;
}

.comment-meta {
  display: flex;
  gap: 8px;
  font-size: 12px;
  margin-bottom: 4px;
}

.comment-author {
  color: var(--brand-primary-dark);
  font-weight: 500;
}

.comment-time {
  color: var(--brand-text-muted);
}

.comment-content {
  font-size: 14px;
  color: var(--brand-text);
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-word;
}

.comment-input-row {
  display: flex;
  gap: 8px;
  align-items: center;
}

.comment-input-row .el-input {
  flex: 1;
}
</style>