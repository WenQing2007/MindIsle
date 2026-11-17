<template>
  <div class="register-container">
    <el-card class="register-card">
      <h2 style="text-align:center">MindIsle 教师注册</h2>
      <el-form ref="registerFormRef" :model="registerForm" label-width="100px">
        <el-form-item label="账号">
          <el-input v-model="registerForm.username" placeholder="至少3个字符"></el-input>
        </el-form-item>
        <el-form-item label="密码">
          <el-input v-model="registerForm.password" type="password" placeholder="至少6个字符"></el-input>
        </el-form-item>
        <el-form-item label="确认密码">
          <el-input v-model="registerForm.confirmPassword" type="password" placeholder="再次输入密码"></el-input>
        </el-form-item>
        <el-form-item label="姓名">
          <el-input v-model="registerForm.name" placeholder="请输入真实姓名"></el-input>
        </el-form-item>
        <el-form-item label="所属学校">
          <el-input v-model="registerForm.school" placeholder="请输入学校名称"></el-input>
        </el-form-item>
        <el-form-item label="科室/教研组">
          <el-input v-model="registerForm.department" placeholder="例如：心理中心、年级组"></el-input>
        </el-form-item>
        <el-form-item label="联系电话">
          <el-input v-model="registerForm.phone" placeholder="选填"></el-input>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleRegister" style="width:100%">注册</el-button>
        </el-form-item>
        <el-form-item>
          <el-link type="primary" @click="goLogin">已有账号？去登录</el-link>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { teacherRegister } from '@/api/teacher'

const router = useRouter()
const registerFormRef = ref(null)
const registerForm = ref({
  username: '',
  password: '',
  confirmPassword: '',
  name: '',
  school: '',
  department: '',
  phone: ''
})

const handleRegister = async () => {
  const f = registerForm.value
  if (!f.username || !f.password || !f.name || !f.school) {
    alert('账号、密码、姓名、学校不能为空')
    return
  }
  if (f.username.length < 3) {
    alert('用户名至少3个字符')
    return
  }
  if (f.password.length < 6) {
    alert('密码至少6个字符')
    return
  }
  if (f.password !== f.confirmPassword) {
    alert('两次输入的密码不一致')
    return
  }
  try {
    const res = await teacherRegister({
      username: f.username,
      password: f.password,
      name: f.name,
      school: f.school,
      department: f.department,
      phone: f.phone
    })
    if (res.code === 200) {
      alert('注册成功！请登录')
      router.push('/teacher/login')
    } else {
      alert(res.msg || '注册失败')
    }
  } catch (err) {
    console.error(err)
    alert('请求异常，请检查后端服务是否启动')
  }
}

const goLogin = () => {
  router.push('/teacher/login')
}
</script>

<style scoped>
.register-container {
  height: 100vh;
  display: flex;
  justify-content: center;
  align-items: center;
  background-color: #f5f7fa;
}
.register-card {
  width: 450px;
}
</style>
