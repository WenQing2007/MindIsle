<template>
  <div class="login-container">
    <el-card class="login-card">
      <h2 style="text-align:center">MindIsle 教师工作台登录</h2>
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
import axios from 'axios'
import { useRouter } from 'vue-router'
const router = useRouter()

const loginFormRef = ref(null)
const loginForm = ref({
  username: '',
  password: ''
})

const handleLogin = async () => {
  if (!loginForm.value.username || !loginForm.value.password) {
    alert("账号密码不能为空")
    return
  }
  try {
    const res = await axios.post('/api/teacher/login', loginForm.value)
    const data = res.data
    if (data.code === 200) {
      localStorage.setItem('token', data.data.token)
      localStorage.setItem('userType', 'teacher')
      alert("教师登录成功，跳转预警列表")
      router.push('/teacher/warnlist')
    } else {
      alert(data.msg || "登录失败")
    }
  } catch (err) {
    console.error(err)
    alert("请求异常，请检查后端服务是否启动")
  }
}
</script>

<style scoped>
.login-container {
  height: 100vh;
  display: flex;
  justify-content: center;
  align-items: center;
  background-color: #f0f2f5;
}
.login-card {
  width: 400px;
}
</style>