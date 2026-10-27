<template>
  <div class="chat-page">
    <el-page-header content="MindIsle AI 心理陪伴" @back="$router.push('/student/home')">
      <template #extra>
        <el-button size="small" @click="showHistory = !showHistory">
          {{ showHistory ? '收起历史' : '历史会话' }}
        </el-button>
        <el-button size="small" type="danger" plain @click="clearAll">清空</el-button>
      </template>
    </el-page-header>

    <el-row :gutter="20" style="margin-top:20px; height: calc(100vh - 180px)">
      <el-col :span="6" v-if="showHistory">
        <el-card style="height:100%; overflow:auto">
          <div style="font-weight:bold; margin-bottom:10px">我的会话</div>
          <div v-if="sessionList.length === 0" style="color:#888; font-size:13px">暂无历史会话</div>
          <div
            v-for="s in sessionList"
            :key="s.id"
            class="session-item"
            :class="{ active: s.id === currentSessionId }"
            @click="switchSession(s.id)"
          >
            <div style="font-size:13px">{{ s.started_at }}</div>
            <div style="font-size:12px; color:#999">
              {{ s.ended_at ? '已结束' : '进行中' }}
            </div>
          </div>
        </el-card>
      </el-col>

      <el-col :span="showHistory ? 18 : 24">
        <el-card style="height:100%; display:flex; flex-direction:column">
          <div ref="msgBox" class="msg-box">
            <div
              v-for="(m, idx) in messages"
              :key="idx"
              class="msg-item"
              :class="m.role === 'user' ? 'msg-right' : 'msg-left'"
            >
              <div class="avatar">{{ m.role === 'user' ? '我' : 'AI' }}</div>
              <div class="bubble" :class="m.role === 'user' ? 'bubble-user' : 'bubble-ai'">
                <div style="white-space:pre-wrap">{{ m.content }}</div>
                <div v-if="m.risk_level_cn" class="risk-tag" :class="'risk-' + m.risk_level">
                  风险评估：{{ m.risk_level_cn }} {{ m.risk_matched ? '· ' + m.risk_matched.join('、') : '' }}
                </div>
                <div v-if="m.is_vetoed" class="veto-alert">
                  ⚠️ AI 已触发安全保护，请立即拨打全国24小时心理援助热线：<b>{{ m.crisis_hotline }}</b>
                </div>
              </div>
            </div>
            <div v-if="loading" class="msg-item msg-left">
              <div class="avatar">AI</div>
              <div class="bubble bubble-ai">
                <div class="loading-dots">
                  <span></span><span></span><span></span>
                </div>
              </div>
            </div>
          </div>

          <div class="input-area">
            <el-input
              v-model="inputText"
              type="textarea"
              :rows="3"
              placeholder="和 MindIsle AI 聊聊你的心情... (Enter 发送，Shift+Enter 换行)"
              @keydown.enter.exact.prevent="send"
              :disabled="loading"
              maxlength="500"
              show-word-limit
            ></el-input>
            <div style="margin-top:8px; text-align:right">
              <el-button type="primary" @click="send" :loading="loading">发送</el-button>
              <el-button @click="startNewSession" :disabled="loading">新会话</el-button>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick, computed } from 'vue'
import { useRouter } from 'vue-router'
import { sendChatMessage, getChatSessions, getChatHistory } from '@/api/student'

const router = useRouter()
const inputText = ref('')
const messages = ref([])
const sessionList = ref([])
const currentSessionId = ref(null)
const showHistory = ref(false)
const loading = ref(false)
const msgBox = ref(null)

const studentId = computed(() => {
  return parseInt(localStorage.getItem('student_id') || '1')
})

const scrollBottom = () => {
  nextTick(() => {
    if (msgBox.value) {
      msgBox.value.scrollTop = msgBox.value.scrollHeight
    }
  })
}

const loadSessions = async () => {
  try {
    const res = await getChatSessions(studentId.value)
    if (res.code === 200) {
      sessionList.value = res.data
    }
  } catch (err) {
    console.error(err)
  }
}

