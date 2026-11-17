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
            <div style="font-size:13px"><b>会话 #{{ s.id }}</b> · {{ s.started_at }}</div>
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
                <!-- 风险评估对低等级（绿/黄/橙）不向学生展示标签或命中词，避免标签感；
                     仅红色高危时展示热线横幅（一票否决，伦理要求不可隐藏危机信号）。 -->
                <div v-if="m.is_vetoed" class="veto-alert">
                  ⚠️ AI 已触发安全保护，请立即拨打全国24小时心理援助热线：<b>{{ m.crisis_hotline }}</b>
                </div>
                <button
                  v-if="m.role === 'assistant' && !loading"
                  class="voice-btn"
                  @click="playingIndex === idx ? stopVoice() : playVoice(m.content, idx)"
                >
                  {{ playingIndex === idx ? '⏹ 停止' : '🔊 朗读' }}
                </button>
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
            <div class="input-toolbar">
              <el-popover
                placement="top-start"
                :width="340"
                trigger="click"
                v-model:visible="showEmoji"
                popper-class="emoji-popover"
              >
                <div class="emoji-panel">
                  <div class="emoji-grid">
                    <span
                      v-for="(e, i) in emojiList"
                      :key="i"
                      class="emoji-item"
                      @click="insertEmoji(e)"
                    >{{ e }}</span>
                  </div>
                </div>
                <template #reference>
                  <el-button size="small" circle class="emoji-btn">
                    😊
                  </el-button>
                </template>
              </el-popover>
              <span class="toolbar-hint">选个表情，表达你的心情</span>
            </div>
            <div class="mic-row">
              <el-button
                circular
                size="small"
                :type="recording ? 'danger' : 'primary'"
                :disabled="loading"
                @mousedown.prevent="startRecord()"
                @mouseup.prevent="stopRecord()"
                @mouseleave="stopRecord()"
                class="mic-btn"
              >
                {{ recording ? '🔴 正在录音，松开结束' : '🎤 按住说话' }}
              </el-button>
              <span class="mic-tip">按住说话，松开即可把语音识别成文字</span>
            </div>
            <el-input
              ref="inputRef"
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
import { ElMessage } from 'element-plus'
import { sendChatMessage, getChatSessions, getChatHistory } from '@/api/student'
import { stt, tts } from '@/api/voice'
import VoiceRecorder from '@/components/VoiceRecorder'

const router = useRouter()
const inputText = ref('')
const messages = ref([])
const sessionList = ref([])
const currentSessionId = ref(null)
const showHistory = ref(false)
const loading = ref(false)
const msgBox = ref(null)
const inputRef = ref(null)
const showEmoji = ref(false)

const emojiList = [
  '😀', '😁', '😂', '🤣', '😊', '😇', '🙂', '😉',
  '😍', '🥰', '😘', '😗', '😚', '😋', '😛', '😜',
  '🤪', '😝', '🤑', '🤗', '🤭', '🤫', '🤔', '🤐',
  '😶', '😐', '😑', '😬', '🙄', '😯', '😦', '😧',
  '😮', '😲', '🥱', '😴', '🤤', '😪', '😫', '😌',
  '😔', '😕', '🙃', '🫠', '🫡', '🤐', '🫥', '🥲',
  '😏', '😒', '🙄', '😬', '🤥', '😌', '😔', '😪',
  '❤️', '🧡', '💛', '💚', '💙', '💜', '🖤', '🤍',
  '🌱', '🌿', '🍀', '🌸', '🌺', '🌻', '🌼', '🌷',
  '☘️', '🍃', '🪴', '🌵', '🌳', '🌴', '🌲', '🌰',
  '☀️', '🌤️', '⛅', '☁️', '🌧️', '🌦️', '⛈️', '🌈',
  '⭐', '🌟', '✨', '💫', '🪐', '🌙', '🌛', '🌜',
  '🎵', '🎶', '🎼', '🎹', '🎷', '🎺', '🎸', '🪕',
  '📚', '📖', '📝', '✏️', '🖊️', '🖋️', '📓', '📔',
  '🏠', '🏡', '🏖️', '🏔️', '🏕️', '⛺', '🌋', '🏜️',
  '🍀', '🎯', '🎨', '🎭', '🎪', '🎢', '🎡', '🎠',
  '🧘', '🏃', '🚶', '💃', '🕺', '👯', '🤝', '🙏',
  '💪', '🫶', '🤲', '👐', '🙌', '🤙', '👋', '✌️',
]

// ---- 语音对话：录音(STT 输入) + 朗读(TTS 输出，支持随时打断) ----
const recorder = new VoiceRecorder()
const recording = ref(false)
const micBusy = ref(false)
const playingIndex = ref(-1)

// 正在播放的后端音频实例（用于随时 stop / 打断）
let currentAudio = null

// 停止当前朗读（后端音频 + 浏览器兜底朗读都会被中止）
const stopVoice = () => {
  if (currentAudio) {
    currentAudio.pause()
    currentAudio.src = ''
    currentAudio = null
  }
  if (window.speechSynthesis) {
    window.speechSynthesis.cancel()
  }
  playingIndex.value = -1
}

