// Case Browser - Murder Index
// Connects to Supabase backend for case data

document.addEventListener('DOMContentLoaded', async () => {
    // Elements
    const caseGrid = document.getElementById('caseGrid');
    const caseCount = document.getElementById('caseCount');
    const loadingState = document.getElementById('loadingState');
    const emptyState = document.getElementById('emptyState');
    const searchInput = document.getElementById('searchInput');
    const clearSearch = document.getElementById('clearSearch');
    const filterState = document.getElementById('filterState');
    const filterType = document.getElementById('filterType');
    const filterYear = document.getElementById('filterYear');
    const filterUnsolved = document.getElementById('filterUnsolved');
    const viewToggle = document.getElementById('viewToggle');
    const prevPage = document.getElementById('prevPage');
    const nextPage = document.getElementById('nextPage');
    const pageInfo = document.getElementById('pageInfo');
    const pagination = document.getElementById('pagination');
    
    // Stats elements
    const statTotal = document.getElementById('statTotal');
    const statUnsolved = document.getElementById('statUnsolved');
    const statMissing = document.getElementById('statMissing');
    const statStates = document.getElementById('statStates');
    
    // Modal elements
    const caseModal = document.getElementById('caseModal');
    const modalBackdrop = document.getElementById('modalBackdrop');
    const modalClose = document.getElementById('modalClose');
    const modalTitle = document.getElementById('modalTitle');
    const modalMeta = document.getElementById('modalMeta');
    const modalBadge = document.getElementById('modalBadge');
    const modalSummary = document.getElementById('modalSummary');
    const modalVictim = document.getElementById('modalVictim');
    const modalEvidence = document.getElementById('modalEvidence');
    const modalTimeline = document.getElementById('modalTimeline');
    const modalSource = document.getElementById('modalSource');
    const modalVictimSection = document.getElementById('modalVictimSection');
    const modalEvidenceSection = document.getElementById('modalEvidenceSection');
    const modalTimelineSection = document.getElementById('modalTimelineSection');
    const modalUpgrade = document.getElementById('modalUpgrade');
    const modalDownload = document.getElementById('modalDownload');
    
    // Content warning & media elements
    const contentWarning = document.getElementById('contentWarning');
    const dismissWarning = document.getElementById('dismissWarning');
    const mediaSection = document.getElementById('mediaSection');
    const mediaGallery = document.getElementById('mediaGallery');
    const mediaAttribution = document.getElementById('mediaAttribution');
    
    // Track if user has dismissed warning this session
    let warningDismissed = sessionStorage.getItem('warningDismissed') === 'true';
    
    // State
    let cases = [];
    let filteredCases = [];
    let currentPage = 1;
    const pageSize = 24;
    let isListView = false;
    let unsolvedOnly = true;
    let allStates = [];
    let allYears = [];
    
    // API base URL - detect environment
    const API_BASE = window.location.hostname === 'localhost' 
        ? 'http://localhost:8000'
        : '/api';  // Vercel proxy
    
    // ========== DATA FETCHING ==========
    async function fetchCases() {
        showLoading(true);
        
        try {
            // Try API first
            const response = await fetch(`${API_BASE}/cases?limit=1000`);
            if (response.ok) {
                const data = await response.json();
                cases = data.cases || data;
                console.log(`📋 Loaded ${cases.length} cases from API`);
            } else {
                throw new Error('API not available');
            }
        } catch (e) {
            console.log('⚠️ API not available, loading sample data...');
            // Load sample/demo data
            cases = generateSampleCases();
        }
        
        // Extract unique states and years for filters
        extractFilterOptions();
        populateFilters();
        
        // Initial filter and render
        applyFilters();
        showLoading(false);
    }
    
    async function fetchStats() {
        try {
            const response = await fetch(`${API_BASE}/cases/stats`);
            if (response.ok) {
                const stats = await response.json();
                updateStats(stats);
                return;
            }
        } catch (e) {
            console.log('⚠️ Stats API not available');
        }
        
        // Calculate from local data
        updateStats({
            total_cases: cases.length,
            unsolved_cases: cases.filter(c => c.status === 'unsolved').length,
            missing_persons: cases.filter(c => c.case_type === 'missing_person').length,
            states_covered: new Set(cases.map(c => c.state)).size
        });
    }
    
    function updateStats(stats) {
        statTotal.textContent = formatNumber(stats.total_cases || 0);
        statUnsolved.textContent = formatNumber(stats.unsolved_cases || 0);
        statMissing.textContent = formatNumber(stats.missing_persons || 0);
        statStates.textContent = stats.states_covered || 0;
    }
    
    function formatNumber(num) {
        if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M';
        if (num >= 1000) return (num / 1000).toFixed(1) + 'K';
        return num.toString();
    }
    
    // ========== SAMPLE DATA ==========
    function generateSampleCases() {
        const states = ['California', 'Texas', 'Florida', 'New York', 'Illinois', 'Ohio', 'Georgia', 'Pennsylvania', 'Michigan', 'Arizona'];
        const cities = {
            'California': ['Los Angeles', 'San Francisco', 'San Diego', 'Oakland'],
            'Texas': ['Houston', 'Dallas', 'Austin', 'San Antonio'],
            'Florida': ['Miami', 'Tampa', 'Orlando', 'Jacksonville'],
            'New York': ['New York City', 'Buffalo', 'Albany', 'Rochester'],
            'Illinois': ['Chicago', 'Springfield', 'Rockford'],
            'Ohio': ['Columbus', 'Cleveland', 'Cincinnati'],
            'Georgia': ['Atlanta', 'Savannah', 'Augusta'],
            'Pennsylvania': ['Philadelphia', 'Pittsburgh', 'Harrisburg'],
            'Michigan': ['Detroit', 'Grand Rapids', 'Lansing'],
            'Arizona': ['Phoenix', 'Tucson', 'Mesa']
        };
        const weapons = ['Handgun', 'Knife', 'Blunt Object', 'Unknown', 'Strangulation', 'Rifle'];
        const relationships = ['Stranger', 'Acquaintance', 'Unknown', 'Family', 'Friend'];
        
        const sampleCases = [];
        for (let i = 0; i < 100; i++) {
            const state = states[Math.floor(Math.random() * states.length)];
            const city = cities[state][Math.floor(Math.random() * cities[state].length)];
            const year = 1980 + Math.floor(Math.random() * 35);
            const month = Math.floor(Math.random() * 12) + 1;
            const age = 18 + Math.floor(Math.random() * 50);
            const gender = Math.random() > 0.4 ? 'male' : 'female';
            const weapon = weapons[Math.floor(Math.random() * weapons.length)];
            
            sampleCases.push({
                id: `sample-${i}`,
                case_id: `CASE-${year}-${String(i).padStart(5, '0')}`,
                title: `Homicide - ${city}, ${state} (${year})`,
                case_type: 'homicide',
                status: 'unsolved',
                date_occurred: `${year}-${String(month).padStart(2, '0')}-01`,
                city: city,
                state: state,
                country: 'USA',
                summary: `A ${age}-year-old ${gender} victim was found in ${city}, ${state}. The weapon used was ${weapon.toLowerCase()}. This case remains unsolved.`,
                source_dataset: 'kaggle_homicide',
                source_url: 'https://www.kaggle.com/datasets/murderaccountability/homicide-reports',
                victim: {
                    age: age,
                    gender: gender,
                    race: ['White', 'Black', 'Hispanic', 'Asian'][Math.floor(Math.random() * 4)]
                },
                evidence: [
                    { type: 'physical', description: `Weapon: ${weapon}` },
                    { type: 'circumstantial', description: `Relationship: ${relationships[Math.floor(Math.random() * relationships.length)]}` }
                ]
            });
        }
        
        return sampleCases;
    }
    
    // ========== FILTERS ==========
    function extractFilterOptions() {
        const stateSet = new Set();
        const yearSet = new Set();
        
        cases.forEach(c => {
            if (c.state) stateSet.add(c.state);
            if (c.date_occurred) {
                const year = new Date(c.date_occurred).getFullYear();
                if (!isNaN(year)) yearSet.add(year);
            }
        });
        
        allStates = Array.from(stateSet).sort();
        allYears = Array.from(yearSet).sort((a, b) => b - a);
    }
    
    function populateFilters() {
        // States
        filterState.innerHTML = '<option value="">All States</option>';
        allStates.forEach(state => {
            const opt = document.createElement('option');
            opt.value = state;
            opt.textContent = state;
            filterState.appendChild(opt);
        });
        
        // Years - group by decade for large datasets
        filterYear.innerHTML = '<option value="">All Years</option>';
        if (allYears.length > 20) {
            // Group by decade
            const decades = [...new Set(allYears.map(y => Math.floor(y / 10) * 10))].sort((a, b) => b - a);
            decades.forEach(decade => {
                const opt = document.createElement('option');
                opt.value = `${decade}s`;
                opt.textContent = `${decade}s`;
                filterYear.appendChild(opt);
            });
        } else {
            allYears.forEach(year => {
                const opt = document.createElement('option');
                opt.value = year;
                opt.textContent = year;
                filterYear.appendChild(opt);
            });
        }
    }
    
    function applyFilters() {
        const search = searchInput.value.toLowerCase().trim();
        const stateFilter = filterState.value;
        const typeFilter = filterType.value;
        const yearFilter = filterYear.value;
        
        filteredCases = cases.filter(c => {
            // Unsolved filter
            if (unsolvedOnly && c.status !== 'unsolved') return false;
            
            // Search
            if (search) {
                const searchFields = [c.title, c.city, c.state, c.summary].join(' ').toLowerCase();
                if (!searchFields.includes(search)) return false;
            }
            
            // State filter
            if (stateFilter && c.state !== stateFilter) return false;
            
            // Type filter
            if (typeFilter && c.case_type !== typeFilter) return false;
            
            // Year filter
            if (yearFilter && c.date_occurred) {
                const caseYear = new Date(c.date_occurred).getFullYear();
                if (yearFilter.endsWith('s')) {
                    const decade = parseInt(yearFilter);
                    if (caseYear < decade || caseYear >= decade + 10) return false;
                } else if (caseYear !== parseInt(yearFilter)) {
                    return false;
                }
            }
            
            return true;
        });
        
        // Sort by quality score (best cases first)
        filteredCases.sort((a, b) => {
            const scoreA = getCaseQualityScore(a);
            const scoreB = getCaseQualityScore(b);
            return scoreB - scoreA;
        });
        
        // Reset to page 1
        currentPage = 1;
        renderCases();
        updateCaseCount();
    }
    
    // ========== RENDERING ==========
    function showLoading(show) {
        loadingState.classList.toggle('hidden', !show);
        caseGrid.classList.toggle('hidden', show);
        pagination.classList.toggle('hidden', show);
    }
    
    function updateCaseCount() {
        caseCount.textContent = `${formatNumber(filteredCases.length)} cases`;
    }
    
    function renderCases() {
        const start = (currentPage - 1) * pageSize;
        const end = start + pageSize;
        const pageCases = filteredCases.slice(start, end);
        
        if (pageCases.length === 0) {
            caseGrid.innerHTML = '';
            emptyState.classList.remove('hidden');
            pagination.classList.add('hidden');
            return;
        }
        
        emptyState.classList.add('hidden');
        pagination.classList.remove('hidden');
        
        caseGrid.innerHTML = pageCases.map(c => renderCaseCard(c)).join('');
        
        // Update pagination
        const totalPages = Math.ceil(filteredCases.length / pageSize);
        pageInfo.textContent = `Page ${currentPage} of ${totalPages}`;
        prevPage.disabled = currentPage === 1;
        nextPage.disabled = currentPage === totalPages;
        
        // Add click handlers
        caseGrid.querySelectorAll('.case-card').forEach(card => {
            card.addEventListener('click', () => {
                const caseId = card.dataset.id;
                const caseData = filteredCases.find(c => c.id === caseId || c.case_id === caseId);
                if (caseData) openModal(caseData);
            });
        });
    }
    
    function renderCaseCard(c) {
        const typeClass = c.case_type === 'missing_person' ? 'missing' : 
                          c.case_type === 'unidentified' ? 'unidentified' : '';
        const typeLabel = c.case_type === 'missing_person' ? 'MISSING' :
                          c.case_type === 'unidentified' ? 'UNIDENTIFIED' : 'HOMICIDE';
        
        const date = c.date_occurred ? formatDate(c.date_occurred) : 'Date Unknown';
        const location = [c.city, c.state].filter(Boolean).join(', ') || 'Unknown Location';
        
        // Calculate quality score
        const qualityScore = getCaseQualityScore(c);
        const quality = getCaseQualityLabel(qualityScore);
        const hasMedia = c.media && c.media.length > 0;
        const isFeatured = c.featured || qualityScore >= 60;
        
        return `
            <div class="case-card" data-id="${c.id || c.case_id}">
                ${isFeatured ? '<span class="featured-badge">FEATURED</span>' : ''}
                <div class="case-quality-badge ${quality.class}">
                    ${hasMedia ? '📷 ' : ''}${quality.label}
                </div>
                <div class="case-card-header">
                    <span class="case-type-badge ${typeClass}">${typeLabel}</span>
                    <span class="case-status">${c.status === 'unsolved' ? 'UNSOLVED' : c.status?.toUpperCase()}</span>
                </div>
                <h3 class="case-card-title">${escapeHtml(c.title)}</h3>
                <div class="case-card-meta">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0118 0z"/><circle cx="12" cy="10" r="3"/></svg>
                    <span>${escapeHtml(location)} • ${date}</span>
                </div>
                <p class="case-card-summary">${escapeHtml(c.summary || 'No summary available.')}</p>
                <div class="case-card-footer">
                    <span class="case-source">${c.source_dataset || 'Unknown Source'}</span>
                    <span class="case-view-btn">
                        View Details
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M5 12h14M12 5l7 7-7 7"/></svg>
                    </span>
                </div>
            </div>
        `;
    }
    
    function formatDate(dateStr) {
        try {
            const date = new Date(dateStr);
            return date.toLocaleDateString('en-US', { year: 'numeric', month: 'short' });
        } catch {
            return dateStr;
        }
    }
    
    function escapeHtml(str) {
        if (!str) return '';
        return str.replace(/[&<>"']/g, char => ({
            '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
        }[char]));
    }
    
    // ========== MODAL ==========
    function openModal(c) {
        modalTitle.textContent = c.title;
        modalMeta.textContent = `${[c.city, c.state].filter(Boolean).join(', ')} • ${c.date_occurred ? formatDate(c.date_occurred) : 'Date Unknown'}`;
        modalBadge.textContent = `CASE ${c.case_id || c.id}`;
        modalSummary.textContent = c.summary || 'No detailed summary available for this case.';
        modalSource.textContent = c.source_dataset || 'Unknown';
        
        // Victim info
        if (c.victim && Object.keys(c.victim).length > 0) {
            modalVictimSection.classList.remove('hidden');
            modalVictim.innerHTML = Object.entries(c.victim)
                .filter(([k, v]) => v != null)
                .map(([k, v]) => `
                    <div class="victim-field">
                        <div class="victim-field-label">${k.replace(/_/g, ' ')}</div>
                        <div class="victim-field-value">${escapeHtml(String(v))}</div>
                    </div>
                `).join('');
        } else {
            modalVictimSection.classList.add('hidden');
        }
        
        // Evidence
        if (c.evidence && c.evidence.length > 0) {
            modalEvidenceSection.classList.remove('hidden');
            modalEvidence.innerHTML = c.evidence.map(e => `
                <div class="evidence-item">
                    <span class="evidence-type">${escapeHtml(e.type?.toUpperCase())}</span>
                    <span class="evidence-desc">${escapeHtml(e.description)}</span>
                </div>
            `).join('');
        } else {
            modalEvidenceSection.classList.add('hidden');
        }
        
        // Timeline
        if (c.date_occurred) {
            modalTimelineSection.classList.remove('hidden');
            const timelineItems = [];
            
            if (c.date_occurred) {
                timelineItems.push(`
                    <div class="timeline-item">
                        <span class="timeline-date">${formatDate(c.date_occurred)}</span>
                        <span class="timeline-event">Incident Occurred</span>
                    </div>
                `);
            }
            
            if (c.date_discovered && c.date_discovered !== c.date_occurred) {
                timelineItems.push(`
                    <div class="timeline-item">
                        <span class="timeline-date">${formatDate(c.date_discovered)}</span>
                        <span class="timeline-event">Case Discovered</span>
                    </div>
                `);
            }
            
            modalTimeline.innerHTML = timelineItems.join('');
        } else {
            modalTimelineSection.classList.add('hidden');
        }
        
        // Content Warning
        if (warningDismissed) {
            contentWarning.classList.add('dismissed');
        } else {
            contentWarning.classList.remove('dismissed');
        }
        
        // Media Gallery
        if (c.media && c.media.length > 0) {
            mediaSection.classList.remove('hidden');
            mediaGallery.innerHTML = c.media.map(m => `
                <div class="media-item" onclick="window.open('${escapeHtml(m.url)}', '_blank')">
                    <img src="${escapeHtml(m.thumbnail || m.url)}" alt="${escapeHtml(m.caption || 'Case media')}" loading="lazy">
                    <div class="media-item-overlay">${escapeHtml(m.caption || m.type)}</div>
                </div>
            `).join('');
            mediaAttribution.textContent = c.media_attribution || '';
        } else {
            // Show placeholder for cases without media
            mediaSection.classList.remove('hidden');
            mediaGallery.innerHTML = `
                <div class="media-placeholder">
                    <span class="media-icon">📷</span>
                    <p>No official case media available</p>
                </div>
            `;
            mediaAttribution.textContent = '';
        }
        
        caseModal.classList.add('active');
        document.body.style.overflow = 'hidden';
    }
    
    // Calculate case quality score based on available evidence
    function getCaseQualityScore(c) {
        let score = 0;
        
        // Has media (+30)
        if (c.media && c.media.length > 0) score += 30;
        
        // Has evidence items (+5 each, max 25)
        if (c.evidence) score += Math.min(c.evidence.length * 5, 25);
        
        // Has victim info (+15)
        if (c.victim && Object.keys(c.victim).length > 2) score += 15;
        
        // Has detailed summary (+10)
        if (c.summary && c.summary.length > 200) score += 10;
        
        // Has specific date (+5)
        if (c.date_occurred) score += 5;
        
        // Has AI analysis generated (+15)
        if (c.thorne_analysis || c.maya_analysis) score += 15;
        
        return score;
    }
    
    function getCaseQualityLabel(score) {
        if (score >= 60) return { label: 'DETAILED', class: 'quality-high' };
        if (score >= 30) return { label: 'STANDARD', class: 'quality-medium' };
        return { label: 'BASIC', class: 'quality-low' };
    }
    
    function closeModal() {
        caseModal.classList.remove('active');
        document.body.style.overflow = '';
    }
    
    // ========== EVENT LISTENERS ==========
    // Search
    let searchTimeout;
    searchInput.addEventListener('input', () => {
        clearTimeout(searchTimeout);
        searchTimeout = setTimeout(applyFilters, 300);
    });
    
    clearSearch.addEventListener('click', () => {
        searchInput.value = '';
        applyFilters();
    });
    
    // Filters
    filterState.addEventListener('change', applyFilters);
    filterType.addEventListener('change', applyFilters);
    filterYear.addEventListener('change', applyFilters);
    
    filterUnsolved.addEventListener('click', () => {
        unsolvedOnly = !unsolvedOnly;
        filterUnsolved.classList.toggle('active', unsolvedOnly);
        applyFilters();
    });
    
    // View toggle
    viewToggle.addEventListener('click', () => {
        isListView = !isListView;
        caseGrid.classList.toggle('list-view', isListView);
        viewToggle.querySelector('.icon-grid').style.display = isListView ? 'none' : 'block';
        viewToggle.querySelector('.icon-list').style.display = isListView ? 'block' : 'none';
    });
    
    // Pagination
    prevPage.addEventListener('click', () => {
        if (currentPage > 1) {
            currentPage--;
            renderCases();
            window.scrollTo({ top: 0, behavior: 'smooth' });
        }
    });
    
    nextPage.addEventListener('click', () => {
        const totalPages = Math.ceil(filteredCases.length / pageSize);
        if (currentPage < totalPages) {
            currentPage++;
            renderCases();
            window.scrollTo({ top: 0, behavior: 'smooth' });
        }
    });
    
    // Modal
    modalClose.addEventListener('click', closeModal);
    modalBackdrop.addEventListener('click', closeModal);
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') closeModal();
    });
    
    modalUpgrade.addEventListener('click', () => {
        window.location.href = 'membership.html';
    });
    
    modalDownload.addEventListener('click', () => {
        alert('Case summary download feature coming soon! Premium members will be able to download detailed PDF dossiers.');
    });
    
    // Content warning dismiss
    dismissWarning.addEventListener('click', () => {
        warningDismissed = true;
        sessionStorage.setItem('warningDismissed', 'true');
        contentWarning.classList.add('dismissed');
    });
    
    // ========== INITIALIZE ==========
    await fetchCases();
    await fetchStats();
    
    console.log('📁 Case Browser ready');
});
