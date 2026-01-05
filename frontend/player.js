// Cold Case Crawler - Dynamic Visual Player
// Loads episode data from JSON for accurate sync

document.addEventListener('DOMContentLoaded', async () => {
    const app = document.getElementById('app');
    const audio = document.getElementById('audio');
    const playBtn = document.getElementById('playBtn');
    const rewindBtn = document.getElementById('rewindBtn');
    const forwardBtn = document.getElementById('forwardBtn');
    const progressBar = document.getElementById('progressBar');
    const progressFill = document.getElementById('progressFill');
    const currentTimeEl = document.getElementById('currentTime');
    const durationEl = document.getElementById('duration');
    const speedBtn = document.getElementById('speedBtn');
    const fullscreenBtn = document.getElementById('fullscreenBtn');
    
    // Visual elements
    const sceneImage = document.getElementById('sceneImage');
    const locationStamp = document.getElementById('locationStamp');
    const stampLocation = document.querySelector('.stamp-location');
    const stampDate = document.querySelector('.stamp-date');
    const dramaticText = document.getElementById('dramaticText');
    const mayaCard = document.getElementById('mayaCard');
    const thorneCard = document.getElementById('thorneCard');
    const evidencePopup = document.getElementById('evidencePopup');
    const evidenceCaption = document.getElementById('evidenceCaption');
    const caseTitle = document.querySelector('.case-title');
    const caseBadge = document.querySelector('.case-badge');
    
    const iconPlay = playBtn.querySelector('.icon-play');
    const iconPause = playBtn.querySelector('.icon-pause');
    
    let isPlaying = false;
    const speeds = [1, 1.25, 1.5, 1.75, 2];
    let speedIndex = 0;
    
    // Episode data - loaded from JSON
    let episodeData = null;
    let visualCues = [];
    let caseImages = [];
    let currentCueIndex = -1;
    let currentImageIndex = 0;

    // Case panel elements
    const casePanel = document.getElementById('casePanel');
    const panelToggle = document.getElementById('panelToggle');
    const panelTitle = document.getElementById('panelTitle');
    const panelMeta = document.getElementById('panelMeta');
    const panelSummary = document.getElementById('panelSummary');
    const panelEvidence = document.getElementById('panelEvidence');

    // ========== LOAD EPISODE DATA ==========
    async function loadEpisodeData() {
        try {
            // First try to fetch from API (works with Vercel->Railway proxy)
            let response = await fetch('/api/episode');
            
            // Fallback to static JSON if API fails
            if (!response.ok) {
                console.log('⚠️ API not available, trying static JSON...');
                response = await fetch('episode_data.json');
            }
            
            if (response.ok) {
                episodeData = await response.json();
                visualCues = episodeData.visualCues || [];
                
                // Update audio source if API provided audioUrl
                if (episodeData.audioUrl) {
                    console.log(`🔊 Loading audio from: ${episodeData.audioUrl}`);
                    audio.src = episodeData.audioUrl;
                    audio.load();
                } else {
                    // Fallback: try to load from backend audio endpoint
                    console.log('🔊 Using audio endpoint fallback');
                    audio.src = '/audio/cold_case_episode.mp3';
                    audio.load();
                }
                
                // Update UI with case info
                if (episodeData.case) {
                    caseTitle.textContent = episodeData.case.title;
                    if (stampLocation) stampLocation.textContent = episodeData.case.location?.toUpperCase() || 'UNKNOWN LOCATION';
                    if (stampDate) stampDate.textContent = episodeData.case.date || 'DATE UNKNOWN';
                    
                    // Update case panel
                    if (panelTitle) panelTitle.textContent = episodeData.case.title;
                    if (panelMeta) panelMeta.textContent = `${episodeData.case.location} • ${episodeData.case.date}`;
                    if (panelSummary) panelSummary.textContent = episodeData.case.summary;
                    
                    // Add evidence items
                    if (panelEvidence && episodeData.case.evidence) {
                        panelEvidence.innerHTML = episodeData.case.evidence.map(e => `
                            <div class="panel-evidence-item">
                                <span class="evidence-type-badge">${e.type}</span>
                                <span class="evidence-desc">${e.description}</span>
                            </div>
                        `).join('');
                    }
                    
                    // Load case images
                    if (episodeData.case.images && episodeData.case.images.length > 0) {
                        caseImages = episodeData.case.images;
                        console.log(`🖼️ Loaded ${caseImages.length} case images`);
                    }
                }
                
                console.log(`📋 Loaded episode: ${episodeData.case?.title}`);
                console.log(`🎬 Visual cues: ${visualCues.length}`);
                return true;
            }
        } catch (e) {
            console.log('⚠️ Failed to load episode data:', e);
        }
        
        // Fallback cues if no JSON
        visualCues = createFallbackCues();
        return false;
    }
    
    function createFallbackCues() {
        // Fallback for when episode_data.json doesn't exist
        return [
            { time: 0, speaker: 'maya', text: 'Welcome to Murder Index...', showLocation: true },
            { time: 5, speaker: 'maya', text: 'Today we investigate a mystery that has haunted investigators for decades.' },
            { time: 12, speaker: 'thorne', text: "Let's examine the evidence." },
            { time: 18, speaker: 'maya', text: 'The victim was found under mysterious circumstances.' },
            { time: 25, speaker: 'thorne', text: 'The forensic evidence tells a different story.' },
            { time: 32, speaker: 'maya', text: 'But what about the witness statements?' },
            { time: 40, speaker: 'thorne', text: 'Witness testimony is notoriously unreliable.' },
            { time: 48, speaker: 'maya', text: 'I have a theory about what really happened.' },
        ];
    }

    // ========== UTILITY FUNCTIONS ==========
    function formatTime(seconds) {
        if (isNaN(seconds) || !isFinite(seconds)) return '0:00';
        const mins = Math.floor(seconds / 60);
        const secs = Math.floor(seconds % 60);
        return `${mins}:${secs.toString().padStart(2, '0')}`;
    }

    // ========== VISUAL UPDATE FUNCTIONS ==========
    function updateVisuals(cue) {
        if (!cue) return;
        
        // Update speaker cards
        const isMaya = cue.speaker === 'maya';
        mayaCard.classList.toggle('active', isMaya);
        thorneCard.classList.toggle('active', !isMaya);
        
        // Update dramatic text with the actual dialogue
        if (cue.text) {
            // Truncate long text for display
            const displayText = cue.text.length > 150 
                ? cue.text.substring(0, 150) + '...' 
                : cue.text;
            dramaticText.textContent = `"${displayText}"`;
            dramaticText.classList.add('visible');
        }
        
        // Show location stamp on first cue or when specified
        if (cue.showLocation) {
            if (cue.location) stampLocation.textContent = cue.location.toUpperCase();
            if (cue.date) stampDate.textContent = cue.date;
            locationStamp.classList.add('visible');
        } else {
            locationStamp.classList.remove('visible');
        }
        
        // Show evidence popup when relevant
        if (cue.showEvidence && cue.evidenceText) {
            evidenceCaption.textContent = cue.evidenceText;
            evidencePopup.classList.add('visible');
            // Auto-hide after 4 seconds
            setTimeout(() => {
                evidencePopup.classList.remove('visible');
            }, 4000);
        }
        
        // Update scene image based on speaker or evidence
        updateSceneImage(cue);
    }
    
    function updateSceneImage(cue) {
        // Show different visuals based on content and available images
        const text = (cue.text || '').toLowerCase();
        
        // Try to find a relevant image from scraped images
        if (caseImages.length > 0) {
            let selectedImage = null;
            
            // Use imageIndex if specified in cue
            if (cue.imageIndex !== undefined && caseImages[cue.imageIndex]) {
                selectedImage = caseImages[cue.imageIndex];
            }
            // Otherwise match image type to content
            else if (text.includes('body') || text.includes('victim') || text.includes('missing')) {
                selectedImage = caseImages.find(img => img.type === 'victim') || caseImages[0];
            } else if (text.includes('evidence') || text.includes('forensic') || text.includes('found')) {
                selectedImage = caseImages.find(img => img.type === 'evidence') || caseImages[1];
            } else if (text.includes('location') || text.includes('scene') || text.includes('area')) {
                selectedImage = caseImages.find(img => img.type === 'location') || caseImages[2];
            } else {
                // Cycle through images
                selectedImage = caseImages[currentImageIndex % caseImages.length];
                currentImageIndex++;
            }
            
            if (selectedImage && selectedImage.path) {
                // Smooth transition
                sceneImage.style.opacity = '0';
                setTimeout(() => {
                    sceneImage.src = selectedImage.path;
                    sceneImage.style.opacity = '0.7';
                }, 300);
                
                // Show attribution
                if (selectedImage.attribution) {
                    showAttribution(selectedImage.attribution);
                }
            }
        }
        
        // Apply visual filters based on content mood
        if (text.includes('body') || text.includes('found') || text.includes('discovered') || text.includes('vanish')) {
            sceneImage.style.filter = 'grayscale(60%) contrast(1.2) brightness(0.7)';
        } else if (text.includes('evidence') || text.includes('forensic') || text.includes('witness')) {
            sceneImage.style.filter = 'grayscale(40%) sepia(20%) contrast(1.1)';
        } else {
            sceneImage.style.filter = 'grayscale(30%) contrast(1.1)';
        }
        
        sceneImage.classList.add('visible');
    }
    
    function showAttribution(text) {
        // Create or update attribution element
        let attrEl = document.getElementById('imageAttribution');
        if (!attrEl) {
            attrEl = document.createElement('div');
            attrEl.id = 'imageAttribution';
            attrEl.className = 'image-attribution';
            document.getElementById('visualStage').appendChild(attrEl);
        }
        attrEl.textContent = text;
        attrEl.classList.add('visible');
        
        // Hide after 3 seconds
        setTimeout(() => {
            attrEl.classList.remove('visible');
        }, 3000);
    }

    function findCurrentCue(time) {
        for (let i = visualCues.length - 1; i >= 0; i--) {
            if (time >= visualCues[i].time) {
                return i;
            }
        }
        return 0;
    }

    // ========== AUDIO CONTROLS ==========
    playBtn.addEventListener('click', async () => {
        if (isPlaying) {
            audio.pause();
        } else {
            try {
                await audio.play();
            } catch (e) {
                console.error('Playback failed:', e);
            }
        }
    });

    audio.addEventListener('play', () => {
        isPlaying = true;
        iconPlay.style.display = 'none';
        iconPause.style.display = 'block';
    });

    audio.addEventListener('pause', () => {
        isPlaying = false;
        iconPlay.style.display = 'block';
        iconPause.style.display = 'none';
    });

    audio.addEventListener('ended', () => {
        isPlaying = false;
        iconPlay.style.display = 'block';
        iconPause.style.display = 'none';
        dramaticText.textContent = 'Episode complete. The case remains open...';
    });

    // Time update - sync visuals
    audio.addEventListener('timeupdate', () => {
        const percent = (audio.currentTime / audio.duration) * 100;
        progressFill.style.width = `${percent}%`;
        currentTimeEl.textContent = formatTime(audio.currentTime);

        // Find and apply current visual cue
        const newCueIndex = findCurrentCue(audio.currentTime);
        if (newCueIndex !== currentCueIndex && visualCues[newCueIndex]) {
            currentCueIndex = newCueIndex;
            updateVisuals(visualCues[currentCueIndex]);
        }
    });

    audio.addEventListener('loadedmetadata', () => {
        durationEl.textContent = formatTime(audio.duration);
    });

    audio.addEventListener('canplaythrough', () => {
        if (audio.duration && isFinite(audio.duration)) {
            durationEl.textContent = formatTime(audio.duration);
        }
    });

    // Seek
    progressBar.addEventListener('click', (e) => {
        const rect = progressBar.getBoundingClientRect();
        const percent = (e.clientX - rect.left) / rect.width;
        audio.currentTime = percent * audio.duration;
    });

    // Rewind/Forward
    rewindBtn.addEventListener('click', () => {
        audio.currentTime = Math.max(0, audio.currentTime - 15);
    });

    forwardBtn.addEventListener('click', () => {
        audio.currentTime = Math.min(audio.duration || 0, audio.currentTime + 15);
    });

    // Speed
    speedBtn.addEventListener('click', () => {
        speedIndex = (speedIndex + 1) % speeds.length;
        const speed = speeds[speedIndex];
        audio.playbackRate = speed;
        speedBtn.textContent = `${speed}×`;
    });

    // Fullscreen
    fullscreenBtn.addEventListener('click', () => {
        if (!document.fullscreenElement) {
            app.requestFullscreen().catch(err => console.log('Fullscreen error:', err));
            app.classList.add('fullscreen');
        } else {
            document.exitFullscreen();
            app.classList.remove('fullscreen');
        }
    });

    document.addEventListener('fullscreenchange', () => {
        if (!document.fullscreenElement) {
            app.classList.remove('fullscreen');
        }
    });

    // Keyboard controls
    document.addEventListener('keydown', (e) => {
        if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;
        
        switch(e.code) {
            case 'Space':
                e.preventDefault();
                playBtn.click();
                break;
            case 'ArrowRight':
                audio.currentTime = Math.min(audio.duration || 0, audio.currentTime + 10);
                break;
            case 'ArrowLeft':
                audio.currentTime = Math.max(0, audio.currentTime - 10);
                break;
            case 'KeyF':
                fullscreenBtn.click();
                break;
        }
    });

    // ========== INITIALIZE ==========
    await loadEpisodeData();
    
    // Coming Soon Teaser dismiss
    const comingSoonTeaser = document.getElementById('comingSoonTeaser');
    const teaserDismiss = document.getElementById('teaserDismiss');
    if (teaserDismiss && comingSoonTeaser) {
        teaserDismiss.addEventListener('click', () => {
            comingSoonTeaser.classList.add('hidden');
            localStorage.setItem('teaserDismissed', 'true');
        });
        // Check if previously dismissed
        if (localStorage.getItem('teaserDismissed') === 'true') {
            comingSoonTeaser.classList.add('hidden');
        }
    }
    
    // Case panel toggle button
    const casePanelToggleBtn = document.getElementById('casePanelToggleBtn');
    
    // Show case panel after a delay
    setTimeout(() => {
        if (casePanel) casePanel.classList.add('visible');
    }, 1000);
    
    // Close panel button (X)
    if (panelToggle) {
        panelToggle.addEventListener('click', () => {
            casePanel.classList.remove('visible');
            // Show the floating toggle button after panel closes
            setTimeout(() => {
                if (casePanelToggleBtn) casePanelToggleBtn.classList.add('visible');
            }, 300);
        });
    }
    
    // Open panel button (floating 📁)
    if (casePanelToggleBtn) {
        casePanelToggleBtn.addEventListener('click', () => {
            casePanelToggleBtn.classList.remove('visible');
            casePanel.classList.add('visible');
        });
    }
    
    // Show initial state
    if (visualCues.length > 0) {
        updateVisuals(visualCues[0]);
    }
    
    console.log('🎬 Cold Case Crawler ready');
    console.log('   SPACE = Play/Pause');
    console.log('   F = Fullscreen');
    console.log('   ←/→ = Skip 10s');
});
