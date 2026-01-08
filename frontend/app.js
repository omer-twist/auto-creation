// ============ CONFIGURATION ============

const LAMBDA_URL = "https://okix5fe77gdvqcwt2ennmdudie0hdnbm.lambda-url.us-east-1.on.aws/";
const CHUNK_SIZE = 50;
const CHUNK_DELAY_MS = 200;

// ============ STATE ============

let CREATIVE_TYPES = {};  // Loaded from API
let campaigns = [];
let fieldData = {};  // Stores data for dynamic fields: { field_name: value }

// ============ INITIALIZATION ============

document.addEventListener('DOMContentLoaded', init);

async function init() {
  try {
    // Fetch config from API
    const response = await fetch(LAMBDA_URL + 'config');
    CREATIVE_TYPES = await response.json();

    populateCreativeTypeDropdown();
    setupUniversalFieldListeners();

    // Render first type
    const firstType = Object.keys(CREATIVE_TYPES)[0];
    if (firstType) {
      document.getElementById('creative-type').value = firstType;
      renderDynamicFields(firstType);
    }

    renderTable();
  } catch (error) {
    console.error('Failed to load config:', error);
    document.getElementById('dynamic-fields').innerHTML = '<div class="loading">Failed to load configuration</div>';
  }
}

function populateCreativeTypeDropdown() {
  const select = document.getElementById('creative-type');
  select.innerHTML = '';

  for (const [key, config] of Object.entries(CREATIVE_TYPES)) {
    const option = document.createElement('option');
    option.value = key;
    option.textContent = config.displayName;
    select.appendChild(option);
  }

  select.addEventListener('change', () => {
    fieldData = {};  // Clear field data when switching types
    renderDynamicFields(select.value);
  });
}

function setupUniversalFieldListeners() {
  // Discount conditional input
  const discountType = document.getElementById('discount-type');
  const discountValue = document.getElementById('discount-value');

  discountType.addEventListener('change', () => {
    const needsValue = ['constant', 'upto'].includes(discountType.value);
    discountValue.classList.toggle('visible', needsValue);
    if (!needsValue) discountValue.value = '';
  });

  // Event conditional input
  const eventType = document.getElementById('event-type');
  const eventName = document.getElementById('event-name');

  eventType.addEventListener('change', () => {
    const needsName = eventType.value === 'custom';
    eventName.classList.toggle('visible', needsName);
    if (!needsName) eventName.value = '';
  });

  // Form submission
  document.getElementById('campaign-form').addEventListener('submit', handleFormSubmit);

  // Send button
  document.getElementById('send-btn').addEventListener('click', sendAll);
}

// ============ GENERIC FIELD RENDERING ============

function renderDynamicFields(creativeType) {
  const config = CREATIVE_TYPES[creativeType];
  if (!config) return;

  const container = document.getElementById('dynamic-fields');
  container.innerHTML = '';

  // Initialize field data and render each field
  for (const field of config.fields || []) {
    container.innerHTML += renderField(field);
    initFieldData(field);
  }

  // Attach event listeners
  attachFieldListeners(config);
  setupConditionListeners(config);
}

function initFieldData(field) {
  if (field.type === 'list') {
    fieldData[field.name] = fieldData[field.name] || [];
  } else if (field.type === 'textarea') {
    fieldData[field.name] = fieldData[field.name] || '';
  } else if (field.type === 'toggle') {
    fieldData[field.name] = fieldData[field.name] ?? field.default ?? false;
  }
}

function renderField(field) {
  // Standalone toggle (no condition) - renders as toggle row
  if (field.type === 'toggle' && !field.condition) {
    return renderStandaloneToggle(field);
  }

  // Simple types with condition: inline (same row)
  if (field.condition && field.type === 'text') {
    return renderInlineConditional(field);
  }

  // Block fields (list, textarea): with or without condition
  if (field.type === 'list') {
    return field.condition
      ? renderBlockConditional(field, renderListSection)
      : renderListSection(field);
  }

  if (field.type === 'textarea') {
    return field.condition
      ? renderBlockConditional(field, renderTextareaSection)
      : renderTextareaSection(field);
  }

  return '';
}

