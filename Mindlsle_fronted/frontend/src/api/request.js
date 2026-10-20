import axios from 'axios'
const service = axios.create({
  baseURL: 'http://127.0.0.1:8000',
  timeout: 5000
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

