<template>
  <div class="resource-page">
    <el-page-header content="📚 心理资源中心" @back="$router.push('/student/home')"></el-page-header>

    <div class="page-intro">
      <el-input v-model="keyword" placeholder="🔍 搜索文章或标签..." clearable size="default" class="search-input" />
      <div class="filter-tags">
        <span class="filter-label">分类：</span>
        <el-tag
          v-for="tag in allTags"
          :key="tag"
          :type="activeTag === tag ? 'success' : 'info'"
          effect="plain"
          class="filter-tag"
          @click="toggleTag(tag)"
        >
          {{ tag }}
        </el-tag>
      </div>
    </div>

    <div class="resource-grid">
      <el-card
        v-for="item in filteredList"
        :key="item.id"
        class="resource-card"
        shadow="hover"
        @click="openDetail(item)"
      >
        <div class="card-cover" :style="{ background: item.cover }">
          <span class="cover-emoji">{{ item.emoji }}</span>
        </div>
        <div class="card-body">
          <div class="card-tags">
            <el-tag size="small" :type="tagColor(item.tag)">{{ item.tag }}</el-tag>
            <span class="card-time">📖 {{ item.readTime }}</span>
          </div>
          <div class="card-title">{{ item.title }}</div>
          <div class="card-summary">{{ item.summary }}</div>
        </div>
      </el-card>
    </div>

    <el-empty v-if="filteredList.length === 0" description="没有找到相关内容"></el-empty>

    <el-dialog v-model="detailVisible" :title="currentItem?.title" width="680px" class="detail-dialog">
      <div class="detail-content" v-if="currentItem">
        <div class="detail-meta">
          <el-tag :type="tagColor(currentItem.tag)">{{ currentItem.tag }}</el-tag>
          <span class="meta-text">📖 {{ currentItem.readTime }}</span>
          <span class="meta-text">📅 {{ currentItem.date }}</span>
        </div>
        <div class="detail-body" v-html="currentItem.content"></div>
      </div>
      <template #footer>
        <el-button @click="detailVisible = false">关闭</el-button>
        <el-button type="primary" @click="openChat">💬 和 AI 聊聊这个话题</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { getPublishedResources } from '@/api/student'

const router = useRouter()
const keyword = ref('')
const activeTag = ref('全部')
const detailVisible = ref(false)
const currentItem = ref(null)

// 后端内容管理里已发布的资源（status=published），非空时优先展示
const published = ref([])
const toLocal = (r) => {
  const map = {
    article: ['📄', '#eef3fa', '文章'],
    audio: ['🎧', '#e8f8f0', '音频'],
    video: ['🎬', '#f5efff', '视频'],
    relax: ['🧘', '#fff4e4', '放松训练']
  }
  const m = map[r.res_type] || ['📄', '#eef3fa', '文章']
  return {
    id: r.id,
    emoji: m[0],
    cover: `linear-gradient(135deg, ${m[1]}, #ffffff)`,
    tag: m[2],
    readTime: '约 3 分钟',
    title: r.title,
    summary: (r.content || '').replace(/<[^>]+>/g, '').slice(0, 60),
    date: (r.created_at || '').slice(0, 10),
    content: r.content || r.url || '',
    isAdmin: true
  }
}
const loadPublished = async () => {
  try {
    const res = await getPublishedResources()
    if (res.code === 200 && Array.isArray(res.data.resources) && res.data.resources.length) {
      published.value = res.data.resources.map(toLocal)
    }
  } catch (e) { /* 后端不可用时回退内置资源 */ }
}
onMounted(loadPublished)

