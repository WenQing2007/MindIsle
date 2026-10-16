import request from './request'

// 学生登录
export function studentLogin(data){
  return request({
    url:'/api/student/login',
    method:'post',
    data
  })
}

// 获取树洞列表
export function getTreeHoleList(){
  return request({
    url:'/api/treehole/list',
    method:'get'
  })
}

// 发布树洞
export function postTreeHole(data){
  return request({
    url:'/api/treehole/add',
    method:'post',
    data
  })
}
