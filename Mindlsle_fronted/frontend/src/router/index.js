import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/student',
    redirect: '/student/login'
  },
  {
    path: '/student/login',
    name: 'StudentLogin',
    component: () => import('../views/student/Login.vue')
  },
  {
    path: '/student/register',
    name: 'StudentRegister',
    component: () => import('../views/student/Register.vue')
  },
  {
    path: '/student/home',
    name: 'StudentHome',
    component: () => import('../views/student/Home.vue')
  },
  {
    path: '/student/treehole',
    name: 'TreeHole',
    component: () => import('../views/student/TreeHole.vue')
  },
  {
    path: '/student/chat',
    name: 'StudentChat',
    component: () => import('../views/student/Chat.vue')
  },
  {
    path: '/student/reports',
    name: 'StudentReports',
    component: () => import('../views/student/ReportList.vue')
  },
  {
    path: '/student/breath',
    name: 'BreathGarden',
    component: () => import('../views/student/BreathGarden.vue')
  },
  {
    path: '/student/assessment',
    name: 'Assessment',
    component: () => import('../views/student/Assessment.vue')
  },
  {
    path: '/student/resources',
    name: 'ResourceCenter',
    component: () => import('../views/student/ResourceCenter.vue')
  },
  {
    path: '/student/scenario',
    name: 'ScenarioPractice',
    component: () => import('../views/student/ScenarioPractice.vue')
  },

  {
    path: '/teacher',
    redirect: '/teacher/login'
  },
  {
    path: '/teacher/login',
    name: 'TeacherLogin',
    component: () => import('../views/teacher/Login.vue')
  },
  // ========== 新增这一条 教师注册路由 ==========
  {
    path: '/teacher/register',
    name: 'TeacherRegister',
    component: () => import('../views/teacher/Register.vue')
  },
  {
    path: '/teacher/warnlist',
    name: 'WarnList',
    component: () => import('../views/teacher/WarnList.vue')
  },

  {
    path: '/admin',
    component: () => import('../views/admin/AdminLayout.vue'),
    redirect: '/admin/users',
    children: [
      { path: 'users', name: 'AdminUsers', component: () => import('../views/admin/Users.vue') },
      { path: 'content', name: 'AdminContent', component: () => import('../views/admin/Content.vue') },
      { path: 'logs', name: 'AdminLogs', component: () => import('../views/admin/Logs.vue') },
      { path: 'config', name: 'AdminConfig', component: () => import('../views/admin/Config.vue') }
    ]
  },
  {
    path: '/admin/login',
    name: 'AdminLogin',
    component: () => import('../views/admin/Login.vue')
  },

  {
    path: '/',
    redirect: '/student/home'
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router

router.beforeEach((to, from, next) => {
  // ========== 白名单加上 '/teacher/register' ==========
  const whiteList = ['/student/login', '/student/register', '/teacher/login', '/teacher/register', '/admin/login']
  const token = localStorage.getItem('token')
  const userType = localStorage.getItem('userType')

  if (token) {
    if (to.path === '/student/login' || to.path === '/teacher/login' || to.path === '/admin/login') {
      if (userType === 'student') next('/student/home')
      else if (userType === 'teacher') next('/teacher/warnlist')
      else if (userType === 'admin') next('/admin/users')
      else next('/')
    } else if (to.path.startsWith('/admin') && userType !== 'admin') {
      // 非管理员访问后台 → 回到自己角色首页
      next(userType === 'teacher' ? '/teacher/warnlist' : '/student/home')
    } else if (to.path.startsWith('/teacher') && userType !== 'teacher') {
      next(userType === 'admin' ? '/admin/users' : '/student/home')
    } else {
      next()
    }
  } else {
    if (whiteList.includes(to.path)) {
      next()
    } else if (to.path.startsWith('/admin')) {
      next('/admin/login')
    } else if (to.path.startsWith('/teacher')) {
      next('/teacher/login')
    } else {
      next('/student/login')
    }
  }
})