function renderStandaloneToggle(field) {
  const checked = field.default ? 'checked' : '';
  return `
    <div class="toggle-row">
      <span class="toggle-label">${escapeHtml(field.label)}</span>
      <label class="toggle-switch">
        <input type="checkbox" data-field="${field.name}" data-type="toggle" ${checked}>
        <span class="toggle-slider"></span>
      </label>
    </div>
  `;
}

function renderInlineConditional(field) {
  const cond = field.condition;
  const opts = cond.options.map(o =>
    `<option value="${o}" ${o === cond.default ? 'selected' : ''}>${o}</option>`
  ).join('');

  return `
    <div class="form-row">
      <label>${escapeHtml(cond.label)}</label>
      <div class="input-wrapper"><div class="input-area">
        <select data-condition-for="${field.name}">${opts}</select>
        <input type="text" data-field="${field.name}" class="conditional-input" placeholder="${field.label || ''}">
      </div></div>
    </div>
  `;
}

function renderBlockConditional(field, contentRenderer) {
  const cond = field.condition;
  let html = '';

  // Toggle row for condition
  html += `
    <div class="toggle-row">
      <span class="toggle-label">${escapeHtml(cond.label)}</span>
      <label class="toggle-switch">
        <input type="checkbox" data-condition-for="${field.name}" ${cond.default ? 'checked' : ''}>
        <span class="toggle-slider"></span>
      </label>
    </div>
  `;

  // Conditional content section
  html += `<div class="conditional-section" data-condition="${field.name}" style="display:none">`;
  html += contentRenderer(field);
  html += `</div>`;

  return html;
}

function renderListSection(field) {
  return `
    <div class="field-section" data-field-section="${field.name}">
      <div class="section-header">
        <span class="section-title">${escapeHtml(field.label)}</span>
        <span class="count-badge" data-count="${field.name}">0</span>
      </div>
      <div class="input-with-button">
        <input type="text" data-list-input="${field.name}" placeholder="Enter item">
        <button type="button" class="add-btn" data-add="${field.name}">+</button>
      </div>
      <ul class="item-list" data-list="${field.name}"></ul>
      <div class="empty-message" data-empty="${field.name}">No items added</div>
      <div class="error-message" data-error="${field.name}"></div>
    </div>
  `;
}

function renderTextareaSection(field) {
  return `
    <div class="field-section" data-field-section="${field.name}">
      <div class="section-header">
        <span class="section-title">${escapeHtml(field.label)}</span>
        <span class="count-badge" data-count="${field.name}">0</span>
      </div>
      <textarea class="text-list-input" data-textarea="${field.name}" placeholder="One item per line"></textarea>
      <div class="error-message" data-error="${field.name}"></div>
    </div>
  `;
}

// ============ CONDITION LISTENERS ============

function setupConditionListeners(config) {
  document.querySelectorAll('[data-condition-for]').forEach(el => {
    const fieldName = el.dataset.conditionFor;
    const field = getFieldByName(fieldName, config);
    if (!field || !field.condition) return;

    // For inline conditionals (select → text): toggle CSS class
    const inlineInput = document.querySelector(`input.conditional-input[data-field="${fieldName}"]`);

    // For block conditionals (toggle → section): toggle display
    const blockSection = document.querySelector(`[data-condition="${fieldName}"]`);

    const updateVisibility = () => {
      if (field.condition.type === 'toggle') {
        // Block: toggle section display
        if (blockSection) blockSection.style.display = el.checked ? 'block' : 'none';
      } else if (field.condition.type === 'select') {
        const show = field.condition.showWhen?.includes(el.value);
        // Inline: toggle CSS class for smooth animation
        if (inlineInput) inlineInput.classList.toggle('visible', show);
        // Block: toggle section display
        if (blockSection) blockSection.style.display = show ? 'block' : 'none';
      }
    };

    el.addEventListener('change', updateVisibility);
    updateVisibility(); // Initial state
  });
}

function getFieldByName(name, config) {
  if (!config) {
    const creativeType = document.getElementById('creative-type').value;
    config = CREATIVE_TYPES[creativeType];
  }
  return (config?.fields || []).find(f => f.name === name);
}

// ============ FIELD EVENT LISTENERS ============

