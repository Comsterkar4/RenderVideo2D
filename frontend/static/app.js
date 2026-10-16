const API_BASE = document.body.dataset.apiBase;
const VIVIBE_SESSION_KEY = 'render-video.vivibe-api-key';

const state = {
  projects: [],
  project: null,
  storyboard: null,
  geminiKeyStatus: null,
  vivibeKeyStatus: null,
};

const elements = {
  serviceStatus: document.querySelector('#service-status'),
  geminiKeyButton: document.querySelector('#gemini-key-button'),
  geminiKeyCount: document.querySelector('#gemini-key-count'),
  geminiKeyDialog: document.querySelector('#gemini-key-dialog'),
  geminiKeyForm: document.querySelector('#gemini-key-form'),
  geminiKeyInput: document.querySelector('#gemini-key-input'),
  geminiKeyStatus: document.querySelector('#gemini-key-status'),
  clearGeminiKeys: document.querySelector('#clear-gemini-keys'),
  vivibeKeyButton: document.querySelector('#vivibe-key-button'),
  vivibeKeyState: document.querySelector('#vivibe-key-state'),
  vivibeKeyDialog: document.querySelector('#vivibe-key-dialog'),
  vivibeKeyForm: document.querySelector('#vivibe-key-form'),
  vivibeKeyInput: document.querySelector('#vivibe-key-input'),
  vivibeKeyStatus: document.querySelector('#vivibe-key-status'),
  clearVivibeKey: document.querySelector('#clear-vivibe-key'),
  projectList: document.querySelector('#project-list'),
  welcomeView: document.querySelector('#welcome-view'),
  createView: document.querySelector('#create-view'),
  projectView: document.querySelector('#project-view'),
  projectForm: document.querySelector('#project-form'),
  projectTitle: document.querySelector('#project-title'),
  projectLanguage: document.querySelector('#project-language'),
  projectMeta: document.querySelector('#project-meta'),
  projectStory: document.querySelector('#project-story'),
  progressList: document.querySelector('#progress-list'),
  actionBanner: document.querySelector('#action-banner'),
  actionTitle: document.querySelector('#action-title'),
  actionDescription: document.querySelector('#action-description'),
  analyzeButton: document.querySelector('#analyze-button'),
  storyboardSection: document.querySelector('#storyboard-section'),
  characterList: document.querySelector('#character-list'),
  characterCount: document.querySelector('#character-count'),
  sceneList: document.querySelector('#scene-list'),
  sceneCount: document.querySelector('#scene-count'),
  storyboardJson: document.querySelector('#storyboard-json'),
  approveButton: document.querySelector('#approve-button'),
  generateImagesButton: document.querySelector('#generate-images-button'),
  approveImagesButton: document.querySelector('#approve-images-button'),
  configureVivibeButton: document.querySelector('#configure-vivibe-button'),
  audioSettingsControl: document.querySelector('#audio-settings-control'),
  vivibeSpeedInput: document.querySelector('#vivibe-speed-input'),
  generateAudioButton: document.querySelector('#generate-audio-button'),
  renderPreviewButton: document.querySelector('#render-preview-button'),
  renderFinalButton: document.querySelector('#render-final-button'),
  imageProviderControl: document.querySelector('#image-provider-control'),
  imageProviderSelect: document.querySelector('#image-provider-select'),
  sceneImageSection: document.querySelector('#scene-image-section'),
  sceneImageList: document.querySelector('#scene-image-list'),
  sceneImageCount: document.querySelector('#scene-image-count'),
  sceneAudioSection: document.querySelector('#scene-audio-section'),
  sceneAudioList: document.querySelector('#scene-audio-list'),
  generateAudioSectionButton: document.querySelector('#generate-audio-section-button'),
  renderVideoSection: document.querySelector('#render-video-section'),
  renderVideoList: document.querySelector('#render-video-list'),
  renderVideoCount: document.querySelector('#render-video-count'),
  loadingOverlay: document.querySelector('#loading-overlay'),
  loadingTitle: document.querySelector('#loading-title'),
  loadingMessage: document.querySelector('#loading-message'),
  toast: document.querySelector('#toast'),
};

const statusSteps = [
  ['draft', 'Nội dung', 'story-source'],
  ['awaiting_storyboard_review', 'Storyboard', 'storyboard-section'],
  ['generating_assets', 'Hình ảnh', 'scene-image-section'],
  ['generating_audio', 'Âm thanh', 'scene-audio-section'],
  ['rendering', 'Render', 'render-video-section'],
  ['completed', 'Hoàn tất', 'render-video-section'],
];

const statusLabels = {
  draft: 'Bản nháp',
  analyzing: 'Đang phân tích',
  awaiting_storyboard_review: 'Chờ duyệt storyboard',
  generating_assets: 'Đang tạo hình ảnh',
  awaiting_asset_review: 'Chờ duyệt hình ảnh',
  generating_audio: 'Đang tạo âm thanh',
  rendering: 'Đang render',
  completed: 'Hoàn tất',
};

