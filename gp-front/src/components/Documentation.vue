<script setup lang="ts">
import { ref } from 'vue'

const toc = [
  { id: 'intro', label: '概述' },
  { id: 'auth', label: '登录与账号' },
  { id: 'fldcf-single', label: '单个图像检测' },
  { id: 'fldcf-batch', label: '批量检测' },
  { id: 'detection-history', label: '检测历史' },
  { id: 'ai-assistant', label: 'AI 助手' },
  { id: 'api', label: '后端接口摘要' },
  { id: 'env', label: '环境与部署提示' },
  { id: 'faq', label: '常见问题' },
] as const

const activeId = ref<string>(toc[0].id)

function goSection(id: string) {
  activeId.value = id
  const el = document.getElementById(`doc-${id}`)
  el?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}
</script>

<template>
  <div class="documentation">
    <aside class="doc-aside" aria-label="文档目录">
      <div class="doc-aside-title">目录</div>
      <nav class="doc-nav">
        <el-button
          v-for="item in toc"
          :key="item.id"
          text
          class="doc-nav-item"
          :type="activeId === item.id ? 'primary' : 'default'"
          @click="goSection(item.id)"
        >
          {{ item.label }}
        </el-button>
      </nav>
    </aside>

    <article class="doc-article">
      <section :id="'doc-intro'" class="doc-section">
        <h3 class="doc-h">概述</h3>
        <p class="doc-p">
          本系统面向<strong>卫星遥感图像伪造检测</strong>：支持单图与批量推理（FLDCF），并提供基于 DeepSeek 的<strong>AI
          助手</strong>解释结果与相关概念；检测摘要写入<strong>数据库</strong>供「检测历史」查看。前端为 Vue 3 + Element Plus，后端为 FastAPI。
        </p>
      </section>

      <section :id="'doc-auth'" class="doc-section">
        <h3 class="doc-h">登录与账号</h3>
        <ul class="doc-ul">
          <li>在登录页使用用户名、密码登录；成功后令牌保存在浏览器本地，后续请求自动携带 <code>Authorization: Bearer</code>。</li>
          <li>部分接口（如 AI 对话）需要登录态；若长时间未操作可能需重新登录。</li>
          <li>个人信息里的头像为<strong>图片上传</strong>（<code>POST /auth/me/avatar</code>），保存在服务端并通过 <code>/static/uploads/avatars/</code> 访问。</li>
        </ul>
      </section>

      <section :id="'doc-fldcf-single'" class="doc-section">
        <h3 class="doc-h">单个图像检测</h3>
        <p class="doc-p">在「单个检测」页可上传一张 RGB 卫星图，选择权重线（如 fakeV / studentL 等），查看：</p>
        <ul class="doc-ul">
          <li>真伪分类及伪造 / 真实概率；</li>
          <li>篡改区域 mask 可视化（黑≈真实像素，白≈篡改）；</li>
          <li>JSON 与图表导出（若页面提供）。</li>
        </ul>
        <p class="doc-p muted">
          推理由后端 FLDCF 服务完成；开发环境下前端通过代理访问独立的 FLDCF 路径（见下文接口摘要）。推理成功的摘要会写入服务端<strong>检测历史</strong>。
        </p>
      </section>

      <section :id="'doc-fldcf-batch'" class="doc-section">
        <h3 class="doc-h">批量图像检测</h3>
        <p class="doc-p">
          「多个检测」支持一次选择多张图片（有数量上限），按队列<strong>顺序</strong>调用与单图相同的推理接口；结果以表格列出，并可导出
          CSV / JSON / 图表等（以页面实际按钮为准）。跑完后会将每张图的摘要写入<strong>检测历史</strong>（含失败项）。
        </p>
      </section>

      <section :id="'doc-detection-history'" class="doc-section">
        <h3 class="doc-h">检测历史</h3>
        <p class="doc-p">
          每次在「单个检测」「多个检测」完成推理后，前端会将<strong>摘要指标</strong>（文件名、权重线、分类、各项概率、尺寸等）提交到后端，写入当前登录用户名下；<strong>不包含</strong>
          mask PNG/base64，以免占用过多存储。可在「检测历史」页分页查看、删除单条记录。
        </p>
        <ul class="doc-ul">
          <li>失败样本也会记一条（含错误信息摘要），便于排查。</li>
          <li>同一账号换设备登录仍可看到历史（数据在服务器）。</li>
        </ul>
      </section>

      <section :id="'doc-ai-assistant'" class="doc-section">
        <h3 class="doc-h">AI 助手</h3>
        <p class="doc-p">
          「AI 助手」连接后端 <code>/aichat</code>，使用 DeepSeek（OpenAI 兼容协议）。需在后端配置环境变量
          <code>DEEPSEEK_BASE_URL</code>、<code>DEEPSEEK_API_KEY</code>；可选 <code>DEEPSEEK_MODEL</code>。
        </p>
        <ul class="doc-ul">
          <li><code>GET /aichat/status</code>：是否已配置密钥（前端据此提示「未配置」）。</li>
          <li><code>POST /aichat/chat</code>：多轮对话，需在 Header 携带 JWT。</li>
          <li>
            输入框上方提供<strong>快捷提问</strong>按钮（如「概率含义」「mask 解读」「权重线区别」等），点击后会自动填入对应完整问题并发送；鼠标悬停按钮可看完整题干。
          </li>
          <li>助手回复按 <strong>Markdown</strong> 渲染（标题、列表、代码块、表格、链接等）；链接在新标签页打开。用户发送内容仍为纯文本。</li>
          <li>
            对话记录保存在浏览器<strong>本地</strong>（<code>localStorage</code>，按账号区分）；刷新页面或下次打开仍可继续查看。「清空对话」会同时清除本地记录；最多保留约 120 条消息以防占满存储。
          </li>
        </ul>
        <p class="doc-p"><strong>预设问题涵盖的主题：</strong></p>
        <ul class="doc-ul">
          <li>伪造 / 真实概率的含义与可疑程度判断；</li>
          <li>mask 黑白区域与篡改占比解读；</li>
          <li>各权重线（fakeV、fakeL、studentV、studentL）的差异与适用场景；</li>
          <li>批量检测的执行方式与导出内容概述；</li>
          <li>伪造检测的常见思路与应用局限。</li>
        </ul>
        <p class="doc-p muted">
          可将「说明文档」与检测页对照使用：先跑推理，再在 AI 助手中询问指标含义或分析建议。
        </p>
      </section>

      <section :id="'doc-api'" class="doc-section">
        <h3 class="doc-h">后端接口摘要</h3>
        <p class="doc-p">以下为便于联调的路由约定（具体字段见 Swagger <code>/docs</code> 或源码）。</p>
        <div class="doc-table-wrap">
          <table class="doc-table">
            <thead>
              <tr>
                <th>模块</th>
                <th>方法</th>
                <th>路径</th>
                <th>说明</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td>认证</td>
                <td>POST</td>
                <td><code>/auth/login</code></td>
                <td>表单登录，返回 access_token</td>
              </tr>
              <tr>
                <td>认证</td>
                <td>GET</td>
                <td><code>/auth/me</code></td>
                <td>当前用户（需 Bearer）</td>
              </tr>
              <tr>
                <td>认证</td>
                <td>PATCH</td>
                <td><code>/auth/me</code></td>
                <td>密码、移除头像（<code>avatar_url: null</code>）</td>
              </tr>
              <tr>
                <td>认证</td>
                <td>POST</td>
                <td><code>/auth/me/avatar</code></td>
                <td>multipart 上传头像图片（需 Bearer）</td>
              </tr>
              <tr>
                <td>检测历史</td>
                <td>POST</td>
                <td><code>/detections</code></td>
                <td>写入一条检测摘要（需 Bearer）</td>
              </tr>
              <tr>
                <td>检测历史</td>
                <td>POST</td>
                <td><code>/detections/batch</code></td>
                <td>批量写入（body.items，需 Bearer）</td>
              </tr>
              <tr>
                <td>检测历史</td>
                <td>GET</td>
                <td><code>/detections</code></td>
                <td>分页查询当前用户记录（需 Bearer）</td>
              </tr>
              <tr>
                <td>检测历史</td>
                <td>DELETE</td>
                <td><code>/detections/{id}</code></td>
                <td>删除一条记录（需 Bearer）</td>
              </tr>
              <tr>
                <td>FLDCF</td>
                <td>GET</td>
                <td><code>/fldcf/status</code></td>
                <td>推理服务状态、设备、权重路径</td>
              </tr>
              <tr>
                <td>FLDCF</td>
                <td>POST</td>
                <td><code>/fldcf/predict</code></td>
                <td>multipart 上传图像 + preset</td>
              </tr>
              <tr>
                <td>AI</td>
                <td>GET</td>
                <td><code>/aichat/status</code></td>
                <td>DeepSeek 是否已配置</td>
              </tr>
              <tr>
                <td>AI</td>
                <td>POST</td>
                <td><code>/aichat/chat</code></td>
                <td>JSON：<code>messages[]</code>（需 Bearer）</td>
              </tr>
            </tbody>
          </table>
        </div>
        <p class="doc-p">
          前端开发代理：Vite 将 <code>/fldcf-api</code> 转发到后端的 <code>/fldcf</code>；主 API 基址由环境变量
          <code>VITE_API_BASE_URL</code> 指向 FastAPI 根地址（如 <code>http://127.0.0.1:8000</code>）。
        </p>
      </section>

      <section :id="'doc-env'" class="doc-section">
        <h3 class="doc-h">环境与部署提示</h3>
        <ul class="doc-ul">
          <li>后端：<code>backend/.env</code>（数据库、JWT、可选 FLDCF 根目录等）；DeepSeek 亦可写在 <code>backend/aichat_api/.env</code>，启动时会合并加载。</li>
          <li>FLDCF 推理依赖 GPU/权重路径，请看后端日志与 <code>/fldcf/status</code> 中的 <code>inference_ready</code>。</li>
          <li>生产环境务必更换 JWT 密钥、数据库口令，且勿将 API Key 提交到版本库。</li>
        </ul>
      </section>

      <section :id="'doc-faq'" class="doc-section">
        <h3 class="doc-h">常见问题</h3>
        <dl class="doc-dl">
          <dt>AI 助手提示「后端未配置 DeepSeek」？</dt>
          <dd>
            在后端配置 <code>DEEPSEEK_BASE_URL</code>、<code>DEEPSEEK_API_KEY</code> 并重启服务；确认 <code>GET /aichat/status</code> 返回
            <code>configured: true</code>。
          </dd>
          <dt>批量检测很慢？</dt>
          <dd>当前实现为顺序请求多张图，总耗时随张数增加；属预期行为。</dd>
          <dt>推理报错或超时？</dt>
          <dd>检查图像格式与大小、后端显存、以及 <code>/fldcf/status</code> 是否已就绪。</dd>
        </dl>
      </section>
    </article>
  </div>
