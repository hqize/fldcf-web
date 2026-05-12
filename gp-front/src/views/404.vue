<template>
  <div class="not-found-container">
    <!-- 背景图片层 -->
    <img :src="bgImage" class="bg-image" alt="404 background" />
    
    <!-- 内容层 -->
    <div class="content">
      <h1>404</h1>
      <p>再深思熟虑下吧~~</p>
      <button @click="goHome">返回首页</button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'
import bgImage from '@/assets/404.gif' 

const router = useRouter()
const goHome = () => {
  router.push('/')
}
</script>

<style scoped>
.not-found-container {
  position: relative;
  width: 100%;
  height: 100vh;
  overflow: hidden;
  display: flex;
  justify-content: center;
  align-items: center;
}

.bg-image {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  object-fit: cover; /* 关键：保持比例覆盖整个容器 */
  z-index: -1; /* 确保图片在内容下方 */
}

.content {
  text-align: center;
  color: white;
  text-shadow: 0 2px 4px rgba(0,0,0,0.5);
  z-index: 1; /* 确保内容在图片上方 */
}

button {
  margin-top: 20px;
  padding: 10px 20px;
  cursor: pointer;
  background-color: rgba(255, 255, 255, 0.2);
  border: 1px solid white;
  color: white;
  border-radius: 4px;
  transition: background-color 0.3s;
}

button:hover {
  background-color: rgba(255, 255, 255, 0.4);
}
</style>