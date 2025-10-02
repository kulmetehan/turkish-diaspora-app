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
// PHASE 2: PERSONALIZATION DATA & STATE
// ============================================

// 50 Cities from backend (25 Dutch + 25 Turkish)
const DUTCH_CITIES = [
    'Rotterdam', 'Amsterdam', 'Den Haag', 'Utrecht', 'Zaanstad',
    'Eindhoven', 'Enschede', 'Arnhem', 'Tilburg', 'Schiedam',
    'Deventer', 'Dordrecht', 'Haarlem', 'Amersfoort', 'Almelo',
    'Nijmegen', 'Vlaardingen', 'Hengelo', 'Almere', 'Apeldoorn',
    'Oss', 'Venlo', 'Haarlemmermeer', 'Breda', 'Bergen op Zoom'
];

const TURKISH_CITIES = [
    'Konya', 'Kayseri', 'Ankara', 'Yozgat', 'Karaman',
    'Kırşehir', 'Niğde', 'Nevşehir', 'Aksaray', 'Adana',
    'Sivas', 'Kars', 'Trabzon', 'Samsun', 'Aydın',
    'İzmir', 'İstanbul', 'Gaziantep', 'Afyonkarahisar', 'Giresun',
    'Denizli', 'Ordu', 'Sakarya', 'Kahramanmaraş', 'Erzincan'
];

// Personalization state
let personalizationPreferences = {
    dutchCities: [],
    turkishCities: [],
    topics: [],
    personalizationEnabled: false
};

// ============================================
// FILTER MODAL FUNCTIONS
// ============================================

function openFiltersModal() {
    const modal = document.getElementById('filterModal');
    modal.classList.add('active');
    document.body.style.overflow = 'hidden';
    
    syncModalCheckboxes();
    
    gtag('event', 'filters_modal_opened', {
        action: 'open_filters'
    });
}

function closeFiltersModal() {
    const modal = document.getElementById('filterModal');
    modal.classList.remove('active');
    document.body.style.overflow = '';
    
    gtag('event', 'filters_modal_closed', {
        action: 'close_filters'
    });
}

function syncModalCheckboxes() {
    document.querySelectorAll('input[data-topic]').forEach(checkbox => {
        const topic = checkbox.dataset.topic;
        checkbox.checked = selectedTopics.has(topic);
    });
    
    document.querySelectorAll('input[data-location]').forEach(checkbox => {
        const location = checkbox.dataset.location;
        checkbox.checked = selectedLocations.has(location);
    });
    
    updateTranslationButton();
}

function toggleTopicCheckbox(topic) {
    if (selectedTopics.has(topic)) {
        selectedTopics.delete(topic);
    } else {
        selectedTopics.add(topic);
    }
    updateFilterBadge();
}

function toggleLocationCheckbox(location) {
    if (selectedLocations.has(location)) {
        selectedLocations.delete(location);
    } else {
        selectedLocations.add(location);
    }
    updateFilterBadge();
}

function clearAllFiltersInModal() {
    selectedTopics.clear();
    selectedLocations.clear();
    
    document.querySelectorAll('input[data-topic], input[data-location]').forEach(checkbox => {
        checkbox.checked = false;
    });
    
    updateFilterBadge();
    
    gtag('event', 'filters_cleared', {
        action: 'clear_all_filters_modal'
    });
}

function applyFiltersAndClose() {
    displayArticles();
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
    
    if (totalFilters === 0) {
        badge.style.display = 'none';
    } else {
        badge.style.display = 'inline-block';
    }
}

// ============================================
// PHASE 2: PERSONALIZATION MODAL FUNCTIONS
// ============================================

function openPersonalizationModal() {
    const modal = document.getElementById('personalizationModal');
    modal.classList.add('active');
    document.body.style.overflow = 'hidden';
    
    // Load current preferences into modal
    loadPreferencesIntoModal();
    
    gtag('event', 'personalization_modal_opened', {
        action: 'open_personalization'
    });
}

function closePersonalizationModal() {
    const modal = document.getElementById('personalizationModal');
    modal.classList.remove('active');
    document.body.style.overflow = '';
    
    // Clear search inputs
    document.getElementById('dutchCitySearch').value = '';
    document.getElementById('turkishCitySearch').value = '';
    hideDutchDropdown();
    hideTurkishDropdown();
    
    gtag('event', 'personalization_modal_closed', {
        action: 'close_personalization'
    });
}

function loadPreferencesIntoModal() {
    // Display selected Dutch cities
    displaySelectedDutchCities();
    
    // Display selected Turkish cities
    displaySelectedTurkishCities();
    
    // Check selected topics
    document.querySelectorAll('.topic-checkbox input[type="checkbox"]').forEach(checkbox => {
        checkbox.checked = personalizationPreferences.topics.includes(checkbox.value);
    });
}

