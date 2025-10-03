// ============================================
// CONFIGURATION & GLOBAL STATE
// ============================================

const API_BASE = window.location.hostname === 'localhost' || 
         window.location.hostname === '127.0.0.1' ||
         window.location.protocol === 'file:'
    ? 'http://127.0.0.1:8000'
    : 'https://diaspora-backend-api.onrender.com';

let allArticles = [];
let filteredArticles = [];
let currentLanguage = 'all';
let selectedTopics = new Set();
let selectedLocations = new Set();
let translationsEnabled = false;

// TDA-20: User ID for reactions (stored in browser)
let userId = localStorage.getItem('diaspora_user_id');
if (!userId) {
    userId = 'user_' + Math.random().toString(36).substr(2, 9) + '_' + Date.now();
    localStorage.setItem('diaspora_user_id', userId);
}

// TDA-20: Store reaction data for optimistic UI
let reactionData = {};

// ============================================
// NEW: FILTER MODAL FUNCTIONS
// ============================================

function openFiltersModal() {
    const modal = document.getElementById('filterModal');
    modal.classList.add('active');
    document.body.style.overflow = 'hidden'; // Prevent background scrolling
    
    // Sync checkbox states with current selections
    syncModalCheckboxes();
    
    gtag('event', 'filters_modal_opened', {
        action: 'open_filters'
    });
}

function closeFiltersModal() {
    const modal = document.getElementById('filterModal');
    modal.classList.remove('active');
    document.body.style.overflow = ''; // Restore scrolling
    
    gtag('event', 'filters_modal_closed', {
        action: 'close_filters'
    });
}

function syncModalCheckboxes() {
    // Sync topic checkboxes
    document.querySelectorAll('input[data-topic]').forEach(checkbox => {
        const topic = checkbox.dataset.topic;
        checkbox.checked = selectedTopics.has(topic);
    });
    
    // Sync location checkboxes
    document.querySelectorAll('input[data-location]').forEach(checkbox => {
        const location = checkbox.dataset.location;
        checkbox.checked = selectedLocations.has(location);
    });
    
    // Sync translation toggle
    updateTranslationButton();
}

function toggleTopicCheckbox(topic) {
    if (selectedTopics.has(topic)) {
        selectedTopics.delete(topic);
    } else {
        selectedTopics.add(topic);
    }
    updateFilterBadge();
    // Note: We don't update the feed here - user clicks "Apply" to apply changes
}

function toggleLocationCheckbox(location) {
    if (selectedLocations.has(location)) {
        selectedLocations.delete(location);
    } else {
        selectedLocations.add(location);
    }
    updateFilterBadge();
    // Note: We don't update the feed here - user clicks "Apply" to apply changes
}

function clearAllFiltersInModal() {
    selectedTopics.clear();
    selectedLocations.clear();
    
    // Uncheck all checkboxes
    document.querySelectorAll('input[data-topic], input[data-location]').forEach(checkbox => {
        checkbox.checked = false;
    });
    
    updateFilterBadge();
    
    gtag('event', 'filters_cleared', {
        action: 'clear_all_filters_modal'
    });
}

function applyFiltersAndClose() {
    displayArticles(); // Apply the filters to the feed
    closeFiltersModal();
    
    gtag('event', 'filters_applied', {
        topics_count: selectedTopics.size,
        locations_count: selectedLocations.size
    });
}

function updateFilterBadge() {
    const totalFilters = selectedTopics.size + selectedLocations.size;
    const badge = document.getElementById('filterBadge');
    badge.textContent = totalFilters;
    
    // Hide badge if no filters active
    if (totalFilters === 0) {
        badge.style.display = 'none';
    } else {
        badge.style.display = 'inline-block';
    }
}

// ============================================
// TDA-18: LOCALSTORAGE PREFERENCES
// ============================================

function saveLanguagePreference(language) {
    localStorage.setItem('preferredLanguage', language);
}

function loadLanguagePreference() {
    const saved = localStorage.getItem('preferredLanguage');
    return saved || 'all';
}

function applySavedLanguagePreference() {
    const savedLanguage = loadLanguagePreference();
    currentLanguage = savedLanguage;
    
    document.querySelectorAll('.language-filter').forEach(btn => {
        if (btn.dataset.language === savedLanguage) {
            btn.classList.add('active');
        } else {
            btn.classList.remove('active');
        }
    });
    
    displayArticles();
}

