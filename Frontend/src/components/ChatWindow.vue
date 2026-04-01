<script setup>
import { ref, onMounted, nextTick } from 'vue';
import { sendChatMessage, fetchTools } from '../services/api';

const messages = ref([]);
const availableTools = ref([]);
const inputQuery = ref('');
const isLoading = ref(false);
const selectedModel = ref('deepseek-chat'); // 'deepseek-chat' or 'deepseek-reasoner'
const sessionId = 'session_' + Math.random().toString(36).substr(2, 9);
const chatContainer = ref(null);

const scrollToBottom = async () => {
  await nextTick();
  if (chatContainer.value) {
    chatContainer.value.scrollTop = chatContainer.value.scrollHeight;
  }
};

// Color scheme per tool icon type
const toolColors = {
  weather: { bg: 'rgba(6, 182, 212, 0.12)', border: '#06b6d4', text: '#67e8f9' },
  news:    { bg: 'rgba(251, 146, 60, 0.12)', border: '#fb923c', text: '#fdba74' },
  stock:   { bg: 'rgba(34, 197, 94, 0.12)', border: '#22c55e', text: '#86efac' },
  default: { bg: 'rgba(148, 163, 184, 0.12)', border: '#94a3b8', text: '#cbd5e1' },
};

// SVG icons per type
const toolSvgIcons = {
  weather: `<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17.5 19H9a7 7 0 1 1 6.71-9h1.79a4.5 4.5 0 1 1 0 9Z"/></svg>`,
  news:    `<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 22h16a2 2 0 0 0 2-2V4a2 2 0 0 0-2-2H8a2 2 0 0 0-2 2v16a2 2 0 0 1-2 2Zm0 0a2 2 0 0 1-2-2v-9c0-1.1.9-2 2-2h2"/><path d="M18 14h-8"/><path d="M15 18h-5"/><path d="M10 6h8v4h-8V6Z"/></svg>`,
  stock:   `<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="22 7 13.5 15.5 8.5 10.5 2 17"/><polyline points="16 7 22 7 22 13"/></svg>`,
  default: `<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>`,
};

onMounted(async () => {
  try {
    const tools = await fetchTools();
    availableTools.value = tools;
    messages.value = [{
      role: 'assistant',
      isWelcome: true,
      tools: tools,
      text: '你好！我是您的多任务智能问答助手。\n请直接向我提问，我会自动调用合适的工具为您服务。',
    }];
  } catch (e) {
    messages.value = [{
      role: 'assistant',
      text: '你好！我是您的多任务智能问答助手。\n⚠️ 暂时无法连接后端服务，请检查 Flask 是否已启动。',
      isError: true,
    }];
  }
  await scrollToBottom();
});

// Core send logic
const sendQuery = async (query) => {
  if (!query.trim() || isLoading.value) return;

  messages.value.push({ role: 'user', text: query });
  isLoading.value = true;
  await scrollToBottom();

  const tempAiMsgIndex = messages.value.length;
  messages.value.push({ role: 'assistant', text: '', loading: true });
  await scrollToBottom();

  try {
    const res = await sendChatMessage(sessionId, query);
    messages.value[tempAiMsgIndex] = {
      role: 'assistant',
      text: res.answer,
      usedTools: res.tools_used || [],
      loading: false
    };
  } catch (error) {
    messages.value[tempAiMsgIndex] = {
      role: 'assistant',
      text: '服务器遇到了问题，请稍后再试。详情：' + (error.message || '未知错误'),
      isError: true,
      loading: false
    };
  } finally {
    isLoading.value = false;
    await scrollToBottom();
  }
};

// Input box handler
const handleSend = () => {
  const q = inputQuery.value;
  inputQuery.value = '';
  sendQuery(q);
};

// Try to get user city via browser Geolocation + OpenStreetMap reverse geocoding
const getUserCity = () => {
  return new Promise((resolve) => {
    if (!navigator.geolocation) { resolve('北京'); return; }
    navigator.geolocation.getCurrentPosition(
      async (pos) => {
        try {
          const { latitude, longitude } = pos.coords;
          const res = await fetch(
            `https://nominatim.openstreetmap.org/reverse?lat=${latitude}&lon=${longitude}&format=json&accept-language=zh`
          );
          const data = await res.json();
          const addr = data.address || {};
          resolve(addr.city || addr.town || addr.county || addr.state || '当前位置');
        } catch { resolve('北京'); }
      },
      () => resolve('北京'),
      { timeout: 5000 }
    );
  });
};