const imageProviderLabels = {
  comfyui: 'ComfyUI',
  gemini: 'Gemini',
};


function selectedImageProvider() {
  return elements.imageProviderSelect.value;
}

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      ...(options.body ? {'Content-Type': 'application/json'} : {}),
      ...options.headers,
    },
  });

  if (!response.ok) {
    let message = `HTTP ${response.status}`;
    try {
      const payload = await response.json();
      message = Array.isArray(payload.detail)
        ? payload.detail.map((item) => item.msg).join(', ')
        : payload.detail || message;
    } catch (_) {
      // Keep the status message when the response is not JSON.
    }
    const error = new Error(message);
    error.status = response.status;
    throw error;
  }

  if (response.status === 204) return null;
  return response.json();
}

function renderGeminiKeyStatus() {
  const settings = state.geminiKeyStatus;
  const count = settings?.count || 0;
  elements.geminiKeyCount.textContent = String(count);
  elements.clearGeminiKeys.disabled = settings?.source !== 'web';
  if (settings?.source === 'web') {
    elements.geminiKeyStatus.textContent = `${count} key đang được giữ trong RAM của backend.`;
  } else if (settings?.source === 'environment') {
    elements.geminiKeyStatus.textContent = 'Đang dùng 1 key từ biến môi trường backend.';
  } else {
    elements.geminiKeyStatus.textContent = 'Chưa cấu hình Gemini API key.';
  }
}

async function loadGeminiKeyStatus() {
  state.geminiKeyStatus = await request('/api/settings/gemini-keys');
  renderGeminiKeyStatus();
}

function openGeminiKeyDialog() {
  elements.geminiKeyInput.value = '';
  elements.geminiKeyDialog.showModal();
  elements.geminiKeyInput.focus();
}

async function saveGeminiKeys(event) {
  event.preventDefault();
  const keys = elements.geminiKeyInput.value
    .split(/\r?\n/)
    .map((key) => key.trim())
    .filter(Boolean);
  elements.geminiKeyInput.value = '';
  if (!keys.length) {
    toast('Nhập ít nhất một Gemini API key.', 'error');
    return;
  }

  try {
    state.geminiKeyStatus = await request('/api/settings/gemini-keys', {
      method: 'PUT',
      body: JSON.stringify({keys}),
    });
    renderGeminiKeyStatus();
    elements.geminiKeyDialog.close();
    toast(`Đã lưu ${state.geminiKeyStatus.count} Gemini key trong RAM.`);
  } catch (error) {
    toast(error.message, 'error');
  }
}

async function clearGeminiKeys() {
  if (!window.confirm('Xóa toàn bộ Gemini key đã nhập trên giao diện?')) return;
  try {
    state.geminiKeyStatus = await request('/api/settings/gemini-keys', {
      method: 'DELETE',
    });
    renderGeminiKeyStatus();
    toast('Đã xóa Gemini key lưu trong RAM.');
  } catch (error) {
    toast(error.message, 'error');
  }
}

function temporaryVivibeKey() {
  try {
    return sessionStorage.getItem(VIVIBE_SESSION_KEY)?.trim() || null;
  } catch (_) {
    return null;
  }
}

function rememberTemporaryVivibeKey(key) {
  try {
    sessionStorage.setItem(VIVIBE_SESSION_KEY, key);
  } catch (_) {
    // Backend RAM storage remains the fallback when session storage is unavailable.
  }
}

function forgetTemporaryVivibeKey() {
  try {
    sessionStorage.removeItem(VIVIBE_SESSION_KEY);
  } catch (_) {
    // Nothing else is required when session storage is unavailable.
  }
}

function renderVivibeKeyStatus() {
  const settings = state.vivibeKeyStatus;
  elements.vivibeKeyState.textContent = settings?.configured ? 'Đã có' : 'Chưa có';
  elements.clearVivibeKey.disabled = settings?.source !== 'web';
  elements.generateAudioButton.disabled = !settings?.configured;
  if (settings?.source === 'web') {
    elements.vivibeKeyStatus.textContent = 'Key đang được giữ trong RAM của backend.';
  } else if (settings?.source === 'environment') {
    elements.vivibeKeyStatus.textContent = 'Đang dùng key từ biến môi trường backend.';
  } else {
    elements.vivibeKeyStatus.textContent = 'Chưa cấu hình ViViBe API key.';
  }
  if (state.project) renderAction(state.project.status);
}

async function loadVivibeKeyStatus() {
  state.vivibeKeyStatus = await request('/api/settings/vivibe-key');
  const temporaryKey = temporaryVivibeKey();
  if (temporaryKey && !state.vivibeKeyStatus.configured) {
    try {
      state.vivibeKeyStatus = await request('/api/settings/vivibe-key', {
        method: 'PUT',
        body: JSON.stringify({key: temporaryKey}),
      });
    } catch (_) {
      forgetTemporaryVivibeKey();
    }
  }
  renderVivibeKeyStatus();
}

