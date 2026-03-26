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

      <div class="config-info">
        <h4>配置说明</h4>
        <ul>
          <li>套餐规格固定为 5 档，仅允许后台维护价格，客户端只能选择套餐编码。</li>
          <li>镜像ID属于后台共享配置，所有套餐共用，客户端不展示也不允许修改。</li>
          <li>价格和共享配置只影响新创建的实例，已创建实例继续保留创建时快照。</li>
          <li>所有系统配置变更都会记录到管理员操作日志中。</li>
        </ul>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { getConfig, updateConfig } from '@/api'

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

onMounted(fetchConfig)
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
