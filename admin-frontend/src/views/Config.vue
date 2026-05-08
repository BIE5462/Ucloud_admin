<template>
  <div class="config-page">
    <el-card>
      <template #header>
        <span>系统配置</span>
      </template>

      <el-form :model="config" label-width="160px" class="config-form">
        <div class="section-title">共享配置</div>

        <el-form-item label="容器镜像ID">
          <el-input
            v-model="config.comp_share_image_id"
            placeholder="请输入容器镜像ID"
            style="width: 360px"
          />
          <span class="form-tip">5 个固定套餐共用此镜像，客户端不会显示或上传镜像ID</span>
        </el-form-item>

        <el-form-item label="启动最低余额 (元)">
          <el-input-number
            v-model="config.min_balance_to_start"
            :min="0"
            :precision="2"
            :step="0.5"
            style="width: 200px"
          />
          <span class="form-tip">用户创建或启动云电脑时所需的最低余额</span>
        </el-form-item>

        <el-form-item label="自动停机阈值 (元)">
          <el-input-number
            v-model="config.auto_stop_threshold"
            :min="0"
            :precision="2"
            :step="0.5"
            style="width: 200px"
          />
          <span class="form-tip">余额低于该值时可供自动停机逻辑使用，默认 0 表示不额外限制</span>
        </el-form-item>

        <el-divider />

        <div class="section-title">固定套餐价格</div>

        <el-table :data="config.config_options" border class="config-table">
          <el-table-column prop="config_code" label="套餐编码" width="120" />
          <el-table-column prop="config_name" label="套餐名称" width="140" />
          <el-table-column prop="gpu_type" label="GPU类型" width="120" />
          <el-table-column prop="cpu_cores" label="CPU核数" width="100" />
          <el-table-column prop="memory_gb" label="内存(GB)" width="100" />
          <el-table-column prop="storage_gb" label="存储(GB)" width="100" />
          <el-table-column label="每分钟价格(元)" min-width="180">
            <template #default="{ row }">
              <el-input-number
                v-model="row.price_per_minute"
                :min="0.01"
                :precision="2"
                :step="0.1"
                style="width: 150px"
              />
            </template>
          </el-table-column>
        </el-table>

        <el-form-item class="action-row">
          <el-button type="primary" @click="handleSave" :loading="saving">
            保存配置
          </el-button>
        </el-form-item>
      </el-form>

      <el-divider />

      <div class="section-header">
        <div class="section-title">服务器管理</div>
        <el-button type="primary" @click="openServerDialog()">新增服务器</el-button>
      </div>

      <el-table
        :data="servers"
        v-loading="serverLoading"
        border
        class="config-table"
      >
        <el-table-column prop="name" label="服务器名称" width="160" />
        <el-table-column prop="ucloud_public_key" label="UCLOUD_PUBLIC_KEY" min-width="220" show-overflow-tooltip />
        <el-table-column prop="ucloud_private_key_masked" label="UCLOUD_PRIVATE_KEY" width="180" />
        <el-table-column prop="ucloud_image_id" label="UCLOUD_IMAGE_ID" min-width="220" show-overflow-tooltip />
        <el-table-column label="操作" width="170" fixed="right">
          <template #default="{ row }">
            <el-button size="small" @click="openServerDialog(row)">编辑</el-button>
            <el-button size="small" type="danger" @click="handleDeleteServer(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-divider />

      <div class="config-info">
        <h4>配置说明</h4>
        <ul>
          <li>套餐规格固定为 5 档，仅允许后台维护价格，客户端只能选择套餐编码。</li>
          <li>服务器名称由客户端登录前手动输入，云电脑创建和后续操作都使用所属服务器的 UCloud 配置。</li>
          <li>共享镜像ID仅用于兼容旧配置，实际创建使用服务器管理中的 UCLOUD_IMAGE_ID。</li>
          <li>价格和共享配置只影响新创建的实例，已创建实例继续保留创建时快照。</li>
          <li>所有系统配置变更都会记录到管理员操作日志中。</li>
        </ul>
      </div>
    </el-card>

    <el-dialog
      v-model="serverDialogVisible"
      :title="serverForm.id ? '编辑服务器' : '新增服务器'"
      width="560px"
    >
      <el-form :model="serverForm" label-width="150px">
        <el-form-item label="服务器名称">
          <el-input v-model="serverForm.name" placeholder="请输入服务器名称" />
        </el-form-item>
        <el-form-item label="UCLOUD_PUBLIC_KEY">
          <el-input v-model="serverForm.ucloud_public_key" placeholder="请输入 UCLOUD_PUBLIC_KEY" />
        </el-form-item>
        <el-form-item label="UCLOUD_PRIVATE_KEY">
          <el-input
            v-model="serverForm.ucloud_private_key"
            type="password"
            show-password
            :placeholder="serverForm.id ? '留空表示不修改' : '请输入 UCLOUD_PRIVATE_KEY'"
          />
        </el-form-item>
        <el-form-item label="UCLOUD_IMAGE_ID">
          <el-input v-model="serverForm.ucloud_image_id" placeholder="请输入 UCLOUD_IMAGE_ID" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="serverDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="serverSaving" @click="handleSaveServer">
          保存
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  createServer,
  deleteServer,
  getConfig,
  getServerList,
  updateConfig,
  updateServer
} from '@/api'

