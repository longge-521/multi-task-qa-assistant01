<script setup>
import { ref, onMounted, nextTick } from 'vue';
import { fetchTools } from '../services/chatService';
import api from '../services/api';
import * as indexService from '../services/indexService';

const messages = ref([]);
const availableTools = ref([]);
const inputQuery = ref('');
const isLoading = ref(false);
const selectedModel = ref('deepseek-chat');
const sessionId = 'session_' + Math.random().toString(36).substr(2, 9);
const chatContainer = ref(null);

// Tool drawer state
const toolDrawerOpen = ref(true);
const selectedToolIcon = ref(null);

const toolExamples = {
  weather: ['查询北京实时天气', '我所在位置的天气', '上海明天天气怎么样'],
  news:    ['最新热门新闻', '科技领域最新资讯', '今日国际新闻'],
  stock:   ['今天A股涨停股票', '昨天涨停的股票', '上周五涨停统计'],
  default: ['搜索知识库相关内容'],
};

const toggleDrawer = () => { toolDrawerOpen.value = !toolDrawerOpen.value; };

const selectTool = (tool) => {
  selectedToolIcon.value = selectedToolIcon.value === tool.icon ? null : tool.icon;
};

const selectedToolData = () => {
  if (!selectedToolIcon.value) return null;
  return availableTools.value.find(t => t.icon === selectedToolIcon.value) || null;
};

const sendExample = (text) => {
  if (isLoading.value) return;
  selectedToolIcon.value = null;
  toolDrawerOpen.value = false;
  sendQuery(text);
};

// Citation management
const showCitationModal = ref(false);
const currentCitation = ref(null);

const scrollToBottom = async () => {
  await nextTick();
  if (chatContainer.value) {
    chatContainer.value.scrollTop = chatContainer.value.scrollHeight;
  }
};