function loadPreferences() {
    const savedTranslation = localStorage.getItem('translationsEnabled');
    if (savedTranslation === 'true') {
        translationsEnabled = true;
        updateTranslationButton();
    }
}

function saveTranslationPreference(value) {
    localStorage.setItem('translationsEnabled', value);
}

function updateTranslationButton() {
    const toggle = document.getElementById('translationToggle');
    if (toggle) {
        toggle.checked = translationsEnabled;
    }
}

// ============================================
// LOCATION FILTERS - UPDATED FOR MODAL
// ============================================

function buildLocationCheckboxes() {
    const allLocations = new Set();
    
    allArticles.forEach(article => {
        if (article.location_tags && Array.isArray(article.location_tags)) {
            article.location_tags.forEach(loc => {
                if (loc && loc.trim()) {
                    allLocations.add(loc.trim());
                }
            });
        }
    });

    const sortedLocations = Array.from(allLocations).sort();
    const container = document.getElementById('locationCheckboxesContainer');
    container.innerHTML = '';

    if (sortedLocations.length === 0) {
        container.innerHTML = '<p style="color: #999; font-size: 13px;">No locations detected in articles</p>';
        return;
    }

    sortedLocations.forEach(location => {
        const label = document.createElement('label');
        label.className = 'checkbox-item';
        
        const checkbox = document.createElement('input');
        checkbox.type = 'checkbox';
        checkbox.setAttribute('data-location', location);
        checkbox.onchange = () => toggleLocationCheckbox(location);
        
        if (selectedLocations.has(location)) {
            checkbox.checked = true;
        }
        
        const span = document.createElement('span');
        span.textContent = location;
        
        label.appendChild(checkbox);
        label.appendChild(span);
        container.appendChild(label);
    });
}

// ============================================
// CONTENT LOADING - FIXED
// ============================================

async function loadContent() {
    const contentGrid = document.getElementById('contentGrid');
    contentGrid.innerHTML = '<div class="loading"><div class="spinner"></div>Loading articles...</div>';

    try {
        const response = await fetch(`${API_BASE}/api/content/latest?limit=100`, {
            mode: 'cors'
        });
        if (!response.ok) throw new Error('Failed to fetch content');
        
        const data = await response.json();
        allArticles = data.items || [];
        
        // FIXED: Display articles immediately, load reactions in background
        buildLocationCheckboxes();
        applySavedLanguagePreference();
        updateFilterBadge();
        await loadStats();
        
        // Load reactions in background (non-blocking)
        loadAllReactions();
        
    } catch (error) {
        console.error('Error loading content:', error);
        contentGrid.innerHTML = `
            <div class="error">
                <p>Unable to load content</p>
                <p style="font-size: 14px; margin-top: 10px;">Make sure the backend is running at ${API_BASE}</p>
            </div>
        `;
    }
}

async function loadStats() {
    try {
        const response = await fetch(`${API_BASE}/api/stats`);
        const data = await response.json();
        
        const stats = data.stats;
        
        const statsBar = document.getElementById('statsBar');
        statsBar.innerHTML = `
            <div class="stat-item">
                <span>📰</span>
                <span>Total: ${stats.total_content || 0}</span>
            </div>
            <div class="stat-item">
                <span>🇳🇱</span>
                <span>Dutch: ${stats.dutch_content || 0}</span>
            </div>
            <div class="stat-item">
                <span>🇹🇷</span>
                <span>Turkish: ${stats.turkish_content || 0}</span>
            </div>
        `;
    } catch (error) {
        console.error('Error loading stats:', error);
    }
}

// ============================================
// TDA-20: EMOJI REACTIONS FUNCTIONS
// ============================================

async function loadAllReactions() {
    for (const article of allArticles) {
        await loadReactionsForArticle(article.id);
    }
}

async function loadReactionsForArticle(articleId) {
    try {
        const countsResponse = await fetch(`${API_BASE}/api/reactions/counts/${articleId}`);
        const countsData = await countsResponse.json();
        
        const userResponse = await fetch(`${API_BASE}/api/reactions/user/${articleId}/${userId}`);
        const userData = await userResponse.json();
        
        reactionData[articleId] = {
            counts: countsData.counts || {'👍': 0, '❤️': 0, '😂': 0, '🔥': 0, '👏': 0},
            userReaction: userData.emoji || null
        };
        
        // Update UI after loading each article's reactions
        updateReactionUI(articleId);
    } catch (error) {
        console.error(`Error loading reactions for article ${articleId}:`, error);
        reactionData[articleId] = {
            counts: {'👍': 0, '❤️': 0, '😂': 0, '🔥': 0, '👏': 0},
            userReaction: null
        };
    }
}