// ============================================
// PHASE 2: FUZZY SEARCH FUNCTION
// ============================================

function fuzzySearch(query, text) {
    query = query.toLowerCase();
    text = text.toLowerCase();
    
    // Exact match gets highest priority
    if (text === query) return 1000;
    
    // Starts with query gets high priority
    if (text.startsWith(query)) return 500;
    
    // Contains query gets medium priority
    if (text.includes(query)) return 250;
    
    // Fuzzy matching: check if all characters in query appear in order
    let queryIndex = 0;
    let score = 0;
    
    for (let i = 0; i < text.length && queryIndex < query.length; i++) {
        if (text[i] === query[queryIndex]) {
            score += 100 - i; // Earlier matches score higher
            queryIndex++;
        }
    }
    
    // All characters found in order
    if (queryIndex === query.length) {
        return score;
    }
    
    return 0; // No match
}

// ============================================
// PHASE 2: DUTCH CITIES AUTOCOMPLETE
// ============================================

function filterDutchCities(query) {
    const dropdown = document.getElementById('dutchCityDropdown');
    
    if (!query || query.trim() === '') {
        dropdown.innerHTML = '';
        dropdown.classList.remove('active');
        return;
    }
    
    // Filter cities using fuzzy search
    const matches = DUTCH_CITIES
        .map(city => ({ city, score: fuzzySearch(query, city) }))
        .filter(item => item.score > 0)
        .sort((a, b) => b.score - a.score)
        .map(item => item.city);
    
    if (matches.length === 0) {
        dropdown.innerHTML = '<div class="autocomplete-no-results">No cities found</div>';
        dropdown.classList.add('active');
        return;
    }
    
    dropdown.innerHTML = matches.map(city => {
        const isSelected = personalizationPreferences.dutchCities.includes(city);
        const className = isSelected ? 'autocomplete-item selected' : 'autocomplete-item';
        const onclick = isSelected ? '' : `onclick="selectDutchCity('${city}')"`;
        return `<div class="${className}" ${onclick}>${city}</div>`;
    }).join('');
    
    dropdown.classList.add('active');
}

function showDutchDropdown() {
    const input = document.getElementById('dutchCitySearch');
    filterDutchCities(input.value);
}

function hideDutchDropdown() {
    const dropdown = document.getElementById('dutchCityDropdown');
    setTimeout(() => {
        dropdown.classList.remove('active');
    }, 200);
}

function selectDutchCity(city) {
    if (!personalizationPreferences.dutchCities.includes(city)) {
        personalizationPreferences.dutchCities.push(city);
        displaySelectedDutchCities();
        
        // Clear search and hide dropdown
        document.getElementById('dutchCitySearch').value = '';
        hideDutchDropdown();
    }
}

function removeDutchCity(city) {
    personalizationPreferences.dutchCities = personalizationPreferences.dutchCities.filter(c => c !== city);
    displaySelectedDutchCities();
}

function displaySelectedDutchCities() {
    const container = document.getElementById('selectedDutchCities');
    
    if (personalizationPreferences.dutchCities.length === 0) {
        container.innerHTML = '';
        return;
    }
    
    container.innerHTML = personalizationPreferences.dutchCities.map(city => `
        <div class="city-chip">
            🇳🇱 ${city}
            <button class="city-chip-remove" onclick="removeDutchCity('${city}')">×</button>
        </div>
    `).join('');
}

// ============================================
// PHASE 2: TURKISH CITIES AUTOCOMPLETE
// ============================================

function filterTurkishCities(query) {
    const dropdown = document.getElementById('turkishCityDropdown');
    
    if (!query || query.trim() === '') {
        dropdown.innerHTML = '';
        dropdown.classList.remove('active');
        return;
    }
    
    const matches = TURKISH_CITIES
        .map(city => ({ city, score: fuzzySearch(query, city) }))
        .filter(item => item.score > 0)
        .sort((a, b) => b.score - a.score)
        .map(item => item.city);
    
    if (matches.length === 0) {
        dropdown.innerHTML = '<div class="autocomplete-no-results">No cities found</div>';
        dropdown.classList.add('active');
        return;
    }
    
    dropdown.innerHTML = matches.map(city => {
        const isSelected = personalizationPreferences.turkishCities.includes(city);
        const className = isSelected ? 'autocomplete-item selected' : 'autocomplete-item';
        const onclick = isSelected ? '' : `onclick="selectTurkishCity('${city}')"`;
        return `<div class="${className}" ${onclick}>${city}</div>`;
    }).join('');
    
    dropdown.classList.add('active');
}

function showTurkishDropdown() {
    const input = document.getElementById('turkishCitySearch');
    filterTurkishCities(input.value);
}

