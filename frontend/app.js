/**
 * Competitor Monitor - Frontend Application
 * Мониторинг конкурентов - MVP ассистент
 */

// === State ===
const state = {
    currentTab: 'text',
    selectedImage: null,
    isLoading: false
};

// === DOM Elements ===
const elements = {
    // Navigation
    navButtons: document.querySelectorAll('.nav-btn'),
    tabContents: document.querySelectorAll('.tab-content'),
    
    // Text analysis
    competitorText: document.getElementById('competitor-text'),
    textShop: document.getElementById('text-shop'),
    analyzeTextBtn: document.getElementById('analyze-text-btn'),
    
    // Image analysis
    imageShop: document.getElementById('image-shop'),
    uploadZone: document.getElementById('upload-zone'),    imageInput: document.getElementById('image-input'),
    previewContainer: document.getElementById('preview-container'),
    imagePreview: document.getElementById('image-preview'),
    removeImageBtn: document.getElementById('remove-image'),
    analyzeImageBtn: document.getElementById('analyze-image-btn'),
    
    // Parse demo
    urlInput: document.getElementById('url-input'),
    parseShop: document.getElementById('parse-shop'),
    parseBtn: document.getElementById('parse-btn'),

    // Reviews
    reviewsShop: document.getElementById('reviews-shop'),
    reviewsSource: document.getElementById('reviews-source'),
    reviewsText: document.getElementById('reviews-text'),
    analyzeReviewsBtn: document.getElementById('analyze-reviews-btn'),

    // Compare
    compareList: document.getElementById('compare-list'),
    compareBtn: document.getElementById('compare-btn'),
    compareMatrix: document.getElementById('compare-matrix'),
    compareSummary: document.getElementById('compare-summary'),
    compareResults: document.getElementById('compare-results'),
    radarChart: document.getElementById('radar-chart'),

    // Competitors tab
    competitorsList: document.getElementById('competitors-list'),
    shopEditSelect: document.getElementById('shop-edit-select'),
    newShopId: document.getElementById('new-shop-id'),
    newShopName: document.getElementById('new-shop-name'),
    newShopUrl: document.getElementById('new-shop-url'),
    newShopMin: document.getElementById('new-shop-min'),
    newShopMax: document.getElementById('new-shop-max'),
    addShopBtn: document.getElementById('add-shop-btn'),
    deleteShopBtn: document.getElementById('delete-shop-btn'),
    
    // History
    historyList: document.getElementById('history-list'),
    clearHistoryBtn: document.getElementById('clear-history-btn'),
    
    // Results
    resultsSection: document.getElementById('results-section'),
    resultsContent: document.getElementById('results-content'),
    closeResultsBtn: document.getElementById('close-results'),
    
    // Loading
    loadingOverlay: document.getElementById('loading-overlay')
};

