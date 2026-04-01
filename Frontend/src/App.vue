<script setup>
import ChatWindow from './components/ChatWindow.vue'
</script>

<template>
  <div class="app-container">
    <header class="app-header">
      <h1>多任务智能问答助手</h1>
      <p class="subtitle">powered by DeepSeek & LangChain</p>
    </header>
    <main class="main-content">
      <ChatWindow />
    </main>
  </div>
</template>

<style scoped>
.app-container {
  display: flex;
  flex-direction: column;
  height: 100vh;
  padding: 1rem;
}

.app-header {
  text-align: center;
  padding-bottom: 1rem;
  border-bottom: 1px solid var(--surface-color);
  animation: fadeIn 0.8s ease-in-out;
}

.app-header h1 {
  margin: 0;
  font-size: 1.8rem;
  font-weight: 600;
  background: linear-gradient(90deg, #60a5fa, #c084fc);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

.subtitle {
  margin: 0.2rem 0 0 0;
  font-size: 0.85rem;
  color: var(--text-secondary);
  opacity: 0.8;
}

.main-content {
  flex: 1;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  margin-top: 1rem;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(-10px); }
  to { opacity: 1; transform: translateY(0); }
}
</style>
