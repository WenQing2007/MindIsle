import request from './request'

export function teacherLogin(data) {
  return request({
    url: '/api/teacher/login',
    method: 'post',
    data
  })
}

export function getWarnings() {
  return request({
    url: '/api/teacher/warnings',
    method: 'get'
  })
}

// ===== 追加这一段 =====
export function teacherRegister(data) {
  return request({
    url: '/api/teacher/register',
    method: 'post',
    data
  })
}
