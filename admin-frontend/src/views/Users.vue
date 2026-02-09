<template>
  <div class="users-page">
    <el-card>
      <template #header>
        <div class="header-actions">
          <span>用户管理</span>
          <el-button type="primary" @click="handleCreate">创建用户</el-button>
        </div>
      </template>

      <!-- 搜索筛选 -->
      <el-form :inline="true" :model="searchForm" class="search-form">
        <el-form-item label="关键词">
          <el-input v-model="searchForm.keyword" placeholder="公司名/手机号" clearable />
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="searchForm.status" placeholder="全部" clearable>
            <el-option label="正常" :value="1" />
            <el-option label="禁用" :value="0" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleSearch">搜索</el-button>
          <el-button @click="resetSearch">重置</el-button>
        </el-form-item>
      </el-form>

      <!-- 用户表格 -->
      <el-table :data="userList" v-loading="loading" border>
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="company_name" label="公司名称" />
        <el-table-column prop="contact_name" label="联系人" />
        <el-table-column prop="phone" label="手机号" />
        <el-table-column prop="balance" label="余额" width="120">
          <template #default="{ row }">
            <span :class="{ 'text-danger': row.balance < 10 }">
              ¥{{ row.balance.toFixed(2) }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="has_container" label="云电脑" width="100">
          <template #default="{ row }">
            <el-tag v-if="row.has_container" :type="row.container_status === 'running' ? 'success' : 'info'">
              {{ row.container_status === 'running' ? '运行中' : '已停止' }}
            </el-tag>
            <el-tag v-else type="info">无</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.status === 1 ? 'success' : 'danger'">
              {{ row.status === 1 ? '正常' : '禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="250" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" size="small" @click="handleEdit(row)">编辑</el-button>
            <el-button type="success" size="small" @click="handleRecharge(row)">充值</el-button>
            <el-button type="danger" size="small" @click="handleResetPassword(row)">重置密码</el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
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
        <el-form-item label="公司名称" prop="company_name">
          <el-input v-model="form.company_name" />
        </el-form-item>
        <el-form-item label="联系人" prop="contact_name">
          <el-input v-model="form.contact_name" />
        </el-form-item>
        <el-form-item label="手机号" prop="phone">
          <el-input v-model="form.phone" :disabled="!!form.id" />
        </el-form-item>
        <el-form-item :label="form.id ? '新密码' : '密码'" prop="password" v-if="!form.id">
          <el-input v-model="form.password" type="password" show-password />
        </el-form-item>
        <el-form-item label="初始余额" prop="initial_balance" v-if="!form.id">
          <el-input-number v-model="form.initial_balance" :min="0" :precision="2" />
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
    <el-dialog v-model="rechargeVisible" title="余额充值" width="400px">
      <el-form :model="rechargeForm" label-width="100px">
        <el-form-item label="当前余额">
          <span class="balance-display">¥{{ currentUser?.balance?.toFixed(2) }}</span>
        </el-form-item>
        <el-form-item label="操作类型">
          <el-radio-group v-model="rechargeForm.type">
            <el-radio label="recharge">充值</el-radio>
            <el-radio label="deduct">扣减</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="金额">
          <el-input-number v-model="rechargeForm.amount" :min="0.01" :precision="2" style="width: 100%" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="rechargeForm.description" type="textarea" rows="2" />
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
import { getUserList, createUser, updateUser, resetUserPassword, changeUserBalance } from '@/api'

const loading = ref(false)
const userList = ref([])
const searchForm = reactive({
  keyword: '',
  status: null
})
const pagination = reactive({
  page: 1,
  page_size: 20,
  total: 0
})

// 创建/编辑弹窗
const dialogVisible = ref(false)
const dialogTitle = ref('创建用户')
const formRef = ref()
const submitLoading = ref(false)
const form = reactive({
  id: null,
  company_name: '',
  contact_name: '',
  phone: '',
  password: '',
  initial_balance: 0,
  status: 1
})

const rules = {
  company_name: [{ required: true, message: '请输入公司名称', trigger: 'blur' }],
  contact_name: [{ required: true, message: '请输入联系人', trigger: 'blur' }],
  phone: [{ required: true, message: '请输入手机号', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur', min: 6 }]
}

// 充值弹窗
const rechargeVisible = ref(false)
const rechargeLoading = ref(false)
const currentUser = ref(null)
const rechargeForm = reactive({
  type: 'recharge',
  amount: 0,
  description: ''
})

const fetchData = async () => {
  loading.value = true
  try {
    const res = await getUserList({
      page: pagination.page,
      page_size: pagination.page_size,
      keyword: searchForm.keyword,
      status: searchForm.status
    })
    if (res.code === 200) {
      userList.value = res.data.items
      pagination.total = res.data.total
    }
  } finally {
    loading.value = false
  }
}

const handleSearch = () => {
  pagination.page = 1
  fetchData()
}

const resetSearch = () => {
  searchForm.keyword = ''
  searchForm.status = null
  handleSearch()
}

const handleCreate = () => {
  dialogTitle.value = '创建用户'
  form.id = null
  form.company_name = ''
  form.contact_name = ''
  form.phone = ''
  form.password = ''
  form.initial_balance = 0
  form.status = 1
  dialogVisible.value = true
}

const handleEdit = (row) => {
  dialogTitle.value = '编辑用户'
  form.id = row.id
  form.company_name = row.company_name
  form.contact_name = row.contact_name
  form.phone = row.phone
  form.status = row.status
  dialogVisible.value = true
}

const handleSubmit = async () => {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return

  submitLoading.value = true
  try {
    if (form.id) {
      await updateUser(form.id, {
        company_name: form.company_name,
        contact_name: form.contact_name,
        status: form.status
      })
      ElMessage.success('更新成功')
    } else {
      await createUser(form)
      ElMessage.success('创建成功')
    }
    dialogVisible.value = false
    fetchData()
  } finally {
    submitLoading.value = false
  }
}

const handleRecharge = (row) => {
  currentUser.value = row
  rechargeForm.type = 'recharge'
  rechargeForm.amount = 0
  rechargeForm.description = ''
  rechargeVisible.value = true
}

const handleRechargeSubmit = async () => {
  if (rechargeForm.amount <= 0) {
    ElMessage.warning('金额必须大于0')
    return
  }

  rechargeLoading.value = true
  try {
    await changeUserBalance(currentUser.value.id, rechargeForm)
    ElMessage.success('操作成功')
    rechargeVisible.value = false
    fetchData()
  } finally {
    rechargeLoading.value = false
  }
}

const handleResetPassword = async (row) => {
  try {
    await ElMessageBox.confirm(`确定要重置用户 "${row.company_name}" 的密码吗？`, '提示', {
      type: 'warning'
    })
    
    const newPassword = Math.random().toString(36).substring(2, 10)
    await resetUserPassword(row.id, { new_password: newPassword })
    
    ElMessageBox.alert(`新密码: ${newPassword}`, '密码重置成功', {
      confirmButtonText: '确定'
    })
  } catch {
    // 取消
  }
}

onMounted(fetchData)
</script>

<style scoped>
.users-page {
  padding: 20px;
}

.header-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.search-form {
  margin-bottom: 20px;
}

.pagination {
  margin-top: 20px;
  justify-content: flex-end;
}

.text-danger {
  color: #F56C6C;
  font-weight: bold;
}

.balance-display {
  font-size: 20px;
  font-weight: bold;
  color: #67C23A;
}
</style>
