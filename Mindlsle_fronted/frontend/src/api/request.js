import axios from 'axios'

const service = axios.create({
  baseURL: '',
  // AI 聊天需要等待大模型（LLM）生成回复，实测约 5~15 秒，因此超时放宽到 60 秒，
  // 避免 LLM 生成稍慢时前端误报"网络异常"。
  timeout: 60000
})

// 请求拦截：自动携带token
service.interceptors.request.use(config => {
  const token = localStorage.getItem('token')
  if(token){
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
}, err => Promise.reject(err))

// 响应拦截
service.interceptors.response.use(res=>{
  return res.data
}, err=>{
  // 401 token失效，清空登录状态跳登录页
  if(err.response?.status === 401){
    localStorage.removeItem('token')
    localStorage.removeItem('userType')
    location.href='/student/login'
  }
  return Promise.reject(err)
})

export default service