// Quick-action on tool card click
const handleCardClick = async (tool) => {
  if (isLoading.value) return;

  if (tool.icon === 'weather') {
    // Show a loading/feedback status in the input area or as a user message
    // Instead of pushing twice, we just push one meaningful message
    messages.value.push({ role: 'user', text: '📍 正在获取当前位置的天气...' });
    await scrollToBottom();
    
    // We try to get the city, but with a short timeout. 
    // If it takes more than 2s or fails, we just send "当前位置" and let the backend IP geolocator handle it.
    const cityPromise = getUserCity();
    const city = await Promise.race([
      cityPromise, 
      new Promise(resolve => setTimeout(() => resolve('当前位置'), 2000))
    ]);
    
    const finalQuery = city === '当前位置' ? '帮我查一下我现在所在位置的实时天气' : `帮我查一下${city}现在的实时天气`;
    
    // Replace the earlier temporary message text to avoid duplication in sendQuery
    messages.value[messages.value.length - 1].text = finalQuery;
    
    // Call the logic from sendQuery BUT WITHOUT its message.push part
    // To do this, I'll extract common logic or just use a flag in sendQuery
    await performChatQuery(finalQuery);
  } else if (tool.icon === 'news') {
    await sendQuery('帮我获取当前最新的热门新闻资讯');
  } else if (tool.icon === 'stock') {
    await sendQuery('帮我查一下今天A股所有涨停的股票');
  } else {
    await sendQuery(`使用 ${tool.label} 功能`);
  }
};

// Refactored helper to handle the actual API call without UI management
const performChatQuery = async (query) => {
  isLoading.value = true;
  await scrollToBottom();

  const tempAiMsgIndex = messages.value.length;
  messages.value.push({ role: 'assistant', text: '', loading: true });
  await scrollToBottom();

  try {
    const res = await sendChatMessage(sessionId, query, selectedModel.value);
    messages.value[tempAiMsgIndex] = {
      role: 'assistant',
      text: res.answer,
      usedTools: res.tools_used || [],
      loading: false
    };
  } catch (error) {
    messages.value[tempAiMsgIndex] = {
      role: 'assistant',
      text: '服务器遇到了问题，请稍后再试。详情：' + (error.message || '未知错误'),
      isError: true,
      loading: false
    };
  } finally {
    isLoading.value = false;
    await scrollToBottom();
  }
};
</script>

<template>
  <div class="chat-wrapper">
    <!-- Model Selector -->
    <div class="model-selector-container">
      <div class="model-selector-pill">
        <button 
          :class="['model-btn', selectedModel === 'deepseek-chat' ? 'active' : '']"
          @click="selectedModel = 'deepseek-chat'"
        >
          <span class="icon">🚀</span> 快速
        </button>
        <button 
          :class="['model-btn', selectedModel === 'deepseek-reasoner' ? 'active' : '']"
          @click="selectedModel = 'deepseek-reasoner'"
        >
          <span class="icon">🧠</span> 智能搜索
        </button>
      </div>
    </div>

    <!-- Message Array -->
    <div class="chat-container" ref="chatContainer">
      <div
        v-for="(msg, index) in messages"
        :key="index"
        :class="['message-row', msg.role === 'user' ? 'row-user' : 'row-ai']"
      >
        <div class="message-bubble" :class="[msg.role === 'user' ? 'bubble-user' : 'bubble-ai', msg.isError ? 'bubble-error' : '']">

          <!-- Loading state -->
          <div v-if="msg.loading" class="typing-indicator">
            <span></span><span></span><span></span>
          </div>

          <div v-else>
            <!-- Used tools badge (conversation response) -->
            <div v-if="msg.usedTools && msg.usedTools.length > 0" class="used-tools-container">
              <span class="used-tool-tag" v-for="(t, idx) in msg.usedTools" :key="idx">
                <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"></path>
                </svg>
                &nbsp;{{ t.tool }}
              </span>
            </div>

            <!-- Message text -->
            <div class="message-text">{{ msg.text }}</div>

            <!-- Welcome tool capability cards -->
            <div v-if="msg.isWelcome && msg.tools && msg.tools.length > 0" class="tool-cards-grid">
              <div
                v-for="tool in msg.tools"
                :key="tool.name"
                class="tool-card"
                :class="{ 'tool-card-disabled': isLoading }"
                :style="{
                  background: (toolColors[tool.icon] || toolColors.default).bg,
                  borderColor: (toolColors[tool.icon] || toolColors.default).border,
                  color: (toolColors[tool.icon] || toolColors.default).text,
                }"
                @click="handleCardClick(tool)"
              >
                <div class="tool-card-header">
                  <span class="tool-card-icon" v-html="toolSvgIcons[tool.icon] || toolSvgIcons.default"></span>
                  <span class="tool-card-label">{{ tool.label }}</span>
                  <span class="tool-card-click-hint">点击体验 →</span>
                </div>
                <div class="tool-card-desc">{{ tool.description }}</div>
              </div>
            </div>
          </div>

        </div>
      </div>
    </div>

    <div class="input-container">
      <input
        v-model="inputQuery"
        @keyup.enter="handleSend"
        placeholder="问我想要知道的事情..."
        :disabled="isLoading"
      />
      <button @click="handleSend" :disabled="isLoading || !inputQuery.trim()">发送</button>
    </div>
  </div>
</template>

<style scoped>
.chat-wrapper {
  background: var(--surface-color);
  border-radius: 16px;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.5);
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
  border: 1px solid rgba(255, 255, 255, 0.05);
  position: relative;
}

