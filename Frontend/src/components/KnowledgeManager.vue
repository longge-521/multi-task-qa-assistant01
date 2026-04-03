<template>
  <div class="rag-lab-container">
    <!-- Sidebar -->
    <aside class="sidebar-nav">
      <div class="brand">
        <div class="logo-box">
          <img
            v-if="!brandLogoError"
            :src="brandLogoSrc"
            alt="RAG Flow Lab"
            class="brand-logo"
            @error="onBrandLogoError"
          />
          <span v-else class="brand-fallback">R</span>
        </div>
        <h2 class="brand-name">RAG Flow Lab</h2>
      </div>

      <nav class="nav-links">
        <div
          v-for="s in sidebarSteps"
          :key="s.id"
          class="nav-item"
          :class="{ active: currentView === s.id }"
          @click="currentView = s.id"
        >
          <span class="nav-icon">{{ s.icon }}</span>
          <span class="nav-text">{{ s.label }}</span>
        </div>
      </nav>

      <div class="sidebar-footer">
        <button class="pipeline-btn" @click="showPipelineModal = true" :disabled="uploadedRawFiles.length === 0">
          <span class="pipeline-icon">⚡</span>
          一键处理
        </button>
      </div>
    </aside>

    <!-- Main Content -->
    <main class="main-content">
      <header class="content-header">
        <h1 class="page-title">{{ currentStepLabel }}</h1>
        <div class="header-utility">
          <div class="stats-badges">
            <div class="stats-item">
              <span class="stats-count" style="color: #e2e8f0">{{ files.length }}</span>
              <span class="stats-label">总计</span>
            </div>
            <div class="stats-item" v-for="s in visibleStats" :key="s.label">
              <span class="stats-count" :style="{ color: s.color }">{{ s.count }}</span>
              <span class="stats-label">{{ s.label }}</span>
            </div>
          </div>
          <div class="status-badge">
            <span class="dot" :class="{ pulse: processing }"></span>
            {{ processing ? processingMsg : '已就绪' }}
          </div>
        </div>
      </header>

      <div class="workspace-layout">
        <!-- Step Config Panel -->
        <section class="config-panel glass">
          <div class="panel-inner">

            <!-- Step 1: Load File -->
            <div v-if="currentView === 'load'" class="step-form">
              <div class="form-group">
                <label>选择文件</label>
                <div class="upload-zone" @click="triggerUpload" @dragover.prevent @drop.prevent="handleDrop">
                  <span class="upload-icon">📁</span>
                  <p v-if="!selectedFilename">点击或拖拽上传 PDF / Word / TXT</p>
                  <p v-else class="selected-file">{{ selectedFilename }}</p>
                </div>
                <input type="file" ref="fileInput" @change="handleFileUpload" accept=".pdf,.txt,.md,.xlsx,.xls" style="display:none" />
              </div>
              <div class="form-group">
                <label>加载解析器</label>
                <select v-model="config.loader_type">
                  <option value="PyMuPDF">PyMuPDF (推荐 - 高精度)</option>
                  <option value="PyPDF">PyPDF (轻量级)</option>
                </select>
              </div>
              <button class="primary-btn" @click="runParse" :disabled="!selectedFilename || processing">
                {{ processing ? '解析中...' : '加载并解析文件' }}
              </button>
            </div>

            <!-- Step 2: Chunking -->
            <div v-else-if="currentView === 'chunk'" class="step-form">
              <div class="form-group">
                <label>选择已解析文档</label>
                <select v-model="selectedFilename">
                  <option value="" disabled>请选择文档</option>
                  <option v-for="f in parsedFiles" :key="f.filename" :value="f.filename">{{ f.filename }}</option>
                </select>
              </div>
              <div class="form-group">
                <label>切块方式</label>
                <select v-model="config.strategy">
                  <option value="recursive">递归切分 (Recursive)</option>
                  <option value="semantic">语义切分 (Semantic)</option>
                  <option value="smart">智能中英文切分 (Smart)</option>
                  <option value="page">按页切分</option>
                </select>
              </div>
              <div class="form-row">
                <div class="form-group">
                  <label>块大小</label>
                  <input type="number" v-model="config.chunk_size" step="100" min="100" />
                </div>
                <div class="form-group">
                  <label>重叠度</label>
                  <input type="number" v-model="config.chunk_overlap" step="10" min="0" />
                </div>
              </div>
              <button class="primary-btn" @click="runChunk" :disabled="!selectedFilename || processing">
                {{ processing ? '切块中...' : '开始文档切块' }}
              </button>
            </div>

            <!-- Step 3: Embedding -->
            <div v-else-if="currentView === 'embedding'" class="step-form">
              <div class="form-group">
                <label>选择已切块文档</label>
                <select v-model="selectedFilename">
                  <option value="" disabled>请选择文档</option>
                  <option v-for="f in chunkedFiles" :key="f.filename" :value="f.filename">{{ f.filename }}</option>
                </select>
              </div>
              <div class="form-group">
                <label>Embedding 提供商</label>
                <select v-model="config.embedding_provider">
                  <option value="HuggingFace">HuggingFace (本地/BGE)</option>
                  <option value="OpenAI">OpenAI / DeepSeek</option>
                </select>
              </div>
              <div class="form-group">
                <label>模型选择</label>
                <select v-model="config.embedding_model">
                  <option value="BAAI/bge-m3">bge-m3 (全能型，推荐)</option>
                  <option value="BAAI/bge-small-zh-v1.5">bge-small-zh (轻量中文)</option>
                  <option value="text-embedding-3-small">text-embedding-3-small</option>
                </select>
              </div>
              <div class="form-group">
                <label>嵌入方式</label>
                <select v-model="config.embedding_mode">
                  <option value="dense">dense（密集）</option>
                  <option value="sparse">sparse（稀疏）</option>
                  <option value="hybrid">hybrid（混合）</option>
                </select>
              </div>
              <div class="form-group">
                <label>目标向量维度（可选）</label>
                <input type="number" v-model.number="config.vector_dimension" min="1" placeholder="例如 1024" />
              </div>
              <button class="primary-btn" @click="runEmbedding" :disabled="!selectedFilename || processing">
                {{ processing ? '向量化计算中...' : '开始向量化' }}
              </button>
            </div>

            <!-- Step 4: Index -->
            <div v-else-if="currentView === 'index'" class="step-form">
              <div class="form-group">
                <label>选择待入库文档</label>
                <select v-model="selectedFilename">
                  <option value="" disabled>请选择文档</option>
                  <option v-for="f in embeddingReadyFiles" :key="f.filename" :value="f.filename">{{ f.filename }}</option>
                </select>
              </div>
              <div class="form-group">
                <label>向量数据库</label>
                <select v-model="config.db_type">
                  <option value="FAISS">FAISS (本地高性能)</option>
                  <option value="Chroma">Chroma (易用存储)</option>
                </select>
              </div>
              <div class="form-group">
                <label>数据库名称 / Collection</label>
                <input type="text" v-model="config.db_name" placeholder="default" />
              </div>
              <button class="primary-btn" @click="runIndex" :disabled="!selectedFilename || processing">
                {{ processing ? '入库中...' : '写入向量数据库' }}
              </button>
            </div>

          </div>
        </section>

        <!-- Preview & Management Area -->
        <section class="display-area">
          <div class="tabs-header">
            <button
              class="tab-btn"
              :class="{ active: activeTab === 'preview' }"
              @click="activeTab = 'preview'"
            >数据预览</button>
            <button
              class="tab-btn"
              :class="{ active: activeTab === 'manage' }"
              @click="activeTab = 'manage'"
            >文档管理</button>
          </div>

          <div class="tab-viewport glass">
            <!-- Tab: Preview -->
            <div v-if="activeTab === 'preview'" class="preview-container">
              <div v-if="!previewData" class="empty-state">
                <div class="empty-icon">📋</div>
                <p>请在左侧选择文件或执行操作以预览数据</p>
              </div>
              <div v-else>
                <!-- Stage sub-tabs -->
                <div class="stage-tabs">
                  <button
                    v-for="st in availablePreviewStages"
                    :key="st.key"
                    class="stage-tab-btn"
                    :class="{ active: previewStage === st.key }"
                    @click="previewStage = st.key"
                  >{{ st.icon }} {{ st.label }}</button>
                </div>

                <div class="preview-scroller">
                  <!-- Parsed content -->
                  <div v-if="previewStage === 'parsed' && previewData.content">
                    <h3 class="preview-title">📥 解析原文</h3>
                    <div class="code-block">{{ previewData.content }}</div>
                  </div>

                  <!-- Chunk results -->
                  <div v-if="previewStage === 'chunked' && previewData.chunks && previewData.chunks.length">
                    <h3 class="preview-title">✂️ 分块结果 ({{ previewData.chunks.length }} 个)</h3>
                    <div class="preview-toolbar">
                      <input
                        v-model.trim="chunkSearchKeyword"
                        class="search-input"
                        placeholder="搜索分块内容..."
                      />
                      <div class="toolbar-info">显示 {{ pagedChunks.length }} / {{ filteredChunks.length }}</div>
                    </div>
                    <div class="split-preview">
                      <div class="split-list">
                        <button
                          v-for="item in pagedChunks"
                          :key="item.displayIndex"
                          class="split-list-item"
                          :class="{ active: selectedChunkIndex === item.displayIndex }"
                          @click="selectedChunkIndex = item.displayIndex"
                        >
                          <div class="item-title">#{{ item.displayIndex + 1 }}</div>
                          <div class="item-snippet">{{ item.content.slice(0, 100) }}</div>
                          <div class="item-meta">{{ item.content.length }} 字</div>
                        </button>
                      </div>
                      <div class="split-detail" v-if="selectedChunk">
                        <div class="detail-header">
                          <strong>分块 #{{ selectedChunkIndex + 1 }}</strong>
                          <div class="detail-actions">
                            <button class="tiny-btn" @click="prevChunk" :disabled="!hasPrevChunk">上一块</button>
                            <button class="tiny-btn" @click="nextChunk" :disabled="!hasNextChunk">下一块</button>
                            <button class="tiny-btn" @click="openFullscreenPreview('chunk')">全屏预览</button>
                            <button class="tiny-btn" @click="copyText(selectedChunk.content)">复制全文</button>
                          </div>
                        </div>
                        <div class="detail-content">{{ selectedChunk.content }}</div>
                        <div class="detail-json">
                          <div class="detail-json-title">Metadata</div>
                          <pre>{{ prettyJson(selectedChunk.metadata) }}</pre>
                        </div>
                      </div>
                    </div>
                    <div class="pager" v-if="filteredChunks.length > chunkPageSize">
                      <button class="tiny-btn" :disabled="chunkPage <= 1" @click="chunkPage--">上一页</button>
                      <span>第 {{ chunkPage }} / {{ chunkPageCount }} 页</span>
                      <button class="tiny-btn" :disabled="chunkPage >= chunkPageCount" @click="chunkPage++">下一页</button>
                    </div>
                  </div>

                  <!-- Embedding results -->
                  <div v-if="previewStage === 'embedding' && previewData.embedding">
                    <h3 class="preview-title">🧠 向量化数据</h3>
                    <div class="embedding-meta">
                      <div class="meta-row"><span class="meta-label">嵌入方式</span><span class="meta-value">{{ previewData.embedding.embedding_mode || 'dense' }}</span></div>
                      <div class="meta-row"><span class="meta-label">模型</span><span class="meta-value">{{ previewData.embedding.embedding_model }}</span></div>
                      <div class="meta-row"><span class="meta-label">提供商</span><span class="meta-value">{{ previewData.embedding.embedding_provider }}</span></div>
                      <div class="meta-row"><span class="meta-label">目标维度</span><span class="meta-value">{{ previewData.embedding.requested_vector_dimension || '自动' }}</span></div>
                      <div class="meta-row"><span class="meta-label">向量维度</span><span class="meta-value">{{ previewData.embedding.vector_dimension }}</span></div>
                      <div class="meta-row"><span class="meta-label">分块数</span><span class="meta-value">{{ previewData.embedding.count }}</span></div>
                      <div class="meta-row"><span class="meta-label">创建时间</span><span class="meta-value">{{ previewData.embedding.created_at }}</span></div>
                    </div>
                    <div class="preview-toolbar">
                      <input
                        v-model.trim="embeddingSearchKeyword"
                        class="search-input"
                        placeholder="搜索向量分块内容..."
                      />
                      <div class="toolbar-info">显示 {{ pagedEmbeddingItems.length }} / {{ filteredEmbeddingItems.length }}</div>
                    </div>
                    <div class="split-preview">
                      <div class="split-list">
                        <button
                          v-for="item in pagedEmbeddingItems"
                          :key="item.chunk_index"
                          class="split-list-item"
                          :class="{ active: selectedEmbeddingIndex === item.chunk_index }"
                          @click="selectedEmbeddingIndex = item.chunk_index"
                        >
                          <div class="item-title">#{{ item.chunk_index + 1 }}</div>
                          <div class="item-snippet">{{ item.content.slice(0, 100) }}</div>
                          <div class="item-meta">{{ item.dimension }} 维</div>
                        </button>
                      </div>
                      <div class="split-detail" v-if="selectedEmbeddingItem">
                        <div class="detail-header">
                          <strong>向量块 #{{ selectedEmbeddingItem.chunk_index + 1 }}</strong>
                          <div class="detail-actions">
                            <button class="tiny-btn" @click="prevEmbedding" :disabled="!hasPrevEmbedding">上一块</button>
                            <button class="tiny-btn" @click="nextEmbedding" :disabled="!hasNextEmbedding">下一块</button>
                            <button class="tiny-btn" @click="openFullscreenPreview('embedding')">全屏预览</button>
                            <button class="tiny-btn" @click="copyText(selectedEmbeddingItem.content)">复制内容</button>
                          </div>
                        </div>
                        <div class="detail-content">{{ selectedEmbeddingItem.content }}</div>
                        <div class="vector-preview">
                          <span class="vec-label">向量 ({{ selectedEmbeddingItem.dimension }}d):</span>
                          <span class="vec-nums">[{{ selectedEmbeddingItem.vector_sample.map(v => Number(v).toFixed(4)).join(', ') }}, ...]</span>
                        </div>
                      </div>
                    </div>
                    <div class="pager" v-if="filteredEmbeddingItems.length > embeddingPageSize">
                      <button class="tiny-btn" :disabled="embeddingPage <= 1" @click="embeddingPage--">上一页</button>
                      <span>第 {{ embeddingPage }} / {{ embeddingPageCount }} 页</span>
                      <button class="tiny-btn" :disabled="embeddingPage >= embeddingPageCount" @click="embeddingPage++">下一页</button>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <!-- Tab: Management -->
            <div v-if="activeTab === 'manage'" class="manage-container">
              <div v-if="files.length === 0" class="empty-state">
                <div class="empty-icon">📂</div>
                <p>暂无文档，请先上传文件</p>
              </div>
              <div v-else class="file-card-list">
                <div v-for="file in files" :key="file.filename" class="file-card">
                  <div class="file-card-top">
                    <div class="file-card-info">
                      <span class="file-icon-lg">{{ getFileIcon(file.filename) }}</span>
                      <div class="file-card-meta">
                        <span class="file-card-name" :title="file.filename">{{ file.filename }}</span>
                        <span class="file-card-size">{{ formatSize(file.size) }}</span>
                      </div>
                    </div>
                    <div class="file-card-actions">
                      <button class="action-btn view" title="预览" @click="loadPreview(file); activeTab = 'preview'">
                        <span>👁️</span><span class="action-label">预览</span>
                      </button>
                      <button class="action-btn process" title="一键处理" @click="runSinglePipeline(file.filename)" :disabled="file.stage === 'indexed' || processing">
                        <span>⚡</span><span class="action-label">处理</span>
                      </button>
                      <button class="action-btn delete" title="删除" @click="deleteFile(file.filename)">
                        <span>🗑️</span><span class="action-label">删除</span>
                      </button>
                    </div>
                  </div>
                  <div class="file-card-bottom">
                    <div class="progress-bar-track">
                      <div class="progress-bar-fill" :style="{ width: getStagePercent(file.stage) + '%' }" :class="'fill-' + file.stage"></div>
                    </div>
                    <div class="progress-labels">
                      <span class="stage-label" :class="file.stage">{{ getStageLabel(file.stage) }}</span>
                      <span class="progress-pct">{{ getStagePercent(file.stage) }}%</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>
      </div>
    </main>

    <!-- Pipeline Modal -->
    <Teleport to="body">
      <div v-if="showPipelineModal" class="modal-overlay" @click.self="showPipelineModal = false">
        <div class="modal-card glass">
          <h2 class="modal-title">⚡ 一键批量处理</h2>
          <p class="modal-desc">将对所有未入库的文档执行完整流水线：解析 → 切块 → 向量化 → 写入向量库</p>

          <div class="modal-config">
            <div class="form-row">
              <div class="form-group">
                <label>切块方式</label>
                <select v-model="config.strategy">
                  <option value="recursive">递归切分</option>
                  <option value="smart">智能中英文切分</option>
                </select>
              </div>
              <div class="form-group">
                <label>块大小</label>
                <input type="number" v-model="config.chunk_size" step="100" min="100" />
              </div>
            </div>
            <div class="form-row">
              <div class="form-group">
                <label>Embedding 模型</label>
                <select v-model="config.embedding_model">
                  <option value="BAAI/bge-m3">bge-m3 (推荐)</option>
                  <option value="BAAI/bge-small-zh-v1.5">bge-small-zh</option>
                </select>
              </div>
                <div class="form-group">
                  <label>嵌入方式</label>
                  <select v-model="config.embedding_mode">
                    <option value="dense">dense</option>
                    <option value="sparse">sparse</option>
                    <option value="hybrid">hybrid</option>
                  </select>
                </div>
              <div class="form-group">
                <label>向量数据库</label>
                <select v-model="config.db_type">
                  <option value="FAISS">FAISS</option>
                  <option value="Chroma">Chroma</option>
                </select>
              </div>
            </div>
          </div>

          <div class="modal-files">
            <p class="modal-files-title">待处理文档 ({{ uploadedRawFiles.length }})</p>
            <div class="modal-file-list">
              <div v-for="f in pendingFiles" :key="f.filename" class="modal-file-item">
                <span class="file-icon">{{ getFileIcon(f.filename) }}</span>
                <span>{{ f.filename }}</span>
                <span class="stage-label" :class="f.stage">{{ getStageLabel(f.stage) }}</span>
              </div>
            </div>
          </div>

          <div class="modal-actions">
            <button class="secondary-btn" @click="showPipelineModal = false">取消</button>
            <button class="primary-btn" @click="runBatchPipeline" :disabled="processing || pendingFiles.length === 0">
              {{ processing ? '处理中...' : '开始处理' }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- Fullscreen preview modal -->
    <Teleport to="body">
      <div v-if="showFullscreenPreview" class="modal-overlay" @click.self="showFullscreenPreview = false">
        <div class="modal-card glass fullscreen-modal-card">
          <div class="fullscreen-modal-header">
            <h2 class="modal-title">{{ fullscreenTitle }}</h2>
            <div class="detail-actions">
              <button class="tiny-btn" @click="copyText(fullscreenContent)">复制全文</button>
              <button class="secondary-btn" @click="showFullscreenPreview = false">关闭</button>
            </div>
          </div>
          <div class="fullscreen-modal-body">
            <div class="detail-content fullscreen-content">{{ fullscreenContent }}</div>
            <div class="detail-json" v-if="fullscreenMeta">
              <div class="detail-json-title">Metadata</div>
              <pre>{{ prettyJson(fullscreenMeta) }}</pre>
            </div>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- Global Processing Overlay -->
    <div v-if="processing" class="global-loader">
      <div class="loader-content">
        <div class="spinner"></div>
        <p>{{ processingMsg }}</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, computed, reactive } from 'vue'