async function handleReactionClick(articleId, emoji, event) {
    event.stopPropagation();
    
    const oldUserReaction = reactionData[articleId]?.userReaction;
    const oldCounts = {...(reactionData[articleId]?.counts || {'👍': 0, '❤️': 0, '😂': 0, '🔥': 0, '👏': 0})};
    
    if (!reactionData[articleId]) {
        reactionData[articleId] = {
            counts: {'👍': 0, '❤️': 0, '😂': 0, '🔥': 0, '👏': 0},
            userReaction: null
        };
    }
    
    if (oldUserReaction === emoji) {
        reactionData[articleId].userReaction = null;
        reactionData[articleId].counts[emoji] = Math.max(0, (reactionData[articleId].counts[emoji] || 0) - 1);
    } else {
        if (oldUserReaction) {
            reactionData[articleId].counts[oldUserReaction] = Math.max(0, (reactionData[articleId].counts[oldUserReaction] || 0) - 1);
        }
        reactionData[articleId].counts[emoji] = (reactionData[articleId].counts[emoji] || 0) + 1;
        reactionData[articleId].userReaction = emoji;
    }
    
    updateReactionUI(articleId);
    
    gtag('event', 'reaction_click', {
        article_id: articleId,
        emoji: emoji,
        action: oldUserReaction === emoji ? 'removed' : 'added'
    });
    
    try {
        const response = await fetch(
            `${API_BASE}/api/reactions/add?content_id=${articleId}&user_id=${userId}&emoji=${encodeURIComponent(emoji)}`,
            { method: 'POST' }
        );
        const data = await response.json();
        
        if (data.success) {
            reactionData[articleId].counts = data.counts;
            updateReactionUI(articleId);
        } else {
            reactionData[articleId].userReaction = oldUserReaction;
            reactionData[articleId].counts = oldCounts;
            updateReactionUI(articleId);
            console.error('Failed to save reaction');
        }
    } catch (error) {
        reactionData[articleId].userReaction = oldUserReaction;
        reactionData[articleId].counts = oldCounts;
        updateReactionUI(articleId);
        console.error('Error saving reaction:', error);
    }
}

function updateReactionUI(articleId) {
    const emojis = ['👍', '❤️', '😂', '🔥', '👏'];
    const data = reactionData[articleId];
    
    if (!data) return;
    
    emojis.forEach(emoji => {
        const btn = document.querySelector(`[data-article-id="${articleId}"][data-emoji="${emoji}"]`);
        if (btn) {
            const count = data.counts[emoji] || 0;
            const isSelected = data.userReaction === emoji;
            
            if (isSelected) {
                btn.classList.add('selected');
            } else {
                btn.classList.remove('selected');
            }
            
            const countSpan = btn.querySelector('.reaction-count');
            if (countSpan) {
                countSpan.textContent = count;
            }
        }
    });
}

function createReactionsBar(articleId) {
    const emojis = ['👍', '❤️', '😂', '🔥', '👏'];
    const data = reactionData[articleId] || {
        counts: {'👍': 0, '❤️': 0, '😂': 0, '🔥': 0, '👏': 0},
        userReaction: null
    };
    
    const buttons = emojis.map(emoji => {
        const count = data.counts[emoji] || 0;
        const isSelected = data.userReaction === emoji;
        const selectedClass = isSelected ? 'selected' : '';
        
        return `
            <button 
                class="reaction-btn ${selectedClass}" 
                data-article-id="${articleId}"
                data-emoji="${emoji}"
                onclick="handleReactionClick('${articleId}', '${emoji}', event)"
                title="React with ${emoji}"
            >
                <span class="reaction-emoji">${emoji}</span>
                <span class="reaction-count">${count}</span>
            </button>
        `;
    }).join('');
    
    return `<div class="reactions-bar">${buttons}</div>`;
}

// ============================================
// ARTICLE DISPLAY
// ============================================