// 引用解析函数
const parseCitations = (text) => {
  if (!text) return { processedText: '', citations: [] };

  const citationRegex = /\[CITATION:([^:]+):(\d+)\]/g;
  const citationsList = [];
  let processedText = text;

  // 提取所有引用标记
  let match;
  while ((match = citationRegex.exec(text)) !== null) {
    const [fullMatch, filename, chunkIndex] = match;
    citationsList.push({ filename, chunkIndex, originalText: fullMatch });
  }

  // 如果没有找到引用标记，直接返回原始内容
  if (citationsList.length === 0) {
    return { processedText: text, citations: [] };
  }

  // 把所有唯一的原始文本提取出来
  const uniqueOriginalTexts = [...new Set(citationsList.map(c => c.originalText))];
  
  // 创建一个映射以便一次性替换所有引用标记
  const citationMap = {};
  citationsList.forEach((citation, index) => {
    const citationNumber = index + 1;
    citationMap[citation.originalText] = `<sup class="citation-link" data-index="${index}" data-filename="${citation.filename}" data-chunk="${citation.chunkIndex}">[${citationNumber}]</sup>`;
  });

  // 使用正则表达式一次性替换所有引用标记
  // 按照长度降序排序，确保长标记优先匹配
  const patterns = uniqueOriginalTexts
    .sort((a, b) => b.length - a.length)
    .map(key => key.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'));

  if (patterns.length > 0) {
    const citationPattern = new RegExp(patterns.join('|'), 'g');
    processedText = processedText.replace(citationPattern, (match) => citationMap[match] || match);
  }

  return { processedText, citations: citationsList };
};

// 引用点击处理函数
const handleCitationClick = async (filename, chunkIndex) => {
  currentCitation.value = { filename, chunkIndex };
  showCitationModal.value = true;

  // 加载该文件的分块内容
  try {
    const data = await indexService.getChunks(filename);
    const chunks = data.chunks || [];

    // 找到对应的分块（chunkIndex是从1开始的）
    const targetChunk = chunks.find((chunk, index) => index + 1 === parseInt(chunkIndex));

    if (targetChunk) {
      currentCitation.value.content = targetChunk.content;
    } else {
      currentCitation.value.content = "未找到对应的分块内容";
    }
  } catch (error) {
    console.error('Failed to fetch chunk content:', error);
    currentCitation.value.content = "加载分块内容失败";
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
      text: '你好！我是您的多任务智能问答助手。\n直接提问或从下方工具栏选择一个工具开始。',
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

const handleChatClick = (e) => {
  const citationEl = e.target.closest('.citation-link');
  if (citationEl) {
    e.preventDefault();
    handleCitationClick(citationEl.dataset.filename, citationEl.dataset.chunk);
  }
};

const sendQuery = async (query) => {
  if (!query.trim() || isLoading.value) return;
  messages.value.push({ role: 'user', text: query });
  await performChatQuery(query);
};

// Input box handler
const handleSend = () => {
  const q = inputQuery.value;
  inputQuery.value = '';
  sendQuery(q);
};

// Refactored helper to handle the actual API call WITH streaming support
const performChatQuery = async (query) => {
  isLoading.value = true;
  await scrollToBottom();

  const tempAiMsgIndex = messages.value.length;
  messages.value.push({ 
    role: 'assistant', 
    text: '', 
    usedTools: [],
    loading: true 
  });
  await scrollToBottom();

  try {
    // We use a clean fetch for streaming since it's easier to handle ReadableStreams
    const response = await fetch(`${api.defaults.baseURL}/chat/stream`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session_id: sessionId,
        query: query,
        model: selectedModel.value
      })
    });

    if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    
            messages.value[tempAiMsgIndex].loading = false;
            messages.value[tempAiMsgIndex].thought = '';

            while (true) {
              const { value, done } = await reader.read();
              if (done) break;
              
              const chunk = decoder.decode(value, { stream: true });
              const lines = chunk.split('\n');
              
              for (const line of lines) {
                if (!line.trim()) continue;
                try {
                  const data = JSON.parse(line);
                  
                  if (data.type === 'token') {
                    messages.value[tempAiMsgIndex].text += data.content;
                  } else if (data.type === 'thought') {
                    messages.value[tempAiMsgIndex].thought += data.content;
                  } else if (data.type === 'tool_start') {
                    messages.value[tempAiMsgIndex].usedTools.push({
                      tool: data.tool,
                      tool_input: data.input,
                      status: 'running'
                    });
                  } else if (data.type === 'tool_end') {
                    // Find the active tool and update its result
                    const toolIdx = messages.value[tempAiMsgIndex].usedTools.findIndex(t => t.tool === data.tool && t.status === 'running');
                    if (toolIdx !== -1) {
                      messages.value[tempAiMsgIndex].usedTools[toolIdx].status = 'done';
                      messages.value[tempAiMsgIndex].usedTools[toolIdx].output = data.output;
                    }
                  } else if (data.type === 'end') {
                    break;
                  }
                } catch (e) {
                  console.warn("Error parsing stream chunk:", e, line);
                }
              }
              // Trigger scroll during streaming
              await scrollToBottom();
            }

            // 解析streaming完成后的引用
            const finalText = messages.value[tempAiMsgIndex].text;
            if (finalText) {
              messages.value[tempAiMsgIndex].citations = parseCitations(finalText);
            }
  } catch (error) {
    messages.value[tempAiMsgIndex] = {
      role: 'assistant',
      text: '服务器通信异常，请检查网络或后端服务。' + (error.message || ''),
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
    <div class="chat-container" ref="chatContainer" @click="handleChatClick">
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

            <!-- Thinking / Reasoning section -->
            <div v-if="msg.thought" class="thought-container">
              <div class="thought-header">
                <span class="thought-icon">🧠</span>
                <span class="thought-label">思考过程</span>
              </div>
              <div class="thought-content">{{ msg.thought }}</div>
            </div>

            <!-- Message text with citation support -->
            <div class="message-text" v-html="msg.citations?.processedText || msg.text || ''"></div>
          </div>

        </div>
      </div>
    </div>

    <!-- Tool drawer + detail strip -->
    <div class="tool-drawer" v-if="availableTools.length > 0">
      <button class="drawer-toggle" @click="toggleDrawer">
        <span class="drawer-toggle-icon">🔧</span>
        <span>{{ availableTools.length }} 个可用工具</span>
        <span class="drawer-arrow" :class="{ open: toolDrawerOpen }">▾</span>
      </button>

      <div v-if="toolDrawerOpen" class="drawer-body">
        <div class="drawer-list">
          <button
            v-for="tool in availableTools"
            :key="tool.name"
            class="drawer-item"
            :class="{ active: selectedToolIcon === tool.icon }"
            :style="{
              '--item-border': (toolColors[tool.icon] || toolColors.default).border,
              '--item-text': (toolColors[tool.icon] || toolColors.default).text,
              '--item-bg': (toolColors[tool.icon] || toolColors.default).bg,
            }"
            @click="selectTool(tool)"
          >
            <span class="drawer-item-icon" v-html="toolSvgIcons[tool.icon] || toolSvgIcons.default"></span>
            <span class="drawer-item-label">{{ tool.label }}</span>
          </button>
        </div>

        <!-- Detail strip -->
        <div v-if="selectedToolData()" class="detail-strip">
          <div class="detail-header">
            <span class="detail-icon" v-html="toolSvgIcons[selectedToolData().icon] || toolSvgIcons.default"></span>
            <span class="detail-name">{{ selectedToolData().label }}</span>
          </div>
          <p class="detail-desc">{{ selectedToolData().description }}</p>
          <div class="detail-examples">
            <button
              v-for="(ex, idx) in (toolExamples[selectedToolData().icon] || toolExamples.default)"
              :key="idx"
              class="example-chip"
              :disabled="isLoading"
              @click="sendExample(ex)"
            >{{ ex }}</button>
          </div>
        </div>
      </div>
    </div>

    <div class="input-container">
      <input
        v-model="inputQuery"
        @keyup.enter="handleSend"
        placeholder="输入问题，或从上方选择工具..."
        :disabled="isLoading"
      />
      <button @click="handleSend" :disabled="isLoading || !inputQuery.trim()">发送</button>
    </div>

    <!-- 引用详情模态框 -->
    <div v-if="showCitationModal" class="citation-modal-overlay" @click.self="showCitationModal = false">
      <div class="citation-modal">
        <div class="modal-header">
          <h3>引用详情</h3>
          <button class="close-btn" @click="showCitationModal = false">×</button>
        </div>
        <div class="modal-content">
          <div v-if="currentCitation">
            <p><strong>文件：</strong>{{ currentCitation.filename }}</p>
            <p><strong>分块索引：</strong>{{ currentCitation.chunkIndex }}</p>
            <div class="citation-content">
              <h4>原文内容：</h4>
              <pre>{{ currentCitation.content }}</pre>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.chat-wrapper {
  background: var(--surface-color);
  border-radius: 0;
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
  position: relative;
}

/* Model Selector Styles */
.model-selector-container {
  display: flex;
  justify-content: center;
  padding: 0.45rem 0;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
  background: rgba(15, 23, 42, 0.3);
  flex-shrink: 0;
}

.model-selector-pill {
  display: flex;
  background: rgba(0, 0, 0, 0.2);
  padding: 3px;
  border-radius: 20px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  gap: 2px;
}

.model-btn {
  border: none;
  background: transparent;
  color: var(--text-secondary);
  padding: 4px 12px;
  border-radius: 16px;
  font-size: 0.75rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  gap: 4px;
}

.model-btn:hover:not(.active) {
  color: var(--text-primary);
  background: rgba(255, 255, 255, 0.05);
}

.model-btn.active {
  background: var(--accent-color);
  color: white;
  box-shadow: 0 2px 8px rgba(59, 130, 246, 0.35);
}

.model-btn .icon {
  font-size: 0.8rem;
}

.chat-container {
  flex: 1;
  overflow-y: auto;
  padding: 0.75rem;
  display: flex;
  flex-direction: column;
  gap: 0.6rem;
  scroll-behavior: smooth;
}

.message-row { display: flex; width: 100%; }
.row-user { justify-content: flex-end; }
.row-ai  { justify-content: flex-start; }

.message-bubble {
  max-width: 90%;
  padding: 0.55rem 0.75rem;
  border-radius: 10px;
  line-height: 1.55;
  font-size: 0.82rem;
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

/* ─── Tool Drawer ─── */
.tool-drawer {
  flex-shrink: 0;
  border-top: 1px solid rgba(255, 255, 255, 0.06);
  background: rgba(15, 23, 42, 0.55);
}

.drawer-toggle {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 0.4rem;
  padding: 0.5rem 0.75rem;
  border: none;
  background: transparent;
  color: var(--text-secondary);
  font-size: 0.82rem;
  font-weight: 500;
  cursor: pointer;
  transition: color 0.15s;
}

.drawer-toggle:hover { color: var(--text-primary); }
.drawer-toggle-icon { font-size: 0.8rem; }

.drawer-arrow {
  margin-left: auto;
  font-size: 0.7rem;
  transition: transform 0.2s;
}

.drawer-arrow.open { transform: rotate(180deg); }

.drawer-body {
  padding: 0 0.6rem 0.5rem;
}

.drawer-list {
  display: flex;
  gap: 0.35rem;
  flex-wrap: wrap;
}

.drawer-item {
  display: flex;
  align-items: center;
  gap: 0.35rem;
  padding: 0.38rem 0.7rem;
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 6px;
  background: rgba(255, 255, 255, 0.03);
  color: var(--text-secondary);
  font-size: 0.8rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s;
}

.drawer-item:hover {
  border-color: var(--item-border);
  color: var(--item-text);
  background: var(--item-bg);
}

.drawer-item.active {
  border-color: var(--item-border);
  color: var(--item-text);
  background: var(--item-bg);
  box-shadow: 0 0 0 1px var(--item-border);
}

.drawer-item-icon { display: flex; align-items: center; }
.drawer-item-icon :deep(svg) { width: 14px; height: 14px; }

.drawer-item-label { white-space: nowrap; }

/* ─── Detail Strip ─── */
.detail-strip {
  margin-top: 0.45rem;
  padding: 0.5rem 0.6rem;
  border-radius: 6px;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.08);
  animation: fadeSlideIn 0.15s ease-out;
}

.detail-header {
  display: flex;
  align-items: center;
  gap: 0.35rem;
  font-size: 0.84rem;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 0.25rem;
}

.detail-icon { display: flex; align-items: center; }
.detail-icon :deep(svg) { width: 15px; height: 15px; }

.detail-name { letter-spacing: 0.01em; }

.detail-desc {
  margin: 0;
  font-size: 0.76rem;
  color: var(--text-secondary);
  line-height: 1.5;
  margin-bottom: 0.4rem;
}

.detail-examples {
  display: flex;
  flex-wrap: wrap;
  gap: 0.3rem;
}

.example-chip {
  padding: 0.25rem 0.55rem;
  border: 1px solid rgba(59, 130, 246, 0.3);
  border-radius: 12px;
  background: rgba(59, 130, 246, 0.08);
  color: #93c5fd;
  font-size: 0.74rem;
  cursor: pointer;
  transition: all 0.15s;
  white-space: nowrap;
}

.example-chip:hover:not(:disabled) {
  background: rgba(59, 130, 246, 0.2);
  border-color: rgba(59, 130, 246, 0.5);
  color: #bfdbfe;
}

.example-chip:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

@keyframes fadeSlideIn {
  from { opacity: 0; transform: translateY(-4px); }
  to   { opacity: 1; transform: translateY(0); }
}

/* Thought / Reasoning Styles */
.thought-container {
  background: rgba(255, 255, 255, 0.03);
  border-left: 2px solid var(--accent-color);
  border-radius: 4px;
  margin: 0.5rem 0 1rem 0;
  padding: 0.8rem;
  font-size: 0.85rem;
  color: var(--text-secondary);
  animation: fadeIn 0.5s ease-out;
}

.thought-header {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 6px;
  font-weight: 600;
  color: var(--accent-color);
  opacity: 0.9;
}

.thought-icon { font-size: 0.9rem; }

.thought-content {
  white-space: pre-wrap;
  font-style: italic;
  line-height: 1.5;
  opacity: 0.8;
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
  padding: 0.5rem 0.6rem;
  background: rgba(15, 23, 42, 0.5);
  border-top: 1px solid var(--tool-border);
  flex-shrink: 0;
}

.input-container input {
  flex: 1;
  background: var(--bg-color);
  border: 1px solid var(--tool-border);
  color: var(--text-primary);
  padding: 0.5rem 0.8rem;
  border-radius: 16px;
  font-size: 0.82rem;
  outline: none;
  transition: all 0.2s;
}

.input-container input:focus {
  border-color: var(--accent-color);
  box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.25);
}

.input-container button {
  background: var(--accent-color);
  color: white;
  border: none;
  padding: 0 1rem;
  margin-left: 0.5rem;
  border-radius: 16px;
  font-size: 0.8rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s;
}

.input-container button:hover:not(:disabled) {
  background: var(--accent-hover);
  transform: translateY(-1px);
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

/* 引用角标样式 */
.citation-link {
  color: #4f46e5;
  text-decoration: underline;
  cursor: pointer;
  font-size: 0.8em;
  margin: 0 2px;
}

.citation-link:hover {
  color: #4338ca;
}

/* 引用模态框样式 */
.citation-modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.citation-modal {
  background: white;
  border-radius: 8px;
  width: 600px;
  max-width: 90%;
  max-height: 80%;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.modal-header {
  padding: 1rem;
  border-bottom: 1px solid #e5e7eb;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.modal-header h3 {
  margin: 0;
  color: #374151;
}

.close-btn {
  background: none;
  border: none;
  font-size: 1.5rem;
  cursor: pointer;
  color: #6b7280;
}

.modal-content {
  padding: 1rem;
  flex: 1;
  overflow-y: auto;
}

.citation-content {
  margin-top: 1rem;
  padding: 1rem;
  background: #f9fafb;
  border-radius: 6px;
  border: 1px solid #e5e7eb;
}

.citation-content h4 {
  margin: 0 0 0.5rem 0;
  color: #374151;
}

.citation-content pre {
  white-space: pre-wrap;
  word-wrap: break-word;
  font-family: inherit;
  line-height: 1.5;
  margin: 0;
}
</style>