import * as loadService from '../services/loadService'
import * as chunkService from '../services/chunkService'
import * as embeddingService from '../services/embeddingService'
import * as indexService from '../services/indexService'
import api from '../services/api'
import brandLogo from '../assets/rag-lab-logo.svg'

const fileInput = ref(null)

const currentView = ref('load')
const activeTab = ref('manage')
const processing = ref(false)
const processingMsg = ref('处理中...')
const selectedFilename = ref('')
const showPipelineModal = ref(false)
const previewStage = ref('parsed')
const chunkSearchKeyword = ref('')
const embeddingSearchKeyword = ref('')
const selectedChunkIndex = ref(0)
const selectedEmbeddingIndex = ref(0)
const chunkPage = ref(1)
const embeddingPage = ref(1)
const chunkPageSize = 12
const embeddingPageSize = 12
const showFullscreenPreview = ref(false)
const fullscreenTitle = ref('')
const fullscreenContent = ref('')
const fullscreenMeta = ref(null)

const sidebarSteps = [
  { id: 'load', icon: '📥', label: '加载文件' },
  { id: 'chunk', icon: '✂️', label: '文档切块' },
  { id: 'embedding', icon: '🧠', label: '向量化' },
  { id: 'index', icon: '💾', label: '写入向量库' }
]