</template>

<style scoped>
.documentation {
  display: grid;
  grid-template-columns: 200px minmax(0, 1fr);
  gap: 24px;
  align-items: start;
  width: 100%;
  max-width: 1100px;
}

@media (max-width: 768px) {
  .documentation {
    grid-template-columns: 1fr;
  }

  .doc-aside {
    position: static;
  }
}

.doc-aside {
  position: sticky;
  top: 12px;
  padding: 14px 12px;
  border-radius: 12px;
  border: 1px solid var(--color-border, #dde2ee);
  background: var(--color-surface, #fff);
  box-shadow: var(--shadow-sm, 0 1px 3px rgba(0, 0, 0, 0.06));
}

.doc-aside-title {
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.08em;
  color: var(--color-text-muted, #94a3b8);
  margin-bottom: 10px;
}

.doc-nav {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.doc-nav-item {
  width: 100%;
  justify-content: flex-start;
  margin: 0;
  padding: 8px 10px;
  font-size: 13px;
  border-radius: 8px;
  font-weight: inherit;
}

.doc-nav-item.el-button--primary {
  font-weight: 600;
}

.doc-article {
  min-width: 0;
  padding: 20px 22px 28px;
  border-radius: 12px;
  border: 1px solid var(--color-border, #dde2ee);
  background: var(--color-surface, #fff);
  box-shadow: var(--shadow-sm, 0 1px 3px rgba(0, 0, 0, 0.06));
  max-height: min(72vh, 640px);
  overflow-y: auto;
}

.doc-section + .doc-section {
  margin-top: 28px;
  padding-top: 24px;
  border-top: 1px dashed var(--color-border, #e5e7eb);
}

.doc-h {
  font-size: 16px;
  font-weight: 700;
  color: var(--color-text-primary, #1a1f36);
  margin: 0 0 12px;
}

.doc-p {
  font-size: 14px;
  line-height: 1.65;
  color: var(--color-text-secondary, #475569);
  margin: 0 0 12px;
}

.doc-p.muted {
  font-size: 13px;
  color: var(--color-text-muted, #94a3b8);
}

.doc-ul {
  margin: 0 0 12px;
  padding-left: 1.25rem;
  font-size: 14px;
  line-height: 1.65;
  color: var(--color-text-secondary, #475569);
}

.doc-ul li {
  margin-bottom: 6px;
}

.doc-ul code,
.doc-p code {
  font-family: var(--font-mono, ui-monospace, monospace);
  font-size: 12px;
  padding: 1px 6px;
  border-radius: 4px;
  background: var(--color-surface-2, #f1f5f9);
  border: 1px solid var(--color-border, #e2e8f0);
}

.doc-table-wrap {
  overflow-x: auto;
  margin: 12px 0 16px;
  border-radius: 8px;
  border: 1px solid var(--color-border, #e5e7eb);
}

.doc-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}

.doc-table th,
.doc-table td {
  padding: 10px 12px;
  text-align: left;
  border-bottom: 1px solid var(--color-border, #f1f5f9);
}

.doc-table th {
  font-weight: 600;
  color: var(--color-text-primary, #1a1f36);
  background: var(--color-surface-2, #f8fafc);
}

.doc-table td {
  color: var(--color-text-secondary, #475569);
}

.doc-table code {
  font-size: 11px;
}

.doc-dl {
  margin: 0;
}

.doc-dl dt {
  font-size: 14px;
  font-weight: 600;
  color: var(--color-text-primary, #1a1f36);
  margin-top: 14px;
}

.doc-dl dt:first-child {
  margin-top: 0;
}

.doc-dl dd {
  margin: 6px 0 0;
  font-size: 14px;
  line-height: 1.65;
  color: var(--color-text-secondary, #475569);
}

.doc-dl dd code {
  font-family: var(--font-mono, ui-monospace, monospace);
  font-size: 12px;
  padding: 1px 6px;
  border-radius: 4px;
  background: var(--color-surface-2, #f1f5f9);
  border: 1px solid var(--color-border, #e2e8f0);
}
</style>
