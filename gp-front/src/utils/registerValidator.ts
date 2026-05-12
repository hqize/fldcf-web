/**
 * 用户注册的校验规则
 */

import type { FormRules } from 'element-plus'
import { reactive } from 'vue'
import { userApi } from '@/api/user'

// 用户数据类型
export interface UserFormData {
    username: string;
    password: string;
    password2: string;
}
// 校验两次密码是否一致
const validateConfirmPassword = (_rule: unknown, value: string, callback: (error?: Error) => void) => {
    if (value === '') {
        callback(new Error('请再次输入密码'));
    } else if (value !== registerUser.password) {
        callback(new Error('两次输入的密码不一致！'));
    } else {
        callback();
    }
};

const validateUsernameAvailable = async (
    _rule: unknown,
    value: string,
    callback: (error?: Error) => void
) => {
    const username = value.trim()
    if (!username) {
        callback()
        return
    }

    try {
        const res = await userApi.checkUsername(username)
        if (!res.available) {
            callback(new Error('用户名已存在，请更换一个'))
            return
        }
        callback()
    } catch {
        // 检查接口异常时不阻断表单提交，交给提交阶段统一提示
        callback()
    }
}

// 登录表单数据

export const registerUser = reactive<UserFormData>({
    username: "",
    password: "",
    password2: ""
})

// 校验规则（规则是静态的，不需要 reactive）
export const registerRules: FormRules = {
    username: [
        {
            message: "用户名不能为空",
            required: true,
            trigger: "blur"
        },
        {
            message: "长度在2到30个字符",
            min: 2,
            max: 30,
            trigger: "blur"
        },
        {
            validator: validateUsernameAvailable,
            trigger: "blur"
        }
    ],
    password: [
        {
            message: "Password could not be empty...",
            required: true,
            trigger: "blur"
        },
        {
            min: 4,
            max: 30,
            message: "Password's length has to be 4 to 30 characters...",
            trigger: "blur"
        }
    ],
    password2: [
        {
            message: "Password could not be empty...",
            required: true,
            trigger: "blur"
        },
        {
            min: 4,
            max: 30,
            message: "Password's length has to be 4 to 30 characters...",
            trigger: "blur"
        },
        {
            validator: validateConfirmPassword,
            trigger: "blur"
        }
    ]
}