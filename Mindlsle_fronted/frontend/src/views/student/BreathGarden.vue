<template>
  <div class="breath-page">
    <el-page-header content="🌬️ 呼吸花园" @back="$router.push('/student/home')"></el-page-header>

    <div class="breath-intro" v-if="!started">
      <div class="intro-card">
        <div class="intro-emoji">🌸</div>
        <h2>让我们一起慢慢呼吸</h2>
        <p>跟随花园的节奏，吸气、屏息、呼气。每次 4 分钟，帮你平静下来。</p>
        <div class="preset-row">
          <div class="preset-title">选择一个节奏：</div>
          <el-radio-group v-model="preset" size="default">
            <el-radio-button value="calm">舒缓 4-7-8</el-radio-button>
            <el-radio-button value="focus">专注 4-4-4-4</el-radio-button>
            <el-radio-button value="relax">放松 5-5</el-radio-button>
          </el-radio-group>
        </div>
        <div class="preset-info">
          <div class="info-box">
            <div class="info-name">舒缓 4-7-8</div>
            <div class="info-desc">吸气 4 秒 → 屏息 7 秒 → 呼气 8 秒</div>
          </div>
          <div class="info-box">
            <div class="info-name">专注 4-4-4-4</div>
            <div class="info-desc">吸气 4 → 屏息 4 → 呼气 4 → 屏息 4</div>
          </div>
          <div class="info-box">
            <div class="info-name">放松 5-5</div>
            <div class="info-desc">吸气 5 秒 → 呼气 5 秒（最简单）</div>
          </div>
        </div>
        <el-button type="primary" size="large" class="start-btn" @click="start">
          🧘 开始练习
        </el-button>
      </div>
    </div>

    <div class="breath-active" v-else>
      <div class="garden-scene">
        <div class="cloud cloud-1">☁️</div>
        <div class="cloud cloud-2">☁️</div>
        <div class="cloud cloud-3">☁️</div>
        <div class="sun">☀️</div>

        <div class="breath-circle">
          <div class="circle-ring"></div>
          <div class="circle-inner">
            <div class="breath-emoji">{{ breathEmoji }}</div>
            <div class="breath-phase">{{ phaseLabel }}</div>
            <div class="breath-count">{{ countdown }}</div>
          </div>
        </div>

        <div class="garden-plants">
          <div class="plant" :style="{ animationDelay: '0s' }">🌱</div>
          <div class="plant" :style="{ animationDelay: '0.3s' }">🌿</div>
          <div class="plant" :style="{ animationDelay: '0.6s' }">🌸</div>
          <div class="plant" :style="{ animationDelay: '0.9s' }">🌼</div>
          <div class="plant" :style="{ animationDelay: '1.2s' }">🌺</div>
          <div class="plant" :style="{ animationDelay: '1.5s' }">🍃</div>
          <div class="plant" :style="{ animationDelay: '1.8s' }">🌻</div>
        </div>
      </div>

      <div class="progress-info">
        <div class="progress-bar">
          <div class="progress-fill" :style="{ width: cycleProgress + '%' }"></div>
        </div>
        <div class="progress-text">
          第 {{ completedCycles + 1 }} / {{ totalCycles }} 次 · 剩余 {{ totalCycles - completedCycles }} 次
        </div>
      </div>

      <div class="control-row">
        <el-button size="large" @click="togglePause">
          {{ paused ? '▶️ 继续' : '⏸ 暂停' }}
        </el-button>
        <el-button size="large" type="danger" plain @click="stop">
          结束练习
        </el-button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onUnmounted } from 'vue'

const preset = ref('calm')
const started = ref(false)
const paused = ref(false)
const completedCycles = ref(0)
const countdown = ref(0)

const phaseIndex = ref(0)
const phaseElapsed = ref(0)
let tickTimer = null

const presets = {
  calm:   { phases: ['吸', '屏', '呼'],  durations: [4, 7, 8] },
  focus:  { phases: ['吸', '屏', '呼', '屏'], durations: [4, 4, 4, 4] },
  relax:  { phases: ['吸', '呼'],        durations: [5, 5] }
}

const totalCycles = 5

const currentPreset = computed(() => presets[preset.value])

const phaseLabel = computed(() => {
  const p = currentPreset.value.phases[phaseIndex.value]
  const map = { '吸': '吸气', '屏': '屏息', '呼': '呼气' }
  return map[p] || p
})

const breathEmoji = computed(() => {
  const p = currentPreset.value.phases[phaseIndex.value]
  if (p === '吸') return '🫁'
  if (p === '屏') return '🌊'
  if (p === '呼') return '🍃'
  return '✨'
})

const cycleProgress = computed(() => {
  const cur = phaseIndex.value
  const phaseTotal = currentPreset.value.durations[cur]
  const phasePct = (phaseElapsed.value / phaseTotal) * 100
  const perPhase = 100 / currentPreset.value.phases.length
  return cur * perPhase + perPhase * (phasePct / 100)
})

let startTime = 0
let pausedAccum = 0
let pauseStart = 0

const tick = () => {
  if (paused.value) return
  const phases = currentPreset.value.phases
  const durs = currentPreset.value.durations
  const dur = durs[phaseIndex.value]

  phaseElapsed.value += 1
  countdown.value = dur - phaseElapsed.value

  if (phaseElapsed.value >= dur) {
    phaseElapsed.value = 0
    phaseIndex.value += 1
    if (phaseIndex.value >= phases.length) {
      phaseIndex.value = 0
      completedCycles.value += 1
      if (completedCycles.value >= totalCycles) {
        finish()
        return
      }
    }
    countdown.value = durs[phaseIndex.value]
  }
}

