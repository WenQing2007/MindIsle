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

  {
    path: '/admin',
    redirect: '/admin/login'
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
  const whiteList = ['/student/login', '/teacher/login', '/admin/login']
  const token = localStorage.getItem('token')

  if (token) {
    if (to.path === '/student/login' || to.path === '/teacher/login' || to.path === '/admin/login') {
      const userType = localStorage.getItem('userType')
      if (userType === 'student') next('/student/home')
      else if (userType === 'teacher') next('/teacher/warnlist')
      else next('/')
    } else {
      next()
    }
  } else {
    if (whiteList.includes(to.path)) {
      next()
    } else {
      next('/student/login')
    }
  }
})