<template>
  <div class="teacher-page">
    <el-page-header content="学生预警名单"></el-page-header>
    <el-card style="margin-top:20px">
      <el-table :data="tableData" border>
        <el-table-column prop="id" label="学号"/>
        <el-table-column prop="name" label="姓名"/>
        <el-table-column prop="level" label="风险等级">
          <template #default="scope">
            <el-tag :type="scope.row.level === '高' ? 'danger' : scope.row.level === '中' ? 'warning' : ''">
              {{scope.row.level}}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="reason" label="预警原因"/>
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
const tableData = [
  {id:"2024001", name:"张三", level:"高", reason:"多次发布消极树洞内容"},
  {id:"2024002", name:"李四", level:"中", reason:"测评结果存在轻度抑郁倾向"}
]
</script>

<style scoped>
.teacher-page{
  padding:30px;
}
</style>
