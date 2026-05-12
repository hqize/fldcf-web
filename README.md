# 遥感图像伪造定位可视化

本项目为前后端分离应用：**后端**基于 FastAPI，提供 JWT 登录与 **FLDCF（Forgery Localization for Remote Sensing）** 推理接口；**前端**基于 Vue 3 + Vite + Element Plus，流程为 **登录 → 工作台首页 → 伪造定位可视化页**。

---

## 仓库结构（概要）

| 路径 | 说明 |
|------|------|
| `backend/` | Python 包根（`PYTHONPATH` 指向此处）；应用入口为 **`backend/src/main.py`**（`app` 与 `uvicorn` 目标 `src.main:app`） |
| `backend/src/auth/` | 登录注册、JWT |
| `backend/src/fldcf_api/` | FLDCF HTTP 路由（`/fldcf/status`、`/fldcf/predict`）、推理封装 |
| `backend/src/core/` | 全局配置 `settings.py`、共享 `schemas.py` |
| `backend/fldcf_data/` | 权重与先验（如 `model_fakeV.pt`、`model/` 下 `model_vi.pt` 等） |
| `backend/src/utils/` | 后端通用工具（**勿与 FLDCF 源码里的 `src/utils` 混淆**，推理时已做命名空间隔离） |
| `gp-front/` | Vue 前端，开发端口通常为 **5173** |
| **`FLDCF_raw/`** | 与 `backend`、`gp-front` **同级**；**只需保留官方仓库里的 `src/` 目录**（拷成 `FLDCF_raw/src/...`），训练数据、`scripts/` 等不必放入 |

### Git 与忽略规则

`.gitignore` 未因目录迁移而必须修改：仍忽略各层 `.env`、Python 缓存与虚拟环境、以及 **`backend/fldcf_data/**/*.pt`** 等大权重文件。仓库根目录无额外 Git 钩子配置。

---

## 环境依赖