function hideTurkishDropdown() {
    const dropdown = document.getElementById('turkishCityDropdown');
    setTimeout(() => {
        dropdown.classList.remove('active');
    }, 200);
}

function selectTurkishCity(city) {
    if (!personalizationPreferences.turkishCities.includes(city)) {
        personalizationPreferences.turkishCities.push(city);
        displaySelectedTurkishCities();
        
        document.getElementById('turkishCitySearch').value = '';
        hideTurkishDropdown();
    }
}

function removeTurkishCity(city) {
    personalizationPreferences.turkishCities = personalizationPreferences.turkishCities.filter(c => c !== city);
    displaySelectedTurkishCities();
}

function displaySelectedTurkishCities() {
    const container = document.getElementById('selectedTurkishCities');
    
    if (personalizationPreferences.turkishCities.length === 0) {
        container.innerHTML = '';
        return;
    }
    
    container.innerHTML = personalizationPreferences.turkishCities.map(city => `
        <div class="city-chip">
            🇹🇷 ${city}
            <button class="city-chip-remove" onclick="removeTurkishCity('${city}')">×</button>
        </div>
    `).join('');
}

// ============================================
// PHASE 2: TOPIC SELECTION
// ============================================

function togglePersonalizationTopic(topic) {
    if (personalizationPreferences.topics.includes(topic)) {
        personalizationPreferences.topics = personalizationPreferences.topics.filter(t => t !== topic);
    } else {
        personalizationPreferences.topics.push(topic);
    }
}

// ============================================
// PHASE 2: SAVE/LOAD PERSONALIZATION
// ============================================

function savePersonalizationPreferences() {
    // Mark as enabled if user has selected anything
    const hasSelections = 
        personalizationPreferences.dutchCities.length > 0 ||
        personalizationPreferences.turkishCities.length > 0 ||
        personalizationPreferences.topics.length > 0;
    
    personalizationPreferences.personalizationEnabled = hasSelections;
    
    // Save to localStorage
    localStorage.setItem('personalizationPreferences', JSON.stringify(personalizationPreferences));
    
    console.log('Saved personalization:', personalizationPreferences);
    
    // Close modal
    closePersonalizationModal();
    
    // Show success message
    alert('✅ Preferences saved!\n\nClick "For You" tab to see your personalized feed.');
    
    gtag('event', 'personalization_saved', {
        dutch_cities: personalizationPreferences.dutchCities.length,
        turkish_cities: personalizationPreferences.turkishCities.length,
        topics: personalizationPreferences.topics.length
    });
}

function loadPersonalizationPreferences() {
    try {
        const saved = localStorage.getItem('personalizationPreferences');
        if (saved) {
            personalizationPreferences = JSON.parse(saved);
            console.log('Loaded personalization:', personalizationPreferences);
        }
    } catch (error) {
        console.error('Error loading personalization preferences:', error);
    }
}

// ============================================
// LOCALSTORAGE PREFERENCES
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
    
    // Load personalization preferences
    loadPersonalizationPreferences();
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
// LOCATION FILTERS
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
// CONTENT LOADING
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
        
        buildLocationCheckboxes();
        applySavedLanguagePreference();
        updateFilterBadge();
        await loadStats();
        
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
// EMOJI REACTIONS FUNCTIONS
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
// PHASE 3: FOR YOU FEED
// ============================================

async function switchToForYouFeed() {
    // Update nav button states
    document.querySelectorAll('.nav-btn').forEach(btn => {
        btn.classList.remove('active');
        if (btn.dataset.tab === 'foryou') {
            btn.classList.add('active');
        }
    });
    
    // Check if user has personalization set up
    if (!personalizationPreferences.personalizationEnabled) {
        // Show empty state - prompt to personalize
        const contentGrid = document.getElementById('contentGrid');
        contentGrid.innerHTML = `
            <div class="empty-state">
                <div style="font-size: 60px; margin-bottom: 20px;">⭐</div>
                <h2 style="font-size: 24px; margin-bottom: 15px; color: #333;">Create Your Personal Feed</h2>
                <p style="font-size: 16px; color: #666; margin-bottom: 30px;">
                    Select your favorite cities and topics to see news that matters to you.
                </p>
                <button onclick="openPersonalizationModal()" style="
                    padding: 14px 32px;
                    background: linear-gradient(135deg, #E30A17 0%, #C7000B 100%);
                    color: white;
                    border: none;
                    border-radius: 25px;
                    font-size: 16px;
                    font-weight: 700;
                    cursor: pointer;
                    box-shadow: 0 4px 12px rgba(227, 10, 23, 0.3);
                ">
                    🎯 Get Started
                </button>
            </div>
        `;
        
        gtag('event', 'for_you_empty_state_shown');
        return;
    }
    
    // User has preferences - fetch personalized content
    await loadPersonalizedContent();
    
    gtag('event', 'tab_switch', {
        tab_name: 'foryou',
        has_preferences: true
    });
}

