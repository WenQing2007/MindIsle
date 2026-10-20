import { createRouter, createWebHistory } from 'vue-router'
const routes = [
  // 学生端路由 /student
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
    path: '/student/report',
    name: 'ReportList',
    component: () => import('../views/student/ReportList.vue')
  },
  // 教师工作台路由 /teacher
  {
    path: '/teacher',
    redirect: '/teacher/login'
  },
  {
    path: '/teacher/login',
    name: 'TeacherLogin',
    component: () => import('../views/teacher/Login.vue')
  },
  {
    path: '/teacher/warnlist',
    name: 'WarnList',
    component: () => import('../views/teacher/WarnList.vue')
  },
  // 管理员后台 /admin
  {
    path: '/admin',
    redirect: '/admin/login'
  },
  {
    path: '/admin/login',
    name: 'AdminLogin',
    component: () => import('../views/admin/Login.vue')
  },
  // 默认首页
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
// 路由全局守卫
router.beforeEach((to, from, next) => {
  // 不需要登录的白名单页面
  const whiteList = ['/student/login', '/teacher/login', '/admin/login']
  const token = localStorage.getItem('token')
  if (token) {
    // 已有token，登录状态
    if (to.path === '/student/login' || to.path === '/teacher/login' || to.path === '/admin/login') {
      // 已经登录，再访问登录页，直接跳对应主页
      const userType = localStorage.getItem('userType')
      if(userType === 'student') next('/student/home')
      else if(userType === 'teacher') next('/teacher/warnlist')
      else next('/')
    } else {
      next()
    }
  } else {
    // 无token
    if (whiteList.includes(to.path)) {
      next()
    } else {
      // 未登录，跳转到学生登录页
      next('/student/login')
    }
  }
})
