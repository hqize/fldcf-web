/**
 * axios 基础封装
 */
import axios from 'axios';
import type {
    AxiosInstance,
    AxiosResponse,
    InternalAxiosRequestConfig
} from 'axios';
import { ElMessage } from 'element-plus';

// 创建 axios 实例
const request: AxiosInstance = axios.create({
    baseURL: import.meta.env.VITE_API_BASE_URL || '/api',
    timeout: 10000,
    headers: {
        'Content-Type': 'application/json'
    }
});

// 请求拦截器
request.interceptors.request.use(
    (config: InternalAxiosRequestConfig) => {
        const token = localStorage.getItem('token');
        if (token) {
            config.headers.Authorization = `Bearer ${token}`;
        }
        // 上传 multipart 时不能使用默认 application/json，否则会丢失 boundary，后端返回 422
        if (config.data instanceof FormData) {
            delete config.headers['Content-Type'];
        }
        return config;
    },
    (error) => {
        console.error('请求错误:', error);
        return Promise.reject(error);
    }
);

// 响应拦截器
request.interceptors.response.use(
    (response: AxiosResponse) => {
        const res = response.data;

        // 后端统一 Result：{ code: "200" | "401" | ..., msg: string, data: any }
        if (res?.code === '200') return res.data;

        // 2xx 但 code != 200：仍按业务失败处理
        ElMessage.error(res?.msg || '请求失败');
        return Promise.reject(res);
    },
    (error) => {
        console.error('响应错误:', error);
        if (error.message.includes('Network Error')) {
            ElMessage.error('网络连接异常');
        } else if (error.message.includes('timeout')) {
            ElMessage.error('请求超时');
        } else {
            ElMessage.error(error.response?.data?.msg || '请求失败');
        }
        return Promise.reject(error);
    }
);

export default request;