const pipelineStages = [
  { key: 'raw', label: '已上传' },
  { key: 'parsed', label: '已解析' },
  { key: 'chunked', label: '已分块' },
  { key: 'embedding_ready', label: '已向量化' },
  { key: 'indexed', label: '已入库' }
]

const stageOrder = { raw: 0, parsed: 1, chunked: 2, embedding_ready: 3, indexed: 4 }

const config = reactive({
  loader_type: 'PyMuPDF',
  use_ocr: false,
  strategy: 'recursive',
  chunk_size: 600,
  chunk_overlap: 60,
  embedding_provider: 'HuggingFace',
  embedding_model: 'BAAI/bge-m3',
  embedding_mode: 'dense',
  vector_dimension: null,
  db_type: 'FAISS',
  db_name: 'default'
})

const previewData = ref(null)
const files = ref([])
const brandLogoSrc = brandLogo
const brandLogoError = ref(false)

const onBrandLogoError = () => {
  brandLogoError.value = true
}

const availablePreviewStages = computed(() => {
  if (!previewData.value) return []
  const stages = []
  if (previewData.value.content) stages.push({ key: 'parsed', icon: '📥', label: '解析数据' })
  if (previewData.value.chunks?.length) stages.push({ key: 'chunked', icon: '✂️', label: '分块数据' })
  if (previewData.value.embedding) stages.push({ key: 'embedding', icon: '🧠', label: '向量数据' })
  return stages
})