function displayArticles() {
    let filtered = [...allArticles];

    if (currentLanguage !== 'all') {
        filtered = filtered.filter(article => article.language === currentLanguage);
    }

    if (selectedTopics.size > 0) {
        filtered = filtered.filter(article => {
            if (!article.category_tags || article.category_tags.length === 0) return false;
            return article.category_tags.some(tag => selectedTopics.has(tag));
        });
    }

    if (selectedLocations.size > 0) {
        filtered = filtered.filter(article => {
            if (!article.location_tags || article.location_tags.length === 0) return false;
            return article.location_tags.some(loc => selectedLocations.has(loc));
        });
    }

    filteredArticles = filtered;

    const contentGrid = document.getElementById('contentGrid');

    if (filtered.length === 0) {
        contentGrid.innerHTML = `
            <div class="empty-state">
                <p>No articles found matching your filters</p>
                <p style="font-size: 14px; margin-top: 10px;">Try adjusting your filters</p>
            </div>
        `;
        return;
    }

    contentGrid.innerHTML = filtered.map((article, index) => {
        const displayTitle = translationsEnabled && article.translated_title 
            ? article.translated_title 
            : article.title;
        
        const displaySummary = translationsEnabled && article.translated_summary 
            ? article.translated_summary 
            : article.summary;

        const displayLanguage = translationsEnabled && article.translated_language
            ? article.translated_language
            : article.language;

        const languageBadge = displayLanguage === 'nl' 
            ? '<span class="badge badge-nl">NL</span>' 
            : '<span class="badge badge-tr">TR</span>';

        const translatedBadge = translationsEnabled && article.translated_title
            ? '<span class="badge badge-translated">Translated</span>'
            : '';

        const categoryTags = article.category_tags && article.category_tags.length > 0
            ? `<div class="article-tags">
                ${article.category_tags.map(tag => 
                    `<span class="tag-chip">${tag}</span>`
                ).join('')}
               </div>`
            : '';

        const locationTags = article.location_tags && article.location_tags.length > 0
            ? `<div class="location-tags">
                ${article.location_tags.map(loc => 
                    `<span class="location-badge">📍 ${loc}</span>`
                ).join('')}
               </div>`
            : '';

        const date = new Date(article.published_at).toLocaleDateString('en-US', {
            month: 'short',
            day: 'numeric',
            year: 'numeric'
        });

        return `
            <div class="article-card">
                <div class="article-content" onclick="openArticleByIndex(${index})">
                    <div class="article-header">
                        <div class="article-badges">
                            ${languageBadge}
                            ${translatedBadge}
                        </div>
                    </div>
                    <div class="article-title">${displayTitle}</div>
                    <div class="article-summary">${displaySummary}</div>
                    ${categoryTags}
                    ${locationTags}
                    <div class="article-meta">
                        <span class="article-source">${article.source?.name || 'Unknown'}</span>
                        <span>${date}</span>
                    </div>
                </div>
                ${createReactionsBar(article.id)}
            </div>
        `;
    }).join('');
}

function openArticleByIndex(index) {
    const article = filteredArticles[index];
    if (!article) {
        console.error('Article not found at index:', index);
        return;
    }

    gtag('event', 'article_click', {
        article_id: article.id,
        article_title: article.title,
        source: article.source?.name || 'Unknown',
        language: article.language,
        category: article.category_tags && article.category_tags.length > 0 ? article.category_tags[0] : 'General',
        location: article.location_tags && article.location_tags.length > 0 ? article.location_tags[0] : 'None',
        translations_enabled: translationsEnabled
    });
    
    window.open(article.url, '_blank');
}

// ============================================
// FILTER FUNCTIONS
// ============================================

function filterByLanguage(lang) {
    currentLanguage = lang;
    saveLanguagePreference(lang);
    
    gtag('event', 'language_filter', {
        selected_language: lang
    });
    
    document.querySelectorAll('.language-filter').forEach(btn => {
        if (btn.dataset.language === lang) {
            btn.classList.add('active');
        } else {
            btn.classList.remove('active');
        }
    });
    
    displayArticles();
}

function toggleTranslations() {
    translationsEnabled = !translationsEnabled;
    saveTranslationPreference(translationsEnabled);
    
    gtag('event', 'translation_toggle', {
        translations_enabled: translationsEnabled
    });
    
    updateTranslationButton();
    displayArticles();
}

// ============================================
// INITIALIZATION
// ============================================

loadPreferences();
loadContent();

// Auto-refresh every 5 minutes
setInterval(loadContent, 300000);

// Close modal when clicking ESC key
document.addEventListener('keydown', function(event) {
    if (event.key === 'Escape') {
        const modal = document.getElementById('filterModal');
        if (modal.classList.contains('active')) {
            closeFiltersModal();
        }
    }
});