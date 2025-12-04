/**
 * Omarchy Defender - Splash Screen Logic
 * Handles intro animations, asset loading, and mouse trap
 */

(function() {
  'use strict';

  // State
  const state = {
    assetsLoaded: false,
    loadProgress: 0,
    mouseWarnings: 0,
    maxMouseWarnings: 3,
    gameStarted: false
  };

  // DOM Elements
  const elements = {
    splash: document.getElementById('splash'),
    game: document.getElementById('game'),
    loadingFill: document.getElementById('loadingFill'),
    loadingText: document.getElementById('loadingText'),
    playButton: document.getElementById('playButton')
  };

  // Assets to preload
  const assets = {
    images: [
      // Core UI
      '/assets/images/ui/grid-cell.png',
      '/assets/images/ui/terminal-bg.png',
      // Enemies
      '/assets/images/enemies/gnome-idle.png',
      '/assets/images/enemies/gnome-attack.png',
      '/assets/images/enemies/mouse-cursor.png',
      // Effects
      '/assets/images/effects/phosphor-glow.png',
      '/assets/images/effects/breach-warning.png'
    ],
    audio: [
      // Commander voice samples (preload a few)
      '/assets/audio/stage1-intro-1.mp3',
      '/assets/audio/calm-1.mp3',
      '/assets/audio/urgent-1.mp3',
      // Sound effects
      '/assets/audio/sfx-terminal-spawn.mp3',
      '/assets/audio/sfx-terminal-close.mp3',
      '/assets/audio/sfx-success.mp3',
      '/assets/audio/sfx-fail.mp3',
      '/assets/audio/sfx-klaxon.mp3'
    ]
  };

  // Initialize
  function init() {
    // Check for mobile/touch device
    if (isMobileDevice()) {
      document.body.classList.add('mobile');
      return; // Mobile warning is shown via CSS
    }

    // Remove loading class after initial animations
    setTimeout(() => {
      document.body.classList.remove('loading');
    }, 5000);

    // Setup keyboard listener
    setupKeyboardListener();

    // Setup mouse trap
    setupMouseTrap();

    // Start asset preloading
    preloadAssets();

    // Check if we're in demo mode
    checkDemoMode();
  }

  // Check if mobile device
  function isMobileDevice() {
    return (
      /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent) ||
      (window.matchMedia && window.matchMedia('(hover: none) and (pointer: coarse)').matches)
    );
  }

  // Keyboard listener for Super+Enter
  function setupKeyboardListener() {
    let superPressed = false;

    document.addEventListener('keydown', (e) => {
      // Track Super/Meta key
      if (e.key === 'Meta' || e.key === 'Super') {
        superPressed = true;
      }

      // Check for Super+Enter
      if (e.key === 'Enter' && (superPressed || e.metaKey)) {
        e.preventDefault();

        if (state.assetsLoaded && !state.gameStarted) {
          startGame();
        }
      }
    });

    document.addEventListener('keyup', (e) => {
      if (e.key === 'Meta' || e.key === 'Super') {
        superPressed = false;
      }
    });

    // Also listen for Escape to show about section
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') {
        const about = document.getElementById('about');
        if (about) {
          about.hidden = !about.hidden;
        }
      }
    });
  }

  // Mouse trap - discourage clicking the Play button
  function setupMouseTrap() {
    elements.playButton.addEventListener('click', (e) => {
      e.preventDefault();

      state.mouseWarnings++;

      // Show warning state
      elements.playButton.classList.add('warning');

      // Play warning sound if available
      playWarningSound();

      if (state.mouseWarnings >= state.maxMouseWarnings) {
        // Extra stern warning
        elements.playButton.textContent = 'NO MICE ALLOWED';
        setTimeout(() => {
          elements.playButton.textContent = 'Super+Enter ONLY';
        }, 2000);
      }

      // Reset warning state after animation
      setTimeout(() => {
        elements.playButton.classList.remove('warning');
      }, 500);
    });

    // Also track any mouse movement/clicks during splash
    document.addEventListener('mousemove', trackMouseActivity);
    document.addEventListener('click', trackMouseActivity);
  }

  // Track mouse activity for contamination system awareness
  let mouseActivityCount = 0;
  function trackMouseActivity() {
    mouseActivityCount++;

    // After too much mouse activity, show a subtle hint
    if (mouseActivityCount === 50) {
      elements.loadingText.textContent = 'Hint: This game is keyboard-only';
      setTimeout(() => {
        elements.loadingText.textContent = state.assetsLoaded
          ? 'Press Super+Enter to begin'
          : 'Loading assets...';
      }, 3000);
    }
  }

  // Play warning sound
  function playWarningSound() {
    try {
      const audio = new Audio('/assets/audio/sfx-warning.mp3');
      audio.volume = 0.3;
      audio.play().catch(() => {});
    } catch (e) {
      // Audio not available
    }
  }

  // Asset preloading
  async function preloadAssets() {
    const totalAssets = assets.images.length + assets.audio.length;
    let loadedCount = 0;

    const updateProgress = () => {
      loadedCount++;
      state.loadProgress = (loadedCount / totalAssets) * 100;
      elements.loadingFill.style.width = state.loadProgress + '%';
      elements.loadingText.textContent = `Loading assets... ${Math.round(state.loadProgress)}%`;
    };

    // Preload images
    const imagePromises = assets.images.map((src) => {
      return new Promise((resolve) => {
        const img = new Image();
        img.onload = () => {
          updateProgress();
          resolve();
        };
        img.onerror = () => {
          updateProgress();
          resolve(); // Continue even if image fails
        };
        img.src = src;
      });
    });

    // Preload audio
    const audioPromises = assets.audio.map((src) => {
      return new Promise((resolve) => {
        const audio = new Audio();
        audio.oncanplaythrough = () => {
          updateProgress();
          resolve();
        };
        audio.onerror = () => {
          updateProgress();
          resolve(); // Continue even if audio fails
        };
        audio.src = src;
      });
    });

    // Wait for all assets
    await Promise.all([...imagePromises, ...audioPromises]);

    // Mark as loaded
    state.assetsLoaded = true;
    elements.loadingFill.style.width = '100%';
    elements.loadingText.textContent = 'Press Super+Enter to begin';

    // Request additional audio caching via service worker
    if ('serviceWorker' in navigator && navigator.serviceWorker.controller) {
      navigator.serviceWorker.controller.postMessage({
        type: 'PRECACHE_AUDIO',
        urls: [
          // Additional voice lines to cache in background
          '/assets/audio/stage1-intro-2.mp3',
          '/assets/audio/stage1-intro-3.mp3',
          '/assets/audio/calm-2.mp3',
          '/assets/audio/calm-3.mp3',
          '/assets/audio/urgent-2.mp3',
          '/assets/audio/angry-1.mp3'
        ]
      });
    }
  }

  // Start the game
  function startGame() {
    if (state.gameStarted) return;
    state.gameStarted = true;

    // Remove mouse tracking
    document.removeEventListener('mousemove', trackMouseActivity);
    document.removeEventListener('click', trackMouseActivity);

    // Fade out splash
    elements.splash.style.transition = 'opacity 0.5s';
    elements.splash.style.opacity = '0';

    setTimeout(() => {
      elements.splash.style.display = 'none';
      elements.game.hidden = false;

      // Initialize Phaser game (defined in game.js)
      if (typeof window.initGame === 'function') {
        window.initGame();
      } else {
        console.error('Game initialization function not found');
      }
    }, 500);
  }

  // Check for demo mode (URL parameter)
  function checkDemoMode() {
    const params = new URLSearchParams(window.location.search);
    const demoScript = params.get('demo');

    if (demoScript) {
      // Store demo script path for game.js to pick up
      window.demoScript = `/demos/${demoScript}.json`;
      elements.loadingText.textContent = `Loading demo: ${demoScript}`;
    }
  }

  // Expose start function for external calls
  window.startOmarchyDefender = startGame;

  // Initialize on DOM ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

})();