const resources = [
  {
    id: 1,
    emoji: '🌧️',
    cover: 'linear-gradient(135deg, #a8c8e0, #c8dce8)',
    tag: '情绪管理',
    readTime: '约 3 分钟',
    title: '心情不好时，试试这 5 个小方法',
    summary: '每个人都会有低落的时候。与其等待心情自己好起来，不如主动做点什么...',
    date: '2024-10-15',
    content: `
      <h4>1. 5-4-3-2-1 感官接地法</h4>
      <p>当情绪上头时，说出：<b>5 个看到的东西</b>、<b>4 个触摸到的</b>、<b>3 个听到的</b>、<b>2 个闻到的</b>、<b>1 个尝到的</b>。这能快速把你拉回当下。</p>
      <h4>2. 给情绪一个"出口"</h4>
      <p>写下来、喊出来、跑一圈...别憋着。情绪像水，堵住只会泛滥。</p>
      <h4>3. 给自己"允许"难过</h4>
      <p>不要说"我不应该难过"。情绪本身没有对错，先接纳它，再慢慢处理。</p>
      <h4>4. 做一件能掌控的小事</h4>
      <p>整理书桌、洗个热水澡、吃顿好的...掌控感能迅速提升情绪。</p>
      <h4>5. 求助不是软弱</h4>
      <p>和信任的人聊聊，或者来找 AI 陪伴。这是对自己负责的表现。</p>
    `
  },
  {
    id: 2,
    emoji: '📚',
    cover: 'linear-gradient(135deg, #f5e6d3, #faf0e4)',
    tag: '学习压力',
    readTime: '约 4 分钟',
    title: '考试前焦虑怎么办？这份清单帮你稳住',
    summary: '考前失眠、心跳加速、脑子一片空白？试试这些经过验证的方法...',
    date: '2024-10-10',
    content: `
      <h4>考前 1 周：</h4>
      <ul>
        <li><b>规律作息比熬夜更重要</b> — 保证 7-8 小时睡眠，大脑才能高效工作</li>
        <li><b>用"过电影"复习</b> — 合上书，在脑子里过一遍知识点，卡壳的地方回去看</li>
        <li><b>每天 30 分钟轻度运动</b> — 散步、慢跑都行，能显著降低皮质醇水平</li>
      </ul>
      <h4>考前 1 天：</h4>
      <ul>
        <li>不要再学新东西了，复习错题本和大纲</li>
        <li>准备好准考证、文具，早点上床</li>
        <li>如果紧张，试试我们的"呼吸花园"5-5 放松练习</li>
      </ul>
      <h4>考试中紧张了：</h4>
      <ul>
        <li>停下来，闭眼深呼吸 3 次（吸 5 秒，呼 7 秒）</li>
        <li>喝口水，活动一下手指</li>
        <li>先挑简单题做，建立信心</li>
      </ul>
    `
  },
  {
    id: 3,
    emoji: '🤝',
    cover: 'linear-gradient(135deg, #e8f8f0, #f0faf4)',
    tag: '人际关系',
    readTime: '约 3 分钟',
    title: '和朋友吵架了怎么办？修复关系的 3 步',
    summary: '再好的朋友也会有矛盾。关键是怎么处理，而不是有没有矛盾...',
    date: '2024-10-08',
    content: `
      <h4>Step 1：先冷静，不要急着解决</h4>
      <p>情绪激动时说的话往往会后悔。给自己 24 小时冷静期，如果能睡着先睡一觉。</p>
      <h4>Step 2：用"我句式"表达感受</h4>
      <p>❌ "你总是不考虑我的感受"<br>✅ "当你 XXX 的时候，我感觉很受伤"</p>
      <p>"我句式"能减少对方的防御心理。</p>
      <h4>Step 3：主动给台阶</h4>
      <p>真正的朋友不会一直僵着。发个表情包、约杯奶茶，先让气氛软下来。</p>
    `
  },
  {
    id: 4,
    emoji: '🌱',
    cover: 'linear-gradient(135deg, #c8ecdb, #eaf5ef)',
    tag: '自我成长',
    readTime: '约 5 分钟',
    title: '认识你自己：青少年自我探索指南',
    summary: '你了解自己吗？你的兴趣、性格、价值观...这些决定了你是谁',
    date: '2024-10-05',
    content: `
      <h4>你可以从这几个维度认识自己：</h4>
      <ul>
        <li><b>性格</b>：你是外向还是内向？喜欢计划还是灵活？</li>
        <li><b>兴趣</b>：什么事情让你忘记时间？</li>
        <li><b>能力</b>：你做什么事情比别人更快更好？</li>
        <li><b>价值观</b>：什么事情对你最重要？自由？责任？创造？</li>
      </ul>
      <h4>小练习：</h4>
      <p>拿出一张纸，写下：</p>
      <ol>
        <li>最近半年让你最有成就感的 3 件事</li>
        <li>最近半年让你最累的 3 件事</li>
        <li>如果不用考虑钱，你最想做什么</li>
      </ol>
      <p>看看你写的，答案其实已经在里面了。</p>
    `
  },
  {
    id: 5,
    emoji: '🧘',
    cover: 'linear-gradient(135deg, #f5efff, #faf4ff)',
    tag: '放松技巧',
    readTime: '约 2 分钟',
    title: '4-7-8 呼吸法：2 分钟快速平静',
    summary: '哈佛大学医生推荐的呼吸方法，亲测有效。跟我们的呼吸花园配合使用',
    date: '2024-10-03',
    content: `
      <h4>怎么做：</h4>
      <ol>
        <li><b>吸气</b> 4 秒 — 鼻子慢慢吸气，心里数 1-2-3-4</li>
        <li><b>屏息</b> 7 秒 — 憋住气，数 1-2-3-4-5-6-7</li>
        <li><b>呼气</b> 8 秒 — 嘴巴慢慢呼气，数 1-2-3-4-5-6-7-8</li>
      </ol>
      <p>连续做 4 次为一组。建议每天睡前做 2 组，帮助入睡。</p>
      <h4>原理：</h4>
      <p>这个节奏能激活我们的"副交感神经"（负责放松的那部分），让心率下降、肌肉放松、思维变慢。</p>
      <p>👉 点击首页的"呼吸花园"，我们帮你计时引导。</p>
    `
  },
  {
    id: 6,
    emoji: '🏠',
    cover: 'linear-gradient(135deg, #fff4e4, #fff9f0)',
    tag: '情绪管理',
    readTime: '约 3 分钟',
    title: '一个人在家害怕？试试这些让家变安全',
    summary: '父母加班、自己在家...别怕，这是锻炼独立的好机会',
    date: '2024-10-01',
    content: `
      <h4>让家变得更"有声音"</h4>
      <ul>
        <li>开着客厅小灯或暖色台灯</li>
        <li>放点轻音乐或有声书</li>
        <li>和朋友/家人视频聊一会儿</li>
      </ul>
      <h4>做点具体的事</h4>
      <ul>
        <li>画画、拼图、练字 — 专注能减少胡思乱想</li>
        <li>给家里绿植浇水、整理书桌 — 小成就感</li>
        <li>做顿简单的饭给自己吃</li>
      </ul>
      <h4>记住：</h4>
      <p>害怕不是胆小的表现。承认自己害怕，然后做点什么让自己感觉好一点，这就是勇敢。</p>
    `
  },
  {
    id: 7,
    emoji: '💤',
    cover: 'linear-gradient(135deg, #a8c8e0, #c8dce8)',
    tag: '放松技巧',
    readTime: '约 3 分钟',
    title: '睡不着怎么办？失眠急救清单',
    summary: '翻来覆去到凌晨？别焦虑，试试这些科学的助眠方法',
    date: '2024-09-28',
    content: `
      <h4>今晚试试：</h4>
      <ul>
        <li>手机放下 — 蓝光会抑制褪黑素</li>
        <li>卧室调暗、调凉（18-22℃ 最佳）</li>
        <li>如果 20 分钟没睡着，起来做别的（看书、听音乐），困了再回床</li>
        <li>试试"呼吸花园"的 4-7-8 舒缓节奏</li>
      </ul>
      <h4>长期改善：</h4>
      <ul>
        <li>固定睡觉和起床时间（包括周末）</li>
        <li>睡前 3 小时不喝奶茶、咖啡</li>
        <li>每天运动 20 分钟，但别在睡前 3 小时</li>
        <li>卧室只用来睡觉和休息（学习、刷手机都别在床上）</li>
      </ul>
    `
  },
  {
    id: 8,
    emoji: '🎯',
    cover: 'linear-gradient(135deg, #e8f8f0, #f0faf4)',
    tag: '自我成长',
    readTime: '约 4 分钟',
    title: '目标太大不知从哪开始？试试"最小行动法"',
    summary: '把大目标拆成"小到不可能失败"的步骤，然后行动',
    date: '2024-09-25',
    content: `
      <h4>什么是"最小行动"？</h4>
      <p>目标："期末要考进前 10 名"<br>→ 最小行动：<b>现在打开数学书，把今天讲的例题再做一遍</b></p>
      <h4>为什么有效？</h4>
      <p>大脑害怕失败，但不会害怕"不可能失败"的事。一旦开始，就会有惯性。</p>
      <h4>试试这个公式：</h4>
      <p><b>大目标 → 拆成周目标 → 拆天目标 → 写出"最小行动"</b></p>
      <p>比如想背单词：</p>
      <ul>
        <li>❌ 目标："这个月背 1000 个词"</li>
        <li>✅ 最小行动："打开 App，过 5 个单词"</li>
      </ul>
    `
  }
]

