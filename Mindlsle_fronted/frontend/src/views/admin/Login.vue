<template>
  <div class="login-container">
    <el-card class="login-card">
      <h2 style="text-align:center">MindIsle 管理员后台登录</h2>
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
const loginFormRef = ref(null)
const loginForm = ref({
  username: '',
  password: ''
})

const handleLogin = () => {
  if(loginForm.value.username && loginForm.value.password){
    localStorage.setItem('token', 'mock-admin-token-789')
    localStorage.setItem('userType', 'admin')
    alert("管理员登录成功")
  }else{
    alert("账号密码不能为空")
  }
}

</script>

<style scoped>
.login-container{
  height:100vh;
  display:flex;
  justify-content:center;
  align-items:center;
  background-color:#eef1f6;
}
.login-card{
  width:400px;
}
</style>
