<script setup>
import { ref, onBeforeUnmount } from 'vue'
import ChatWindow from './components/ChatWindow.vue'
import KnowledgeManager from './components/KnowledgeManager.vue'

const workbenchRef = ref(null)
const isChatOpen = ref(false)
const resizing = ref(false)
const chatWidth = ref(480)
const resizeState = {
  resizing: false,
  startX: 0,
  startWidth: 0
}
const MIN_CHAT_WIDTH = 360
const MAX_CHAT_WIDTH = 760

const clamp = (value, min, max) => Math.max(min, Math.min(max, value))

const openChat = () => {
  isChatOpen.value = true
}

const closeChat = () => {
  isChatOpen.value = false
}

const startResize = (e) => {
  e.preventDefault()
  resizeState.resizing = true
  resizing.value = true
  resizeState.startX = e.clientX
  resizeState.startWidth = chatWidth.value
  window.addEventListener('mousemove', onResizeMove)
  window.addEventListener('mouseup', stopInteractions)
}

const onResizeMove = (e) => {
  if (!resizeState.resizing || !workbenchRef.value) return
  const rect = workbenchRef.value.getBoundingClientRect()
  const dx = resizeState.startX - e.clientX
  const maxAllowed = Math.min(MAX_CHAT_WIDTH, Math.floor(rect.width * 0.7))
  chatWidth.value = clamp(
    resizeState.startWidth + dx,
    MIN_CHAT_WIDTH,
    Math.max(MIN_CHAT_WIDTH, maxAllowed)
  )
}

const stopInteractions = () => {
  resizeState.resizing = false
  resizing.value = false
  window.removeEventListener('mousemove', onResizeMove)
  window.removeEventListener('mouseup', stopInteractions)
}

onBeforeUnmount(() => {
  stopInteractions()
})
</script>

<template>
  <div class="app-container">
    <div class="knowledge-workbench" ref="workbenchRef">
      <button class="chat-drawer-trigger" @click="openChat" v-if="!isChatOpen">
        💬 打开对话
      </button>

      <div class="workbench-split">
        <section class="knowledge-pane">
          <KnowledgeManager />
        </section>
        <template v-if="isChatOpen">
          <div class="splitter" @mousedown="startResize" :class="{ active: resizing }"></div>
          <aside class="chat-docked-panel" :style="{ width: `${chatWidth}px` }">
            <div class="chat-docked-header">
              <span class="chat-docked-title">💬 对话助手</span>
              <button class="close-btn" @click="closeChat" title="关闭对话">×</button>
            </div>
            <div class="chat-docked-body">
              <ChatWindow />
            </div>
          </aside>
        </template>
      </div>
    </div>
  </div>
</template>

<style scoped>
.app-container {
  width: 100vw;
  height: 100vh;
  overflow: hidden;
  display: flex;
}

.knowledge-workbench {
  position: relative;
  width: 100%;
  height: 100%;
  min-height: 0;
  display: flex;
}

.chat-drawer-trigger {
  position: absolute;
  top: 0.6rem;
  right: 0.75rem;
  z-index: 35;
  border: none;
  border-radius: 999px;
  padding: 0.5rem 0.9rem;
  background: linear-gradient(135deg, #6366f1 0%, #4f46e5 100%);
  color: #fff;
  font-weight: 600;
  cursor: pointer;
  box-shadow: 0 4px 14px rgba(79, 70, 229, 0.4);
  font-size: 0.8rem;
  transition: transform 0.15s, box-shadow 0.15s;
}

.chat-drawer-trigger:hover {
  transform: translateY(-1px);
  box-shadow: 0 6px 20px rgba(79, 70, 229, 0.5);
}

.workbench-split {
  width: 100%;
  height: 100%;
  display: flex;
  min-height: 0;
}

.knowledge-pane {
  flex: 1;
}

.splitter {
  width: 6px;
  cursor: col-resize;
  background: transparent;
  position: relative;
}

.splitter::after {
  content: "";
  position: absolute;
  left: 2px;
  top: 0;
  bottom: 0;
  width: 2px;
  background: rgba(148, 163, 184, 0.25);
}

.splitter.active::after,
.splitter:hover::after {
  background: rgba(99, 102, 241, 0.8);
}

.chat-docked-panel {
  background: #0f172a;
  border-left: 1px solid rgba(255, 255, 255, 0.12);
  display: flex;
  flex-direction: column;
  box-shadow: -8px 0 24px rgba(0, 0, 0, 0.35);
  overflow: hidden;
  min-width: 360px;
}

.chat-docked-header {
  height: 48px;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 0.75rem 0 1rem;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
  background: rgba(15, 23, 42, 0.95);
}

.chat-docked-title {
  font-size: 0.88rem;
  font-weight: 600;
  color: #e2e8f0;
  letter-spacing: 0.02em;
}

.close-btn {
  border: none;
  background: rgba(255,255,255,0.06);
  color: #94a3b8;
  font-size: 1.1rem;
  line-height: 1;
  width: 28px;
  height: 28px;
  border-radius: 6px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background 0.15s, color 0.15s;
}

.close-btn:hover {
  background: rgba(239, 68, 68, 0.2);
  color: #fca5a5;
}

.chat-docked-body {
  flex: 1;
  min-height: 0;
  padding: 0;
}

</style>