const allTagList = computed(() => ['全部', ...new Set(listSource.value.map(r => r.tag))])
const allTags = allTagList

// 数据源：优先显示后台发布的资源，否则回退内置静态资源
const listSource = computed(() => (published.value.length ? published.value : resources))

const filteredList = computed(() => {
  return listSource.value.filter(r => {
    const matchTag = activeTag.value === '全部' || r.tag === activeTag.value
    const matchKey = !keyword.value ||
      r.title.includes(keyword.value) ||
      (r.summary || '').includes(keyword.value) ||
      r.tag.includes(keyword.value)
    return matchTag && matchKey
  })
})

const toggleTag = (tag) => {
  activeTag.value = tag
}

const tagColor = (tag) => {
  return {
    '情绪管理': 'danger',
    '学习压力': 'warning',
    '人际关系': 'success',
    '自我成长': 'primary',
    '放松技巧': 'info'
  }[tag] || ''
}

const openDetail = (item) => {
  currentItem.value = item
  detailVisible.value = true
}

const openChat = () => {
  detailVisible.value = false
  router.push('/student/chat')
}
</script>

<style scoped>
.resource-page {
  padding: 20px 30px;
  max-width: 1100px;
  margin: 0 auto;
  background: #ffffff;
  min-height: 100vh;
}

