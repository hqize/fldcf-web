/**
 * 用户登录的校验规则
 */

import type { FormRules } from 'element-plus'
import { reactive } from 'vue'

// 用户数据类型
export interface UserFormData {
    username: string;
    password: string;
}

// 登录表单数据

export const loginUser = reactive<UserFormData>({
    username: "",
    password: ""
})

// 校验规则（规则是静态的，不需要 reactive）
export const loginRules: FormRules = {
    username: [
        {
            message: "用户名不能为空",
            required: true, 
            trigger: "blur" 
        },
        {
            min: 2,
            max: 50,
            message: "用户名长度应为2到50个字符",
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
    ]
}