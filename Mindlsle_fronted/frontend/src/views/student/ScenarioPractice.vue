<template>
  <div class="scenario-page">
    <el-page-header content="🎭 情景演练" @back="$router.push('/student/home')"></el-page-header>

    <template v-if="!currentScene">
      <div class="intro-banner">
        <div class="intro-emoji">🎬</div>
        <div class="intro-text">
          <h2>在模拟场景中练习应对</h2>
          <p>选择一个场景，和 AI 一起角色扮演。你会遇到不同选择，每一个选择都有不同的结果。</p>
        </div>
      </div>

      <el-row :gutter="20">
        <el-col :xs="24" :sm="12" :md="8" v-for="scene in scenes" :key="scene.id">
          <el-card shadow="hover" class="scene-card" @click="startScene(scene.id)">
            <div class="scene-cover" :style="{ background: scene.cover }">
              <span class="scene-emoji">{{ scene.emoji }}</span>
            </div>
            <div class="scene-body">
              <div class="scene-title">{{ scene.title }}</div>
              <div class="scene-desc">{{ scene.desc }}</div>
              <div class="scene-meta">
                <el-tag size="small" :type="scene.level === '简单' ? 'success' : scene.level === '中等' ? 'warning' : 'danger'">{{ scene.level }}</el-tag>
                <span class="scene-tip">约 {{ scene.turns }} 轮对话</span>
              </div>
            </div>
          </el-card>
        </el-col>
      </el-row>
    </template>

    <template v-else>
      <div class="chat-header-bar">
        <el-button size="small" @click="currentScene = null">← 返回场景列表</el-button>
        <div class="scene-info">
          <span class="info-emoji">{{ currentScene.emoji }}</span>
          <span class="info-title">{{ currentScene.title }}</span>
        </div>
        <el-button size="small" type="danger" plain @click="restartScene">🔄 重新开始</el-button>
      </div>

      <div class="chat-area">
        <div
          v-for="(msg, idx) in messages"
          :key="idx"
          class="msg-item"
          :class="msg.role === 'user' ? 'msg-right' : 'msg-left'"
        >
          <div class="avatar">{{ msg.role === 'user' ? '你' : 'AI' }}</div>
          <div class="bubble" :class="msg.role === 'user' ? 'bubble-user' : 'bubble-ai'">
            <div class="bubble-text">{{ msg.content }}</div>
            <div v-if="msg.feedback" class="feedback-box" :class="'feedback-' + msg.feedback.type">
              <b>{{ msg.feedback.title }}</b>
              <div>{{ msg.feedback.text }}</div>
            </div>
          </div>
        </div>

        <div v-if="showEnding" class="ending-card">
          <div class="ending-emoji">{{ endingEmoji }}</div>
          <div class="ending-title">🎉 情景演练完成！</div>
          <div class="ending-summary">{{ currentScene.title }} · {{ endingSummary }}</div>
          <div class="ending-stats">
            <div class="stat-box">
              <div class="stat-num" style="color:#63b980">{{ score.good }}</div>
              <div class="stat-label">✨ 好选择</div>
            </div>
            <div class="stat-box">
              <div class="stat-num" style="color:#e2a86e">{{ score.mid }}</div>
              <div class="stat-label">🤔 一般</div>
            </div>
            <div class="stat-box">
              <div class="stat-num" style="color:#e07a7a">{{ score.bad }}</div>
              <div class="stat-label">⚠️ 不理想</div>
            </div>
          </div>
        </div>
      </div>

      <div v-if="currentChoice && !showEnding" class="choice-area">
        <div class="choice-prompt">👉 你会怎么做？</div>
        <div
          v-for="(c, i) in currentChoice.options"
          :key="i"
          class="choice-btn"
          @click="makeChoice(i)"
        >
          <span class="choice-letter">{{ String.fromCharCode(65 + i) }}</span>
          <span class="choice-text">{{ c.text }}</span>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, nextTick } from 'vue'