// === API Functions ===
const api = {
    baseUrl: '',
    
    async analyzeText(text, shop) {
        const response = await fetch(`${this.baseUrl}/analyze_text`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text, shop: shop || '' })
        });
        return response.json();
    },

    async analyzeImage(file, mode, shop) {
        const formData = new FormData();
        formData.append('file', file);

        const response = await fetch(
            `${this.baseUrl}/analyze_image?mode=${encodeURIComponent(mode || 'site')}&shop=${encodeURIComponent(shop || '')}`,
            { method: 'POST', body: formData }
        );
        return response.json();
    },
    
    async parseDemo(url, shop) {
        const response = await fetch(`${this.baseUrl}/parse_demo`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ url, shop: shop || '' })
        });
        return response.json();
    },

    async analyzeReviews(text, shop, source) {
        const response = await fetch(`${this.baseUrl}/analyze_reviews`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text, shop: shop || '', source: source || '' })
        });
        return response.json();
    },

    async getCompetitors() {
        const response = await fetch(`${this.baseUrl}/competitors`);
        return response.json();
    },

    async getCompetitorsFull() {
        const response = await fetch(`${this.baseUrl}/competitors/full`);
        return response.json();
    },

    async addCompetitor(payload) {
        const response = await fetch(`${this.baseUrl}/competitors`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        if (!response.ok) {
            const err = await response.json().catch(() => ({}));
            throw new Error(err.detail || `Ошибка ${response.status}`);
        }
        return response.json();
    },

    async updateCompetitor(shopId, payload) {
        const response = await fetch(`${this.baseUrl}/competitors/${encodeURIComponent(shopId)}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        if (!response.ok) {
            const err = await response.json().catch(() => ({}));
            throw new Error(err.detail || `Ошибка ${response.status}`);
        }
        return response.json();
    },

    async deleteCompetitor(shopId) {
        const response = await fetch(`${this.baseUrl}/competitors/${encodeURIComponent(shopId)}`, {
            method: 'DELETE'
        });
        if (!response.ok) {
            const err = await response.json().catch(() => ({}));
            throw new Error(err.detail || `Ошибка ${response.status}`);
        }
        return response.json();
    },

    async compareShops(shopIds) {
        const response = await fetch(`${this.baseUrl}/compare`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ shop_ids: shopIds })
        });
        return response.json();
    },
    
    async getHistory() {
        const response = await fetch(`${this.baseUrl}/history`);
        return response.json();
    },
    
    async clearHistory() {
        const response = await fetch(`${this.baseUrl}/history`, {
            method: 'DELETE'
        });
        return response.json();
    }
};

// === UI Functions ===
const ui = {
    showLoading() {
        state.isLoading = true;
        elements.loadingOverlay.style.display = 'flex';
    },
    
    hideLoading() {
        state.isLoading = false;
        elements.loadingOverlay.style.display = 'none';
    },
    
    showTab(tabId) {
        state.currentTab = tabId;
        
        // Update navigation
        elements.navButtons.forEach(btn => {
            btn.classList.toggle('active', btn.dataset.tab === tabId);
        });
        
        // Update content
        elements.tabContents.forEach(content => {
            content.classList.toggle('active', content.id === `${tabId}-tab`);
        });
        
        // Load history if needed
        if (tabId === 'history') {
            this.loadHistory();
        }

        // Refresh competitors (new names may appear)
        if (tabId === 'compare' || tabId === 'competitors') {
            handlers.loadCompetitors();
        }
    },
    
    showResults(html) {
        elements.resultsContent.innerHTML = html;
        elements.resultsSection.hidden = false;
        elements.resultsSection.scrollIntoView({ behavior: 'smooth' });
    },
    
    hideResults() {
        elements.resultsSection.hidden = true;
    },
    
    showError(message) {
        const html = `
            <div class="error-message">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <circle cx="12" cy="12" r="10"/>
                    <line x1="12" y1="8" x2="12" y2="12"/>
                    <line x1="12" y1="16" x2="12.01" y2="16"/>
                </svg>
                <span>${message}</span>
            </div>
        `;
        this.showResults(html);
    },
    
    renderScores(analysis, fields) {
        const labels = {
            design_score: 'Дизайн сайта',
            bouquet_design_score: 'Дизайн букетов',
            animation_potential: 'Анимации/интерактив',
            freshness_guarantee_score: 'Гарантия свежести',
            delivery_clarity_score: 'Понятность доставки',
            promo_offer_strength: 'Сила акций',
            visual_style_score: 'Визуальный стиль',
            color_harmony_score: 'Гармония цвета',
            instagrammability_score: 'Виральность'
        };
        const rows = (fields || []).filter(f => analysis && analysis[f] !== undefined && analysis[f] !== null && analysis[f] !== 0);
        if (!rows.length) return '';
        return `
            <div class="result-block">
                <h3>Оценки (0–10)</h3>
                ${rows.map(f => `
                    <div class="score-display">
                        <span>${labels[f] || f}</span>
                        <span class="score-value">${analysis[f]}/10</span>
                        <div class="score-bar"><div class="score-fill" style="width: ${(analysis[f] / 10) * 100}%"></div></div>
                    </div>
                `).join('')}
                ${analysis.price_segment ? `<p>Ценовой сегмент: ${analysis.price_segment}</p>` : ''}
            </div>
        `;
    },

    renderTextAnalysis(analysis) {
        return `
            ${this.renderScores(analysis, ['design_score', 'bouquet_design_score', 'animation_potential', 'freshness_guarantee_score', 'delivery_clarity_score', 'promo_offer_strength'])}
            ${this.renderResultBlock('Сильные стороны', analysis.strengths, 'strengths')}
            ${this.renderResultBlock('Слабые стороны', analysis.weaknesses, 'weaknesses')}
            ${this.renderResultBlock('Уникальные предложения', analysis.unique_offers, 'unique')}
            ${this.renderResultBlock('Рекомендации', analysis.recommendations, 'recommendations')}
            ${analysis.summary ? `
                <div class="result-block result-summary">
                    <h3>
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                            <polyline points="14 2 14 8 20 8"/>
                        </svg>
                        Резюме
                    </h3>
                    <p>${analysis.summary}</p>
                </div>
            ` : ''}
        `;
    },
    
    renderImageAnalysis(analysis, mode) {
        const scorePercent = (analysis.visual_style_score / 10) * 100;

        const bouquetExtra = (mode === 'bouquet') ? `
            ${analysis.bouquet_composition_analysis ? `
                <div class="result-block"><h3>Композиция букета</h3><p>${analysis.bouquet_composition_analysis}</p></div>
            ` : ''}
            ${this.renderResultBlock('Состав (распознанные цветы)', analysis.dominant_flowers, 'insights')}
            ${this.renderResultBlock('Оформление', analysis.styling_elements, 'insights')}
            ${this.renderResultBlock('Подходящие поводы', analysis.occasion_fit, 'insights')}
        ` : '';

        return `
            ${this.renderScores(analysis, mode === 'bouquet'
                ? ['design_score', 'visual_style_score', 'color_harmony_score', 'instagrammability_score']
                : ['design_score', 'visual_style_score', 'instagrammability_score'])}
            <div class="result-block">
                <h3>
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <rect x="3" y="3" width="18" height="18" rx="2" ry="2"/>
                        <circle cx="8.5" cy="8.5" r="1.5"/>
                        <polyline points="21 15 16 10 5 21"/>
                    </svg>
                    Описание изображения
                </h3>
                <p>${analysis.description}</p>
            </div>
            
            <div class="result-block">
                <h3>
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/>
                    </svg>
                    Оценка визуального стиля
                </h3>
                <div class="score-display">
                    <span class="score-value">${analysis.visual_style_score}/10</span>
                    <div class="score-bar">
                        <div class="score-fill" style="width: ${scorePercent}%"></div>
                    </div>
                </div>
                <p>${analysis.visual_style_analysis}</p>
            </div>
            
            ${this.renderResultBlock('Маркетинговые инсайты', analysis.marketing_insights, 'insights')}
            ${this.renderResultBlock('Рекомендации', analysis.recommendations, 'recommendations')}
            ${bouquetExtra}
        `;
    },

    renderReviews(analysis) {
        const pct = (v) => `${Math.round((v || 0) * 100)}%`;
        return `
            <div class="result-block">
                <h3>Тональность: ${(analysis.sentiment ?? 0).toFixed(2)} (−1…1)</h3>
                <p>Жалобы на доставку: ${pct(analysis.delivery_complaints_ratio)} · на свежесть: ${pct(analysis.freshness_complaints_ratio)} · несоответствие фото: ${analysis.photo_mismatch_mentions ?? 0}</p>
            </div>
            ${this.renderResultBlock('Хвалят', analysis.positive_themes, 'strengths')}
            ${this.renderResultBlock('Жалуются', analysis.negative_themes, 'weaknesses')}
            ${analysis.summary ? `<div class="result-block"><h3>Резюме</h3><p>${analysis.summary}</p></div>` : ''}
        `;
    },

    renderCompare(result) {
        if (!result || !result.matrix || !result.matrix.length) return '<p>Нет данных для сравнения</p>';
        const shops = result.competitors || [];
        const shopName = (sid) => (handlers._shops && handlers._shops[sid]) ? handlers._shops[sid].name : sid;
        let html = '<div class="result-block"><h3>Сравнительная матрица</h3><table class="compare-table"><thead><tr><th>Критерий</th>';
        shops.forEach(s => { html += `<th>${shopName(s)}</th>`; });
        html += '</tr></thead><tbody>';
        // Направление: цены — побеждает минимум, скоры — максимум
        const LOWER_IS_BETTER = new Set(['price_min', 'price_max']);
        result.matrix.forEach(row => {
            // Подсветка всех лучших (ничьи тоже желтым), только для числовых строк
            let best = null;
            const lower = LOWER_IS_BETTER.has(row.criterion);
            if (row.values) {
                Object.values(row.values).forEach(v => {
                    if (typeof v !== 'number') return;
                    if (best === null || (lower ? v < best : v > best)) best = v;
                });
            }
            html += `<tr><td>${row.criterion}</td>`;
            shops.forEach(s => {
                const v = row.values ? row.values[s] : '';
                const win = (best !== null && v === best) || (best === null && row.winner === s)
                    ? ' class="winner-cell"' : '';
                html += `<td${win}>${v ?? ''}</td>`;
            });
            html += '</tr>';
        });
        html += '</tbody></table></div>';
        return html;
    },

    drawRadar(result) {
        const canvas = elements.radarChart;
        if (!canvas || typeof Chart === 'undefined') return;
        if (this._radar) { this._radar.destroy(); this._radar = null; }
        const numericRows = (result.matrix || []).filter(r =>
            r.values && Object.values(r.values).every(v => typeof v === 'number'));
        const labels = numericRows.slice(0, 6).map(r => r.criterion);
        if (!labels.length) return;
        const palette = ['#22d3ee', '#a78bfa', '#34d399', '#fbbf24', '#f87171', '#60a5fa'];
        const datasets = (result.competitors || []).map((s, i) => ({
            label: (handlers._shops && handlers._shops[s]) ? handlers._shops[s].name : s,
            data: numericRows.slice(0, 6).map(r => r.values[s] ?? 0),
            borderColor: palette[i % palette.length],
            backgroundColor: palette[i % palette.length] + '33'
        }));
        this._radar = new Chart(canvas, {
            type: 'radar',
            data: { labels, datasets },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: { r: { min: 0, max: 10 } }
            }
        });
    },
    
    renderParsedContent(data) {
        const parsed = data;
        
        return `
            <div class="parsed-content">
                <div class="label">URL:</div>
                <div class="value">${parsed.url}</div>
                
                <div class="label">Title:</div>
                <div class="value">${parsed.title || 'Не найден'}</div>
                
                <div class="label">H1:</div>
                <div class="value">${parsed.h1 || 'Не найден'}</div>
                
                <div class="label">Первый абзац:</div>
                <div class="value">${parsed.first_paragraph || 'Не найден'}</div>
            </div>
            
            ${parsed.analysis ? this.renderTextAnalysis(parsed.analysis) : ''}
        `;
    },
    
    renderResultBlock(title, items, type) {
        if (!items || items.length === 0) return '';
        
        const icons = {
            strengths: '<path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/>',
            weaknesses: '<circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/>',
            unique: '<polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/>',
            recommendations: '<circle cx="12" cy="12" r="10"/><path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"/><line x1="12" y1="17" x2="12.01" y2="17"/>',
            insights: '<path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/>'
        };
        
        return `
            <div class="result-block">
                <h3>
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        ${icons[type] || icons.recommendations}
                    </svg>
                    ${title}
                </h3>
                <ul>
                    ${items.map(item => `<li>${item}</li>`).join('')}
                </ul>
            </div>
        `;
    },
    
    async loadHistory() {
        try {
            const data = await api.getHistory();
            this.renderHistory(data.items);
        } catch (error) {
            console.error('Failed to load history:', error);
        }
    },
    
    renderHistory(items) {
        if (!items || items.length === 0) {
            elements.historyList.innerHTML = `
                <div class="history-empty">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <circle cx="12" cy="12" r="10"/>
                        <polyline points="12 6 12 12 16 14"/>
                    </svg>
                    <p>История пуста</p>
                </div>
            `;
            return;
        }
        
        const icons = {
            text: '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/>',
            image: '<rect x="3" y="3" width="18" height="18" rx="2" ry="2"/><circle cx="8.5" cy="8.5" r="1.5"/><polyline points="21 15 16 10 5 21"/>',
            parse: '<circle cx="12" cy="12" r="10"/><line x1="2" y1="12" x2="22" y2="12"/><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/>'
        };
        
        const typeLabels = {
            text: 'Анализ текста',
            image: 'Анализ изображения',
            parse: 'Парсинг сайта'
        };
        
        elements.historyList.innerHTML = items.map(item => {
            const date = new Date(item.timestamp);
            const timeStr = date.toLocaleString('ru-RU', {
                day: '2-digit',
                month: '2-digit',
                hour: '2-digit',
                minute: '2-digit'
            });
            
            return `
                <div class="history-item">
                    <div class="history-icon">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            ${icons[item.request_type] || icons.text}
                        </svg>
                    </div>
                    <div class="history-content">
                        <div class="history-type">${typeLabels[item.request_type] || item.request_type}</div>
                        <div class="history-summary">${item.request_summary}</div>
                    </div>
                    <div class="history-time">${timeStr}</div>
                </div>
            `;
        }).join('');
    }
};

// === Event Handlers ===
const handlers = {
    // Navigation
    handleNavClick(e) {
        const btn = e.target.closest('.nav-btn');
        if (btn) {
            ui.showTab(btn.dataset.tab);
        }
    },
    
    // Text analysis
    async handleAnalyzeText() {
        const text = elements.competitorText.value.trim();
        const shop = elements.textShop ? elements.textShop.value.trim() : '';
        if (!handlers.requireShop(shop)) return;
        
        if (text.length < 10) {
            ui.showError('Введите текст минимум 10 символов для анализа');
            return;
        }
        
        ui.showLoading();
        
        try {
            const result = await api.analyzeText(text, shop);
            
            if (result.success && result.analysis) {
                ui.showResults(ui.renderTextAnalysis(result.analysis));
            } else {
                ui.showError(result.error || 'Произошла ошибка при анализе');
            }
        } catch (error) {
            ui.showError('Ошибка соединения с сервером');
            console.error(error);
        } finally {
            ui.hideLoading();
        }
    },
    
    // Image upload
    handleUploadClick() {
        elements.imageInput.click();
    },
    
    handleImageSelect(e) {
        const file = e.target.files[0];
        if (file) {
            this.processImage(file);
        }
    },
    
    handleDragOver(e) {
        e.preventDefault();
        elements.uploadZone.classList.add('dragover');
    },
    
    handleDragLeave(e) {
        e.preventDefault();
        elements.uploadZone.classList.remove('dragover');
    },
    
    handleDrop(e) {
        e.preventDefault();
        elements.uploadZone.classList.remove('dragover');
        
        const file = e.dataTransfer.files[0];
        if (file && file.type.startsWith('image/')) {
            this.processImage(file);
        }
    },
    
    processImage(file) {
        state.selectedImage = file;
        
        const reader = new FileReader();
        reader.onload = (e) => {
            elements.imagePreview.src = e.target.result;
            elements.previewContainer.hidden = false;
            elements.uploadZone.querySelector('.upload-content').hidden = true;
            elements.analyzeImageBtn.disabled = false;
        };
        reader.readAsDataURL(file);
    },
    
    handleRemoveImage() {
        state.selectedImage = null;
        elements.imageInput.value = '';
        elements.imagePreview.src = '';
        elements.previewContainer.hidden = true;
        elements.uploadZone.querySelector('.upload-content').hidden = false;
        elements.analyzeImageBtn.disabled = true;
    },
    
    async handleAnalyzeImage() {
        if (!state.selectedImage) {
            ui.showError('Выберите изображение для анализа');
            return;
        }

        const modeEl = document.querySelector('input[name="image-mode"]:checked');
        const mode = modeEl ? modeEl.value : 'site';
        const shop = elements.imageShop ? elements.imageShop.value.trim() : '';
        if (!handlers.requireShop(shop)) return;

        ui.showLoading();

        try {
            const result = await api.analyzeImage(state.selectedImage, mode, shop);

            if (result.success && result.analysis) {
                ui.showResults(ui.renderImageAnalysis(result.analysis, mode));
            } else {
                ui.showError(result.error || 'Произошла ошибка при анализе изображения');
            }
        } catch (error) {
            ui.showError('Ошибка соединения с сервером');
            console.error(error);
        } finally {
            ui.hideLoading();
        }
    },
    
    // Parse demo
    async handleParse() {
        let url = elements.urlInput.value.trim();
        const shop = elements.parseShop ? elements.parseShop.value.trim() : '';
        if (!handlers.requireShop(shop)) return;
        
        if (!url) {
            ui.showError('Введите URL сайта для парсинга');
            return;
        }
        
        // Add protocol if missing
        if (!url.startsWith('http://') && !url.startsWith('https://')) {
            url = 'https://' + url;
        }
        
        ui.showLoading();
        
        try {
            const result = await api.parseDemo(url, shop);
            
            if (result.success && result.data) {
                ui.showResults(ui.renderParsedContent(result.data));
            } else {
                ui.showError(result.error || 'Не удалось распарсить сайт');
            }
        } catch (error) {
            ui.showError('Ошибка соединения с сервером');
            console.error(error);
        } finally {
            ui.hideLoading();
        }
    },
    
    // Reviews
    async handleAnalyzeReviews() {
        const text = elements.reviewsText.value.trim();
        const shop = elements.reviewsShop.value.trim();
        const source = elements.reviewsSource.value.trim();
        if (!handlers.requireShop(shop)) return;

        if (text.length < 10) {
            ui.showError('Вставьте текст отзывов минимум 10 символов');
            return;
        }

        ui.showLoading();

        try {
            const result = await api.analyzeReviews(text, shop, source);

            if (result.success && result.analysis) {
                ui.showResults(ui.renderReviews(result.analysis));
            } else {
                ui.showError(result.error || 'Произошла ошибка при анализе отзывов');
            }
        } catch (error) {
            ui.showError('Ошибка соединения с сервером');
            console.error(error);
        } finally {
            ui.hideLoading();
        }
    },

    // Compare
    async loadCompetitors() {
        try {
            const data = await api.getCompetitors();
            const shops = data.items || [];
            handlers._shops = {};
            shops.forEach(s => { handlers._shops[s.id] = s; });
            const options = '<option value="">— выберите конкурента —</option>' + shops
                .map(s => `<option value="${s.id}">${s.name}</option>`)
                .join('');

            [elements.textShop, elements.imageShop, elements.parseShop, elements.reviewsShop]
                .forEach(sel => { if (sel) sel.innerHTML = options; });

            if (elements.compareList) {
                elements.compareList.innerHTML = shops.map(s => `
                    <label>
                        <input type="checkbox" class="compare-check" value="${s.id}">
                        ${s.name} (${s.price_min ?? '?'}–${s.price_max ?? '?'} ₽)
                    </label>
                `).join('');
            }

            await this.loadCompetitorsFull();
        } catch (error) {
            console.error('Failed to load competitors:', error);
        }
    },

    async loadCompetitorsFull() {
        if (!elements.competitorsList) return;
        try {
            const data = await api.getCompetitorsFull();
            const ids = Object.keys(data || {});
            if (!ids.length) {
                elements.competitorsList.innerHTML = '<p>Нет конкурентов</p>';
                return;
            }
            elements.competitorsList.innerHTML = ids.map(sid => {
                const s = data[sid] || {};
                const a = s.analyses || {};
                const objects = [];
                if (a.text) objects.push({ key: 'text', title: 'Текст', entry: a.text, kind: 'text' });
                if (a.site) objects.push({ key: 'site', title: 'Сайт', entry: a.site, kind: 'text' });
                (a.bouquets || []).forEach((e, i) => objects.push({ key: `bouquet-${i}`, title: `Букет ${i + 1}`, entry: e, kind: 'bouquet' }));
                (a.images || []).forEach((e, i) => objects.push({ key: `image-${i}`, title: `Скриншот ${i + 1}`, entry: e, kind: 'site' }));
                (a.reviews || []).forEach((e, i) => objects.push({ key: `review-${i}`, title: `Отзывы ${i + 1}`, entry: e, kind: 'reviews' }));
                const objectsHtml = objects.length ? objects.map(o => {
                    const meta = o.entry.meta || {};
                    const ts = (o.entry.ts || '').slice(0, 16).replace('T', ' ');
                    const sub = [ts, meta.filename, meta.url, meta.source, meta.mode].filter(Boolean).join(' · ');
                    let body = '';
                    try {
                        const r = o.entry.result || {};
                        if (o.kind === 'text') body = ui.renderTextAnalysis(r);
                        else if (o.kind === 'bouquet') body = ui.renderImageAnalysis(r, 'bouquet');
                        else if (o.kind === 'site') body = (r.description !== undefined)
                            ? ui.renderImageAnalysis(r, 'site')
                            : ui.renderTextAnalysis(r);
                        else if (o.kind === 'reviews') body = ui.renderReviews(r);
                    } catch (e) { body = '<p>Не удалось отобразить</p>'; }
                    return `<details class="analysis-item"><summary>${o.title}${sub ? ` <small>${sub}</small>` : ''}</summary>${body}</details>`;
                }).join('') : '<p>Анализов пока нет — привяжите анализ к конкуренту из других вкладок</p>';
                return `
                    <details class="competitor-item">
                        <summary>${s.name || sid} <small>id=${sid} · ${s.price_min ?? '?'}–${s.price_max ?? '?'} ₽ · ${s.url || ''}</small></summary>
                        ${objectsHtml}
                    </details>
                `;
            }).join('');

            // Форма редактирования: список + заполнение полей
            if (elements.shopEditSelect) {
                const current = elements.shopEditSelect.value;
                elements.shopEditSelect.innerHTML = '<option value="">— новый конкурент —</option>' + ids.map(sid =>
                    `<option value="${sid}">${(data[sid] || {}).name || sid}</option>`).join('');
                if (current && data[current]) elements.shopEditSelect.value = current;
            }
        } catch (error) {
            console.error('Failed to load competitors full:', error);
        }
    },

    // Подстановка сайта конкурента в поле URL (редактирование не блокируется)
    prefillParseUrl() {
        const sid = elements.parseShop ? elements.parseShop.value : '';
        const shop = sid && handlers._shops ? handlers._shops[sid] : null;
        if (shop && shop.url && elements.urlInput && !elements.urlInput.value) {
            elements.urlInput.value = shop.url.replace(/^https?:\/\//, '');
        }
    },

    // Очистка результатов + полей ввода при смене конкурента
    clearTabInputs(tabId) {
        ui.hideResults();
        if (tabId === 'text' && elements.competitorText) elements.competitorText.value = '';
        if (tabId === 'reviews') {
            if (elements.reviewsText) elements.reviewsText.value = '';
            if (elements.reviewsSource) elements.reviewsSource.value = '';
        }
        if (tabId === 'image' && handlers.handleRemoveImage) handlers.handleRemoveImage();
        if (tabId === 'parse' && elements.urlInput) elements.urlInput.value = '';
    },

    requireShop(value) {
        if (!value) {
            ui.showError('Выберите конкурента из списка');
            return false;
        }
        return true;
    },

    async handleAddShop() {
        const editId = elements.shopEditSelect ? elements.shopEditSelect.value : '';
        const name = elements.newShopName.value.trim();
        if (!name && !editId) {
            ui.showError('Название обязательно');
            return;
        }
        const toNum = (v) => (v !== '' && v !== null ? Number(v) : null);
        const url = elements.newShopUrl.value.trim();
        const priceMin = toNum(elements.newShopMin.value);
        const priceMax = toNum(elements.newShopMax.value);
        try {
            if (editId) {
                const payload = {};
                if (name) payload.name = name;
                payload.url = url;
                if (priceMin !== null) payload.price_min = priceMin;
                if (priceMax !== null) payload.price_max = priceMax;
                await api.updateCompetitor(editId, payload);
            } else {
                await api.addCompetitor({
                    id: elements.newShopId.value.trim(),
                    name,
                    url,
                    price_min: priceMin,
                    price_max: priceMax
                });
            }
            elements.newShopId.value = '';
            elements.newShopName.value = '';
            elements.newShopUrl.value = '';
            elements.newShopMin.value = '';
            elements.newShopMax.value = '';
            if (elements.shopEditSelect) elements.shopEditSelect.value = '';
            await handlers.loadCompetitors();
        } catch (error) {
            ui.showError(error.message || 'Не удалось сохранить');
        }
    },

    fillEditForm() {
        const sid = elements.shopEditSelect ? elements.shopEditSelect.value : '';
        if (!sid) return;
        api.getCompetitorsFull().then(data => {
            const s = (data || {})[sid];
            if (!s) return;
            elements.newShopId.value = s.id || sid;
            elements.newShopName.value = s.name || '';
            elements.newShopUrl.value = s.url || '';
            elements.newShopMin.value = (s.price_min ?? '');
            elements.newShopMax.value = (s.price_max ?? '');
        }).catch(e => console.error(e));
    },

    async handleDeleteShop() {
        const sid = elements.shopEditSelect ? elements.shopEditSelect.value : '';
        if (!sid) {
            ui.showError('Выберите конкурента для удаления');
            return;
        }
        if (!confirm(`Удалить конкурента и все его анализы?`)) return;
        try {
            await api.deleteCompetitor(sid);
            elements.shopEditSelect.value = '';
            elements.newShopId.value = '';
            elements.newShopName.value = '';
            elements.newShopUrl.value = '';
            elements.newShopMin.value = '';
            elements.newShopMax.value = '';
            await handlers.loadCompetitors();
        } catch (error) {
            ui.showError(error.message || 'Не удалось удалить');
        }
    },

    async handleCompare() {
        const checked = Array.from(document.querySelectorAll('.compare-check:checked'))
            .map(el => el.value);

        if (checked.length < 2) {
            ui.showError('Отметьте галками минимум 2 конкурентов');
            return;
        }

        ui.showLoading();

        try {
            const result = await api.compareShops(checked);

            if (result.success) {
                elements.compareResults.hidden = false;
                elements.compareMatrix.innerHTML = ui.renderCompare(result);
                elements.compareSummary.innerHTML = result.overall_summary
                    ? `<div class="result-block"><h3>Вывод</h3><p>${result.overall_summary}</p></div>` : '';
                ui.drawRadar(result);
                document.getElementById('radar-card').scrollIntoView({ behavior: 'smooth', block: 'start' });
            } else {
                ui.showError(result.error || 'Не удалось сравнить');
            }
        } catch (error) {
            ui.showError('Ошибка соединения с сервером');
            console.error(error);
        } finally {
            ui.hideLoading();
        }
    },

    // History
    async handleClearHistory() {
        if (!confirm('Вы уверены, что хотите очистить историю?')) {
            return;
        }
        
        try {
            await api.clearHistory();
            ui.renderHistory([]);
        } catch (error) {
            console.error('Failed to clear history:', error);
        }
    },
    
    // Results
    handleCloseResults() {
        ui.hideResults();
    }
};

// === Initialize ===
function init() {
    // Navigation
    elements.navButtons.forEach(btn => {
        btn.addEventListener('click', handlers.handleNavClick.bind(handlers));
    });
    
    // Text analysis
    elements.analyzeTextBtn.addEventListener('click', handlers.handleAnalyzeText.bind(handlers));
    
    // Image upload
    elements.uploadZone.addEventListener('click', handlers.handleUploadClick.bind(handlers));
    elements.imageInput.addEventListener('change', handlers.handleImageSelect.bind(handlers));
    elements.uploadZone.addEventListener('dragover', handlers.handleDragOver.bind(handlers));
    elements.uploadZone.addEventListener('dragleave', handlers.handleDragLeave.bind(handlers));
    elements.uploadZone.addEventListener('drop', handlers.handleDrop.bind(handlers));
    elements.removeImageBtn.addEventListener('click', handlers.handleRemoveImage.bind(handlers));
    elements.analyzeImageBtn.addEventListener('click', handlers.handleAnalyzeImage.bind(handlers));
    
    // Parse demo
    elements.parseBtn.addEventListener('click', handlers.handleParse.bind(handlers));
    elements.urlInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') handlers.handleParse.call(handlers);
    });

    // Reviews
    elements.analyzeReviewsBtn.addEventListener('click', handlers.handleAnalyzeReviews.bind(handlers));

    // Compare
    elements.compareBtn.addEventListener('click', handlers.handleCompare.bind(handlers));
    handlers.loadCompetitors();

    // Competitors tab
    elements.addShopBtn.addEventListener('click', handlers.handleAddShop.bind(handlers));
    elements.deleteShopBtn.addEventListener('click', handlers.handleDeleteShop.bind(handlers));
    elements.shopEditSelect.addEventListener('change', handlers.fillEditForm.bind(handlers));

    // Строгий выбор: смена конкурента очищает результаты и ввод вкладки
    const shopSelects = [
        [elements.textShop, 'text'],
        [elements.imageShop, 'image'],
        [elements.parseShop, 'parse'],
        [elements.reviewsShop, 'reviews']
    ];
    shopSelects.forEach(([sel, tabId]) => {
        if (sel) sel.addEventListener('change', () => handlers.clearTabInputs(tabId));
    });
    if (elements.parseShop) elements.parseShop.addEventListener('change', handlers.prefillParseUrl.bind(handlers));
    
    // History
    elements.clearHistoryBtn.addEventListener('click', handlers.handleClearHistory.bind(handlers));
    
    // Results
    elements.closeResultsBtn.addEventListener('click', handlers.handleCloseResults.bind(handlers));
    
    // Show default tab
    ui.showTab('text');
}

// Start app
document.addEventListener('DOMContentLoaded', init);

