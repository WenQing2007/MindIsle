<template>
  <div class="login-container">
    <el-card class="login-card">
      <h2 style="text-align:center">MindIsle 学生登录</h2>
      <el-form ref="loginFormRef" :model="loginForm" label-width="80px">
        <el-form-item label="账号">
          <el-input v-model="loginForm.username"></el-input>
        </el-form-item>
        <el-form-item label="密码">
          <el-input v-model="loginForm.password" type="password"></el-input>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleLogin">登录</el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>
<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
const router = useRouter()
const loginFormRef = ref(null)
const loginForm = ref({
  username: '',
  password: ''
})
import { studentLogin } from '@/api/student'
const handleLogin = async () => {
  if (!loginForm.value.username || !loginForm.value.password) {
    alert("账号密码不能为空")
    return
  }
  try {
    const res = await studentLogin(loginForm.value)
    if (res.code === 200) {
      localStorage.setItem('token', res.data.token)
      localStorage.setItem('student_id', res.data.student_id)
      localStorage.setItem('userType', 'student')
      alert("登录成功，跳转学生主页")
      router.push('/student/home')
    } else {
      alert(res.msg || "登录失败")
    }
  } catch (err) {
    console.error(err)
    alert("请求异常，请检查后端服务是否启动")
  }
}
</script>
<style scoped>
.login-container{
  height:100vh;
  display:flex;
  justify-content:center;
  align-items:center;
  background-color:#f5f7fa;
}
.login-card{
  width:400px;
}
</style>
