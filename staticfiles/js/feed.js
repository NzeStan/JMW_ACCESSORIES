// static/js/feed.js

// Track active players
let players = {};
let currentlyPlaying = null;

// Initialize Intersection Observer
const observerOptions = {
    root: null,
    rootMargin: '-50px 0px',
    threshold: 0.7  // High threshold to ensure good visibility before playing
};

function onPlayerReady(event) {
    const player = event.target;
    const videoId = player.getVideoData().video_id;
    players[videoId] = player;
    
    // Set initial volume and quality
    player.setVolume(50);
    player.setPlaybackQuality('hd720');
}

function onPlayerStateChange(event) {
    const player = event.target;
    const videoId = player.getVideoData().video_id;
    
    if (event.data === YT.PlayerState.PLAYING) {
        // Pause other playing videos
        if (currentlyPlaying && currentlyPlaying !== videoId) {
            players[currentlyPlaying].pauseVideo();
        }
        currentlyPlaying = videoId;
    }
}

function initializePlayer(element) {
    if (!element.dataset.initialized) {
        new YT.Player(element.id, {
            videoId: element.dataset.videoId,
            playerVars: {
                autoplay: 1,        // Enable autoplay
                mute: 1,           // Muted by default (required for autoplay)
                controls: 1,        // Show video controls
                modestbranding: 1,  // Minimal YouTube branding
                rel: 0,            // Don't show related videos
                playsinline: 1,     // Play inline on mobile
                enablejsapi: 1      // Enable JavaScript API
            },
            events: {
                onReady: onPlayerReady,
                onStateChange: onPlayerStateChange
            }
        });
        element.dataset.initialized = 'true';
    }
}

// Handle video visibility and autoplay
const handleIntersection = (entries) => {
    entries.forEach(entry => {
        const videoId = entry.target.dataset.videoId;
        if (!players[videoId]) return;

        if (entry.isIntersecting) {
            players[videoId].playVideo();
        } else {
            players[videoId].pauseVideo();
        }
    });
};

const observer = new IntersectionObserver(handleIntersection, observerOptions);

// Initialize new content
function initializeContent() {
    document.querySelectorAll('.youtube-player:not([data-initialized])').forEach(element => {
        initializePlayer(element);
        observer.observe(element);
    });
}

// HTMX handlers for infinite scroll
document.addEventListener('htmx:afterRequest', function(evt) {
    if (evt.detail.xhr.status === 200) {
        const content = evt.detail.xhr.response;
        if (content.trim() === '') {
            // No more content, remove infinite scroll trigger
            evt.detail.target.removeAttribute('hx-trigger');
        } else {
            // Update offset for next request
            const currentOffset = parseInt(evt.detail.target.getAttribute('hx-vals').match(/\d+/)[0]);
            evt.detail.target.setAttribute('hx-vals', `{"offset": "${currentOffset + 10}"}`);
        }
    }
});

// Share functionality
async function shareContent(url) {
    if (navigator.share) {
        try {
            await navigator.share({ url: url });
        } catch (error) {
            console.log('Share error:', error);
        }
    } else {
        const dummy = document.createElement('input');
        document.body.appendChild(dummy);
        dummy.value = url;
        dummy.select();
        document.execCommand('copy');
        document.body.removeChild(dummy);
        
        // Show toast notification
        const toast = document.createElement('div');
        toast.className = 'toast toast-end';
        toast.innerHTML = `
            <div class="alert alert-success shadow-lg">
                <div>
                    <i class="fas fa-check-circle"></i>
                    <span>Link copied to clipboard!</span>
                </div>
            </div>
        `;
        document.body.appendChild(toast);
        setTimeout(() => toast.remove(), 3000);
    }
}

// Initialize everything
document.addEventListener('DOMContentLoaded', initializeContent);
document.addEventListener('htmx:afterSettle', initializeContent);
window.onYouTubeIframeAPIReady = initializeContent;