function attachFieldListeners(config) {
  for (const field of config.fields || []) {
    if (field.type === 'list') {
      const addBtn = document.querySelector(`[data-add="${field.name}"]`);
      const inputEl = document.querySelector(`[data-list-input="${field.name}"]`);

      if (addBtn && inputEl) {
        addBtn.addEventListener('click', () => addListItem(field));
        inputEl.addEventListener('keypress', (e) => {
          if (e.key === 'Enter') {
            e.preventDefault();
            addListItem(field);
          }
        });
      }
    }

    if (field.type === 'textarea') {
      const textarea = document.querySelector(`[data-textarea="${field.name}"]`);
      if (textarea) {
        textarea.addEventListener('input', () => updateTextareaCount(field));
      }
    }

    if (field.type === 'toggle' && !field.condition) {
      const toggle = document.querySelector(`[data-field="${field.name}"][data-type="toggle"]`);
      if (toggle) {
        toggle.addEventListener('change', () => {
          fieldData[field.name] = toggle.checked;
        });
      }
    }
  }
}

// ============ FIELD DATA MANAGEMENT ============

function addListItem(field) {
  const inputEl = document.querySelector(`[data-list-input="${field.name}"]`);
  const value = inputEl.value.trim();

  if (!value) return;

  // Check duplicates
  if (fieldData[field.name].includes(value)) {
    alert('This item has already been added');
    return;
  }

  fieldData[field.name].push(value);
  inputEl.value = '';
  renderList(field);
}

function removeListItem(fieldName, index) {
  fieldData[fieldName].splice(index, 1);
  const field = getFieldByName(fieldName);
  if (field) renderList(field);
}

function renderList(field) {
  const list = document.querySelector(`[data-list="${field.name}"]`);
  const empty = document.querySelector(`[data-empty="${field.name}"]`);
  const countBadge = document.querySelector(`[data-count="${field.name}"]`);
  const items = fieldData[field.name] || [];

  list.innerHTML = '';
  empty.style.display = items.length === 0 ? 'block' : 'none';

  if (countBadge) {
    countBadge.textContent = items.length;
    countBadge.classList.toggle('complete', items.length > 0);
  }

  items.forEach((item, index) => {
    const li = document.createElement('li');
    li.innerHTML = `
      <span class="item-text" title="${escapeHtml(item)}">${escapeHtml(truncateText(item))}</span>
      <button type="button" class="btn-remove" onclick="removeListItem('${field.name}', ${index})">&times;</button>
    `;
    list.appendChild(li);
  });
}

function updateTextareaCount(field) {
  const textarea = document.querySelector(`[data-textarea="${field.name}"]`);
  const countBadge = document.querySelector(`[data-count="${field.name}"]`);

  if (!textarea || !countBadge) return;

  const lines = getTextLines(textarea.value);
  countBadge.textContent = lines.length;
  countBadge.classList.toggle('complete', lines.length > 0);
}

function getTextLines(text) {
  return text.split('\n').map(l => l.trim()).filter(l => l.length > 0);
}

// ============ VALIDATION ============

function validateUniversalFields() {
  let valid = true;

  // Topic
  const topic = document.getElementById('topic');
  const topicError = document.getElementById('topic-error');
  if (!topic.value.trim()) {
    showError(topic, topicError, 'Topic is required');
    valid = false;
  } else {
    clearError(topic, topicError);
  }

  // URL
  const url = document.getElementById('url');
  const urlError = document.getElementById('url-error');
  const urlValue = url.value.trim();
  if (!urlValue) {
    showError(url, urlError, 'URL is required');
    valid = false;
  } else {
    try {
      const parsed = new URL(urlValue);
      if (!['bestselling.today', 'www.bestselling.today'].includes(parsed.hostname)) {
        showError(url, urlError, 'URL must be from bestselling.today');
        valid = false;
      } else {
        clearError(url, urlError);
      }
    } catch {
      showError(url, urlError, 'Invalid URL format');
      valid = false;
    }
  }

  // Page Type
  const pageType = document.getElementById('page-type');
  const pageTypeError = document.getElementById('page-type-error');
  if (!pageType.value) {
    showError(pageType, pageTypeError, 'Please select a page type');
    valid = false;
  } else {
    clearError(pageType, pageTypeError);
  }

  // Discount
  const discountType = document.getElementById('discount-type');
  const discountValue = document.getElementById('discount-value');
  const discountError = document.getElementById('discount-error');
  if (['constant', 'upto'].includes(discountType.value)) {
    const num = parseInt(discountValue.value, 10);
    if (!discountValue.value || isNaN(num) || num < 1 || num > 99) {
      showError(discountValue, discountError, 'Enter a number between 1-99');
      valid = false;
    } else {
      clearError(discountValue, discountError);
    }
  }

  // Event
  const eventType = document.getElementById('event-type');
  const eventName = document.getElementById('event-name');
  const eventError = document.getElementById('event-error');
  if (eventType.value === 'custom' && !eventName.value.trim()) {
    showError(eventName, eventError, 'Event name is required');
    valid = false;
  } else {
    clearError(eventName, eventError);
  }

  return valid;
}

