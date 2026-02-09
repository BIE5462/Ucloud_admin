import axios from 'axios'
import { ElMessage } from 'element-plus'
import { useAdminStore } from '@/stores/admin'
import router from '@/router'

const api = axios.create({
  baseURL: '/api',
  timeout: 30000
})

// 请求拦截器
api.interceptors.request.use(
  (config) => {
    const adminStore = useAdminStore()
    if (adminStore.token) {
      config.headers.Authorization = `Bearer ${adminStore.token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// 响应拦截器
api.interceptors.response.use(
  (response) => {
    const res = response.data
    if (res.code !== 200) {
      ElMessage.error(res.message || '请求失败')
      if (res.code === 401) {
        const adminStore = useAdminStore()
        adminStore.logout()
        router.push('/login')
      }
      return Promise.reject(new Error(res.message))
    }
    return res
  },
  (error) => {
    const message = error.response?.data?.message || '网络错误'
    ElMessage.error(message)
    if (error.response?.status === 401) {
      const adminStore = useAdminStore()
      adminStore.logout()
      router.push('/login')
    }
    return Promise.reject(error)
  }
)

// 认证相关
export const login = (username, password) => 
  api.post('/auth/admin/login', { username, password })

export const logout = () => 
  api.post('/auth/logout')

// 仪表盘
export const getDashboard = () => 
  api.get('/admin/dashboard')

// 用户管理
export const getUserList = (params) => 
  api.get('/admin/users', { params })

export const createUser = (data) => 
  api.post('/admin/users', data)

export const updateUser = (id, data) => 
  api.put(`/admin/users/${id}`, data)

export const resetUserPassword = (id, data) => 
  api.post(`/admin/users/${id}/reset-password`, data)

export const changeUserBalance = (id, data) =>
  api.post(`/admin/users/${id}/balance`, data)

export const getUserDetail = (id) =>
  api.get(`/admin/users/${id}`)

export const deleteUser = (id) =>
  api.delete(`/admin/users/${id}`)

// 管理员管理
export const getAdminList = (params) => 
  api.get('/admin/admins', { params })

export const createAdmin = (data) => 
  api.post('/admin/admins', data)

export const updateAdmin = (id, data) => 
  api.put(`/admin/admins/${id}`, data)

export const deleteAdmin = (id) => 
  api.delete(`/admin/admins/${id}`)

export const resetAdminPassword = (id, data) => 
  api.post(`/admin/admins/${id}/reset-password`, data)

// 系统配置
export const getConfig = () => 
  api.get('/admin/config')

export const updatePrice = (data) => 
  api.put('/admin/config/price', data)

export default api
