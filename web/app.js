// ============================================
// CONFIGURATION & GLOBAL STATE
// ============================================

const API_BASE = window.location.hostname === 'localhost' || 
                 window.location.hostname === '127.0.0.1' ||
                 window.location.protocol === 'file:'
    ? 'http://127.0.0.1:8000'
    : 'https://diaspora-backend-api.onrender.com';

// Global state
let allArticles = [];
let filteredArticles = [];
let currentLanguage = 'all';
let translationsEnabled = false;
let userId = null;

// City lists for selection
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

// Generate or retrieve user ID
function getUserId() {
    let id = localStorage.getItem('userId');
    if (!id) {
        id = 'user_' + Math.random().toString(36).substr(2, 9) + '_' + Date.now();
        localStorage.setItem('userId', id);
    }
    return id;
}

userId = getUserId();

// ============================================
// LOAD PREFERENCES
// ============================================

function loadPreferences() {
    currentLanguage = localStorage.getItem('preferredLanguage') || 'all';
    translationsEnabled = localStorage.getItem('translationsEnabled') === 'true';
    updateTranslationButton();
}

function savePreference(key, value) {
    localStorage.setItem(key, value);
}

// ============================================
// CONTENT LOADING
// ============================================

async function loadContent() {
    try {
        document.getElementById('articleFeed').innerHTML = `
            <div class="loading">
                <div class="spinner"></div>
                <p>Loading articles...</p>
            </div>
        `;

        const response = await fetch(`${API_BASE}/api/content/main?limit=50`);
        const data = await response.json();

        if (data.success && data.items && data.items.length > 0) {
            allArticles = data.items;
            applySavedLanguagePreference();
            displayArticles();
            loadAllReactions();
        } else {
            throw new Error('No articles found');
        }
    } catch (error) {
        console.error('❌ Error loading content:', error);
        
        document.getElementById('articleFeed').innerHTML = `
            <div class="error">
                <h3>❌ Failed to load articles</h3>
                <p>Please check your connection and try again.</p>
                <button onclick="loadContent()" class="btn-primary">Retry</button>
            </div>
        `;
    }
}

// ============================================
// LANGUAGE FILTERING
// ============================================