const scenes = [
  {
    id: 'exam',
    emoji: '📝',
    title: '考前焦虑',
    desc: '明天就要期末考试了，你翻来覆去睡不着...',
    cover: 'linear-gradient(135deg, #f5e6d3, #faf0e4)',
    level: '简单',
    turns: 3,
    startNode: 0,
    intro: '（晚上 11 点）明天就要期末考试了，你躺在床上，脑子里一直过着知识点...越想越紧张，心跳加速，完全睡不着。',
    dialogue: [
      {
        text: '（晚上 11 点）明天就要期末考试了，你躺在床上，脑子里一直过着知识点...越想越紧张，心跳加速，完全睡不着。',
        next: 1
      },
      {
        text: '你翻了个身，看了一眼手机 — 11:30 了。明天要考数学和语文，心里莫名一阵慌。',
        options: [
          { text: '起来继续复习，能看一点是一点', score: 'bad', feedback: { title: '⚠️ 不太建议', text: '这个时候继续复习只会让大脑更兴奋，反而更睡不着。而且疲劳状态下效率极低。' }, next: 2 },
          { text: '开个小夜灯，闭目做几次深呼吸', score: 'good', feedback: { title: '✨ 很棒！', text: '睡前放松是正确的选择。试试我们呼吸花园的 4-7-8 节奏，能有效安抚紧张的神经。' }, next: 2 },
          { text: '刷一会儿短视频转移注意力', score: 'mid', feedback: { title: '🤔 可以但不算最佳', text: '短暂转移注意力是好的，但短视频的蓝光会抑制褪黑素分泌，反而影响睡眠。' }, next: 2 }
        ]
      },
      {
        text: '（时间来到第二天早上）你感觉怎么样？',
        options: [
          { text: '精神还不错，带着小紧张去考场', score: 'good', feedback: { title: '✨ 很好！', text: '适度的紧张能让你更专注，这叫"唤醒水平"，保持住就好。' }, next: 3 },
          { text: '还是很慌，手心全是汗', score: 'mid', feedback: { title: '💡 试试', text: '进考场前做 3 次深呼吸（吸 5 秒呼 7 秒），能快速降低焦虑水平。' }, next: 3 },
          { text: '有点困，脑子不太清楚', score: 'bad', feedback: { title: '⚠️ 不太理想', text: '昨晚没睡好确实会影响状态。考场上先做简单题，找回状态后再啃难题。' }, next: 3 }
        ]
      },
      {
        text: '考试结束，你感觉发挥得如何？',
        options: [
          { text: '还不错，尽力了就好', score: 'good', feedback: { title: '✨ 很棒！', text: '对自己宽容一点，这是最重要的心态。' }, next: 'end' },
          { text: '有些题没把握，有点担心', score: 'mid', feedback: { title: '💡 正常反应', text: '考完就放掉吧，过度担心不会改变结果。总结经验下次更好。' }, next: 'end' }
        ]
      }
    ]
  },
  {
    id: 'friend',
    emoji: '🤝',
    title: '和朋友闹矛盾',
    desc: '你和最好的朋友因为一件小事吵架了...',
    cover: 'linear-gradient(135deg, #f5efff, #faf4ff)',
    level: '中等',
    turns: 3,
    startNode: 0,
    intro: '课间，你和好朋友因为"谁拿了你的笔记本"这件事吵了起来。她很生气地走开了...',
    dialogue: [
      {
        text: '课间，你和好朋友因为"谁拿了你的笔记本"这件事吵了起来。她很生气地走开了...',
        next: 1
      },
      {
        text: '上课铃响了，你们各自回到座位，一节课都没说话。你心里有点不是滋味。',
        options: [
          { text: '下课后主动找她，用"我句式"说感受', score: 'good', feedback: { title: '✨ 高情商做法！', text: '"我句式"能减少对方的防御。比如："刚才我有点急了，因为那个笔记本对我挺重要的，我不是想怪你..."' }, next: 2 },
          { text: '等她先来道歉，我没错', score: 'bad', feedback: { title: '⚠️ 不太建议', text: '关系僵着对谁都不好。先给台阶不代表你输了，而是你更在乎这段友谊。' }, next: 2 },
          { text: '写个小纸条传给她', score: 'mid', feedback: { title: '🤔 可以试试', text: '纸条是温和的方式，但面对面沟通的效果更好，能让她感受到你的真诚。' }, next: 2 }
        ]
      },
      {
        text: '放学后，你们还在冷战。你路过她的座位，看到她在收拾书包...',
        options: [
          { text: '停下来，递一瓶她常喝的奶茶', score: 'good', feedback: { title: '✨ 好温柔！', text: '用行动破冰比说对不起更有效。一杯奶茶就把台阶递过去了。' }, next: 3 },
          { text: '就这样擦身而过，假装没看见', score: 'bad', feedback: { title: '⚠️ 不太理想', text: '沉默会让矛盾沉淀下来，下次爆发会更严重。' }, next: 3 },
          { text: '发条消息："今天的事对不起"', score: 'mid', feedback: { title: '💡 有点生硬', text: '道歉是对的，但可以说更具体一点，比如"今天我态度不好，那个笔记本确实不是什么大事，对不起啊"' }, next: 3 }
        ]
      },
      {
        text: '（三天后）你们和好了吗？',
        options: [
          { text: '和好了，还一起吃了午饭', score: 'good', feedback: { title: '✨ 太好了！', text: '好的友谊需要主动维护。这次的小波折让你们更了解怎么相处了。' }, next: 'end' },
          { text: '还没说话，有点尴尬', score: 'mid', feedback: { title: '💡 再迈一步', text: '试试找个小事主动搭话，比如借个笔、问作业。破冰之后就好起来了。' }, next: 'end' }
        ]
      }
    ]
  },
  {
    id: 'stress',
    emoji: '💼',
    title: '被安排的周末',
    desc: '周末又被塞满了补习班，你一点都不想去...',
    cover: 'linear-gradient(135deg, #fff4e4, #fff9f0)',
    level: '中等',
    turns: 3,
    startNode: 0,
    intro: '妈妈给你报了三个补习班，周六周日排得满满当当。你看着同学在朋友圈发出去玩的照片，心里堵得慌...',
    dialogue: [
      {
        text: '妈妈给你报了三个补习班，周六周日排得满满当当。你看着同学在朋友圈发出去玩的照片，心里堵得慌...',
        next: 1
      },
      {
        text: '周五晚上，妈妈又在催你早点睡觉准备明天的课程。你心里很不爽。',
        options: [
          { text: '好好和妈妈说说你的感受', score: 'good', feedback: { title: '✨ 最棒的选择！', text: '试试："妈妈，我知道你想让我变好，但我现在有点累了。能不能有半天让我自己安排？"' }, next: 2 },
          { text: '不说了，硬着头皮去上吧', score: 'bad', feedback: { title: '⚠️ 不太建议', text: '长期压抑会积累成更大的情绪问题。而且累着学效率也低。' }, next: 2 },
          { text: '假装生病不去', score: 'mid', feedback: { title: '🤔 治标不治本', text: '逃一次课容易，但没解决根本问题。妈妈还是会给你安排，你也还是不开心。' }, next: 2 }
        ]
      },
      {
        text: '你终于鼓起勇气和妈妈谈了，她有些惊讶，但也在听。',
        options: [
          { text: '说出具体的感受和需求', score: 'good', feedback: { title: '✨ 继续保持', text: '具体比笼统更有力量："上周六上完课我累得下午都不想动了，能不能给我留半天休息？"' }, next: 3 },
          { text: '发脾气，指责妈妈不懂我', score: 'bad', feedback: { title: '⚠️ 不太好', text: '发脾气会让妈妈进入防御模式，反而听不进你的话。先冷静一下再谈。' }, next: 3 }
        ]
      },
      {
        text: '（一周后）情况有变化吗？',
        options: [
          { text: '妈妈同意减掉一个班，我有半天自由时间了！', score: 'good', feedback: { title: '🎉 完美！', text: '沟通的力量！你不仅解决了问题，还学会了表达自己的需要。' }, next: 'end' },
          { text: '谈完没什么变化，妈妈说这是为我好', score: 'mid', feedback: { title: '💡 没关系', text: '改变需要时间。可以试试让爸爸或老师帮忙说说，或者先执行再慢慢调整。' }, next: 'end' }
        ]
      }
    ]
  }
]