const filteredChunks = computed(() => {
  const chunks = previewData.value?.chunks || []
  const kw = chunkSearchKeyword.value.toLowerCase()
  if (!kw) return chunks.map((c, idx) => ({ ...c, displayIndex: idx }))
  return chunks
    .map((c, idx) => ({ ...c, displayIndex: idx }))
    .filter(c => (c.content || '').toLowerCase().includes(kw))
})

const chunkPageCount = computed(() => {
  return Math.max(1, Math.ceil(filteredChunks.value.length / chunkPageSize))
})

const pagedChunks = computed(() => {
  if (chunkPage.value > chunkPageCount.value) chunkPage.value = chunkPageCount.value
  const start = (chunkPage.value - 1) * chunkPageSize
  return filteredChunks.value.slice(start, start + chunkPageSize)
})

const selectedChunk = computed(() => {
  const list = filteredChunks.value
  if (!list.length) return null
  const exact = list.find(c => c.displayIndex === selectedChunkIndex.value)
  return exact || list[0]
})

const selectedChunkDisplayIndex = computed(() => {
  if (!selectedChunk.value) return -1
  return filteredChunks.value.findIndex(c => c.displayIndex === selectedChunk.value.displayIndex)
})

const hasPrevChunk = computed(() => selectedChunkDisplayIndex.value > 0)
const hasNextChunk = computed(() => selectedChunkDisplayIndex.value >= 0 && selectedChunkDisplayIndex.value < filteredChunks.value.length - 1)

const filteredEmbeddingItems = computed(() => {
  const items = previewData.value?.embedding?.items || []
  const kw = embeddingSearchKeyword.value.toLowerCase()
  if (!kw) return items
  return items.filter(i => (i.content || '').toLowerCase().includes(kw))
})

const embeddingPageCount = computed(() => {
  return Math.max(1, Math.ceil(filteredEmbeddingItems.value.length / embeddingPageSize))
})

const pagedEmbeddingItems = computed(() => {
  if (embeddingPage.value > embeddingPageCount.value) embeddingPage.value = embeddingPageCount.value
  const start = (embeddingPage.value - 1) * embeddingPageSize
  return filteredEmbeddingItems.value.slice(start, start + embeddingPageSize)
})

const selectedEmbeddingItem = computed(() => {
  const list = filteredEmbeddingItems.value
  if (!list.length) return null
  const exact = list.find(i => i.chunk_index === selectedEmbeddingIndex.value)
  return exact || list[0]
})

const selectedEmbeddingDisplayIndex = computed(() => {
  if (!selectedEmbeddingItem.value) return -1
  return filteredEmbeddingItems.value.findIndex(i => i.chunk_index === selectedEmbeddingItem.value.chunk_index)
})

const hasPrevEmbedding = computed(() => selectedEmbeddingDisplayIndex.value > 0)
const hasNextEmbedding = computed(() => selectedEmbeddingDisplayIndex.value >= 0 && selectedEmbeddingDisplayIndex.value < filteredEmbeddingItems.value.length - 1)

const parsedFiles = computed(() => files.value.filter(f => stageOrder[f.stage] >= 1))
const chunkedFiles = computed(() => files.value.filter(f => stageOrder[f.stage] >= 2))
const embeddingReadyFiles = computed(() => files.value.filter(f => stageOrder[f.stage] >= 3))
const uploadedRawFiles = computed(() => files.value.filter(f => f.stage !== 'indexed'))
const pendingFiles = computed(() => files.value.filter(f => f.stage !== 'indexed'))

const currentStepLabel = computed(() => sidebarSteps.find(s => s.id === currentView.value)?.label)

const stageStats = computed(() => {
  const counts = { raw: 0, parsed: 0, chunked: 0, embedding_ready: 0, indexed: 0 }
  files.value.forEach(f => {
    if (f.stage in counts) counts[f.stage]++
  })
  return [
    { label: '待处理', count: counts.raw, color: '#94a3b8' },
    { label: '已解析', count: counts.parsed, color: '#f59e0b' },
    { label: '已分块', count: counts.chunked, color: '#3b82f6' },
    { label: '已向量化', count: counts.embedding_ready, color: '#a855f7' },
    { label: '已入库', count: counts.indexed, color: '#10b981' }
  ]
})

const visibleStats = computed(() => stageStats.value.filter(s => s.count > 0))

function isStageReached(fileStage, targetStage) {
  return (stageOrder[fileStage] || 0) >= (stageOrder[targetStage] || 0)
}

const fetchData = async () => {
  try {
    files.value = await loadService.getFiles()
  } catch (e) {
    console.error("Fetch failed", e)
  }
}

const triggerUpload = () => fileInput.value.click()

const handleDrop = async (e) => {
  const f = e.dataTransfer.files[0]
  if (!f) return
  processing.value = true
  processingMsg.value = `正在上传 ${f.name}...`
  const fd = new FormData()
  fd.append('file', f)
  try {
    const data = await loadService.uploadFile(fd)
    selectedFilename.value = data.filename
    await fetchData()
  } catch (e) {
    alert("上传失败: " + (e.response?.data?.detail || e.message))
  } finally {
    processing.value = false
  }
}

const handleFileUpload = async (e) => {
  const f = e.target.files[0]
  if (!f) return
  processing.value = true
  processingMsg.value = `正在上传 ${f.name}...`
  const fd = new FormData()
  fd.append('file', f)
  try {
    const data = await loadService.uploadFile(fd)
    selectedFilename.value = data.filename
    await fetchData()
  } catch (e) {
    alert("上传失败: " + (e.response?.data?.detail || e.message))
  } finally {
    processing.value = false
    e.target.value = ''
  }
}

const loadPreview = async (file) => {
  selectedFilename.value = file.filename
  previewData.value = null
  activeTab.value = 'preview'
  try {
    const [pData, cData, eData] = await Promise.allSettled([
      indexService.getParsedState(file.filename),
      chunkService.getChunkState(file.filename),
      embeddingService.getEmbeddingPreview(file.filename)
    ])
    const parsed = pData.status === 'fulfilled' && !pData.value.error ? pData.value.content : null
    const chunks = cData.status === 'fulfilled' && !cData.value.error ? cData.value.chunks : null
    const embedding = eData.status === 'fulfilled' && !eData.value.error ? eData.value : null

    previewData.value = { content: parsed, chunks, embedding }
    chunkSearchKeyword.value = ''
    embeddingSearchKeyword.value = ''
    chunkPage.value = 1
    embeddingPage.value = 1
    selectedChunkIndex.value = 0
    selectedEmbeddingIndex.value = 0

    if (embedding) previewStage.value = 'embedding'
    else if (chunks?.length) previewStage.value = 'chunked'
    else if (parsed) previewStage.value = 'parsed'
  } catch (e) {
    previewData.value = null
  }
}