// 按住说话：开始录音（请求麦克风权限）
const startRecord = async () => {
  if (recording.value || micBusy.value || loading.value) return
  micBusy.value = true
  try {
    await recorder.start()
    recording.value = true
  } catch (e) {
    ElMessage.warning('无法录音：' + (e || '请授予麦克风权限'))
  } finally {
    micBusy.value = false
  }
}

// 松开：停止录音并上传识别文字
const stopRecord = async () => {
  if (!recording.value) return
  const blob = await recorder.stop()
  recording.value = false
  if (!blob) return
  ElMessage.info('正在识别语音…')
  try {
    const res = await stt(blob, 'record.wav')
    if (res.code === 200 && res.data.text) {
      inputText.value = res.data.text
      ElMessage.success('已识别，可修改后点击「发送」')
    } else {
      ElMessage.warning(res.msg || '未识别到内容，请再试一次')
    }
  } catch (e) {
    ElMessage.error('语音识别失败：' + (e.message || e))
  }
}

// 朗读 AI 回复（TTS，支持随时打断：重复点击当前项 = 停止，点其它项 = 切换）
const playVoice = async (text, idx) => {
  if (!text || loading.value) return
  // 先停掉任何已在播放的声音，实现"随时打断/切换"
  stopVoice()
  playingIndex.value = idx
  let used = false
  try {
    const res = await tts(text)
    if (res.code === 200 && res.data.url) {
      used = true
      const audio = new Audio(res.data.url)
      currentAudio = audio
      const finish = () => { if (currentAudio === audio) { currentAudio = null; playingIndex.value = -1 } }
      audio.onended = finish
      audio.onerror = () => { finish(); readAloudLocal(text, idx) }
      audio.play()
    }
  } catch (e) {
    // 后端语音暂不可用时，回退用浏览器原生朗读
  }
  if (!used) readAloudLocal(text, idx)
}

// 最终兜底：用浏览器原生 speechSynthesis 朗读（任何环境都能出声，也支持打断）
const readAloudLocal = (text, idx) => {
  playingIndex.value = idx
  if (window.speechSynthesis && window.SpeechSynthesisUtterance) {
    const u = new SpeechSynthesisUtterance(text)
    u.lang = 'zh-CN'
    u.onend = () => { playingIndex.value = -1 }
    u.onerror = () => { playingIndex.value = -1 }
    window.speechSynthesis.speak(u)
  } else {
    playingIndex.value = -1
    ElMessage.warning('语音服务暂不可用，请使用 Chrome / Edge 浏览器')
  }
}

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
    const timedOut = err.code === 'ECONNABORTED' || /timeout/i.test(err.message || '')
    const msg = timedOut
      ? '⚠️ 回复生成超时了（大模型生成较慢），请稍后重试'
      : '⚠️ 网络异常，请确认后端服务已启动（python -m uvicorn backend.app:app --port 8000）'
    messages.value.push({ role: 'assistant', content: msg })
  } finally {
    loading.value = false
    scrollBottom()
  }
}

const insertEmoji = (emoji) => {
  inputText.value += emoji
  showEmoji.value = false
  nextTick(() => {
    const ta = inputRef.value?.textarea
    if (ta) {
      ta.focus()
      const pos = ta.value.length
      ta.setSelectionRange(pos, pos)
    }
  })
}

const clearAll = () => {
  messages.value = []
  currentSessionId.value = null
}

onMounted(async () => {
  // 先刷新会话列表
  await loadSessions()
  // 仅当尚未开始新对话时，一次性自动恢复最近会话（避免与用户操作并发竞态覆盖）
  if (!currentSessionId.value && sessionList.value.length) {
    await switchSession(sessionList.value[0].id)
  }
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
.mic-row {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 8px;
}
.mic-btn { flex-shrink: 0; }
.mic-tip { font-size: 12px; color: #909399; }
.voice-btn {
  margin-top: 8px;
  background: transparent;
  border: none;
  color: #409eff;
  cursor: pointer;
  font-size: 12px;
  padding: 0;
}
.voice-btn:hover { text-decoration: underline; }
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

.input-toolbar {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 8px;
}

.emoji-btn {
  background: var(--brand-bg-soft) !important;
  border: 1px solid var(--brand-border) !important;
  font-size: 16px;
  transition: all 0.2s;
}

.emoji-btn:hover {
  background: var(--brand-primary-light) !important;
  transform: scale(1.1);
}

.toolbar-hint {
  font-size: 12px;
  color: var(--brand-text-muted);
}

.emoji-panel {
  padding: 6px;
}

.emoji-grid {
  display: grid;
  grid-template-columns: repeat(8, 1fr);
  gap: 2px;
  max-height: 220px;
  overflow-y: auto;
}

.emoji-item {
  font-size: 18px;
  text-align: center;
  padding: 4px 2px;
  cursor: pointer;
  border-radius: 6px;
  transition: all 0.15s;
  user-select: none;
  line-height: 1;
}

.emoji-item:hover {
  background: var(--brand-bg-soft);
  transform: scale(1.25);
}
</style>

<style>
.emoji-popover {
  padding: 4px !important;
  border-radius: var(--brand-radius-md) !important;
  border: 1px solid var(--brand-border) !important;
}

.emoji-popover .el-popover__content {
  padding: 0 !important;
}
</style>