function validateDynamicFields() {
  const creativeType = document.getElementById('creative-type').value;
  const config = CREATIVE_TYPES[creativeType];
  if (!config) return true;

  let valid = true;

  for (const field of config.fields || []) {
    // Skip if field has condition and condition is not met
    if (field.condition && !isConditionMet(field)) {
      continue;
    }

    const errorEl = document.querySelector(`[data-error="${field.name}"]`);
    if (!errorEl) continue;

    if (field.type === 'list' && field.required) {
      const items = fieldData[field.name] || [];
      if (items.length === 0) {
        errorEl.textContent = 'At least one item required';
        errorEl.classList.add('visible');
        valid = false;
      } else {
        errorEl.classList.remove('visible');
      }
    }

    if (field.type === 'textarea' && field.required) {
      const textarea = document.querySelector(`[data-textarea="${field.name}"]`);
      const lines = getTextLines(textarea?.value || '');
      if (lines.length === 0) {
        errorEl.textContent = 'At least one item required';
        errorEl.classList.add('visible');
        valid = false;
      } else {
        errorEl.classList.remove('visible');
      }
    }
  }

  return valid;
}

function isConditionMet(field) {
  if (!field.condition) return true;

  const condEl = document.querySelector(`[data-condition-for="${field.name}"]`);
  if (!condEl) return true;

  if (field.condition.type === 'toggle') {
    return condEl.checked;
  }
  if (field.condition.type === 'select') {
    return field.condition.showWhen?.includes(condEl.value);
  }
  return true;
}

function showError(input, errorDiv, message) {
  input.classList.add('invalid');
  errorDiv.textContent = message;
  errorDiv.classList.add('visible');
}

function clearError(input, errorDiv) {
  input.classList.remove('invalid');
  errorDiv.classList.remove('visible');
}

// ============ FORM SUBMISSION ============

function handleFormSubmit(e) {
  e.preventDefault();

  if (!validateUniversalFields() || !validateDynamicFields()) {
    return;
  }

  const campaign = collectFormData();
  campaigns.push(campaign);
  renderTable();
  resetForm();
}

function collectFormData() {
  const creativeType = document.getElementById('creative-type').value;
  const config = CREATIVE_TYPES[creativeType];

  const data = {
    creativeType,
    topic: document.getElementById('topic').value.trim(),
    url: document.getElementById('url').value.trim(),
    pageType: document.getElementById('page-type').value,
    discountType: document.getElementById('discount-type').value,
    discountValue: document.getElementById('discount-value').value.trim(),
    eventType: document.getElementById('event-type').value,
    eventName: document.getElementById('event-name').value.trim()
  };

  // Collect field values
  for (const field of config?.fields || []) {
    const value = collectFieldValue(field);
    if (value !== undefined) {
      data[field.name] = value;
    }
  }

  return data;
}

function collectFieldValue(field) {
  // If has condition, check if condition is met
  if (field.condition && !isConditionMet(field)) {
    return undefined; // Condition not met, don't send
  }

  // Return value based on type
  switch (field.type) {
    case 'text': {
      const input = document.querySelector(`[data-field="${field.name}"]`);
      return input?.value?.trim() || '';
    }
    case 'textarea': {
      const textarea = document.querySelector(`[data-textarea="${field.name}"]`);
      return getTextLines(textarea?.value || '');
    }
    case 'list':
      return [...(fieldData[field.name] || [])];
    case 'toggle': {
      const toggle = document.querySelector(`[data-field="${field.name}"][data-type="toggle"]`);
      return toggle?.checked ?? field.default ?? false;
    }
    case 'select': {
      const select = document.querySelector(`[data-field="${field.name}"]`);
      return select?.value || field.default || field.options?.[0];
    }
    default:
      return undefined;
  }
}

