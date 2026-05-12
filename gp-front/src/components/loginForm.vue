<template>
    <el-form :model="loginUser" :rules="loginRules" label-width="100px" class="loginForm sign-in-form" ref="loginForm">
        <el-form-item label="用户名" prop="username">
            <el-input v-model="loginUser.username" placeholder="Enter username..." />
        </el-form-item>
        <el-form-item label="密码" prop="password">
            <el-input
                v-model="loginUser.password"
                type="password"
                show-password
                placeholder="Enter password"
            />
        </el-form-item>
        <el-form-item>
            <el-button type="primary" class="submit-btn" @click="handleLogin">登录</el-button>
        </el-form-item>
        <!-- 忘记密码 -->
        <div class="tiparea">
            <p>忘记密码？<a href="#">立即找回</a></p>
        </div>
    </el-form>
</template>
<script setup lang="ts">

import { ref } from 'vue';
import type { FormInstance, FormRules } from 'element-plus';

import { ElMessage } from 'element-plus';


// 1. 定义 Props
interface UserForm {
    username: string;
    password: string;
}

const props = defineProps<{
    loginUser: UserForm;
    loginRules: FormRules;
}>();

// 2. 定义 emits (向父组件发送事件)
const emit = defineEmits<{
    (e: 'login-success', payload: { access_token: string; token_type: string }): void;
}>();

// 3. 获取表单实例
const loginForm = ref<FormInstance | null>(null);

// 4. 处理登录逻辑
import { userApi } from '@/api/user'; 
const handleLogin = async () => {
    if (!loginForm.value) return;

    try {
        // 1. 表单校验
        await loginForm.value.validate();

        console.log('表单校验通过，准备发送请求...', props.loginUser);

        // 2. 调用后端接口
        // request.ts 成功时会返回后端的 data 字段
        const res = await userApi.login({
            username: props.loginUser.username,
            password: props.loginUser.password
        });

        console.log('登录成功，后端返回数据:', res);

        // 3. Token 由父组件写入 Pinia（与 localStorage 同步）
        if (res?.access_token) {
            ElMessage.success('登录成功！');
            emit('login-success', res);
            return;
        }

        ElMessage.warning('登录成功但未获取到 access_token，请检查后端返回');

    } catch (error: unknown) {
        // 5. 错误处理
        // request.ts 中的拦截器已经弹出了 ElMessage 错误提示
        // 这里只需要处理逻辑上的失败
        console.error('登录请求失败:', error);
    }
};
</script>
<style scoped>
/* form */
.loginForm {
    margin-top: 20px;
    background-color: #fff;
    padding: 20px 40px 20px 20px;
    border-radius: 5px;
    box-shadow: 0px 5px 10px #693f3fcc;
}

.submit-btn {
    width: 100%;
}

.tiparea {
    text-align: right;
    font-size: 12px;
    color: #333;
}

.tiparea p a {
    color: #409eff;
}
</style>