const currentScene = ref(null)
const messages = ref([])
const currentChoice = ref(null)
const currentNodeIndex = ref(0)
const showEnding = ref(false)
const score = ref({ good: 0, mid: 0, bad: 0 })

const endingEmoji = computed(() => {
  if (score.value.good >= score.value.mid + score.value.bad) return '🌟'
  if (score.value.bad > score.value.good) return '💪'
  return '🌱'
})

const endingSummary = computed(() => {
  const total = score.value.good + score.value.mid + score.value.bad
  if (total === 0) return '完成啦！'
  const rate = score.value.good / total
  if (rate >= 0.7) return '你的应对方式非常棒！继续保持这种积极沟通的态度～'
  if (rate >= 0.4) return '整体不错，还有一些可以做得更好的地方，下次试试新选择吧！'
  return '没关系，每一次练习都是成长。再试一次，你会有不同选择的勇气～'
})

const startScene = (id) => {
  const scene = scenes.find(s => s.id === id)
  if (!scene) return
  currentScene.value = scene
  messages.value = [{ role: 'assistant', content: scene.intro }]
  currentNodeIndex.value = 1
  showEnding.value = false
  score.value = { good: 0, mid: 0, bad: 0 }
  nextTick(() => advance())
}

const restartScene = () => {
  if (currentScene.value) startScene(currentScene.value.id)
}