const runParse = async () => {
  processing.value = true
  processingMsg.value = `正在解析 ${selectedFilename.value}...`
  try {
    const data = await loadService.parseFile(selectedFilename.value, config.loader_type, config.use_ocr)
    previewData.value = { content: data.result?.content, chunks: null, embedding: null }
    previewStage.value = 'parsed'
    await fetchData()
    activeTab.value = 'preview'
  } catch (e) {
    alert("解析失败: " + (e.response?.data?.detail || e.message))
  } finally {
    processing.value = false
  }
}

const runChunk = async () => {
  processing.value = true
  processingMsg.value = `正在切块 ${selectedFilename.value}...`
  try {
    const data = await chunkService.chunkFile(selectedFilename.value, config.strategy, config.chunk_size, config.chunk_overlap)
    previewData.value = {
      content: previewData.value?.content,
      chunks: data.result?.chunks,
      embedding: null
    }
    previewStage.value = 'chunked'
    await fetchData()
    activeTab.value = 'preview'
  } catch (e) {
    alert("分块失败: " + (e.response?.data?.detail || e.message))
  } finally {
    processing.value = false
  }
}

const runEmbedding = async () => {
  processing.value = true
  processingMsg.value = `正在向量化计算 ${selectedFilename.value}（首次可能需要下载模型）...`
  try {
    await embeddingService.configEmbedding(
      selectedFilename.value,
      config.embedding_provider,
      config.embedding_model,
      config.embedding_mode,
      config.vector_dimension || null
    )
    const eData = await embeddingService.getEmbeddingPreview(selectedFilename.value)
    previewData.value = {
      content: previewData.value?.content,
      chunks: previewData.value?.chunks,
      embedding: eData.error ? null : eData
    }
    previewStage.value = 'embedding'
    await fetchData()
    activeTab.value = 'preview'
  } catch (e) {
    alert("向量化失败: " + (e.response?.data?.detail || e.message))
  } finally {
    processing.value = false
  }
}

const runIndex = async () => {
  processing.value = true
  processingMsg.value = `正在写入向量数据库 ${selectedFilename.value}...`
  try {
    await indexService.indexFile(selectedFilename.value, config.db_type, config.db_name)
    await fetchData()
    alert("入库成功！文档已可用于知识库问答。")
  } catch (e) {
    alert("入库失败: " + (e.response?.data?.detail || e.message))
  } finally {
    processing.value = false
  }
}

const runSinglePipeline = async (filename) => {
  processing.value = true
  processingMsg.value = `正在处理 ${filename}（解析→切块→向量化→入库）...`
  try {
    await api.post(`/knowledge/pipeline/${filename}`, {
      loader_type: config.loader_type,
      use_ocr: config.use_ocr,
      strategy: config.strategy,
      chunk_size: config.chunk_size,
      chunk_overlap: config.chunk_overlap,
      embedding_provider: config.embedding_provider,
      embedding_model: config.embedding_model,
      embedding_mode: config.embedding_mode,
      vector_dimension: config.vector_dimension || null,
      db_type: config.db_type,
      db_name: config.db_name
    }, { timeout: 600000 })
    await fetchData()
  } catch (e) {
    alert("处理失败: " + (e.response?.data?.detail || e.message))
  } finally {
    processing.value = false
  }
}

const runBatchPipeline = async () => {
  showPipelineModal.value = false
  const targets = pendingFiles.value.map(f => f.filename)
  for (let i = 0; i < targets.length; i++) {
    processing.value = true
    processingMsg.value = `正在处理 (${i + 1}/${targets.length}) ${targets[i]}...`
    try {
      await api.post(`/knowledge/pipeline/${targets[i]}`, {
        loader_type: config.loader_type,
        use_ocr: config.use_ocr,
        strategy: config.strategy,
        chunk_size: config.chunk_size,
        chunk_overlap: config.chunk_overlap,
        embedding_provider: config.embedding_provider,
        embedding_model: config.embedding_model,
        embedding_mode: config.embedding_mode,
        vector_dimension: config.vector_dimension || null,
        db_type: config.db_type,
        db_name: config.db_name
      }, { timeout: 600000 })
    } catch (e) {
      alert(`处理 ${targets[i]} 失败: ${e.response?.data?.detail || e.message}`)
    }
  }
  await fetchData()
  processing.value = false
}

const deleteFile = async (filename) => {
  if (!confirm(`确定要删除 "${filename}" 吗？此操作将同时清除关联的解析和向量数据。`)) return
  try {
    await loadService.deleteFile(filename)
    if (selectedFilename.value === filename) {
      selectedFilename.value = ''
      previewData.value = null
    }
    await fetchData()
  } catch (e) {
    alert("删除失败: " + (e.response?.data?.detail || e.message))
  }
}

const getStageLabel = (s) => ({
  raw: '待处理',
  parsed: '已解析',
  chunked: '已分块',
  embedding_ready: '已向量化',
  indexed: '已入库'
}[s] || s)

const getFileIcon = (f) => {
  if (f.endsWith('.pdf')) return '📄'
  if (f.endsWith('.md')) return '📝'
  if (f.endsWith('.txt')) return '📃'
  if (f.endsWith('.xlsx') || f.endsWith('.xls')) return '📊'
  return '📁'
}

const getStagePercent = (stage) => {
  const percents = { raw: 10, parsed: 30, chunked: 55, embedding_ready: 80, indexed: 100 }
  return percents[stage] || 0
}

const formatSize = (bytes) => {
  if (!bytes || bytes === 0) return '—'
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}

const prettyJson = (obj) => {
  if (!obj) return '{}'
  return JSON.stringify(obj, null, 2)
}

const copyText = async (text) => {
  try {
    await navigator.clipboard.writeText(text || '')
    alert('已复制到剪贴板')
  } catch (e) {
    alert('复制失败，请手动复制')
  }
}

const prevChunk = () => {
  if (!hasPrevChunk.value) return
  const target = filteredChunks.value[selectedChunkDisplayIndex.value - 1]
  selectedChunkIndex.value = target.displayIndex
}

const nextChunk = () => {
  if (!hasNextChunk.value) return
  const target = filteredChunks.value[selectedChunkDisplayIndex.value + 1]
  selectedChunkIndex.value = target.displayIndex
}

const prevEmbedding = () => {
  if (!hasPrevEmbedding.value) return
  const target = filteredEmbeddingItems.value[selectedEmbeddingDisplayIndex.value - 1]
  selectedEmbeddingIndex.value = target.chunk_index
}

const nextEmbedding = () => {
  if (!hasNextEmbedding.value) return
  const target = filteredEmbeddingItems.value[selectedEmbeddingDisplayIndex.value + 1]
  selectedEmbeddingIndex.value = target.chunk_index
}

