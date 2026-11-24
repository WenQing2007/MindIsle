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

// ===== 预警人工复核 + 阈值 =====
export function reviewWarning(assessment_id, status, note) {
  return request({
    url: `/api/teacher/warnings/${assessment_id}/review`,
    method: 'post',
    data: { status, note: note || '' }
  })
}
export function getWarningConfig() {
  return request({ url: '/api/teacher/warning-config', method: 'get' })
}
export function setWarningConfig(min_level) {
  return request({ url: '/api/teacher/warning-config', method: 'post', data: { min_level } })
}
