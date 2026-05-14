<template>
    <el-form :model="registerUser" :rules="registerRules" label-width="100px" class="registerForm sign-up-form"
        ref="registerForm">
        <el-form-item label="用户名" prop="username">
            <el-input v-model="registerUser.username" placeholder="Enter username..." />
        </el-form-item>
        <el-form-item label="密码" prop="password">
            <el-input
                v-model="registerUser.password"
                type="password"
                show-password
                placeholder="Enter password..."
            />
        </el-form-item>
        <el-form-item label="确认密码" prop="password2">
            <el-input
                v-model="registerUser.password2"
                type="password"
                show-password
                placeholder="Confirm password..."
            />
        </el-form-item>
        <el-form-item>
            <el-button type="primary" class="submit-btn" @click="handleRegister">注册</el-button>
        </el-form-item>

    </el-form>
</template>
<script lang="ts" setup>
import { ref } from 'vue';
import type { FormInstance, FormRules } from 'element-plus';

import { ElMessage } from 'element-plus';

// 1.定义Props
interface UserForm {
    username: string;
    password: string;
    password2: string;
}

const props = defineProps<{
    registerUser: UserForm;
    registerRules: FormRules;
}>();

// 2.定义emits(向父组件发送事件)
const emit = defineEmits<{
    (e: 'register-success', payload: { username: string; password: string }): void;
}>();

// 3.获取表单实例
const registerForm = ref<FormInstance | null>(null);



// 4.处理注册逻辑
import { userApi } from '@/api/user';
const handleRegister = async () => {
    if (!registerForm.value) return;
    try {
        await registerForm.value.validate();
        
        // 调用注册接口
        await userApi.register({
            username: props.registerUser.username,
            password: props.registerUser.password
        });

        ElMessage.success('注册成功，请登录');
        emit('register-success', {
            username: props.registerUser.username,
            password: props.registerUser.password
        });
        
        // 可选：注册成功后自动切换回登录模式
        // 这通常需要父组件控制，或者通过emit让父组件切换signUpMode
        
    } catch (error: unknown) {
        const msg =
            typeof error === 'object' &&
            error !== null &&
            'msg' in error &&
            typeof (error as { msg?: unknown }).msg === 'string'
                ? (error as { msg: string }).msg
                : '';

        if (msg.includes('用户名已存在')) {
            ElMessage.error('用户名已存在，请更换一个再注册');
        } else if (msg) {
            ElMessage.error(msg);
        }

        console.error('注册失败:', error);
    }
};
</script>
<style scoped>
/* register */
.registerForm {
    margin-top: 20px;
    background-color: #fff;
    padding: 20px 40px 20px 20px;
    border-radius: 5px;
    box-shadow: 0px 5px 10px #cccc;
}

.submit-btn {
    width: 100%;
}
</style>