.page-intro {
  margin-bottom: 24px;
}

.search-input {
  margin-bottom: 16px;
  max-width: 480px;
}

.filter-tags {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
}

.filter-label {
  font-size: 13px;
  color: var(--brand-text-soft);
  margin-right: 4px;
}

.filter-tag {
  cursor: pointer;
  transition: all 0.2s;
}

.resource-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 20px;
}

.resource-card {
  cursor: pointer;
  transition: all 0.3s;
  overflow: hidden;
  padding: 0 !important;
}

.resource-card:hover {
  transform: translateY(-4px);
}

.resource-card :deep(.el-card__body) {
  padding: 0 !important;
}

.card-cover {
  height: 100px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.cover-emoji {
  font-size: 40px;
}

.card-body {
  padding: 16px 20px 20px;
}

.card-tags {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.card-time {
  font-size: 12px;
  color: var(--brand-text-muted);
}

.card-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--brand-text);
  margin-bottom: 6px;
  line-height: 1.4;
}

.card-summary {
  font-size: 13px;
  color: var(--brand-text-soft);
  line-height: 1.5;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.detail-dialog :deep(.el-dialog) {
  background: #ffffff;
}

.detail-dialog :deep(.el-dialog__header) {
  background: #ffffff;
  border-bottom: 1px solid #f0f0f0;
  margin-right: 0 !important;
  padding: 18px 24px;
}

.detail-dialog :deep(.el-dialog__body) {
  padding: 0;
  background: #ffffff;
}

.detail-dialog :deep(.el-dialog__footer) {
  border-top: 1px solid #f0f0f0;
  padding: 14px 24px;
  background: #ffffff;
}

.detail-content {
  padding: 20px 28px;
}

.detail-meta {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 18px;
  padding-bottom: 14px;
  border-bottom: 1px solid var(--brand-border);
}

.meta-text {
  font-size: 13px;
  color: var(--brand-text-muted);
}

.detail-body {
  font-size: 15px;
  line-height: 1.9;
  color: var(--brand-text);
}

.detail-body h4 {
  margin: 18px 0 10px 0;
  color: var(--brand-primary-dark);
  font-size: 16px;
}

.detail-body p {
  margin: 0 0 12px 0;
}

.detail-body ul, .detail-body ol {
  margin: 0 0 12px 0;
  padding-left: 20px;
}

.detail-body li {
  margin-bottom: 6px;
}
</style>