const switchSession = async (sid) => {
  currentSessionId.value = sid
  try {
    const res = await getChatHistory(sid)
    if (res.code === 200) {
      messages.value = res.data.messages
      scrollBottom()
    }
  } catch (err) {
    console.error(err)
  }
}

const startNewSession = () => {
  currentSessionId.value = null
  messages.value = []
}

const send = async () => {
  const text = inputText.value.trim()
  if (!text || loading.value) return

  messages.value.push({ role: 'user', content: text })
  inputText.value = ''
  loading.value = true
  scrollBottom()

  try {
    const res = await sendChatMessage({
      student_id: studentId.value,
      message: text,
      session_id: currentSessionId.value
    })
    if (res.code === 200) {
      const d = res.data
      currentSessionId.value = d.session_id
      messages.value.push({
        role: 'assistant',
        content: d.reply,
        risk_level: d.risk_level,
        risk_level_cn: d.risk_level_cn,
        risk_matched: d.risk_matched,
        is_vetoed: d.is_vetoed,
        crisis_hotline: d.crisis_hotline,
      })
      scrollBottom()
      loadSessions()
    } else {
      messages.value.push({ role: 'assistant', content: '⚠️ 发送失败：' + (res.msg || '未知错误') })
    }
  } catch (err) {
    messages.value.push({ role: 'assistant', content: '⚠️ 网络异常，请检查后端服务是否启动' })
  } finally {
    loading.value = false
    scrollBottom()
  }
}

const clearAll = () => {
  messages.value = []
  currentSessionId.value = null
}

onMounted(() => {
  loadSessions()
})
</script>

<style scoped>
.chat-page {
  padding: 20px 30px;
}
.msg-box {
  flex: 1;
  overflow-y: auto;
  padding: 10px;
}
.msg-item {
  display: flex;
  margin-bottom: 16px;
  align-items: flex-start;
}
.msg-right { flex-direction: row-reverse; }
.avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: #409eff;
  color: #fff;
  text-align: center;
  line-height: 36px;
  font-size: 13px;
  flex-shrink: 0;
  margin: 0 8px;
}
.msg-left .avatar { background: #67c23a; }
.bubble {
  max-width: 70%;
  padding: 12px 16px;
  border-radius: 10px;
  font-size: 14px;
  line-height: 1.6;
}
.bubble-user { background: #ecf5ff; color: #303133; }
.bubble-ai   { background: #f0f9eb; color: #303133; }
.risk-tag {
  margin-top: 8px;
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 12px;
  display: inline-block;
}
.risk-tag.risk-green  { background:#f0f9eb; color:#67c23a; }
.risk-tag.risk-yellow { background:#fdf6ec; color:#e6a23c; }
.risk-tag.risk-orange { background:#faecd8; color:#f56c1c; }
.risk-tag.risk-red    { background:#fef0f0; color:#f56c6c; }
.veto-alert {
  margin-top: 8px;
  padding: 10px;
  background: #fef0f0;
  border-radius: 6px;
  color: #f56c6c;
  font-size: 13px;
}
.input-area {
  border-top: 1px solid #ebeef5;
  padding-top: 12px;
}
.loading-dots {
  display: inline-flex;
  gap: 4px;
  padding: 4px 0;
}
.loading-dots span {
  width: 8px; height: 8px; background: #999; border-radius: 50%;
  animation: blink 1.4s infinite;
}
.loading-dots span:nth-child(2) { animation-delay: .2s; }
.loading-dots span:nth-child(3) { animation-delay: .4s; }
@keyframes blink {
  0%, 80%, 100% { opacity: .3; }
  40% { opacity: 1; }
}
.session-item {
  padding: 10px;
  margin-bottom: 8px;
  border-radius: 6px;
  cursor: pointer;
  background: #f5f7fa;
  transition: background .2s;
}
.session-item:hover { background: #ecf5ff; }
.session-item.active { background: #d9ecff; border: 1px solid #409eff; }
</style>