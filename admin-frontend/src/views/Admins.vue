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
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column prop="username" label="用户名" width="120" />
        <el-table-column prop="company_name" label="公司名" width="150" show-overflow-tooltip />
        <el-table-column prop="contact_name" label="联系人" width="100" />
        <el-table-column prop="phone" label="手机号-账号" width="120" />
        <el-table-column prop="balance" label="余额" width="100">
          <template #default="{ row }">
            <span :class="{ 'text-danger': row.balance < 100 }">
              ¥{{ row.balance?.toFixed(2) }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="用户数" width="100">
          <template #default="{ row }">
            {{ row.user_count || 0 }}/{{ row.max_users }}
          </template>
        </el-table-column>
        <el-table-column prop="role" label="角色" width="110">
          <template #default="{ row }">
            <el-tag :type="row.role === 'super_admin' ? 'danger' : 'info'">
              {{ row.role === 'super_admin' ? '超级管理员' : '管理员' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="80">
          <template #default="{ row }">
            <el-tag :type="row.status === 1 ? 'success' : 'danger'">
              {{ row.status === 1 ? '正常' : '禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="140" />
        <el-table-column prop="last_login_at" label="最后登录" width="140" />
        <el-table-column label="操作" width="280" fixed="right">
          <template #default="{ row }">
            <el-button type="success" size="small" @click="handleRecharge(row)">充值</el-button>
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
        <el-form-item label="公司名" prop="company_name">
          <el-input v-model="form.company_name" placeholder="请输入公司名" />
        </el-form-item>
        <el-form-item label="联系人" prop="contact_name">
          <el-input v-model="form.contact_name" placeholder="请输入联系人姓名" />
        </el-form-item>
        <el-form-item label="手机号-账号" prop="phone">
          <el-input v-model="form.phone" placeholder="请输入手机号-账号" />
        </el-form-item>
        <el-form-item label="初始余额" prop="initial_balance" v-if="!form.id">
          <el-input-number v-model="form.initial_balance" :min="0" :precision="2" style="width: 200px" />
          <span class="form-hint">元</span>
        </el-form-item>
        <el-form-item label="用户上限" prop="max_users">
          <el-input-number v-model="form.max_users" :min="1" :max="1000" style="width: 200px" />
          <span class="form-hint">个</span>
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

    <!-- 充值弹窗 -->
    <el-dialog v-model="rechargeVisible" title="代理余额充值" width="400px">
      <el-form :model="rechargeForm" ref="rechargeFormRef" label-width="100px">
        <el-form-item label="代理账号">
          <span>{{ currentAdmin?.username }}</span>
        </el-form-item>
        <el-form-item label="当前余额">
          <span class="balance-display">¥{{ currentAdmin?.balance?.toFixed(2) }}</span>
        </el-form-item>
        <el-form-item label="操作类型" prop="type">
          <el-radio-group v-model="rechargeForm.type">
            <el-radio label="recharge">充值</el-radio>
            <el-radio label="deduct">扣减</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="金额" prop="amount">
          <el-input-number v-model="rechargeForm.amount" :min="0.01" :precision="2" style="width: 200px" />
          <span class="form-hint">元</span>
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="rechargeForm.description" type="textarea" :rows="2" placeholder="可选" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="rechargeVisible = false">取消</el-button>
        <el-button type="primary" @click="handleRechargeSubmit" :loading="rechargeLoading">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getAdminList, createAdmin, updateAdmin, deleteAdmin, resetAdminPassword, rechargeAdminBalance } from '@/api'

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

// 充值弹窗
const rechargeVisible = ref(false)
const rechargeFormRef = ref()
const rechargeLoading = ref(false)
const currentAdmin = ref(null)
const rechargeForm = reactive({
  type: 'recharge',
  amount: 0,
  description: ''
})
const form = reactive({
  id: null,
  username: '',
  password: '',
  role: 'admin',
  status: 1,
  company_name: '',
  contact_name: '',
  phone: '',
  initial_balance: 0,
  max_users: 10
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
  form.company_name = ''
  form.contact_name = ''
  form.phone = ''
  form.initial_balance = 0
  form.max_users = 10
  dialogVisible.value = true
}

const handleEdit = (row) => {
  dialogTitle.value = '编辑管理员'
  form.id = row.id
  form.username = row.username
  form.role = row.role
  form.status = row.status
  form.company_name = row.company_name || ''
  form.contact_name = row.contact_name || ''
  form.phone = row.phone || ''
  form.max_users = row.max_users || 10
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
        status: form.status,
        max_users: form.max_users,
        company_name: form.company_name,
        contact_name: form.contact_name,
        phone: form.phone
      })
      ElMessage.success('更新成功')
    } else {
      await createAdmin({
        username: form.username,
        password: form.password,
        role: form.role,
        status: form.status,
        company_name: form.company_name,
        contact_name: form.contact_name,
        phone: form.phone,
        initial_balance: form.initial_balance,
        max_users: form.max_users
      })
      ElMessage.success('创建成功')
    }
    dialogVisible.value = false
    fetchData()
  } finally {
    submitLoading.value = false
  }
}

// 打开充值弹窗
const handleRecharge = (row) => {
  currentAdmin.value = row
  rechargeForm.type = 'recharge'
  rechargeForm.amount = 0
  rechargeForm.description = ''
  rechargeVisible.value = true
}

// 提交充值
const handleRechargeSubmit = async () => {
  if (!rechargeForm.amount || rechargeForm.amount <= 0) {
    ElMessage.warning('请输入有效的金额')
    return
  }
  
  rechargeLoading.value = true
  try {
    await rechargeAdminBalance(currentAdmin.value.id, {
      type: rechargeForm.type,
      amount: rechargeForm.amount,
      description: rechargeForm.description
    })
    ElMessage.success(rechargeForm.type === 'recharge' ? '充值成功' : '扣减成功')
    rechargeVisible.value = false
    fetchData()
  } finally {
    rechargeLoading.value = false
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

.text-danger {
  color: #f56c6c;
}

.form-hint {
  margin-left: 10px;
  color: #909399;
}

.balance-display {
  font-size: 18px;
  font-weight: bold;
  color: #67c23a;
}
</style>