const openFullscreenPreview = (kind) => {
  if (kind === 'chunk' && selectedChunk.value) {
    fullscreenTitle.value = `分块 #${selectedChunk.value.displayIndex + 1} 全文预览`
    fullscreenContent.value = selectedChunk.value.content || ''
    fullscreenMeta.value = selectedChunk.value.metadata || null
    showFullscreenPreview.value = true
    return
  }

  if (kind === 'embedding' && selectedEmbeddingItem.value) {
    fullscreenTitle.value = `向量块 #${selectedEmbeddingItem.value.chunk_index + 1} 全文预览`
    fullscreenContent.value = selectedEmbeddingItem.value.content || ''
    fullscreenMeta.value = {
      chunk_index: selectedEmbeddingItem.value.chunk_index,
      dimension: selectedEmbeddingItem.value.dimension,
      vector_sample: selectedEmbeddingItem.value.vector_sample
    }
    showFullscreenPreview.value = true
  }
}

const isEditableTarget = (target) => {
  if (!target) return false
  const tag = (target.tagName || '').toLowerCase()
  return tag === 'input' || tag === 'textarea' || tag === 'select' || target.isContentEditable
}

const handleKeydown = (e) => {
  if (isEditableTarget(e.target)) return

  if (e.key === 'Escape' && showFullscreenPreview.value) {
    showFullscreenPreview.value = false
    return
  }

  if (activeTab.value !== 'preview') return

  if (previewStage.value === 'chunked') {
    if (e.key === 'ArrowUp') {
      e.preventDefault()
      prevChunk()
    } else if (e.key === 'ArrowDown') {
      e.preventDefault()
      nextChunk()
    }
    return
  }

  if (previewStage.value === 'embedding') {
    if (e.key === 'ArrowUp') {
      e.preventDefault()
      prevEmbedding()
    } else if (e.key === 'ArrowDown') {
      e.preventDefault()
      nextEmbedding()
    }
  }
}

onMounted(() => {
  fetchData()
  window.addEventListener('keydown', handleKeydown)
})

onBeforeUnmount(() => {
  window.removeEventListener('keydown', handleKeydown)
})
</script>

<style scoped>
.rag-lab-container {
  display: flex;
  height: 100%;
  width: 100%;
  background: #0a0f1e;
  color: #e2e8f0;
  font-family: 'Inter', system-ui, sans-serif;
  overflow: hidden;
  border-radius: 12px;
}

/* ===== Sidebar ===== */
.sidebar-nav {
  width: 240px;
  min-width: 240px;
  background: #111827;
  display: flex;
  flex-direction: column;
  border-right: 1px solid rgba(255,255,255,0.05);
}