function openVivibeKeyDialog() {
  elements.vivibeKeyInput.value = '';
  elements.vivibeKeyDialog.showModal();
  elements.vivibeKeyInput.focus();
}

async function saveVivibeKey(event) {
  event.preventDefault();
  const key = elements.vivibeKeyInput.value.trim();
  elements.vivibeKeyInput.value = '';
  if (!key) {
    toast('Nhập ViViBe API key.', 'error');
    return;
  }

  try {
    state.vivibeKeyStatus = await request('/api/settings/vivibe-key', {
      method: 'PUT',
      body: JSON.stringify({key}),
    });
    rememberTemporaryVivibeKey(key);
    renderVivibeKeyStatus();
    elements.vivibeKeyDialog.close();
    toast('Đã lưu ViViBe API key trong RAM và tạm trong phiên trình duyệt.');
  } catch (error) {
    toast(error.message, 'error');
  }
}

async function clearVivibeKey() {
  if (!window.confirm('Xóa ViViBe API key đã nhập trên giao diện?')) return;
  try {
    state.vivibeKeyStatus = await request('/api/settings/vivibe-key', {
      method: 'DELETE',
    });
    forgetTemporaryVivibeKey();
    renderVivibeKeyStatus();
    toast('Đã xóa ViViBe API key khỏi RAM và phiên trình duyệt.');
  } catch (error) {
    toast(error.message, 'error');
  }
}


function showOnly(view) {
  [elements.welcomeView, elements.createView, elements.projectView].forEach((item) => {
    item.classList.toggle('hidden', item !== view);
  });
}

function setBusy(active, title = 'Đang xử lý…', message = 'Vui lòng giữ trang này mở.') {
  elements.loadingTitle.textContent = title;
  elements.loadingMessage.textContent = message;
  elements.loadingOverlay.classList.toggle('hidden', !active);
}

let toastTimer;
function toast(message, kind = 'success') {
  clearTimeout(toastTimer);
  elements.toast.textContent = message;
  elements.toast.className = `toast ${kind}`;
  toastTimer = setTimeout(() => elements.toast.classList.add('hidden'), 4200);
}