const defaultConfigOptions = [
  {
    config_code: 'config_1',
    config_name: '3080Ti12G',
    gpu_type: '3080Ti',
    cpu_cores: 12,
    memory_gb: 32,
    storage_gb: 200,
    price_per_minute: 0.5
  },
  {
    config_code: 'config_2',
    config_name: '309024G',
    gpu_type: '3090',
    cpu_cores: 16,
    memory_gb: 64,
    storage_gb: 200,
    price_per_minute: 0.5
  },
  {
    config_code: 'config_3',
    config_name: '409024G',
    gpu_type: '4090',
    cpu_cores: 16,
    memory_gb: 64,
    storage_gb: 200,
    price_per_minute: 0.5
  },
  {
    config_code: 'config_4',
    config_name: '509032G',
    gpu_type: '5090',
    cpu_cores: 16,
    memory_gb: 96,
    storage_gb: 200,
    price_per_minute: 0.5
  },
  {
    config_code: 'config_5',
    config_name: '409048G',
    gpu_type: '4090',
    cpu_cores: 16,
    memory_gb: 96,
    storage_gb: 200,
    price_per_minute: 0.5
  }
]

const buildDefaultConfigOptions = () =>
  defaultConfigOptions.map(item => ({ ...item }))

const normalizeConfigOptions = (configOptions = []) => {
  const optionMap = new Map(
    configOptions.map(item => [item.config_code, item])
  )

  return defaultConfigOptions.map(item => ({
    ...item,
    ...(optionMap.get(item.config_code) || {})
  }))
}

const config = ref({
  min_balance_to_start: 2.5,
  auto_stop_threshold: 0,
  comp_share_image_id: '',
  config_options: buildDefaultConfigOptions()
})

const saving = ref(false)
const servers = ref([])
const serverLoading = ref(false)
const serverSaving = ref(false)
const serverDialogVisible = ref(false)
const serverForm = ref({
  id: null,
  name: '',
  ucloud_private_key: '',
  ucloud_public_key: '',
  ucloud_image_id: ''
})

const fetchConfig = async () => {
  const res = await getConfig()
  if (res.code === 200) {
    config.value = {
      ...config.value,
      ...res.data,
      config_options: normalizeConfigOptions(res.data.config_options)
    }
  }
}

const fetchServers = async () => {
  serverLoading.value = true
  try {
    const res = await getServerList()
    if (res.code === 200) {
      servers.value = res.data.items || []
    }
  } finally {
    serverLoading.value = false
  }
}

const resetServerForm = () => {
  serverForm.value = {
    id: null,
    name: '',
    ucloud_private_key: '',
    ucloud_public_key: '',
    ucloud_image_id: ''
  }
}