const advance = () => {
  if (!currentScene.value) return
  const node = currentScene.value.dialogue[currentNodeIndex.value]
  if (!node) {
    showEnding.value = true
    return
  }
  if (node.text) {
    messages.value.push({ role: 'assistant', content: node.text })
    nextTick(() => scrollToBottom())
  }
  if (node.options) {
    currentChoice.value = node
  } else if (node.next !== undefined) {
    currentNodeIndex.value = node.next
    nextTick(() => advance())
  }
}

const makeChoice = (idx) => {
  if (!currentChoice.value) return
  const option = currentChoice.value.options[idx]

  messages.value.push({
    role: 'user',
    content: option.text
  })

  if (option.score === 'good') score.value.good++
  else if (option.score === 'mid') score.value.mid++
  else score.value.bad++

  if (option.feedback) {
    messages.value.push({
      role: 'assistant',
      content: option.feedback.title,
      feedback: {
        type: option.score,
        title: option.feedback.title,
        text: option.feedback.text
      }
    })
  }

  currentChoice.value = null
  currentNodeIndex.value = option.next

  nextTick(() => {
    scrollToBottom()
    if (option.next === 'end') {
      setTimeout(() => { showEnding.value = true }, 600)
    } else {
      setTimeout(() => advance(), 800)
    }
  })
}

const scrollToBottom = () => {
  const area = document.querySelector('.chat-area')
  if (area) area.scrollTop = area.scrollHeight
}
</script>

<style scoped>
.scenario-page {
  padding: 20px 30px;
  min-height: 100vh;
}

.intro-banner {
  display: flex;
  align-items: center;
  gap: 24px;
  padding: 24px 30px;
  margin-bottom: 24px;
  background: linear-gradient(135deg, #f5efff 0%, #f0f9ff 100%);
  border-radius: 20px;
}

.intro-emoji {
  font-size: 48px;
  flex-shrink: 0;
}

.intro-text h2 {
  margin: 0 0 6px 0;
  color: var(--brand-text);
}

.intro-text p {
  margin: 0;
  color: var(--brand-text-soft);
  font-size: 14px;
}

.scene-card {
  cursor: pointer;
  transition: all 0.3s;
  padding: 0 !important;
  margin-bottom: 20px;
}

.scene-card:hover {
  transform: translateY(-4px);
}

.scene-card :deep(.el-card__body) {
  padding: 0 !important;
}

.scene-cover {
  height: 120px;
  display: flex;
  justify-content: center;
  align-items: center;
}

.scene-emoji {
  font-size: 48px;
}

.scene-body {
  padding: 16px 20px 20px;
}

.scene-title {
  font-size: 18px;
  font-weight: 600;
  color: var(--brand-text);
  margin-bottom: 6px;
}

.scene-desc {
  font-size: 13px;
  color: var(--brand-text-soft);
  margin-bottom: 12px;
  line-height: 1.5;
}

.scene-meta {
  display: flex;
  align-items: center;
  gap: 8px;
}

.scene-tip {
  font-size: 12px;
  color: var(--brand-text-muted);
}

.chat-header-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 20px;
  background: var(--brand-bg-soft);
  border-radius: 14px;
  margin-bottom: 16px;
}

