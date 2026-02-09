<template>
  <div class="admins-page">
    <el-card>
      <template #header>
        <div class="header-actions">
          <span>管理员管理</span>
          <el-button type="primary" @click="handleCreate">创建管理员</el-button>
        </div>
      </template>

      <el-table :data="adminList" v-loading="loading" border>
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="username" label="用户名" />
        <el-table-column prop="role" label="角色" width="120">
          <template #default="{ row }">
            <el-tag :type="row.role === 'super_admin' ? 'danger' : 'info'">
              {{ row.role === 'super_admin' ? '超级管理员' : '管理员' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.status === 1 ? 'success' : 'danger'">
              {{ row.status === 1 ? '正常' : '禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="180" />
        <el-table-column prop="last_login_at" label="最后登录" width="180" />
        <el-table-column label="操作" width="250" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" size="small" @click="handleEdit(row)">编辑</el-button>
            <el-button type="warning" size="small" @click="handleResetPassword(row)">重置密码</el-button>
            <el-button type="danger" size="small" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-pagination
        v-model:current-page="pagination.page"
        v-model:page-size="pagination.page_size"
        :total="pagination.total"
        layout="total, sizes, prev, pager, next"
        @change="fetchData"
        class="pagination"
      />
    </el-card>

    <!-- 创建/编辑弹窗 -->
    <el-dialog v-model="dialogVisible" :title="dialogTitle" width="500px">
      <el-form :model="form" :rules="rules" ref="formRef" label-width="100px">
        <el-form-item label="用户名" prop="username">
          <el-input v-model="form.username" :disabled="!!form.id" />
        </el-form-item>
        <el-form-item label="密码" prop="password" v-if="!form.id">
          <el-input v-model="form.password" type="password" show-password />
        </el-form-item>
        <el-form-item label="角色" prop="role">
          <el-radio-group v-model="form.role">
            <el-radio label="admin">管理员</el-radio>
            <el-radio label="super_admin">超级管理员</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="状态" prop="status">
          <el-radio-group v-model="form.status">
            <el-radio :label="1">正常</el-radio>
            <el-radio :label="0">禁用</el-radio>
          </el-radio-group>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit" :loading="submitLoading">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getAdminList, createAdmin, updateAdmin, deleteAdmin, resetAdminPassword } from '@/api'

const loading = ref(false)
const adminList = ref([])
const pagination = reactive({
  page: 1,
  page_size: 20,
  total: 0
})

const dialogVisible = ref(false)
const dialogTitle = ref('创建管理员')
const formRef = ref()
const submitLoading = ref(false)
const form = reactive({
  id: null,
  username: '',
  password: '',
  role: 'admin',
  status: 1
})

const rules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur', min: 6 }]
}

const fetchData = async () => {
  loading.value = true
  try {
    const res = await getAdminList({
      page: pagination.page,
      page_size: pagination.page_size
    })
    if (res.code === 200) {
      adminList.value = res.data.items
      pagination.total = res.data.total
    }
  } finally {
    loading.value = false
  }
}

const handleCreate = () => {
  dialogTitle.value = '创建管理员'
  form.id = null
  form.username = ''
  form.password = ''
  form.role = 'admin'
  form.status = 1
  dialogVisible.value = true
}

const handleEdit = (row) => {
  dialogTitle.value = '编辑管理员'
  form.id = row.id
  form.username = row.username
  form.role = row.role
  form.status = row.status
  dialogVisible.value = true
}

const handleSubmit = async () => {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return

  submitLoading.value = true
  try {
    if (form.id) {
      await updateAdmin(form.id, {
        role: form.role,
        status: form.status
      })
      ElMessage.success('更新成功')
    } else {
      await createAdmin(form)
      ElMessage.success('创建成功')
    }
    dialogVisible.value = false
    fetchData()
  } finally {
    submitLoading.value = false
  }
}

const handleResetPassword = async (row) => {
  try {
    await ElMessageBox.confirm(`确定要重置管理员 "${row.username}" 的密码吗？`, '提示', {
      type: 'warning'
    })
    
    const newPassword = Math.random().toString(36).substring(2, 10)
    await resetAdminPassword(row.id, { new_password: newPassword })
    
    ElMessageBox.alert(`新密码: ${newPassword}`, '密码重置成功', {
      confirmButtonText: '确定'
    })
  } catch {
    // 取消
  }
}

const handleDelete = async (row) => {
  try {
    await ElMessageBox.confirm(`确定要删除管理员 "${row.username}" 吗？`, '提示', {
      type: 'warning'
    })
    
    await deleteAdmin(row.id)
    ElMessage.success('删除成功')
    fetchData()
  } catch {
    // 取消
  }
}

onMounted(fetchData)
</script>

<style scoped>
.admins-page {
  padding: 20px;
}

.header-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.pagination {
  margin-top: 20px;
  justify-content: flex-end;
}
</style>