async function loadPersonalizedContent() {
    const contentGrid = document.getElementById('contentGrid');
    contentGrid.innerHTML = '<div class="loading"><div class="spinner"></div>Loading your personalized feed...</div>';
    
    try {
        // Build query parameters from preferences
        const allCities = [
            ...personalizationPreferences.dutchCities,
            ...personalizationPreferences.turkishCities
        ];
        
        const params = new URLSearchParams();
        if (allCities.length > 0) {
            params.append('cities', allCities.join(','));
        }
        if (personalizationPreferences.topics.length > 0) {
            params.append('topics', personalizationPreferences.topics.join(','));
        }
        params.append('limit', '50');
        
        const url = `${API_BASE}/api/content/personalized?${params.toString()}`;
        console.log('Fetching personalized content:', url);
        
        const response = await fetch(url, { mode: 'cors' });
        if (!response.ok) throw new Error('Failed to fetch personalized content');
        
        const data = await response.json();
        const personalizedArticles = data.items || [];
        
        console.log(`Loaded ${personalizedArticles.length} personalized articles`);
        
        if (personalizedArticles.length === 0) {
            contentGrid.innerHTML = `
                <div class="empty-state">
                    <div style="font-size: 60px; margin-bottom: 20px;">🔍</div>
                    <h2 style="font-size: 24px; margin-bottom: 15px; color: #333;">No Articles Found</h2>
                    <p style="font-size: 16px; color: #666; margin-bottom: 20px;">
                        No articles match your current preferences.
                    </p>
                    <p style="font-size: 14px; color: #999; margin-bottom: 30px;">
                        Try adding more cities or topics, or check back later for new content.
                    </p>
                    <button onclick="openPersonalizationModal()" style="
                        padding: 12px 28px;
                        background: #E30A17;
                        color: white;
                        border: none;
                        border-radius: 20px;
                        font-size: 15px;
                        font-weight: 600;
                        cursor: pointer;
                    ">
                        ✏️ Edit Preferences
                    </button>
                </div>
            `;
            return;
        }
        
        // Display personalized articles
        filteredArticles = personalizedArticles;
        
        contentGrid.innerHTML = personalizedArticles.map((article, index) => {
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
        
        // Load reactions for personalized articles
        for (const article of personalizedArticles) {
            await loadReactionsForArticle(article.id);
        }
        
    } catch (error) {
        console.error('Error loading personalized content:', error);
        contentGrid.innerHTML = `
            <div class="error">
                <p>Unable to load personalized content</p>
                <p style="font-size: 14px; margin-top: 10px;">Please try again or adjust your preferences.</p>
                <button onclick="switchToMainFeed()" style="
                    margin-top: 20px;
                    padding: 10px 24px;
                    background: #E30A17;
                    color: white;
                    border: none;
                    border-radius: 20px;
                    cursor: pointer;
                ">
                    Back to Main Feed
                </button>
            </div>
        `;
    }
}

// ============================================
// FOOTER NAVIGATION
// ============================================

function switchToMainFeed() {
    // Update nav button states
    document.querySelectorAll('.nav-btn').forEach(btn => {
        btn.classList.remove('active');
        if (btn.dataset.tab === 'main') {
            btn.classList.add('active');
        }
    });
    
    // Reload main content
    displayArticles();
    
    console.log('Switched to Main feed');
    
    gtag('event', 'tab_switch', {
        tab_name: 'main'
    });
}

// ============================================
// INITIALIZATION
// ============================================

loadPreferences();
loadContent();

// Auto-refresh every 5 minutes
setInterval(loadContent, 300000);

// Close modals when clicking ESC key
document.addEventListener('keydown', function(event) {
    if (event.key === 'Escape') {
        const filterModal = document.getElementById('filterModal');
        const personalizationModal = document.getElementById('personalizationModal');
        
        if (filterModal.classList.contains('active')) {
            closeFiltersModal();
        }
        if (personalizationModal.classList.contains('active')) {
            closePersonalizationModal();
        }
    }
});

// Close dropdowns when clicking outside
document.addEventListener('click', function(event) {
    const dutchSearch = document.getElementById('dutchCitySearch');
    const turkishSearch = document.getElementById('turkishCitySearch');
    const dutchDropdown = document.getElementById('dutchCityDropdown');
    const turkishDropdown = document.getElementById('turkishCityDropdown');
    
    if (dutchSearch && !dutchSearch.contains(event.target) && !dutchDropdown.contains(event.target)) {
        hideDutchDropdown();
    }
    
    if (turkishSearch && !turkishSearch.contains(event.target) && !turkishDropdown.contains(event.target)) {
        hideTurkishDropdown();
    }
});

console.log('✅ Diaspora app initialized with personalization');