function resetForm() {
  // Reset universal fields
  document.getElementById('topic').value = '';
  document.getElementById('url').value = '';
  document.getElementById('page-type').value = '';
  document.getElementById('discount-type').value = 'none';
  document.getElementById('discount-value').value = '';
  document.getElementById('discount-value').classList.remove('visible');
  document.getElementById('event-type').value = 'none';
  document.getElementById('event-name').value = '';
  document.getElementById('event-name').classList.remove('visible');

  // Clear field data and re-render
  fieldData = {};
  const creativeType = document.getElementById('creative-type').value;
  renderDynamicFields(creativeType);

  document.getElementById('topic').focus();
}

// ============ QUEUE TABLE ============

function renderTable() {
  const tbody = document.getElementById('queue-body');
  const emptyState = document.getElementById('empty-state');
  const countSpan = document.getElementById('count');
  const sendBtn = document.getElementById('send-btn');

  tbody.innerHTML = '';

  campaigns.forEach((c, i) => {
    const tr = document.createElement('tr');
    tr.style.animationDelay = `${i * 0.05}s`;

    const discount = formatDiscount(c);
    const event = c.eventType === 'custom' ? c.eventName : '-';
    const urlPath = c.url ? new URL(c.url).pathname : '-';

    const config = CREATIVE_TYPES[c.creativeType];
    const typeLabel = config?.displayName || c.creativeType;

    tr.innerHTML = `
      <td>${i + 1}</td>
      <td><span class="cell-type highlight">${escapeHtml(typeLabel)}</span></td>
      <td class="cell-topic" title="${escapeHtml(c.topic)}">${escapeHtml(c.topic)}</td>
      <td class="cell-topic" title="${escapeHtml(c.url)}">${escapeHtml(urlPath)}</td>
      <td>${c.pageType}</td>
      <td>${discount}</td>
      <td>${escapeHtml(event)}</td>
      <td class="cell-actions">
        <button class="btn-action btn-edit" onclick="editCampaign(${i})"><span>&#9999;</span></button>
        <button class="btn-action btn-delete" onclick="deleteCampaign(${i})">&times;</button>
      </td>
    `;
    tbody.appendChild(tr);
  });

  const count = campaigns.length;
  emptyState.style.display = count === 0 ? 'block' : 'none';
  countSpan.textContent = `${count} campaign${count !== 1 ? 's' : ''} queued`;
  sendBtn.disabled = count === 0;
}

function formatDiscount(c) {
  switch (c.discountType) {
    case 'constant': return c.discountValue ? `${c.discountValue}%` : '-';
    case 'upto': return c.discountValue ? `up to ${c.discountValue}%` : '-';
    case '24h': return '24h';
    default: return '-';
  }
}

function editCampaign(index) {
  const campaign = campaigns[index];
  const config = CREATIVE_TYPES[campaign.creativeType];

  // Set creative type first
  document.getElementById('creative-type').value = campaign.creativeType;

  // Set universal fields
  document.getElementById('topic').value = campaign.topic;
  document.getElementById('url').value = campaign.url;
  document.getElementById('page-type').value = campaign.pageType;
  document.getElementById('discount-type').value = campaign.discountType;

  if (['constant', 'upto'].includes(campaign.discountType)) {
    document.getElementById('discount-value').classList.add('visible');
    document.getElementById('discount-value').value = campaign.discountValue;
  }

  document.getElementById('event-type').value = campaign.eventType;
  if (campaign.eventType === 'custom') {
    document.getElementById('event-name').classList.add('visible');
    document.getElementById('event-name').value = campaign.eventName;
  }

  // Restore field data
  fieldData = {};
  for (const field of config?.fields || []) {
    if (field.type === 'list') {
      fieldData[field.name] = [...(campaign[field.name] || [])];
    } else if (field.type === 'textarea') {
      fieldData[field.name] = (campaign[field.name] || []).join('\n');
    } else if (field.type === 'toggle') {
      fieldData[field.name] = campaign[field.name] ?? field.default ?? false;
    }
  }

  // Render form with restored data
  renderDynamicFields(campaign.creativeType);

  // Set toggle states and other field values
  for (const field of config?.fields || []) {
    if (field.type === 'toggle' && !field.condition) {
      const el = document.querySelector(`[data-field="${field.name}"][data-type="toggle"]`);
      if (el) el.checked = campaign[field.name] ?? field.default ?? false;
    }
    if (field.type === 'textarea') {
      const textarea = document.querySelector(`[data-textarea="${field.name}"]`);
      if (textarea) {
        textarea.value = fieldData[field.name];
        updateTextareaCount(field);
      }
    }
    if (field.type === 'list') {
      renderList(field);
    }
  }

  // Remove from queue
  campaigns.splice(index, 1);
  renderTable();

  document.getElementById('topic').focus();
}