const start = () => {
  started.value = true
  paused.value = false
  phaseIndex.value = 0
  phaseElapsed.value = 0
  completedCycles.value = 0
  countdown.value = currentPreset.value.durations[0]
  tickTimer = setInterval(tick, 1000)
}

const togglePause = () => {
  paused.value = !paused.value
}

const stop = () => {
  if (tickTimer) clearInterval(tickTimer)
  started.value = false
  completedCycles.value = 0
  phaseIndex.value = 0
  phaseElapsed.value = 0
}

const finish = () => {
  if (tickTimer) clearInterval(tickTimer)
  setTimeout(() => {
    alert('🌟 练习完成！你做得很棒，感觉怎么样？')
    stop()
  }, 300)
}

onUnmounted(() => {
  if (tickTimer) clearInterval(tickTimer)
})
</script>

<style scoped>
.breath-page {
  padding: 20px 30px;
  min-height: 100vh;
}

.breath-intro {
  display: flex;
  justify-content: center;
  padding: 40px 0;
}

.intro-card {
  max-width: 600px;
  width: 100%;
  padding: 40px;
  background: linear-gradient(135deg, #eaf5ef 0%, #f0f9ff 100%);
  border-radius: 24px;
  border: 1px solid rgba(92, 184, 149, 0.15);
  text-align: center;
}

.intro-emoji {
  font-size: 64px;
  margin-bottom: 12px;
  animation: floatSoft 3s ease-in-out infinite;
}

.intro-card h2 {
  margin: 0 0 10px 0;
  color: var(--brand-text);
}

.intro-card > p {
  color: var(--brand-text-soft);
  margin: 0 0 24px 0;
  font-size: 14px;
}

.preset-row {
  margin-bottom: 20px;
}

.preset-title {
  font-size: 13px;
  color: var(--brand-text-soft);
  margin-bottom: 10px;
}

.preset-info {
  display: grid;
  gap: 10px;
  margin-bottom: 24px;
}

.info-box {
  background: rgba(255, 255, 255, 0.6);
  border-radius: 12px;
  padding: 12px 16px;
  text-align: left;
}

.info-name {
  font-weight: 600;
  color: var(--brand-text);
  font-size: 14px;
  margin-bottom: 4px;
}

.info-desc {
  font-size: 13px;
  color: var(--brand-text-soft);
}

.start-btn {
  font-size: 16px;
  padding: 14px 40px !important;
}

.breath-active {
  padding: 20px 0;
}

.garden-scene {
  position: relative;
  height: 480px;
  border-radius: 24px;
  background: linear-gradient(180deg, #c8ecdb 0%, #eaf5ef 40%, #fdfaf4 100%);
  overflow: hidden;
  display: flex;
  justify-content: center;
  align-items: center;
}

.cloud {
  position: absolute;
  font-size: 40px;
  opacity: 0.7;
  animation: drift 20s linear infinite;
}

.cloud-1 { top: 40px;  left: 10%;  animation-duration: 25s; }
.cloud-2 { top: 80px;  left: 40%;  animation-duration: 30s; font-size: 32px; }
.cloud-3 { top: 60px;  left: 70%;  animation-duration: 22s; font-size: 36px; }

@keyframes drift {
  0%   { transform: translateX(-20px); }
  50%  { transform: translateX(20px); }
  100% { transform: translateX(-20px); }
}

.sun {
  position: absolute;
  top: 30px;
  right: 60px;
  font-size: 50px;
  animation: spin 10s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to   { transform: rotate(360deg); }
}

.breath-circle {
  position: relative;
  width: 240px;
  height: 240px;
  display: flex;
  justify-content: center;
  align-items: center;
}

.circle-ring {
  position: absolute;
  inset: 0;
  border-radius: 50%;
  border: 3px solid rgba(92, 184, 149, 0.4);
  animation: breathRing 15s ease-in-out infinite;
}

.circle-inner {
  width: 180px;
  height: 180px;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(92, 184, 149, 0.25) 0%, rgba(92, 184, 149, 0.05) 70%);
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  animation: breathCore 15s ease-in-out infinite;
}

@keyframes breathRing {
  0%, 100% { transform: scale(0.9); opacity: 0.5; }
  30%      { transform: scale(1.15); opacity: 0.8; }
  50%      { transform: scale(1.2);  opacity: 1; }
  80%      { transform: scale(0.95); opacity: 0.6; }
}

@keyframes breathCore {
  0%, 100% { transform: scale(0.9); }
  30%      { transform: scale(1.1); }
  50%      { transform: scale(1.15); }
  80%      { transform: scale(0.95); }
}

.breath-emoji {
  font-size: 48px;
  margin-bottom: 4px;
}

.breath-phase {
  font-size: 16px;
  color: var(--brand-primary-dark);
  font-weight: 600;
}

.breath-count {
  font-size: 32px;
  font-weight: bold;
  color: var(--brand-primary);
}

.garden-plants {
  position: absolute;
  bottom: 20px;
  left: 0;
  right: 0;
  display: flex;
  justify-content: space-around;
  font-size: 36px;
}

.plant {
  animation: sway 3s ease-in-out infinite;
  transform-origin: bottom center;
}

@keyframes sway {
  0%, 100% { transform: rotate(-5deg); }
  50%      { transform: rotate(5deg); }
}

.progress-info {
  margin-top: 24px;
}

.progress-bar {
  height: 8px;
  background: rgba(92, 184, 149, 0.15);
  border-radius: 20px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, var(--brand-primary-light) 0%, var(--brand-primary) 100%);
  border-radius: 20px;
  transition: width 1s linear;
}

.progress-text {
  text-align: center;
  margin-top: 10px;
  font-size: 13px;
  color: var(--brand-text-soft);
}

.control-row {
  display: flex;
  justify-content: center;
  gap: 16px;
  margin-top: 24px;
}
</style>