function element(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

async function checkBackend() {
  try {
    await request('/health');
    elements.serviceStatus.classList.add('online');
    elements.serviceStatus.querySelector('span:last-child').textContent = 'Backend hoạt động';
  } catch (error) {
    elements.serviceStatus.classList.remove('online');
    elements.serviceStatus.querySelector('span:last-child').textContent = 'Mất kết nối backend';
    toast(`Không thể kết nối backend: ${error.message}`, 'error');
  }
}

async function loadProjects() {
  state.projects = await request('/api/projects');
  renderProjectList();
  if (!state.projects.length && !state.project) showOnly(elements.welcomeView);
}

function renderProjectList() {
  elements.projectList.replaceChildren();
  if (!state.projects.length) {
    const empty = element('p', 'empty-list', 'Chưa có dự án.');
    elements.projectList.append(empty);
    return;
  }

  state.projects.forEach((project) => {
    const button = element('button', 'project-item');
    button.type = 'button';
    button.classList.toggle('active', state.project?.id === project.id);
    button.append(
      element('strong', '', project.title),
      element('span', '', statusLabels[project.status] || project.status),
      element('small', '', `${project.aspect_ratio} · Tiếng Việt`),
    );
    button.addEventListener('click', () => selectProject(project.id));
    elements.projectList.append(button);
  });
}

async function selectProject(projectId) {
  setBusy(true, 'Đang mở dự án…');
  try {
    state.project = await request(`/api/projects/${projectId}`);
    try {
      state.storyboard = await request(`/api/projects/${projectId}/storyboard`);
    } catch (error) {
      if (error.status === 409) state.storyboard = null;
      else throw error;
    }
    renderProject();
    renderProjectList();
    showOnly(elements.projectView);
  } catch (error) {
    toast(error.message, 'error');
  } finally {
    setBusy(false);
  }
}

function renderProject() {
  const project = state.project;
  elements.projectTitle.textContent = project.title;
  elements.projectLanguage.textContent = `Tiếng Việt · ${statusLabels[project.status] || project.status}`;
  elements.projectMeta.textContent = `${project.aspect_ratio} · Hoạt hình 2D`;
  elements.projectStory.textContent = project.story;
  renderProgress(project.status);
  renderAction(project.status);
  renderStoryboard();
  renderSceneImages();
  renderSceneAudio();
  renderVideos();
}

function scrollToProjectSection(targetId) {
  const target = document.querySelector(`#${targetId}`);
  if (!target) return;
  target.scrollIntoView({behavior: 'smooth', block: 'start'});
}

function renderProgress(status) {
  elements.progressList.replaceChildren();
  const normalized = status === 'analyzing' ? 'draft' : status === 'awaiting_asset_review' ? 'generating_assets' : status;
  const activeIndex = Math.max(0, statusSteps.findIndex(([key]) => key === normalized));
  statusSteps.forEach(([key, label, targetId], index) => {
    const item = element('li', index < activeIndex ? 'done' : index === activeIndex ? 'active' : '');
    item.dataset.status = key;
    item.dataset.target = targetId;
    item.tabIndex = 0;
    item.setAttribute('role', 'button');
    item.setAttribute('aria-label', `Mở phần ${label}`);
    item.append(
      element('span', '', index < activeIndex ? '✓' : String(index + 1)),
      element('strong', '', label),
    );
    const navigate = () => scrollToProjectSection(targetId);
    item.addEventListener('click', navigate);
    item.addEventListener('keydown', (event) => {
      if (event.key === 'Enter' || event.key === ' ') {
        event.preventDefault();
        navigate();
      }
    });
    elements.progressList.append(item);
  });
}

function renderAction(status) {
  const canAnalyze = status === 'draft' || status === 'awaiting_storyboard_review';
  const imagePhase = ['generating_assets', 'awaiting_asset_review'].includes(status);
  const audioPhase = status === 'generating_audio';
  const renderPhase = ['rendering', 'completed'].includes(status);
  elements.analyzeButton.classList.toggle('hidden', !canAnalyze);
  elements.generateImagesButton.classList.toggle('hidden', status !== 'generating_assets');
  elements.approveImagesButton.classList.toggle('hidden', status !== 'awaiting_asset_review');
  elements.configureVivibeButton.classList.toggle('hidden', !audioPhase);
  elements.audioSettingsControl.classList.toggle('hidden', !audioPhase);
  elements.generateAudioButton.classList.toggle('hidden', !audioPhase);
  elements.renderPreviewButton.classList.toggle('hidden', !renderPhase);
  elements.renderFinalButton.classList.toggle('hidden', !renderPhase);
  elements.imageProviderControl.classList.toggle('hidden', !imagePhase);

  if (status === 'draft') {
    elements.actionTitle.textContent = 'Tạo storyboard';
    elements.actionDescription.textContent = 'Ollama sẽ phân tích truyện, tạo Character Bible và chia cảnh.';
    elements.analyzeButton.textContent = 'Phân tích truyện';
  } else if (status === 'awaiting_storyboard_review') {
    elements.actionTitle.textContent = 'Kiểm tra storyboard';
    elements.actionDescription.textContent = 'Đọc lại nhân vật và từng cảnh. Chỉnh JSON nếu cần rồi duyệt.';
    elements.analyzeButton.textContent = 'Phân tích lại';
  } else if (status === 'generating_assets') {
    const provider = selectedImageProvider();
    elements.actionTitle.textContent = 'Tạo hình ảnh cho từng cảnh';
    elements.actionDescription.textContent = provider === 'gemini'
      ? 'Gemini tạo ảnh qua API key được cấu hình an toàn ở backend.'
      : 'ComfyUI dùng Stable Diffusion 1.5 và tạo ảnh tuần tự để tiết kiệm bộ nhớ.';
  } else if (status === 'awaiting_asset_review') {
    elements.actionTitle.textContent = 'Kiểm tra hình ảnh';
    elements.actionDescription.textContent = 'Xem từng cảnh, chọn nguồn và tạo lại ảnh chưa đạt rồi duyệt.';
  } else if (status === 'generating_audio') {
    elements.actionTitle.textContent = 'Tạo giọng đọc bằng ViViBe';
    elements.actionDescription.textContent = 'Giọng Adam cố định. Chọn tốc độ để tạo WAV và SRT cho từng cảnh.';
  } else if (status === 'rendering') {
    elements.actionTitle.textContent = 'Dựng video theo thời lượng lời đọc';
    elements.actionDescription.textContent = 'Mỗi ảnh được pan/zoom đúng thời lượng WAV; phụ đề được ghép theo timeline.';
  } else if (status === 'completed') {
    elements.actionTitle.textContent = 'Video đã sẵn sàng';
    elements.actionDescription.textContent = 'Có thể xem, tải xuống hoặc render lại preview/final sau khi thay đổi media.';
  }
}

function renderStoryboard() {
  const storyboard = state.storyboard;
  elements.storyboardSection.classList.toggle('hidden', !storyboard);
  if (!storyboard) return;

  elements.characterCount.textContent = `${storyboard.characters.length} nhân vật`;
  elements.characterList.replaceChildren();
  storyboard.characters.forEach((character) => {
    const card = element('article', 'character-card');
    card.append(
      element('span', 'character-id', character.id),
      element('h3', '', character.name),
      element('p', '', character.appearance),
      element('small', '', character.prompt_fragment),
    );
    elements.characterList.append(card);
  });

  elements.sceneCount.textContent = `${storyboard.scenes.length} cảnh`;
  elements.sceneList.replaceChildren();
  storyboard.scenes.forEach((scene) => {
    const card = element('article', 'scene-card');
    const index = element('div', 'scene-index', String(scene.order).padStart(2, '0'));
    const content = element('div', 'scene-content');
    const heading = element('div', 'scene-heading');
    heading.append(
      element('h3', '', scene.location),
      element('span', 'duration', `${scene.duration_seconds}s`),
    );
    const cast = element('div', 'tag-list');
    scene.character_ids.forEach((id) => cast.append(element('span', '', id)));
    const effects = element('div', 'effects');
    effects.append(element('strong', '', 'SFX '), element('span', '', scene.sound_effects.join(' · ') || '—'));
    content.append(
      heading,
      cast,
      element('p', 'narration', scene.narration),
      element('p', 'prompt-line', scene.image_prompt),
      effects,
    );
    card.append(index, content);
    elements.sceneList.append(card);
  });

  elements.storyboardJson.value = JSON.stringify(storyboard, null, 2);
  const editable = state.project.status === 'awaiting_storyboard_review';
  elements.storyboardJson.disabled = !editable;
  document.querySelector('#save-storyboard-button').disabled = !editable;
  elements.approveButton.disabled = !editable;
}

function currentImageForScene(sceneId) {
  const matches = state.project.assets.filter(
    (asset) => asset.scene_id === sceneId
      && asset.kind === 'scene_image'
      && asset.status === 'completed',
  );
  return matches.at(-1) || null;
}

function renderSceneImages() {
  const showImages = ['generating_assets', 'awaiting_asset_review', 'generating_audio', 'rendering', 'completed']
    .includes(state.project.status);
  elements.sceneImageSection.classList.toggle('hidden', !showImages);
  if (!showImages) return;

  const completed = state.project.scenes
    .filter((scene) => currentImageForScene(scene.id))
    .length;
  elements.sceneImageCount.textContent = `${completed}/${state.project.scenes.length} ảnh`;
  elements.sceneImageList.replaceChildren();

  state.project.scenes.forEach((scene) => {
    const asset = currentImageForScene(scene.id);
    const card = element('article', 'scene-image-card');
    const preview = element('div', 'scene-image-preview');
    if (asset) {
      const image = element('img');
      image.src = `${API_BASE}/api/assets/${asset.id}/content?v=${asset.sha256 || asset.id}`;
      image.alt = `Ảnh cảnh ${scene.order}: ${scene.location}`;
      image.loading = 'lazy';
      preview.append(image);
    } else {
      preview.append(
        element('span', 'scene-image-placeholder-index', String(scene.order).padStart(2, '0')),
        element('small', '', scene.status === 'image_failed' ? 'Tạo ảnh thất bại' : 'Chưa có ảnh'),
      );
    }

    const body = element('div', 'scene-image-body');
    body.append(
      element('span', 'eyebrow', `Cảnh ${String(scene.order).padStart(2, '0')}`),
      element('h3', '', scene.location),
      element('p', '', scene.image_prompt),
    );
    if (asset) {
      body.append(
        element(
          'small',
          'scene-image-provider',
          `${imageProviderLabels[asset.provider] || asset.provider} · ${asset.model || 'model mặc định'}`,
        ),
      );
    }
    if (['generating_assets', 'awaiting_asset_review'].includes(state.project.status)) {
      const retry = element('button', 'secondary-button', asset ? 'Tạo lại ảnh' : 'Tạo ảnh cảnh này');
      retry.type = 'button';
      retry.addEventListener('click', () => generateSceneImage(scene.id, Boolean(asset)));
      body.append(retry);
    }

    card.append(preview, body);
    elements.sceneImageList.append(card);
  });
}

function latestNarrationAttemptForScene(sceneId) {
  const matches = state.project.assets.filter(
    (asset) => asset.scene_id === sceneId && asset.kind === 'narration_audio',
  );
  return matches.at(-1) || null;
}

function currentAudioForScene(sceneId) {
  const matches = state.project.assets.filter(
    (asset) => asset.scene_id === sceneId
      && asset.kind === 'narration_audio'
      && asset.status === 'completed',
  );
  return matches.at(-1) || null;
}

function currentSubtitleForScene(sceneId) {
  const matches = state.project.assets.filter(
    (asset) => asset.scene_id === sceneId
      && asset.kind === 'narration_subtitle'
      && asset.status === 'completed',
  );
  return matches.at(-1) || null;
}

function renderSceneAudio() {
  const showAudio = ['generating_audio', 'rendering', 'completed'].includes(state.project.status);
  elements.sceneAudioSection.classList.toggle('hidden', !showAudio);
  if (!showAudio) return;

  const completed = state.project.scenes
    .filter((scene) => currentAudioForScene(scene.id))
    .length;
  const missing = state.project.scenes.length - completed;
  if (elements.generateAudioSectionButton) {
    elements.generateAudioSectionButton.classList.toggle(
      'hidden',
      !missing || !state.vivibeKeyStatus?.configured,
    );
    elements.generateAudioSectionButton.textContent = missing
      ? `Tạo ${missing} cảnh audio còn thiếu`
      : 'Tạo audio còn thiếu';
    elements.generateAudioSectionButton.disabled = hasProcessingAudio();
  }
  elements.sceneAudioList.replaceChildren();

  const audioBusy = hasProcessingAudio();
  state.project.scenes.forEach((scene) => {
    const asset = currentAudioForScene(scene.id);
    const subtitle = currentSubtitleForScene(scene.id);
    const latest = latestNarrationAttemptForScene(scene.id);
    const card = element('article', 'scene-audio-card');
    const heading = element('div', 'scene-audio-heading');
    heading.append(
      element('span', 'eyebrow', `Cảnh ${String(scene.order).padStart(2, '0')}`),
      element('strong', '', `${scene.duration_seconds}s`),
    );
    card.append(
      heading,
      element('h3', '', scene.location),
      element('p', 'scene-audio-narration', scene.narration),
    );

    if (asset) {
      const audio = element('audio');
      audio.controls = true;
      audio.preload = 'metadata';
      audio.src = `${API_BASE}/api/assets/${asset.id}/content?v=${asset.sha256 || asset.id}`;
      card.append(audio);

      const metadata = element(
        'small',
        'scene-audio-metadata',
        `ViViBe · giọng ${asset.metadata.voice_name || 'Adam'} · tốc độ ${asset.metadata.speed}`,
      );
      card.append(metadata);
      if (subtitle) {
        const subtitleLink = element('a', 'subtitle-link', 'Tải phụ đề SRT');
        subtitleLink.href = `${API_BASE}/api/assets/${subtitle.id}/content?v=${subtitle.sha256 || subtitle.id}`;
        subtitleLink.download = `scene-${String(scene.order).padStart(2, '0')}.srt`;
        card.append(subtitleLink);
      }
    } else {
      const statusText = latest?.status === 'failed'
        ? `Thất bại: ${latest.metadata.error || 'ViViBe không tạo được audio'}`
        : latest?.status === 'processing' || latest?.status === 'submitting'
          ? 'ViViBe đang xử lý…'
          : 'Chưa có âm thanh';
      card.append(element('p', latest?.status === 'failed' ? 'audio-error' : 'audio-status', statusText));
    }

    if (['generating_audio', 'rendering', 'completed'].includes(state.project.status)) {
      const active = ['submitting', 'processing'].includes(latest?.status);
      const retry = element('button', 'secondary-button', asset ? 'Tạo lại âm thanh' : 'Tạo âm thanh cảnh này');
      retry.type = 'button';
      retry.disabled = audioBusy || active || !state.vivibeKeyStatus?.configured;
      retry.addEventListener('click', () => generateSceneAudio(scene.id));
      card.append(retry);
    }

    elements.sceneAudioList.append(card);
  });
}
function currentRenderVideos() {
  return state.project.assets
    .filter((asset) => asset.kind === 'render_video' && asset.status === 'completed')
    .sort((left, right) => left.created_at.localeCompare(right.created_at));
}

function renderVideos() {
  const videos = currentRenderVideos();
  elements.renderVideoSection.classList.toggle('hidden', !videos.length);
  if (!videos.length) return;

  elements.renderVideoCount.textContent = `${videos.length} bản render`;
  elements.renderVideoList.replaceChildren();
  videos.forEach((asset) => {
    const card = element('article', 'render-video-card');
    const quality = asset.metadata.quality === 'final' ? 'Final' : 'Preview';
    const video = element('video');
    video.controls = true;
    video.preload = 'metadata';
    video.src = `${API_BASE}/api/assets/${asset.id}/content?v=${asset.sha256 || asset.id}`;
    const download = element('a', 'primary-button', `Tải ${quality}`);
    download.href = video.src;
    download.download = `${state.project.id}-${asset.metadata.quality}.mp4`;
    card.append(
      element('div', 'render-video-heading', `${quality} · ${asset.metadata.duration_seconds}s`),
      video,
      download,
    );
    elements.renderVideoList.append(card);
  });
}


async function createProject(event) {
  event.preventDefault();
  const form = new FormData(elements.projectForm);
  const payload = Object.fromEntries(form.entries());
  setBusy(true, 'Đang tạo dự án…');
  try {
    const project = await request('/api/projects', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
    elements.projectForm.reset();
    await loadProjects();
    await selectProject(project.id);
    toast('Đã tạo dự án.');
  } catch (error) {
    toast(error.message, 'error');
  } finally {
    setBusy(false);
  }
}

async function analyzeProject() {
  setBusy(true, 'Ollama đang phân tích truyện…', 'Lần đầu chạy trên CPU có thể mất một lúc.');
  try {
    state.project = await request(`/api/projects/${state.project.id}/analyze`, {method: 'POST'});
    state.storyboard = await request(`/api/projects/${state.project.id}/storyboard`);
    await loadProjects();
    renderProject();
    toast('Storyboard đã sẵn sàng để duyệt.');
  } catch (error) {
    toast(error.message, 'error');
  } finally {
    setBusy(false);
  }
}

async function saveStoryboard() {
  let payload;
  try {
    payload = JSON.parse(elements.storyboardJson.value);
  } catch (error) {
    toast(`JSON không hợp lệ: ${error.message}`, 'error');
    return;
  }

  setBusy(true, 'Đang lưu storyboard…');
  try {
    state.project = await request(`/api/projects/${state.project.id}/storyboard`, {
      method: 'PUT',
      body: JSON.stringify(payload),
    });
    state.storyboard = await request(`/api/projects/${state.project.id}/storyboard`);
    renderProject();
    toast('Đã lưu storyboard.');
  } catch (error) {
    toast(error.message, 'error');
  } finally {
    setBusy(false);
  }
}

async function approveStoryboard() {
  setBusy(true, 'Đang duyệt storyboard…');
  try {
    state.project = await request(`/api/projects/${state.project.id}/storyboard/approve`, {method: 'POST'});
    await loadProjects();
    renderProject();
    toast('Storyboard đã được duyệt.');
  } catch (error) {
    toast(error.message, 'error');
  } finally {
    setBusy(false);
  }
}

async function generateProjectImages() {
  const provider = selectedImageProvider();
  const providerLabel = imageProviderLabels[provider];
  setBusy(
    true,
    `${providerLabel} đang tạo hình ảnh…`,
    provider === 'gemini'
      ? 'Các cảnh được gửi tuần tự tới Gemini API.'
      : 'Các cảnh được xử lý tuần tự. Không đóng dịch vụ ComfyUI trong lúc này.',
  );
  try {
    state.project = await request(`/api/projects/${state.project.id}/images/generate`, {
      method: 'POST',
      body: JSON.stringify({provider}),
    });
    await loadProjects();
    renderProject();
    toast(`Đã tạo xong hình ảnh bằng ${providerLabel}.`);
  } catch (error) {
    toast(error.message, 'error');
    await selectProject(state.project.id);
  } finally {
    setBusy(false);
  }
}

async function generateSceneImage(sceneId, regenerate) {
  const provider = selectedImageProvider();
  const providerLabel = imageProviderLabels[provider];
  setBusy(
    true,
    `${providerLabel} đang ${regenerate ? 'tạo lại' : 'tạo'} ảnh…`,
    provider === 'gemini'
      ? 'Ảnh được tạo qua Gemini API.'
      : 'Model sẽ được giải phóng khỏi bộ nhớ sau khi hoàn thành.',
  );
  try {
    state.project = await request(
      `/api/projects/${state.project.id}/scenes/${sceneId}/image`,
      {
        method: 'POST',
        body: JSON.stringify({provider}),
      },
    );
    await loadProjects();
    renderProject();
    toast(`${regenerate ? 'Đã tạo lại' : 'Đã tạo'} ảnh cảnh bằng ${providerLabel}.`);
  } catch (error) {
    toast(error.message, 'error');
    await selectProject(state.project.id);
  } finally {
    setBusy(false);
  }
}

async function approveImages() {
  setBusy(true, 'Đang duyệt hình ảnh…');
  try {
    state.project = await request(`/api/projects/${state.project.id}/images/approve`, {method: 'POST'});
    await loadProjects();
    renderProject();
    toast('Hình ảnh đã được duyệt.');
  } catch (error) {
    toast(error.message, 'error');
  } finally {
    setBusy(false);
  }
}

function selectedAudioOptions() {
  const speed = Number(elements.vivibeSpeedInput.value || 1);
  if (!Number.isFinite(speed) || speed < 0.5 || speed > 2) {
    throw new Error('Tốc độ ViViBe phải nằm trong khoảng 0.5–2.0.');
  }
  return {speed};
}

function currentAudioFailure() {
  for (const scene of state.project.scenes) {
    const latest = latestNarrationAttemptForScene(scene.id);
    if (latest?.status === 'failed') {
      return latest.metadata.error || `Không tạo được âm thanh cho cảnh ${scene.order}.`;
    }
  }
  return null;
}

function hasProcessingAudio() {
  return state.project.scenes.some((scene) => {
    const latest = latestNarrationAttemptForScene(scene.id);
    return ['submitting', 'processing'].includes(latest?.status);
  });
}

function delay(milliseconds) {
  return new Promise((resolve) => setTimeout(resolve, milliseconds));
}

async function pollProjectAudio() {
  while (state.project.status === 'generating_audio') {
    const failure = currentAudioFailure();
    if (failure) throw new Error(failure);
    if (!hasProcessingAudio()) {
      throw new Error('Không có job ViViBe đang xử lý. Hãy thử tạo lại âm thanh.');
    }
    await delay(3000);
    state.project = await request(`/api/projects/${state.project.id}/audio/refresh`, {
      method: 'POST',
    });
    renderProject();
  }
}

async function generateProjectAudio() {
  let options;
  try {
    options = selectedAudioOptions();
  } catch (error) {
    toast(error.message, 'error');
    return;
  }

  setBusy(true, 'ViViBe đang tạo âm thanh…', 'Đang tạo WAV và SRT cho từng cảnh.');
  try {
    state.project = await request(`/api/projects/${state.project.id}/audio/generate`, {
      method: 'POST',
      body: JSON.stringify(options),
    });
    renderProject();
    await pollProjectAudio();
    await loadProjects();
    renderProject();
    toast('Đã tạo xong âm thanh cho tất cả cảnh.');
  } catch (error) {
    toast(error.message, 'error');
    await selectProject(state.project.id);
  } finally {
    setBusy(false);
  }
}

async function generateSceneAudio(sceneId) {
  let options;
  try {
    options = selectedAudioOptions();
  } catch (error) {
    toast(error.message, 'error');
    return;
  }

  setBusy(true, 'ViViBe đang tạo âm thanh…', 'Đang xử lý lời dẫn của cảnh đã chọn.');
  try {
    state.project = await request(
      `/api/projects/${state.project.id}/scenes/${sceneId}/audio`,
      {
        method: 'POST',
        body: JSON.stringify(options),
      },
    );
    renderProject();
    await pollProjectAudio();
    await loadProjects();
    renderProject();
    toast('Đã tạo xong âm thanh cho cảnh.');
  } catch (error) {
    toast(error.message, 'error');
    await selectProject(state.project.id);
  } finally {
    setBusy(false);
  }
}


async function renderVideo(quality) {
  setBusy(
    true,
    quality === 'final' ? 'Đang render video final…' : 'Đang render preview…',
    'Ảnh và lời đọc đang được ghép theo timeline.',
  );
  try {
    state.project = await request(`/api/projects/${state.project.id}/render`, {
      method: 'POST',
      body: JSON.stringify({quality}),
    });
    renderProject();
    await loadProjects();
    toast(quality === 'final' ? 'Đã render video final.' : 'Đã render preview.');
  } catch (error) {
    toast(error.message, 'error');
    await selectProject(state.project.id);
  } finally {
    setBusy(false);
  }
}

async function deleteProject() {
  if (!window.confirm(`Xóa dự án “${state.project.title}”? Dữ liệu liên quan cũng sẽ bị xóa.`)) return;
  setBusy(true, 'Đang xóa dự án…');
  try {
    await request(`/api/projects/${state.project.id}`, {method: 'DELETE'});
    state.project = null;
    state.storyboard = null;
    await loadProjects();
    showOnly(elements.welcomeView);
    toast('Đã xóa dự án.');
  } catch (error) {
    toast(error.message, 'error');
  } finally {
    setBusy(false);
  }
}

function openCreateView() {
  showOnly(elements.createView);
  elements.projectForm.querySelector('input[name="title"]').focus();
}

elements.geminiKeyButton.addEventListener('click', openGeminiKeyDialog);
elements.geminiKeyForm.addEventListener('submit', saveGeminiKeys);
elements.clearGeminiKeys.addEventListener('click', clearGeminiKeys);
document.querySelector('#close-gemini-key-dialog').addEventListener('click', () => {
  elements.geminiKeyInput.value = '';
  elements.geminiKeyDialog.close();
});
elements.vivibeKeyButton.addEventListener('click', openVivibeKeyDialog);
elements.configureVivibeButton.addEventListener('click', openVivibeKeyDialog);
elements.vivibeKeyForm.addEventListener('submit', saveVivibeKey);
elements.clearVivibeKey.addEventListener('click', clearVivibeKey);
document.querySelector('#close-vivibe-key-dialog').addEventListener('click', () => {
  elements.vivibeKeyInput.value = '';
  elements.vivibeKeyDialog.close();
});

document.querySelector('#new-project-button').addEventListener('click', openCreateView);
document.querySelector('#welcome-create-button').addEventListener('click', openCreateView);
document.querySelector('#cancel-create-button').addEventListener('click', () => {
  if (state.project) showOnly(elements.projectView);
  else showOnly(elements.welcomeView);
});
elements.projectForm.addEventListener('submit', createProject);
elements.analyzeButton.addEventListener('click', analyzeProject);
document.querySelector('#save-storyboard-button').addEventListener('click', saveStoryboard);
elements.approveButton.addEventListener('click', approveStoryboard);
elements.generateImagesButton.addEventListener('click', generateProjectImages);
elements.approveImagesButton.addEventListener('click', approveImages);
elements.generateAudioButton.addEventListener('click', generateProjectAudio);
if (elements.generateAudioSectionButton) {
  elements.generateAudioSectionButton.addEventListener('click', generateProjectAudio);
}
elements.renderPreviewButton.addEventListener('click', () => renderVideo('preview'));
elements.renderFinalButton.addEventListener('click', () => renderVideo('final'));
elements.imageProviderSelect.addEventListener('change', () => {
  if (state.project) renderAction(state.project.status);
});
document.querySelector('#refresh-button').addEventListener('click', () => selectProject(state.project.id));
document.querySelector('#delete-button').addEventListener('click', deleteProject);

(async function initialize() {
  await checkBackend();
  try {
    await Promise.all([loadProjects(), loadGeminiKeyStatus(), loadVivibeKeyStatus()]);
  } catch (error) {
    toast(error.message, 'error');
  }
})();