function deleteCampaign(index) {
  campaigns.splice(index, 1);
  renderTable();
}

// ============ SEND CAMPAIGNS ============

function buildPayload(campaign) {
  const config = CREATIVE_TYPES[campaign.creativeType];

  const payload = {
    topic: campaign.topic,
    url: campaign.url,
    page_type: campaign.pageType,
    creative_type: campaign.creativeType
  };

  // Discount
  if (campaign.discountType === 'constant' && campaign.discountValue) {
    payload.discount = `${campaign.discountValue}%`;
  } else if (campaign.discountType === 'upto' && campaign.discountValue) {
    payload.discount = `up to ${campaign.discountValue}%`;
  } else if (campaign.discountType === '24h') {
    payload.discount = '24h';
  }

  // Event
  if (campaign.eventType === 'custom' && campaign.eventName) {
    payload.event = campaign.eventName;
  }

  // Dynamic fields
  for (const field of config?.fields || []) {
    const value = campaign[field.name];

    // Skip if no value or empty
    if (value === undefined || value === null) continue;
    if (Array.isArray(value) && value.length === 0) continue;
    if (value === '') continue;

    // For toggles, only send if different from default
    if (field.type === 'toggle' && value === field.default) continue;

    payload[field.name] = value;
  }

  return payload;
}

async function sendAll() {
  if (campaigns.length === 0) return;

  const sendBtn = document.getElementById('send-btn');
  sendBtn.disabled = true;
  showStatus('info', `Sending 0/${campaigns.length}...`);

  let sent = 0;
  let failed = 0;
  const errors = [];

  for (let i = 0; i < campaigns.length; i += CHUNK_SIZE) {
    const chunk = campaigns.slice(i, i + CHUNK_SIZE);

    const results = await Promise.allSettled(
      chunk.map(c => sendCampaign(c))
    );

    results.forEach((result, idx) => {
      if (result.status === 'fulfilled') {
        sent++;
      } else {
        failed++;
        errors.push({ index: i + idx, error: result.reason });
      }
    });

    showStatus('info', `Sending ${sent + failed}/${campaigns.length}...`);

    if (i + CHUNK_SIZE < campaigns.length) {
      await sleep(CHUNK_DELAY_MS);
    }
  }

  if (failed === 0) {
    showStatus('success', `All ${sent} campaigns sent successfully`);
    campaigns = [];
    renderTable();
  } else {
    showStatus('error', `Sent ${sent}, failed ${failed}. Check console for details.`);
    console.error('Failed campaigns:', errors);
    sendBtn.disabled = false;
  }
}

async function sendCampaign(campaign) {
  const response = await fetch(LAMBDA_URL, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(buildPayload(campaign))
  });

  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }

  return response.json();
}

// ============ UTILITIES ============

function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

function showStatus(type, message) {
  const statusDiv = document.getElementById('status');
  statusDiv.className = `visible ${type}`;
  statusDiv.textContent = message;
}

function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text || '';
  return div.innerHTML;
}

function truncateText(text) {
  if (!text) return '';
  if (text.length <= 40) return text;
  return text.substring(0, 37) + '...';
}

// Make functions globally accessible for onclick handlers
window.removeListItem = removeListItem;
window.editCampaign = editCampaign;
window.deleteCampaign = deleteCampaign;
