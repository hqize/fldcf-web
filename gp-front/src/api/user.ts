/**
 * axios进一步封装，专用与user用户相关操作
 */
import request from '@/utils/request';

// 后端用户：id / username / role / avatar_url
export interface UserInfo {
    id: number;
    username: string;
    role: string;
    avatar_url?: string | null;
}

export interface LoginParams {
    username: string;
    password: string;
}

export interface RegisterParams {
    username: string;
    password: string;
    avatar_url?: string | null;
}

export interface LoginResult {
    access_token: string;
    token_type: string;
}

export interface UsernameAvailabilityResult {
    username: string;
    available: boolean;
}

// 用户相关 API
export const userApi = {
    // 登录
    login(data: LoginParams): Promise<LoginResult> {
        // 后端使用 OAuth2PasswordRequestForm => x-www-form-urlencoded
        const form = new URLSearchParams();
        form.append('username', data.username);
        form.append('password', data.password);
        return request.post('/auth/login', form, {
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
        });
    },

    // 注册
    register(data: RegisterParams): Promise<UserInfo> {
        return request.post('/auth/register', {
            username: data.username,
            password: data.password,
            ...(data.avatar_url != null && data.avatar_url !== ''
                ? { avatar_url: data.avatar_url }
                : {})
        });
    },

    // 获取用户信息
    getUserInfo() {
        return request.get<UserInfo>('/auth/me');
    },

    // 检查用户名可用性
    checkUsername(username: string): Promise<UsernameAvailabilityResult> {
        return request.get('/auth/check-username', {
            params: { username }
        });
    },

    /** 更新当前用户（PATCH /auth/me）：密码、移除头像（avatar_url: null）等 */
    patchMe(data: { password?: string; avatar_url?: string | null }) {
        return request.patch('/auth/me', data) as Promise<UserInfo>;
    },

    /** 上传头像图片（POST /auth/me/avatar，multipart 字段 file） */
    uploadAvatar(file: File) {
        const form = new FormData();
        form.append('file', file);
        return request.post('/auth/me/avatar', form, {
            timeout: 60_000,
        }) as Promise<UserInfo>;
    },

    // 退出登录
    logout() {
        return request.post('/user/logout'); // 后端暂无该接口，先保留占位
    }
};