- **Python**：建议使用虚拟环境（仓库内可有 `.venv`），安装依赖：

  ```bash
  cd backend
  pip install -r requirements.txt
  ```

  PyTorch 请按本机 CUDA/CPU 情况从 [PyTorch 官网](https://pytorch.org/) 安装匹配版本（`requirements.txt` 中的 `torchvision` 需与 `torch` 版本匹配）。

- **Node.js**：用于前端，建议使用当前 LTS。

- **MySQL**：ORM 使用 Tortoise + aiomysql，数据库连接串见下文 `DB_URL`。

- **FLDCF 官方源码**：推理**只依赖**官方工程里的 **`src/`** 树。在 **`acid/FLDCF_raw/`** 下放置 **`src`** 即可（即从 FLDCF(raw) 只复制 **`src` 文件夹**到 `FLDCF_raw/src`）；不必拷贝仓库根的 `data/`、`scripts/` 等。此时 **`backend/.env` 可不写 `FLDCF_ROOT`**。亦可用 **`FLDCF_ROOT`** 指向其它路径，详见 `backend/.env.example`。

---

## 后端配置

1. 复制环境变量模板：

   ```bash
   cd backend
   copy .env.example .env
   ```

2. 编辑 **`backend/.env`**（不要提交到 Git）：

   - **`DB_URL`**：MySQL 连接串，示例：`mysql://user:pass@127.0.0.1:3306/数据库名`
   - **`JWT_SECRET_KEY`**：生产环境必须设为随机长密钥（本地可为空但会有告警）
   - **`AUTH_INIT_USERNAME` / `AUTH_INIT_PASSWORD`**：首次启动时若不存在管理员账号则创建（默认常为 `admin` 等，按你 `.env` 为准）
   - **`FLDCF_ROOT`**（推荐）：FLDCF(raw) **项目根目录**的绝对路径，该目录下须有 **`src`** 子目录

3. 启动后端（在 `backend` 目录下，任选其一）：

   ```bash
   cd backend
   uvicorn src.main:app --reload --host 127.0.0.1 --port 8000
   ```

   或使用包方式启动（同样会走 `src/main.py` 里的热重载与日志配置）：

   ```bash
   cd backend
   python -m src.main
   ```

   - API 文档（若启用）：默认 `http://127.0.0.1:8000/docs`
   - 静态测试页：`/` 可重定向到 `/static/index.html`
   - FLDCF：**`GET /fldcf/status`**、**`POST /fldcf/predict`**（挂载前缀 `/fldcf`）

---

## FLDCF 权重与可选环境变量

- 整网权重放在 **`backend/fldcf_data/`**，默认文件名如：`model_fakeV.pt`、`model_fakeL.pt`、`model_studentV.pt`、`model_studentL.pt`（可按需在 `.env` 中用 `FLDCF_CHECKPOINT_*` 覆盖路径，见 `backend/src/fldcf_api/inference.py` 顶部说明）。
- **`backend/fldcf_data/model/`** 下需有官方流程使用的先验命名，如 **`model_vi.pt`**；LoveDA 线另需 **`model_lo.pt`** 等（见推理代码与注释）。
- 其他常用变量（可选）：`FLDCF_PRESET`、`FLDCF_CPU`、`FLDCF_MAX_UPLOAD_BYTES`、`FLDCF_MASK_OVERRIDE` 等，见 `backend/src/fldcf_api/inference.py`。

---

## 前端配置与运行

```bash
cd gp-front
npm install
npm run dev
```

- 开发环境下，Vite 将 **`/fldcf-api`** 代理到 `http://127.0.0.1:8000`，并重写为后端的 **`/fldcf`**（见 `gp-front/vite.config.ts`）。因此前端默认通过 **`/fldcf-api/status`**、**`/fldcf-api/predict`** 访问推理接口。
- 若直连后端而不走代理，可设置环境变量 **`VITE_FLDCF_BASE_URL`**（例如 `http://127.0.0.1:8000/fldcf`）。

### 页面与路由

| 路径 | 说明 |
|------|------|
| `/` | 重定向到 **`/entrance`**（登录页） |
| `/entrance` | 登录 / 注册（未登录可访问；已登录会跳到首页） |
| `/home` | 工作台首页（需登录） |
| `/viz`、`/dev/fldcf-api` | 伪造定位可视化（同一组件，需登录） |

Token 存于浏览器 **`localStorage`** 的 `token` 字段；路由前置守卫未登录会跳转登录页。

---

## 典型使用流程

1. 启动 MySQL，配置并初始化 **`backend/.env`**。
2. 配置 **`FLDCF_ROOT`** 并准备好 **`fldcf_data`** 下权重与 `model/` 先验。
3. 启动后端：`uvicorn src.main:app --reload`（目录在 `backend`），或 `python -m src.main`。
4. 启动前端：`npm run dev`（目录在 `gp-front`）。
5. 浏览器打开前端地址，**登录** → 进入 **首页** → 打开 **伪造定位可视化** → 上传图片进行推理。

---

## 接口摘要

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/auth/login` 等 | 认证相关（见 `backend/src/auth/`） |
| GET | `/fldcf/status` | 推理服务状态、权重路径、是否已加载等 |
| POST | `/fldcf/predict` | 表单上传图片文件，字段 `file`；可选 `preset`（`fakeV` / `fakeL` / `studentV` / `studentL`） |

与 `/auth` 一致，成功时响应体为 **`{ code, msg, data }`**（`data` 内为状态或预测字段）；错误由全局异常处理为同形信封或 HTTP 状态码。

跨域允许的来源由环境变量 **`CORS_ALLOW_ORIGINS`**（逗号分隔）配置，默认包含本地开发端口与 `http://localhost`（见 `backend/src/main.py`）。

---

## Docker 部署（概要）

仓库根目录提供 **`docker-compose.yml`**、`backend/Dockerfile`、`gp-front/Dockerfile`。容器内为 **`uvicorn src.main:app`**（`PYTHONPATH=/app/backend`）；本地在 `backend` 目录使用 **`uvicorn src.main:app --reload`** 或 **`python -m src.main`**。

1. **准备**：保留 **`FLDCF_raw/src`**（已打进后端镜像）；将 **`backend/fldcf_data`** 下权重与 **`model/`** 先放好（与本地一致，通过卷挂载进容器）。
2. **环境**：复制 **`docker.env.example`** 为 **`docker.env`**，填写 **`JWT_SECRET_KEY`**、**`AUTH_INIT_PASSWORD`**（至少 10 位）、**`MYSQL_ROOT_PASSWORD`** 等。
3. **启动**：在仓库根目录执行  
   `docker compose --env-file docker.env up --build`
4. **访问**：浏览器打开 **`http://localhost`**（Nginx 托管前端，并把 **`/api`、`/fldcf-api`** 反代到后端）；API 文档 **`http://localhost:8000/docs`**。

**CPU / GPU 可选（Docker）**

- **默认 CPU 小镜像**：`docker.env` 保持 `PYTORCH_VARIANT` 不填或 `cpu`，`FLDCF_CPU=1`。
- **用 GPU**：主机安装 **NVIDIA 驱动** 与 **[NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html)**；在 `docker.env` 中设置 **`PYTORCH_VARIANT=cu124`** 与 **`FLDCF_CPU=0`**，然后叠加 **`docker-compose.gpu.yml`**：  
  `docker compose -f docker-compose.yml -f docker-compose.gpu.yml --env-file docker.env up --build`  
  推理仍可在请求里用表单参数 **`use_cpu`** 临时覆盖（与本地一致）；无 GPU 或未叠加上述文件时，CUDA 版 wheel 在容器内会 **自动退回 CPU**（`torch.cuda.is_available()` 为 false）。

---

## 常见问题

- **`ModuleNotFoundError: No module named 'utils.tools'`**  
  已在本项目 `fldcf_api` 的 `load()` 中通过暂存/恢复 `sys.modules` 的 `utils` 与 **本仓库 `backend/src/utils`** 解耦；若仍异常，请确认 **`FLDCF_ROOT`** 指向的目录下存在 **`src/utils/tools.py`**。

- **预热失败 / `inference_ready` 为 false**  
  检查 **`FLDCF_ROOT`**、`fldcf_data` 权重与 **`model_vi.pt`** 等先验是否齐全，并查看终端日志。

- **前端上传返回 500**  
  勿在 axios 中手动设置 `Content-Type: multipart/form-data`（应让浏览器带 **boundary**）；具体已在前端 `FldcfApiTest.vue` 中处理。

- **CORS**  
  设置环境变量 **`CORS_ALLOW_ORIGINS`**（逗号分隔完整 Origin），Docker + Nginx 同域时一般会包含 `http://localhost`。

- **4K / 大图导致 502 或进程消失**  
  推理默认将 **`FLDCF_MAX_INPUT_SIDE`**（默认 **2048**）作为最长边上限并自动缩小；仍 OOM 时返回 **503** 业务错误而非拖垮 worker。设为 **0** 可关闭缩放（不推荐）。响应中含 **`input_was_downscaled`**、**`input_original_*`**。

---

## 许可与引用

若使用[FLDCF](https://github.com/littlebeen/Forgery-localization-for-remote-sensing) 代码与论文以及相关权重，请遵循原作者许可并在学术工作中正确引用。本 README 仅描述本仓库的集成与运行方式。