/* Model Selector Styles */
.model-selector-container {
  display: flex;
  justify-content: center;
  padding: 1rem 0;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
  background: rgba(15, 23, 42, 0.3);
}

.model-selector-pill {
  display: flex;
  background: rgba(0, 0, 0, 0.2);
  padding: 4px;
  border-radius: 24px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  gap: 4px;
}

.model-btn {
  border: none;
  background: transparent;
  color: var(--text-secondary);
  padding: 6px 16px;
  border-radius: 20px;
  font-size: 0.85rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  display: flex;
  align-items: center;
  gap: 6px;
}

.model-btn:hover:not(.active) {
  color: var(--text-primary);
  background: rgba(255, 255, 255, 0.05);
}

.model-btn.active {
  background: var(--accent-color);
  color: white;
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.4);
}

.model-btn .icon {
  font-size: 1rem;
}

.chat-container {
  flex: 1;
  overflow-y: auto;
  padding: 1.5rem;
  display: flex;
  flex-direction: column;
  gap: 1.2rem;
  scroll-behavior: smooth;
}

.message-row { display: flex; width: 100%; }
.row-user { justify-content: flex-end; }
.row-ai  { justify-content: flex-start; }

.message-bubble {
  max-width: 85%;
  padding: 1rem 1.2rem;
  border-radius: 12px;
  line-height: 1.7;
  font-size: 0.95rem;
  animation: popIn 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275) forwards;
  opacity: 0;
  transform: translateY(10px) scale(0.95);
}

.bubble-user {
  background: var(--user-msg-bg);
  color: #fff;
  border-bottom-right-radius: 0;
}

.bubble-ai {
  background: var(--ai-msg-bg);
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2);
  border-bottom-left-radius: 0;
}

.bubble-error { border-left: 4px solid #ef4444; }

.message-text {
  white-space: pre-wrap;
  word-wrap: break-word;
}

/* Tool cards for welcome message */
.tool-cards-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
  gap: 0.75rem;
  margin-top: 1rem;
}

.tool-card {
  border: 1px solid;
  border-radius: 10px;
  padding: 0.75rem 0.9rem;
  transition: transform 0.2s, box-shadow 0.2s, opacity 0.2s;
  cursor: pointer;
  user-select: none;
}

.tool-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.35);
}

.tool-card:active {
  transform: translateY(-1px) scale(0.98);
}

.tool-card-disabled {
  opacity: 0.5;
  cursor: not-allowed;
  pointer-events: none;
}

.tool-card-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-weight: 600;
  font-size: 0.85rem;
  margin-bottom: 0.4rem;
}

.tool-card-icon { display: flex; align-items: center; flex-shrink: 0; }

.tool-card-label { letter-spacing: 0.02em; flex: 1; }

.tool-card-click-hint {
  font-size: 0.7rem;
  opacity: 0.6;
  font-weight: 400;
  letter-spacing: 0;
  white-space: nowrap;
  transition: opacity 0.2s;
}

.tool-card:hover .tool-card-click-hint {
  opacity: 1;
}

.tool-card-desc {
  font-size: 0.78rem;
  opacity: 0.85;
  line-height: 1.5;
}

/* Used tools badges (on AI response messages) */
.used-tools-container {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem;
  margin-bottom: 0.7rem;
  padding-bottom: 0.7rem;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.used-tool-tag {
  background: var(--tool-bg);
  border: 1px solid var(--tool-border);
  color: var(--accent-color);
  font-size: 0.72rem;
  padding: 3px 9px;
  border-radius: 10px;
  display: flex;
  align-items: center;
}

/* Input container */
.input-container {
  display: flex;
  padding: 1rem;
  background: rgba(15, 23, 42, 0.5);
  border-top: 1px solid var(--tool-border);
}

.input-container input {
  flex: 1;
  background: var(--bg-color);
  border: 1px solid var(--tool-border);
  color: var(--text-primary);
  padding: 0.8rem 1.2rem;
  border-radius: 20px;
  font-size: 1rem;
  outline: none;
  transition: all 0.3s;
}

.input-container input:focus {
  border-color: var(--accent-color);
  box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.3);
}

.input-container button {
  background: var(--accent-color);
  color: white;
  border: none;
  padding: 0 1.5rem;
  margin-left: 0.8rem;
  border-radius: 20px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.input-container button:hover:not(:disabled) {
  background: var(--accent-hover);
  transform: translateY(-2px);
}

.input-container button:disabled { opacity: 0.5; cursor: not-allowed; }

.typing-indicator { display: flex; align-items: center; gap: 4px; height: 24px; }
.typing-indicator span {
  width: 6px; height: 6px;
  background-color: var(--text-secondary);
  border-radius: 50%;
  animation: bounce 1.4s infinite ease-in-out both;
}
.typing-indicator span:nth-child(1) { animation-delay: -0.32s; }
.typing-indicator span:nth-child(2) { animation-delay: -0.16s; }

@keyframes bounce {
  0%, 80%, 100% { transform: scale(0); }
  40% { transform: scale(1); }
}

@keyframes popIn {
  to { opacity: 1; transform: translateY(0) scale(1); }
}
</style>