const openServerDialog = (server = null) => {
  if (server) {
    serverForm.value = {
      id: server.id,
      name: server.name,
      ucloud_private_key: '',
      ucloud_public_key: server.ucloud_public_key,
      ucloud_image_id: server.ucloud_image_id
    }
  } else {
    resetServerForm()
  }
  serverDialogVisible.value = true
}

const handleSave = async () => {
  const compShareImageId = config.value.comp_share_image_id.trim()

  if (!compShareImageId) {
    ElMessage.warning('容器镜像ID不能为空')
    return
  }

  if (config.value.min_balance_to_start < 0) {
    ElMessage.warning('启动最低余额不能小于0')
    return
  }

  if (config.value.auto_stop_threshold < 0) {
    ElMessage.warning('自动停机阈值不能小于0')
    return
  }

  const hasInvalidPrice = config.value.config_options.some(
    item => Number(item.price_per_minute) <= 0
  )
  if (hasInvalidPrice) {
    ElMessage.warning('所有套餐价格都必须大于0')
    return
  }

  saving.value = true
  try {
    await updateConfig({
      min_balance_to_start: config.value.min_balance_to_start,
      auto_stop_threshold: config.value.auto_stop_threshold,
      comp_share_image_id: compShareImageId,
      config_prices: config.value.config_options.map(item => ({
        config_code: item.config_code,
        price_per_minute: item.price_per_minute
      }))
    })
    ElMessage.success('配置保存成功')
    await fetchConfig()
  } finally {
    saving.value = false
  }
}

const handleSaveServer = async () => {
  const name = serverForm.value.name.trim()
  const publicKey = serverForm.value.ucloud_public_key.trim()
  const privateKey = serverForm.value.ucloud_private_key.trim()
  const imageId = serverForm.value.ucloud_image_id.trim()

  if (!name) {
    ElMessage.warning('服务器名称不能为空')
    return
  }
  if (!publicKey) {
    ElMessage.warning('UCLOUD_PUBLIC_KEY不能为空')
    return
  }
  if (!serverForm.value.id && !privateKey) {
    ElMessage.warning('UCLOUD_PRIVATE_KEY不能为空')
    return
  }
  if (!imageId) {
    ElMessage.warning('UCLOUD_IMAGE_ID不能为空')
    return
  }

  const payload = {
    name,
    ucloud_public_key: publicKey,
    ucloud_image_id: imageId
  }
  if (privateKey) {
    payload.ucloud_private_key = privateKey
  }

  serverSaving.value = true
  try {
    if (serverForm.value.id) {
      await updateServer(serverForm.value.id, payload)
      ElMessage.success('服务器更新成功')
    } else {
      await createServer(payload)
      ElMessage.success('服务器创建成功')
    }
    serverDialogVisible.value = false
    await fetchServers()
  } finally {
    serverSaving.value = false
  }
}

const handleDeleteServer = async (server) => {
  await ElMessageBox.confirm(
    `确定删除服务器“${server.name}”吗？有关联云电脑时后端会阻止删除。`,
    '删除确认',
    {
      confirmButtonText: '删除',
      cancelButtonText: '取消',
      type: 'warning'
    }
  )
  await deleteServer(server.id)
  ElMessage.success('服务器删除成功')
  await fetchServers()
}

onMounted(() => {
  fetchConfig()
  fetchServers()
})
</script>

<style scoped>
.config-page {
  padding: 20px;
}

.config-form {
  max-width: 980px;
}

.section-title {
  margin-bottom: 18px;
  font-size: 16px;
  font-weight: 600;
  color: #303133;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.section-header .section-title {
  margin-bottom: 0;
}

.form-tip {
  margin-left: 15px;
  color: #666;
  font-size: 14px;
}

.config-table {
  margin-bottom: 20px;
}

.action-row :deep(.el-form-item__content) {
  justify-content: flex-start;
}

.config-info {
  margin-top: 20px;
  padding: 20px;
  background: #f5f7fa;
  border-radius: 8px;
}

.config-info h4 {
  margin-bottom: 15px;
  color: #333;
}

.config-info ul {
  padding-left: 20px;
  color: #666;
  line-height: 2;
}
</style>