.scene-info {
  display: flex;
  align-items: center;
  gap: 8px;
}

.info-emoji {
  font-size: 22px;
}

.info-title {
  font-weight: 600;
  color: var(--brand-text);
}

.chat-area {
  max-height: 500px;
  overflow-y: auto;
  padding: 10px;
  margin-bottom: 16px;
}

.msg-item {
  display: flex;
  margin-bottom: 16px;
  align-items: flex-start;
}

.msg-left { }
.msg-right { flex-direction: row-reverse; }

.avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  text-align: center;
  line-height: 36px;
  font-size: 13px;
  flex-shrink: 0;
  margin: 0 10px;
  color: white;
  font-weight: 600;
}

.msg-right .avatar { background: #5cb895; }
.msg-left .avatar { background: #a8c8e0; }

.bubble {
  max-width: 70%;
  padding: 12px 16px;
  border-radius: 16px;
  font-size: 14px;
  line-height: 1.6;
}

.bubble-user {
  background: linear-gradient(135deg, #8dd4b8 0%, #5cb895 100%);
  color: white;
  border-bottom-right-radius: 4px;
}

.bubble-ai {
  background: white;
  color: var(--brand-text);
  border: 1px solid var(--brand-border);
  border-bottom-left-radius: 4px;
}

.feedback-box {
  margin-top: 10px;
  padding: 10px 12px;
  border-radius: 10px;
  font-size: 13px;
  line-height: 1.6;
}

.feedback-good {
  background: #e8f8f0;
  border: 1px solid #8dd4b8;
  color: #3d9a78;
}

.feedback-mid {
  background: #fff9ed;
  border: 1px solid #f5d89a;
  color: #c88f3a;
}

.feedback-bad {
  background: #fef0f0;
  border: 1px solid #f8b4b4;
  color: #c56666;
}

.feedback-box b {
  display: block;
  margin-bottom: 4px;
}

.choice-area {
  padding: 16px;
  background: var(--brand-bg-soft);
  border-radius: 16px;
}

.choice-prompt {
  font-weight: 600;
  color: var(--brand-text);
  margin-bottom: 12px;
}

.choice-btn {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 18px;
  margin-bottom: 10px;
  background: white;
  border: 2px solid var(--brand-border);
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.2s;
}

.choice-btn:hover {
  border-color: var(--brand-primary-light);
  background: white;
  transform: translateX(4px);
}

.choice-letter {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: var(--brand-primary);
  color: white;
  text-align: center;
  line-height: 28px;
  font-weight: 600;
  font-size: 14px;
  flex-shrink: 0;
}

.choice-text {
  font-size: 14px;
  color: var(--brand-text);
}

.ending-card {
  text-align: center;
  padding: 40px 20px;
  background: linear-gradient(135deg, #f0f9ff 0%, #eaf5ef 100%);
  border-radius: 20px;
  animation: fadeInUp 0.5s ease;
}

.ending-emoji {
  font-size: 64px;
  margin-bottom: 12px;
}

.ending-title {
  font-size: 22px;
  font-weight: 600;
  color: var(--brand-text);
  margin-bottom: 8px;
}

.ending-summary {
  color: var(--brand-text-soft);
  font-size: 14px;
  max-width: 500px;
  margin: 0 auto 24px;
  line-height: 1.6;
}

.ending-stats {
  display: flex;
  justify-content: center;
  gap: 30px;
}

.stat-box {
  padding: 14px 28px;
  background: white;
  border-radius: 14px;
}

.stat-num {
  font-size: 32px;
  font-weight: bold;
  line-height: 1;
}

.stat-label {
  font-size: 12px;
  color: var(--brand-text-muted);
  margin-top: 6px;
}
</style>