.brand {
  padding: 1.5rem 1.25rem;
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.logo-box {
  width: 38px;
  height: 38px;
  background: #6366f1;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  box-shadow: 0 0 12px rgba(99, 102, 241, 0.4);
}

.brand-logo { width: 28px; height: 28px; }
.brand-fallback {
  color: #e2e8f0;
  font-weight: 800;
  font-size: 1rem;
}
.brand-name { font-size: 1.1rem; font-weight: 700; color: #fff; white-space: nowrap; }

.nav-links { padding: 0.5rem 0.75rem; flex: 1; }
.nav-item {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.85rem 1rem;
  border-radius: 10px;
  cursor: pointer;
  margin-bottom: 0.25rem;
  transition: all 0.2s;
  color: #94a3b8;
  font-size: 0.9rem;
}

.nav-item:hover { background: rgba(255,255,255,0.05); color: #fff; }
.nav-item.active {
  background: linear-gradient(135deg, rgba(99, 102, 241, 0.2) 0%, rgba(99, 102, 241, 0.05) 100%);
  color: #818cf8;
  border-left: 3px solid #6366f1;
}

.nav-icon { font-size: 1.1rem; }
.nav-text { font-weight: 500; }

.sidebar-footer {
  padding: 1rem 0.75rem;
  border-top: 1px solid rgba(255,255,255,0.05);
}

.pipeline-btn {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  padding: 0.75rem;
  background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
  border: none;
  border-radius: 10px;
  color: #fff;
  font-weight: 600;
  font-size: 0.9rem;
  cursor: pointer;
  transition: all 0.2s;
  box-shadow: 0 4px 12px rgba(245, 158, 11, 0.25);
}

.pipeline-btn:hover:not(:disabled) { transform: translateY(-1px); box-shadow: 0 6px 18px rgba(245, 158, 11, 0.35); }
.pipeline-btn:disabled { opacity: 0.4; cursor: not-allowed; }
.pipeline-icon { font-size: 1.1rem; }

/* ===== Main Content ===== */
.main-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  padding: 1.5rem;
  overflow-y: auto;
  min-width: 0;
}

.content-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.25rem;
  flex-wrap: wrap;
  gap: 0.75rem;
}

.page-title { font-size: 1.5rem; font-weight: 700; color: #fff; }

.header-utility { display: flex; align-items: center; gap: 1rem; }

.stats-badges {
  display: flex;
  gap: 1rem;
}

.stats-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.1rem;
}

.stats-count { font-size: 1.1rem; font-weight: 700; }
.stats-label { font-size: 0.7rem; color: #94a3b8; }

.status-badge {
  background: rgba(16, 185, 129, 0.1);
  color: #10b981;
  padding: 0.4rem 0.85rem;
  border-radius: 99px;
  font-size: 0.8rem;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 0.4rem;
  white-space: nowrap;
}

.dot { width: 7px; height: 7px; background: #10b981; border-radius: 50%; flex-shrink: 0; }
.dot.pulse { animation: pulse 2s infinite; }

@keyframes pulse {
  0% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.4; transform: scale(1.5); }
  100% { opacity: 1; transform: scale(1); }
}

/* ===== Workspace Layout ===== */
.workspace-layout {
  display: grid;
  grid-template-columns: 320px 1fr;
  gap: 1.5rem;
  flex: 1;
  min-height: 0;
}

.glass {
  background: rgba(30, 41, 59, 0.5);
  backdrop-filter: blur(16px);
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 16px;
}

/* ===== Config Panel ===== */
.config-panel { padding: 1.25rem; height: fit-content; }

.form-group { margin-bottom: 1.25rem; }
.form-group label {
  display: block;
  margin-bottom: 0.4rem;
  font-size: 0.8rem;
  font-weight: 600;
  color: #94a3b8;
}

.upload-zone {
  border: 2px dashed rgba(255,255,255,0.1);
  border-radius: 12px;
  padding: 1.75rem 1rem;
  text-align: center;
  cursor: pointer;
  transition: 0.25s;
}

.upload-zone:hover { border-color: #6366f1; background: rgba(99, 102, 241, 0.05); }
.upload-icon { font-size: 1.75rem; display: block; margin-bottom: 0.4rem; }
.selected-file { color: #818cf8; font-weight: 600; word-break: break-all; }

select, input[type="number"], input[type="text"] {
  width: 100%;
  background: #1e293b;
  border: 1px solid rgba(255,255,255,0.1);
  color: #fff;
  padding: 0.65rem 0.85rem;
  border-radius: 8px;
  outline: none;
  font-size: 0.85rem;
  box-sizing: border-box;
}

select:focus, input:focus { border-color: #6366f1; }

.form-row { display: flex; gap: 0.75rem; }
.form-row .form-group { flex: 1; }

.primary-btn {
  width: 100%;
  background: linear-gradient(135deg, #6366f1 0%, #4f46e5 100%);
  color: #fff;
  border: none;
  padding: 0.85rem;
  border-radius: 10px;
  font-weight: 600;
  font-size: 0.9rem;
  cursor: pointer;
  transition: 0.25s;
  box-shadow: 0 4px 12px rgba(79, 70, 229, 0.3);
}

.primary-btn:hover:not(:disabled) { transform: translateY(-1px); box-shadow: 0 6px 20px rgba(79, 70, 229, 0.4); }
.primary-btn:disabled { opacity: 0.45; cursor: not-allowed; }

.secondary-btn {
  padding: 0.85rem 1.5rem;
  background: rgba(255,255,255,0.08);
  color: #e2e8f0;
  border: 1px solid rgba(255,255,255,0.1);
  border-radius: 10px;
  font-weight: 600;
  cursor: pointer;
  transition: 0.2s;
}

.secondary-btn:hover { background: rgba(255,255,255,0.12); }

/* ===== Display Area ===== */
.display-area {
  display: flex;
  flex-direction: column;
  min-width: 0;
  min-height: 0;
}

.tabs-header { display: flex; gap: 0.5rem; margin-bottom: 0.5rem; }
.tab-btn {
  background: transparent;
  border: none;
  color: #94a3b8;
  padding: 0.5rem 1rem;
  font-size: 0.9rem;
  font-weight: 600;
  cursor: pointer;
  transition: 0.2s;
  border-bottom: 2px solid transparent;
}

.tab-btn.active { color: #fff; border-bottom-color: #6366f1; }

.tab-viewport {
  flex: 1;
  padding: 1.25rem;
  overflow: auto;
  min-height: 0;
}

/* ===== Empty State ===== */
.empty-state {
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: #475569;
  text-align: center;
  gap: 0.75rem;
  min-height: 200px;
}

.empty-icon { font-size: 3rem; opacity: 0.5; }

/* ===== Stage Tabs ===== */
.stage-tabs {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 1rem;
  border-bottom: 1px solid rgba(255,255,255,0.06);
  padding-bottom: 0.75rem;
}
.stage-tab-btn {
  background: rgba(255,255,255,0.04);
  border: 1px solid rgba(255,255,255,0.08);
  color: #94a3b8;
  padding: 0.4rem 1rem;
  border-radius: 8px;
  cursor: pointer;
  font-size: 0.82rem;
  font-weight: 600;
  transition: all 0.2s;
}
.stage-tab-btn:hover {
  background: rgba(99,102,241,0.12);
  color: #c7d2fe;
}
.stage-tab-btn.active {
  background: linear-gradient(135deg, #6366f1, #8b5cf6);
  color: #fff;
  border-color: transparent;
  box-shadow: 0 2px 8px rgba(99,102,241,0.3);
}

/* ===== Embedding Meta ===== */
.embedding-meta {
  background: rgba(139,92,246,0.08);
  border: 1px solid rgba(139,92,246,0.2);
  border-radius: 12px;
  padding: 1rem 1.25rem;
  margin-bottom: 1rem;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 0.5rem 1.5rem;
}
.meta-row {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}
.meta-label {
  font-size: 0.75rem;
  color: #a78bfa;
  font-weight: 600;
  white-space: nowrap;
}
.meta-value {
  font-size: 0.8rem;
  color: #e2e8f0;
  font-family: 'Fira Code', monospace;
}

/* ===== Vector Preview ===== */
.embedding-card .vector-preview {
  margin-top: 0.5rem;
  padding-top: 0.5rem;
  border-top: 1px dashed rgba(255,255,255,0.08);
  display: flex;
  flex-wrap: wrap;
  gap: 0.25rem;
  align-items: baseline;
}
.vec-label {
  font-size: 0.7rem;
  color: #a78bfa;
  font-weight: 600;
}
.vec-nums {
  font-size: 0.7rem;
  color: #64748b;
  font-family: 'Fira Code', monospace;
  word-break: break-all;
}

/* ===== Preview ===== */
.preview-scroller { max-width: 100%; }
.preview-toolbar {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  margin-bottom: 0.8rem;
}

.search-input {
  flex: 1;
  max-width: 380px;
  background: #0f172a;
  border: 1px solid rgba(255,255,255,0.08);
  color: #e2e8f0;
  border-radius: 8px;
  padding: 0.55rem 0.75rem;
}

.toolbar-info {
  font-size: 0.75rem;
  color: #94a3b8;
}

.split-preview {
  display: grid;
  grid-template-columns: 320px 1fr;
  gap: 0.85rem;
}

.split-list {
  max-height: 480px;
  overflow-y: auto;
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 10px;
  padding: 0.4rem;
  background: rgba(15,23,42,0.45);
}

.split-list-item {
  width: 100%;
  text-align: left;
  border: 1px solid rgba(255,255,255,0.06);
  background: rgba(255,255,255,0.02);
  border-radius: 8px;
  margin-bottom: 0.45rem;
  padding: 0.55rem 0.65rem;
  color: #e2e8f0;
  cursor: pointer;
}

.split-list-item.active {
  border-color: rgba(99,102,241,0.55);
  background: rgba(99,102,241,0.12);
}

.item-title {
  font-size: 0.78rem;
  color: #c7d2fe;
  font-weight: 700;
}

.item-snippet {
  margin-top: 0.25rem;
  font-size: 0.75rem;
  color: #cbd5e1;
  line-height: 1.35;
  max-height: 2.7em;
  overflow: hidden;
}

.item-meta {
  margin-top: 0.28rem;
  font-size: 0.68rem;
  color: #94a3b8;
}

.split-detail {
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 10px;
  background: rgba(15,23,42,0.45);
  padding: 0.8rem;
  min-height: 420px;
}

.detail-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.65rem;
  gap: 0.6rem;
}

.detail-actions {
  display: flex;
  align-items: center;
  gap: 0.45rem;
  flex-wrap: wrap;
}

.tiny-btn {
  border: 1px solid rgba(255,255,255,0.12);
  border-radius: 6px;
  background: rgba(255,255,255,0.06);
  color: #e2e8f0;
  padding: 0.3rem 0.6rem;
  font-size: 0.72rem;
  cursor: pointer;
}

.tiny-btn:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.detail-content {
  white-space: pre-wrap;
  max-height: 250px;
  overflow-y: auto;
  font-size: 0.82rem;
  line-height: 1.55;
  color: #e2e8f0;
  background: rgba(2,6,23,0.5);
  border: 1px solid rgba(255,255,255,0.05);
  border-radius: 8px;
  padding: 0.75rem;
}

.detail-json {
  margin-top: 0.75rem;
}

.detail-json-title {
  font-size: 0.72rem;
  color: #94a3b8;
  margin-bottom: 0.35rem;
}

.detail-json pre {
  margin: 0;
  white-space: pre-wrap;
  max-height: 140px;
  overflow-y: auto;
  font-size: 0.72rem;
  background: rgba(2,6,23,0.5);
  border: 1px solid rgba(255,255,255,0.05);
  border-radius: 8px;
  padding: 0.6rem;
  color: #cbd5e1;
}

.pager {
  margin-top: 0.8rem;
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 0.55rem;
  color: #94a3b8;
  font-size: 0.78rem;
}

.preview-title {
  font-size: 1.1rem;
  font-weight: 700;
  margin-bottom: 0.75rem;
  color: #fff;
  border-left: 3px solid #6366f1;
  padding-left: 0.75rem;
}

.code-block {
  background: #0f172a;
  padding: 1.25rem;
  border-radius: 10px;
  font-family: 'Fira Code', 'Consolas', monospace;
  font-size: 0.85rem;
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-all;
  color: #94a3b8;
  border: 1px solid rgba(255,255,255,0.05);
  max-height: 300px;
  overflow-y: auto;
  margin-bottom: 1.5rem;
}

.chunks-preview { margin-top: 0.5rem; }

.chunk-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: 1rem;
}

.chunk-card {
  background: rgba(255,255,255,0.03);
  border: 1px solid rgba(255,255,255,0.05);
  padding: 1rem;
  border-radius: 12px;
  position: relative;
  transition: 0.2s;
}

.chunk-card:hover { background: rgba(255,255,255,0.06); border-color: #6366f1; }
.chunk-id { position: absolute; top: 0.6rem; right: 0.6rem; font-size: 0.7rem; font-weight: 800; color: #6366f1; opacity: 0.5; }
.chunk-content {
  font-size: 0.8rem;
  line-height: 1.5;
  color: #cbd5e1;
  display: -webkit-box;
  -webkit-line-clamp: 5;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.chunk-meta {
  margin-top: 0.5rem;
  font-size: 0.7rem;
  color: #64748b;
}

/* ===== File Card List ===== */
.manage-container { height: 100%; overflow-y: auto; }

.file-card-list {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.file-card {
  background: rgba(255,255,255,0.03);
  border: 1px solid rgba(255,255,255,0.06);
  border-radius: 12px;
  padding: 1rem 1.25rem;
  transition: all 0.2s;
}

.file-card:hover {
  background: rgba(255,255,255,0.05);
  border-color: rgba(99, 102, 241, 0.3);
}

.file-card-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  margin-bottom: 0.75rem;
}

.file-card-info {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  min-width: 0;
  flex: 1;
}

.file-icon-lg { font-size: 1.5rem; flex-shrink: 0; }

.file-card-meta {
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
  min-width: 0;
}

.file-card-name {
  font-weight: 600;
  font-size: 0.9rem;
  color: #e2e8f0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.file-card-size {
  font-size: 0.75rem;
  color: #64748b;
}

.file-card-actions {
  display: flex;
  gap: 0.5rem;
  flex-shrink: 0;
}

.action-btn {
  display: flex;
  align-items: center;
  gap: 0.3rem;
  padding: 0.4rem 0.7rem;
  background: rgba(255,255,255,0.06);
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 8px;
  color: #94a3b8;
  font-size: 0.78rem;
  cursor: pointer;
  transition: all 0.2s;
  white-space: nowrap;
}

.action-btn .action-label { font-weight: 500; }

.action-btn.view:hover { background: rgba(99, 102, 241, 0.15); border-color: rgba(99, 102, 241, 0.3); color: #818cf8; }
.action-btn.process:hover { background: rgba(245, 158, 11, 0.15); border-color: rgba(245, 158, 11, 0.3); color: #fbbf24; }
.action-btn.delete:hover { background: rgba(239, 68, 68, 0.15); border-color: rgba(239, 68, 68, 0.3); color: #f87171; }
.action-btn:disabled { opacity: 0.3; cursor: not-allowed; }

/* ===== Progress Bar ===== */
.file-card-bottom {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
}

.progress-bar-track {
  width: 100%;
  height: 4px;
  background: #1e293b;
  border-radius: 4px;
  overflow: hidden;
}

.progress-bar-fill {
  height: 100%;
  border-radius: 4px;
  transition: width 0.4s ease;
}

.fill-raw { background: #475569; }
.fill-parsed { background: linear-gradient(90deg, #f59e0b, #fbbf24); }
.fill-chunked { background: linear-gradient(90deg, #3b82f6, #60a5fa); }
.fill-embedding_ready { background: linear-gradient(90deg, #8b5cf6, #a78bfa); }
.fill-indexed { background: linear-gradient(90deg, #10b981, #34d399); }

.progress-labels {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.progress-pct {
  font-size: 0.7rem;
  color: #64748b;
  font-weight: 600;
}

.stage-label {
  font-size: 0.7rem;
  font-weight: 600;
  padding: 0.15rem 0.5rem;
  border-radius: 99px;
  display: inline-block;
}

.stage-label.raw { background: rgba(148, 163, 184, 0.15); color: #94a3b8; }
.stage-label.parsed { background: rgba(245, 158, 11, 0.15); color: #f59e0b; }
.stage-label.chunked { background: rgba(59, 130, 246, 0.15); color: #3b82f6; }
.stage-label.embedding_ready { background: rgba(168, 85, 247, 0.15); color: #a855f7; }
.stage-label.indexed { background: rgba(16, 185, 129, 0.15); color: #10b981; }

/* ===== Modal ===== */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(10, 15, 30, 0.8);
  backdrop-filter: blur(6px);
  z-index: 1100;
  display: flex;
  align-items: center;
  justify-content: center;
}

.modal-card {
  width: 520px;
  max-width: 90vw;
  max-height: 80vh;
  overflow-y: auto;
  padding: 2rem;
}

.modal-title { font-size: 1.25rem; font-weight: 700; color: #fff; margin-bottom: 0.5rem; }
.modal-desc { color: #94a3b8; font-size: 0.85rem; margin-bottom: 1.5rem; }

.modal-config { margin-bottom: 1.5rem; }

.modal-files { margin-bottom: 1.5rem; }
.modal-files-title { font-size: 0.85rem; font-weight: 600; color: #94a3b8; margin-bottom: 0.5rem; }

.modal-file-list {
  max-height: 160px;
  overflow-y: auto;
  border: 1px solid rgba(255,255,255,0.05);
  border-radius: 10px;
  padding: 0.5rem;
}

.modal-file-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem;
  border-radius: 6px;
  font-size: 0.85rem;
}

.modal-file-item:hover { background: rgba(255,255,255,0.03); }

.modal-file-item .stage-label { margin-left: auto; }

.modal-actions {
  display: flex;
  gap: 0.75rem;
  justify-content: flex-end;
}

.modal-actions .primary-btn { width: auto; padding: 0.85rem 2rem; }

.fullscreen-modal-card {
  width: min(1100px, 95vw);
  max-height: 88vh;
  padding: 1.1rem 1.2rem;
}

.fullscreen-modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  margin-bottom: 0.8rem;
}

.fullscreen-modal-body {
  display: flex;
  flex-direction: column;
  gap: 0.7rem;
}

.fullscreen-content {
  max-height: 52vh;
}

/* ===== Global Loader ===== */
.global-loader {
  position: fixed;
  inset: 0;
  background: rgba(10, 15, 30, 0.75);
  backdrop-filter: blur(6px);
  z-index: 1000;
  display: flex;
  align-items: center;
  justify-content: center;
}

.loader-content { text-align: center; }
.spinner {
  width: 44px;
  height: 44px;
  border: 3px solid rgba(99, 102, 241, 0.1);
  border-top-color: #6366f1;
  border-radius: 50%;
  animation: rotate 1s infinite linear;
  margin: 0 auto 1rem;
}

@keyframes rotate { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }

@media (max-width: 1200px) {
  .split-preview {
    grid-template-columns: 1fr;
  }
}

/* ===== Scrollbar ===== */
::-webkit-scrollbar { width: 5px; height: 5px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.1); border-radius: 10px; }
::-webkit-scrollbar-thumb:hover { background: rgba(255,255,255,0.2); }
</style>
