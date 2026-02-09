import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { login as loginApi, getConfig } from '@/api'

export const useAdminStore = defineStore('admin', () => {
  // State
  const token = ref(localStorage.getItem('admin_token') || '')
  const adminInfo = ref(JSON.parse(localStorage.getItem('admin_info') || 'null'))
  const systemConfig = ref(null)
  
  // Getters
  const isSuperAdmin = computed(() => adminInfo.value?.role === 'super_admin')
  const isLoggedIn = computed(() => !!token.value)
  
  // Actions
  const setToken = (newToken) => {
    token.value = newToken
    localStorage.setItem('admin_token', newToken)
  }
  
  const setAdminInfo = (info) => {
    adminInfo.value = info
    localStorage.setItem('admin_info', JSON.stringify(info))
  }
  
  const login = async (username, password) => {
    const res = await loginApi(username, password)
    if (res.code === 200) {
      setToken(res.data.token)
      setAdminInfo(res.data.admin)
      return true
    }
    return false
  }
  
  const logout = () => {
    token.value = ''
    adminInfo.value = null
    localStorage.removeItem('admin_token')
    localStorage.removeItem('admin_info')
  }
  
  const fetchSystemConfig = async () => {
    const res = await getConfig()
    if (res.code === 200) {
      systemConfig.value = res.data
    }
  }
  
  return {
    token,
    adminInfo,
    systemConfig,
    isSuperAdmin,
    isLoggedIn,
    login,
    logout,
    fetchSystemConfig
  }
})