function filterByLanguage(language) {
    currentLanguage = language;
    savePreference('preferredLanguage', language);
    
    document.querySelectorAll('.language-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    event.target.classList.add('active');
    
    displayArticles();
    
    if (typeof gtag !== 'undefined') {
        gtag('event', 'language_filter', {
            language: language
        });
    }
}

function applySavedLanguagePreference() {
    const savedLanguage = loadPreference('preferredLanguage') || 'all';
    currentLanguage = savedLanguage;
    
    document.querySelectorAll('.language-btn').forEach(btn => {
        btn.classList.remove('active');
        if ((savedLanguage === 'all' && btn.textContent === 'All') ||
            (savedLanguage === 'nl' && btn.textContent === 'Dutch') ||
            (savedLanguage === 'tr' && btn.textContent === 'Turkish')) {
            btn.classList.add('active');
        }
    });
}

function loadPreference(key) {
    return localStorage.getItem(key);
}

// ============================================
// DISPLAY ARTICLES
// ============================================

function displayArticles() {
    filteredArticles = allArticles.filter(article => {
        if (currentLanguage === 'all') return true;
        return article.language === currentLanguage;
    });

    const feedContainer = document.getElementById('articleFeed');
    
    if (filteredArticles.length === 0) {
        feedContainer.innerHTML = `
            <div style="text-align: center; padding: 60px 20px; color: #666;">
                <h3 style="font-size: 24px; margin-bottom: 20px;">No articles found</h3>
                <p style="font-size: 16px;">Try changing your filter settings</p>
            </div>
        `;
        return;
    }

    feedContainer.innerHTML = filteredArticles.map((article, index) => {
        const title = translationsEnabled && article.translated_title 
            ? article.translated_title 
            : article.title;
        
        const summary = translationsEnabled && article.translated_summary 
            ? article.translated_summary 
            : article.summary;
        
        const displayLanguage = translationsEnabled && article.translated_language
            ? article.translated_language
            : article.language;

        const categoryTags = article.category_tags && article.category_tags.length > 0
            ? article.category_tags.map(tag => 
                `<span class="tag">${tag}</span>`
              ).join('')
            : '';

        const locationTags = article.location_tags && article.location_tags.length > 0
            ? article.location_tags.map(tag => 
                `<span class="tag location-tag">📍 ${tag}</span>`
              ).join('')
            : '';

        const translatedBadge = translationsEnabled && article.translated_title
            ? '<span class="badge translated-badge">Translated</span>'
            : '';

        return `
            <div class="article-card" onclick="openArticle(${index})">
                <div class="article-header">
                    <div class="article-meta">
                        <span class="badge language-badge">${displayLanguage.toUpperCase()}</span>
                        ${translatedBadge}
                    </div>
                </div>
                <h3 class="article-title">${title}</h3>
                <p class="article-summary">${summary}</p>
                
                ${categoryTags || locationTags ? `
                    <div class="article-tags">
                        ${categoryTags}
                        ${locationTags}
                    </div>
                ` : ''}
                
                <div class="article-footer">
                    <span class="article-source">${article.source.name}</span>
                    <span class="article-date">${new Date(article.published_at).toLocaleDateString()}</span>
                </div>
                
                <div class="reactions-bar" onclick="event.stopPropagation()">
                    <button class="reaction-btn" onclick="toggleReaction('${article.id}', '👍')">
                        <span class="reaction-emoji">👍</span>
                        <span class="reaction-count" id="count-${article.id}-👍">0</span>
                    </button>
                    <button class="reaction-btn" onclick="toggleReaction('${article.id}', '❤️')">
                        <span class="reaction-emoji">❤️</span>
                        <span class="reaction-count" id="count-${article.id}-❤️">0</span>
                    </button>
                    <button class="reaction-btn" onclick="toggleReaction('${article.id}', '😂')">
                        <span class="reaction-emoji">😂</span>
                        <span class="reaction-count" id="count-${article.id}-😂">0</span>
                    </button>
                    <button class="reaction-btn" onclick="toggleReaction('${article.id}', '🔥')">
                        <span class="reaction-emoji">🔥</span>
                        <span class="reaction-count" id="count-${article.id}-🔥">0</span>
                    </button>
                    <button class="reaction-btn" onclick="toggleReaction('${article.id}', '👏')">
                        <span class="reaction-emoji">👏</span>
                        <span class="reaction-count" id="count-${article.id}-👏">0</span>
                    </button>
                </div>
            </div>
        `;
    }).join('');

    loadAllReactions();
}

// ============================================
// EMOJI REACTIONS
// ============================================

async function toggleReaction(contentId, emoji) {
    const btn = event.target.closest('.reaction-btn');
    const isSelected = btn.classList.contains('selected');
    
    btn.classList.toggle('selected');
    
    try {
        const response = await fetch(
            `${API_BASE}/api/reactions/add?content_id=${contentId}&user_id=${userId}&emoji=${encodeURIComponent(emoji)}`,
            { method: 'POST' }
        );
        
        const data = await response.json();
        
        if (data.success) {
            updateReactionCounts(contentId, data.counts);
            
            document.querySelectorAll(`[onclick*="${contentId}"]`).forEach(b => {
                if (b !== btn) b.classList.remove('selected');
            });
            
            if (data.action === 'removed') {
                btn.classList.remove('selected');
            }
        }
    } catch (error) {
        console.error('Reaction error:', error);
        btn.classList.toggle('selected');
    }
    
    if (typeof gtag !== 'undefined') {
        gtag('event', 'reaction', {
            emoji: emoji,
            action: isSelected ? 'remove' : 'add'
        });
    }
}

async function loadAllReactions() {
    for (const article of filteredArticles) {
        try {
            const [countsRes, userRes] = await Promise.all([
                fetch(`${API_BASE}/api/reactions/counts/${article.id}`),
                fetch(`${API_BASE}/api/reactions/user/${article.id}/${userId}`)
            ]);
            
            const countsData = await countsRes.json();
            const userData = await userRes.json();
            
            if (countsData.success) {
                updateReactionCounts(article.id, countsData.counts);
            }
            
            if (userData.success && userData.emoji) {
                const btn = document.querySelector(`[onclick="toggleReaction('${article.id}', '${userData.emoji}')"]`);
                if (btn) btn.classList.add('selected');
            }
        } catch (error) {
            console.error(`Error loading reactions for ${article.id}:`, error);
        }
    }
}

function updateReactionCounts(contentId, counts) {
    ['👍', '❤️', '😂', '🔥', '👏'].forEach(emoji => {
        const countEl = document.getElementById(`count-${contentId}-${emoji}`);
        if (countEl) {
            countEl.textContent = counts[emoji] || 0;
        }
    });
}

// ============================================
// TRANSLATION TOGGLE
// ============================================

function toggleTranslations() {
    translationsEnabled = !translationsEnabled;
    savePreference('translationsEnabled', translationsEnabled);
    updateTranslationButton();
    displayArticles();
    
    if (typeof gtag !== 'undefined') {
        gtag('event', 'translation_toggle', {
            enabled: translationsEnabled
        });
    }
}

function updateTranslationButton() {
    const btn = document.querySelector('.translation-toggle-btn');
    
    if (translationsEnabled) {
        btn.classList.add('active');
        btn.title = 'Translations: ON';
    } else {
        btn.classList.remove('active');
        btn.title = 'Translations: OFF';
    }
}

// ============================================
// OPEN ARTICLE
// ============================================

function openArticle(index) {
    const article = filteredArticles[index];
    window.open(article.url, '_blank');
    
    if (typeof gtag !== 'undefined') {
        gtag('event', 'article_click', {
            article_id: article.id,
            article_title: article.title,
            source: article.source.name,
            language: article.language
        });
    }
}

// ============================================
// ONBOARDING
// ============================================

let currentOnboardingScreen = 1;

function checkFirstVisit() {
    const hasVisited = localStorage.getItem('hasCompletedOnboarding');
    
    if (!hasVisited) {
        showOnboarding();
    }
}

function showOnboarding() {
    const modal = document.getElementById('onboardingModal');
    modal.classList.add('active');
    currentOnboardingScreen = 1;
    
    loadPreferencesIntoOnboarding();
}

function filterDutchCities() {
    const searchTerm = document.getElementById('dutchCitySearch').value.toLowerCase();
    const container = document.getElementById('dutchCityList');
    
    if (searchTerm.length < 1) {
        container.innerHTML = '';
        return;
    }
    
    const matches = DUTCH_CITIES.filter(city => 
        city.toLowerCase().includes(searchTerm)
    );
    
    container.innerHTML = matches.map(city => `
        <label>
            <input type="checkbox" class="dutch-city-checkbox" value="${city}">
            ${city}
        </label>
    `).join('');
    
    loadPreferencesIntoOnboarding();
}

function filterTurkishCities() {
    const searchTerm = document.getElementById('turkishCitySearch').value.toLowerCase();
    const container = document.getElementById('turkishCityList');
    
    if (searchTerm.length < 1) {
        container.innerHTML = '';
        return;
    }
    
    const matches = TURKISH_CITIES.filter(city => 
        city.toLowerCase().includes(searchTerm)
    );
    
    container.innerHTML = matches.map(city => `
        <label>
            <input type="checkbox" class="turkish-city-checkbox" value="${city}">
            ${city}
        </label>
    `).join('');
    
    loadPreferencesIntoOnboarding();
}

function nextOnboardingScreen() {
    document.getElementById(`onboardingScreen${currentOnboardingScreen}`).style.display = 'none';
    currentOnboardingScreen++;
    document.getElementById(`onboardingScreen${currentOnboardingScreen}`).style.display = 'block';
}

function prevOnboardingScreen() {
    document.getElementById(`onboardingScreen${currentOnboardingScreen}`).style.display = 'none';
    currentOnboardingScreen--;
    document.getElementById(`onboardingScreen${currentOnboardingScreen}`).style.display = 'block';
}

function skipOnboarding() {
    localStorage.setItem('hasCompletedOnboarding', 'true');
    closeOnboarding();
}

function finishOnboarding() {
    savePreferences();
    localStorage.setItem('hasCompletedOnboarding', 'true');
    closeOnboarding();
    
    showSuccessMessage('Preferences saved! Your feed is now personalized.');
    
    const activeTab = document.querySelector('.nav-btn.active');
    if (activeTab && activeTab.dataset.tab === 'foryou') {
        loadPersonalizedFeed();
    }
}

function closeOnboarding() {
    const modal = document.getElementById('onboardingModal');
    modal.classList.remove('active');
}

function loadPreferencesIntoOnboarding() {
    const savedCities = JSON.parse(localStorage.getItem('selectedCities') || '[]');
    const savedTopics = JSON.parse(localStorage.getItem('selectedTopics') || '[]');
    
    savedCities.forEach(city => {
        const checkbox = document.querySelector(`#onboardingScreen1 input[value="${city}"]`);
        if (checkbox) checkbox.checked = true;
    });
    
    savedTopics.forEach(topic => {
        const checkbox = document.querySelector(`#onboardingTopicSelection input[value="${topic}"]`);
        if (checkbox) checkbox.checked = true;
    });
}

function savePreferences() {
    const dutchCheckboxes = document.querySelectorAll('.dutch-city-checkbox:checked');
    const turkishCheckboxes = document.querySelectorAll('.turkish-city-checkbox:checked');
    
    const selectedCities = [];
    dutchCheckboxes.forEach(cb => selectedCities.push(cb.value));
    turkishCheckboxes.forEach(cb => selectedCities.push(cb.value));
    
    const topicCheckboxes = document.querySelectorAll('#onboardingTopicSelection input:checked');
    const selectedTopics = Array.from(topicCheckboxes).map(cb => cb.value);
    
    localStorage.setItem('selectedCities', JSON.stringify(selectedCities));
    localStorage.setItem('selectedTopics', JSON.stringify(selectedTopics));
    
    console.log('✅ Preferences saved:', { cities: selectedCities, topics: selectedTopics });
}

// ============================================
// SETTINGS MODAL
// ============================================

function openSettings() {
    const modal = document.getElementById('settingsModal');
    modal.classList.add('active');
    
    loadPreferencesIntoSettings();
    
    if (typeof gtag !== 'undefined') {
        gtag('event', 'open_settings');
    }
}

function closeSettings() {
    const modal = document.getElementById('settingsModal');
    modal.classList.remove('active');
}

function filterSettingsDutchCities() {
    const searchTerm = document.getElementById('settingsDutchCitySearch').value.toLowerCase();
    const container = document.getElementById('settingsDutchCityList');
    
    if (searchTerm.length < 1) {
        container.innerHTML = '';
        return;
    }
    
    const matches = DUTCH_CITIES.filter(city => 
        city.toLowerCase().includes(searchTerm)
    );
    
    container.innerHTML = matches.map(city => `
        <label>
            <input type="checkbox" class="settings-dutch-city-checkbox" value="${city}">
            ${city}
        </label>
    `).join('');
    
    loadPreferencesIntoSettings();
}

function filterSettingsTurkishCities() {
    const searchTerm = document.getElementById('settingsTurkishCitySearch').value.toLowerCase();
    const container = document.getElementById('settingsTurkishCityList');
    
    if (searchTerm.length < 1) {
        container.innerHTML = '';
        return;
    }
    
    const matches = TURKISH_CITIES.filter(city => 
        city.toLowerCase().includes(searchTerm)
    );
    
    container.innerHTML = matches.map(city => `
        <label>
            <input type="checkbox" class="settings-turkish-city-checkbox" value="${city}">
            ${city}
        </label>
    `).join('');
    
    loadPreferencesIntoSettings();
}

function loadPreferencesIntoSettings() {
    const savedCities = JSON.parse(localStorage.getItem('selectedCities') || '[]');
    const savedTopics = JSON.parse(localStorage.getItem('selectedTopics') || '[]');
    
    savedCities.forEach(city => {
        const checkbox = document.querySelector(`#settingsModal input[value="${city}"]`);
        if (checkbox) checkbox.checked = true;
    });
    
    savedTopics.forEach(topic => {
        const checkbox = document.querySelector(`#settingsTopicSelection input[value="${topic}"]`);
        if (checkbox) checkbox.checked = true;
    });
}

function clearAllPreferences() {
    if (confirm('Are you sure you want to clear all your preferences?')) {
        localStorage.removeItem('selectedCities');
        localStorage.removeItem('selectedTopics');
        
        document.querySelectorAll('#settingsModal input[type="checkbox"]').forEach(cb => {
            cb.checked = false;
        });
        
        document.getElementById('settingsDutchCitySearch').value = '';
        document.getElementById('settingsTurkishCitySearch').value = '';
        document.getElementById('settingsDutchCityList').innerHTML = '';
        document.getElementById('settingsTurkishCityList').innerHTML = '';
        
        showSuccessMessage('All preferences cleared');
        
        if (typeof gtag !== 'undefined') {
            gtag('event', 'clear_preferences');
        }
    }
}

function saveSettings() {
    const dutchCheckboxes = document.querySelectorAll('.settings-dutch-city-checkbox:checked');
    const turkishCheckboxes = document.querySelectorAll('.settings-turkish-city-checkbox:checked');
    
    const selectedCities = [];
    dutchCheckboxes.forEach(cb => selectedCities.push(cb.value));
    turkishCheckboxes.forEach(cb => selectedCities.push(cb.value));
    
    const topicCheckboxes = document.querySelectorAll('#settingsTopicSelection input:checked');
    const selectedTopics = Array.from(topicCheckboxes).map(cb => cb.value);
    
    localStorage.setItem('selectedCities', JSON.stringify(selectedCities));
    localStorage.setItem('selectedTopics', JSON.stringify(selectedTopics));
    
    console.log('✅ Settings saved:', { cities: selectedCities, topics: selectedTopics });
    
    closeSettings();
    
    showSuccessMessage('Settings saved successfully!');
    
    const activeTab = document.querySelector('.nav-btn.active');
    if (activeTab && activeTab.dataset.tab === 'foryou') {
        loadPersonalizedFeed();
    }
    
    if (typeof gtag !== 'undefined') {
        gtag('event', 'save_settings', {
            cities_count: selectedCities.length,
            topics_count: selectedTopics.length
        });
    }
}

function showSuccessMessage(message) {
    const existingMsg = document.querySelector('.success-message');
    if (existingMsg) existingMsg.remove();
    
    const msgDiv = document.createElement('div');
    msgDiv.className = 'success-message';
    msgDiv.textContent = message;
    document.body.appendChild(msgDiv);
    
    setTimeout(() => {
        msgDiv.remove();
    }, 3000);
}

// ============================================
// PERSONALIZED FEED
// ============================================

async function loadPersonalizedFeed() {
    const savedCities = JSON.parse(localStorage.getItem('selectedCities') || '[]');
    const savedTopics = JSON.parse(localStorage.getItem('selectedTopics') || '[]');
    
    if (savedCities.length === 0 && savedTopics.length === 0) {
        document.getElementById('articleFeed').innerHTML = `
            <div style="text-align: center; padding: 60px 20px; color: #666;">
                <h3 style="font-size: 24px; margin-bottom: 20px;">No preferences set</h3>
                <p style="font-size: 16px; margin-bottom: 30px;">
                    Select your favorite cities and topics to see personalized content
                </p>
                <button onclick="openSettings()" class="btn-primary">
                    Set Your Preferences
                </button>
            </div>
        `;
        return;
    }
    
    document.getElementById('articleFeed').innerHTML = `
        <div class="loading">
            <div class="spinner"></div>
            <p>Loading your personalized feed...</p>
        </div>
    `;
    
    try {
        const citiesParam = savedCities.join(',');
        const topicsParam = savedTopics.join(',');
        
        const url = `${API_BASE}/api/content/personalized?cities=${encodeURIComponent(citiesParam)}&topics=${encodeURIComponent(topicsParam)}&limit=50`;
        
        console.log('📡 Fetching personalized feed:', url);
        
        const response = await fetch(url);
        const data = await response.json();
        
        if (data.success && data.items && data.items.length > 0) {
            allArticles = data.items;
            currentLanguage = 'all';
            displayArticles();
            
            console.log(`✅ Loaded ${data.items.length} personalized articles`);
            
            if (typeof gtag !== 'undefined') {
                gtag('event', 'load_personalized_feed', {
                    article_count: data.items.length,
                    cities_count: savedCities.length,
                    topics_count: savedTopics.length
                });
            }
        } else {
            document.getElementById('articleFeed').innerHTML = `
                <div style="text-align: center; padding: 60px 20px; color: #666;">
                    <h3 style="font-size: 24px; margin-bottom: 20px;">No articles found</h3>
                    <p style="font-size: 16px; margin-bottom: 30px;">
                        We couldn't find articles matching your preferences.<br>
                        Try adjusting your city or topic selections.
                    </p>
                    <button onclick="openSettings()" class="btn-primary">
                        Update Preferences
                    </button>
                </div>
            `;
        }
        
    } catch (error) {
        console.error('❌ Error loading personalized feed:', error);
        
        document.getElementById('articleFeed').innerHTML = `
            <div class="error">
                <h3>Failed to load personalized feed</h3>
                <p>Please check your connection and try again.</p>
                <button onclick="loadPersonalizedFeed()" class="btn-primary">Retry</button>
            </div>
        `;
    }
}

// ============================================
// FOOTER NAVIGATION
// ============================================

function switchToMainFeed() {
    console.log('Switching to Main feed');
    
    document.querySelectorAll('.nav-btn').forEach(btn => {
        btn.classList.remove('active');
        if (btn.dataset.tab === 'main') {
            btn.classList.add('active');
        }
    });
    
    const filterBar = document.getElementById('languageFilterBar');
    if (filterBar) {
        filterBar.style.display = 'flex';
    }
    
    loadContent();
    
    if (typeof gtag !== 'undefined') {
        gtag('event', 'tab_switch', {
            tab_name: 'main'
        });
    }
}

function switchToForYouFeed() {
    console.log('Switching to For You feed (personalized)');
    
    document.querySelectorAll('.nav-btn').forEach(btn => {
        btn.classList.remove('active');
        if (btn.dataset.tab === 'foryou') {
            btn.classList.add('active');
        }
    });
    
    const filterBar = document.getElementById('languageFilterBar');
    if (filterBar) {
        filterBar.style.display = 'none';
    }
    
    loadPersonalizedFeed();
    
    if (typeof gtag !== 'undefined') {
        gtag('event', 'tab_switch', {
            tab_name: 'for_you'
        });
    }
}

// ============================================
// INITIALIZATION
// ============================================

loadPreferences();
loadContent();
checkFirstVisit();

setInterval(loadContent, 300000);

console.log('✅ Diaspora app initialized');