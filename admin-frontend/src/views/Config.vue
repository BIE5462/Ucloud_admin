<template>
  <div class="config-page">
    <el-card>
      <template #header>
        <span>系统配置</span>
      </template>

      <el-form :model="config" label-width="180px" class="config-form">
        <div class="section-title">计费配置</div>

        <el-form-item label="每分钟价格 (元)">
          <el-input-number
            v-model="config.price_per_minute"
            :min="0.01"
            :precision="2"
            :step="0.1"
            style="width: 200px"
          />
          <span class="form-tip">云电脑运行每分钟的价格</span>
        </el-form-item>

        <el-form-item label="启动最低余额 (元)">
          <el-input-number
            v-model="config.min_balance_to_start"
            :min="0"
            :precision="2"
            :step="0.5"
            style="width: 200px"
          />
          <span class="form-tip">启动云电脑所需的最低余额</span>
        </el-form-item>

        <el-divider />

        <div class="section-title">容器规格配置</div>

        <el-form-item label="容器镜像ID">
          <el-input
            v-model="config.comp_share_image_id"
            placeholder="请输入容器镜像ID"
            style="width: 360px"
          />
          <span class="form-tip">新建云电脑实例时使用的镜像ID</span>
        </el-form-item>

        <el-form-item label="GPU类型">
          <el-input
            v-model="config.gpu_type"
            placeholder="请输入GPU类型"
            style="width: 260px"
          />
          <span class="form-tip">新建云电脑实例时使用的GPU型号</span>
        </el-form-item>

        <el-form-item label="CPU核数">
          <el-input-number
            v-model="config.cpu_cores"
            :min="1"
            :precision="0"
            :step="1"
            style="width: 200px"
          />
          <span class="form-tip">新建云电脑实例时使用的CPU核数</span>
        </el-form-item>

        <el-form-item label="内存 (GB)">
          <el-input-number
            v-model="config.memory_gb"
            :min="1"
            :precision="0"
            :step="1"
            style="width: 200px"
          />
          <span class="form-tip">后台按GB配置，创建实例时自动换算为MB</span>
        </el-form-item>

        <el-form-item>
          <el-button type="primary" @click="handleSave" :loading="saving">
            保存配置
          </el-button>
        </el-form-item>
      </el-form>

      <el-divider />

      <div class="config-info">
        <h4>配置说明</h4>
        <ul>
          <li>价格与容器规格配置只影响新创建的实例，已创建实例保持创建时的配置快照</li>
          <li>启动最低余额用于限制余额不足时创建或启动云电脑</li>
          <li>容器镜像ID、GPU类型、CPU核数、内存大小统一由系统后台控制</li>
          <li>所有系统配置变更都会被记录在管理员操作日志中</li>
        </ul>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { getConfig, updateConfig } from '@/api'

const config = ref({
  price_per_minute: 0.5,
  min_balance_to_start: 2.5,
  auto_stop_threshold: 0,
  comp_share_image_id: '',
  gpu_type: '',
  cpu_cores: 12,
  memory_gb: 32
})

const saving = ref(false)

const fetchConfig = async () => {
  const res = await getConfig()
  if (res.code === 200) {
    config.value = {
      ...config.value,
      ...res.data
    }
  }
}

const handleSave = async () => {
  const compShareImageId = config.value.comp_share_image_id.trim()
  const gpuType = config.value.gpu_type.trim()

  if (config.value.price_per_minute <= 0) {
    ElMessage.warning('价格必须大于0')
    return
  }

  if (config.value.min_balance_to_start < 0) {
    ElMessage.warning('启动最低余额不能小于0')
    return
  }

  if (!compShareImageId) {
    ElMessage.warning('容器镜像ID不能为空')
    return
  }

  if (!gpuType) {
    ElMessage.warning('GPU类型不能为空')
    return
  }

  if (config.value.cpu_cores <= 0) {
    ElMessage.warning('CPU核数必须大于0')
    return
  }

  if (config.value.memory_gb <= 0) {
    ElMessage.warning('内存大小必须大于0')
    return
  }

  saving.value = true
  try {
    await updateConfig({
      price_per_minute: config.value.price_per_minute,
      min_balance_to_start: config.value.min_balance_to_start,
      comp_share_image_id: compShareImageId,
      gpu_type: gpuType,
      cpu_cores: config.value.cpu_cores,
      memory_gb: config.value.memory_gb
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
  max-width: 760px;
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
