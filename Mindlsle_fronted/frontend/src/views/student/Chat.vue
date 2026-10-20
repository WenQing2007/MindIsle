<template>
  <div class="chat-container">
    <!-- 左侧会话栏 -->
    <div class="chat-sidebar">
      <div class="sidebar-header">
        <el-button type="primary" @click="createNewSession">新建对话</el-button>
      </div>
      <div class="session-list">
        <div
          class="session-item"
          :class="{ active: currentSessionId === item.session_id }"
          v-for="item in sessionList"
          :key="item.session_id"
          @click="switchSession(item.session_id)"
        >
          <div class="session-title">会话 {{ item.session_id }}</div>
          <el-button size="small" type="danger" link @click.stop="endSession(item.session_id)">结束</el-button>
        </div>
      </div>
    </div>

    <!-- 右侧聊天主区域 -->
    <div class="chat-main">
      <div class="message-box" ref="messageBoxRef">
        <div class="msg-item" :class="msg.role" v-for="msg in msgList" :key="msg.id">
          <div class="msg-bubble">
            <p>{{ msg.content }}</p>
          </div>
        </div>
        <div v-if="loading" class="msg-item assistant">
          <div class="msg-bubble">AI正在思考...</div>
        </div>
      </div>

      <!-- 输入区 -->
      <div class="input-area">
        <el-input
          v-model="sendText"
          type="textarea"
          :rows="3"
          placeholder="写下你想说的话..."
          @keydown.ctrl.enter="sendMessage"
        />
        <el-button type="primary" @click="sendMessage" :loading="loading">发送</el-button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { getSessionList, getHistory, sendChatMsg, closeSession } from '@/api/chat'

// 学生id，登录后存在localStorage
const studentIdRaw = localStorage.getItem('student_id')
const studentId = ref(Number(studentIdRaw))
const sessionList = ref([])
const currentSessionId = ref(null)
const msgList = ref([])
const sendText = ref('')
const loading = ref(false)
const messageBoxRef = ref(null)

// 滚动到底部
const scrollBottom = () => {
  nextTick(() => {
    if (messageBoxRef.value) {
      messageBoxRef.value.scrollTop = messageBoxRef.value.scrollHeight
    }
  })
}

// 加载会话列表
const loadSessions = async () => {
  const res = await getSessionList(studentId.value)
  sessionList.value = res.sessions
}

// 切换会话，加载历史记录
const switchSession = async (sid) => {
  currentSessionId.value = sid
  const res = await getHistory(sid)
  msgList.value = res.messages
  scrollBottom()
}

// 新建会话（发第一条消息的时候自动创建，这里只是先选中空）
const createNewSession = () => {
  currentSessionId.value = null
  msgList.value = []
}

// 发送消息
const sendMessage = async () => {
  if (!sendText.value.trim()) {
    ElMessage.warning('不能发送空消息')
    return
  }
  loading.value = true
  try {
    const res = await sendChatMsg({
      student_id: studentId.value,
      message: sendText.value.trim(),
      session_id: currentSessionId.value
    })
    // 发送成功后更新会话id、消息列表
    currentSessionId.value = res.session_id
    sendText.value = ''
    // 重新拉取历史，简单粗暴保证数据一致
    await switchSession(currentSessionId.value)
    // 刷新会话列表（新增会话会出现在侧边栏）
    await loadSessions()
  } catch (err) {
    ElMessage.error('发送失败')
  } finally {
    loading.value = false
  }
}

// 结束会话
const endSession = async (sid) => {
  await closeSession(sid)
  ElMessage.success('会话已结束')
  await loadSessions()
  // 如果当前正在看这个会话，清空
  if (currentSessionId.value === sid) {
    createNewSession()
  }
}

onMounted(() => {
  loadSessions()
})
</script>

<style scoped>
.chat-container {
  display: flex;
  height: calc(100vh - 120px);
  gap:12px;
}
.chat-sidebar {
  width: 240px;
  border:1px solid #eee;
  border-radius:8px;
  padding:12px;
  display:flex;
  flex-direction:column;
}
.sidebar-header{
  margin-bottom:12px;
}
.session-list{
  flex:1;
  overflow-y:auto;
}
.session-item{
  padding:8px 10px;
  border-radius:6px;
  cursor:pointer;
  display:flex;
  justify-content:space-between;
  align-items:center;
  margin-bottom:6px;
}
.session-item:hover{
  background:#f5f7fa;
}
.session-item.active{
  background:#e8f3ff;
}

.chat-main{
  flex:1;
  border:1px solid #eee;
  border-radius:8px;
  display:flex;
  flex-direction:column;
}
.message-box{
  flex:1;
  padding:16px;
  overflow-y:auto;
}
.msg-item{
  margin-bottom:14px;
  display:flex;
}
.msg-item.user{
  justify-content:flex-end;
}
.msg-item.assistant{
  justify-content:flex-start;
}
.msg-bubble{
  max-width:60%;
  padding:10px 14px;
  border-radius:10px;
  white-space:pre-wrap;
}
.msg-item.user .msg-bubble{
  background:#409eff;
  color:white;
}
.msg-item.assistant .msg-bubble{
  background:#f4f4f5;
  color:#333;
}
.input-area{
  padding:12px;
  border-top:1px solid #eee;
  display:flex;
  gap:10px;
  align-items:flex-end;
}
.input-area .el-textarea{
  flex:1;
}
</style>
