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
    gameStarted: false,
    audioUnlocked: false,
    stampAnimationFired: false,
    stampShownQuietly: false,
    sounds: {}
  };

  // DOM Elements
  const elements = {
    splash: document.getElementById('splash'),
    playButton: document.getElementById('playButton')
  };

  // Assets to preload
  const assets = {
    images: [
      // Core UI
      '/assets/images/grid-cell.png',
      '/assets/images/terminal-bg.png',
      // Enemies
      '/assets/images/gnome-idle.png',
      '/assets/images/gnome-attack.png',
      '/assets/images/mouse-cursor.png',
      // Effects
      '/assets/images/phosphor-glow.png',
      '/assets/images/breach-warning.png'
    ],
    audio: [
      // Intro narration and music
      '/assets/audio/intro-narration.mp3',
      '/assets/audio/intro-music.mp3',
      // Splash sound effects
      '/assets/audio/sfx-stamp.mp3',
      '/assets/audio/sfx-stamp-impact.mp3',
      '/assets/audio/sfx-warning.mp3',
      // Stage 1 intro (preload all 4)
      '/assets/audio/stage1-intro-1.mp3',
      '/assets/audio/stage1-intro-2.mp3',
      '/assets/audio/stage1-intro-3.mp3',
      '/assets/audio/stage1-intro-4.mp3',
      // First stage commands (preload first few for instant playback)
      '/assets/audio/cmd-deploy-terminal.mp3',
      '/assets/audio/cmd-reinforce.mp3',
      '/assets/audio/cmd-hostiles-right.mp3',
      '/assets/audio/cmd-threat-below.mp3',
      '/assets/audio/cmd-breach-contained.mp3',
      // Commander emotions
      '/assets/audio/calm-1.mp3',
      '/assets/audio/calm-2.mp3'
    ]
  };

  // Initialize
  function init() {
    // Check for mobile/touch device
    if (isMobileDevice()) {
      document.body.classList.add('mobile');
      return; // Mobile warning is shown via CSS
    }

    // Add waiting state - animations paused until user clicks play
    document.body.classList.add('waiting-for-user');

    // Initialize audio early (creates Howl objects, ready for user interaction)
    initAudio();

    // Get the audio unlock overlay (acts as the play button)
    const overlay = document.getElementById('audioUnlock');

    // Play button is hidden via CSS (.waiting-for-user .play-button)
    // It will be shown by JS after the intro sequence starts

    // Master unlock handler - starts the intro sequence
    const startExperience = () => {
      if (state.audioUnlocked) return;
      state.audioUnlocked = true;

      // Hide the overlay
      if (overlay) {
        overlay.classList.add('hidden');
      }

      // Remove waiting state - enables CSS animations
      document.body.classList.remove('waiting-for-user');

      // Remove loading class after intro sequence
      setTimeout(() => {
        document.body.classList.remove('loading');
      }, 5000);

      // SEQUENCE:
      // 0ms: Stamp slams immediately with sound
      // 2s: Theme music begins (quiet, fading in)
      // 3.5s: Narration starts

      // Stamp slam - play sounds first, then trigger visual after audio starts
      state.stampAnimationFired = true;

      // Start sounds and wait for them to actually begin playing
      const playStampSequence = () => {
        // Trigger visual animation now that sound is playing
        const stamp = document.querySelector('.logo-stamp');
        if (stamp) {
          // Reset any quiet state - always play the slam animation
          stamp.classList.remove('fade-in');
          stamp.classList.remove('visible');
          stamp.style.removeProperty('opacity');
          // Force reflow to restart animation
          void stamp.offsetWidth;
          // Play the slam animation
          stamp.classList.add('slam-now');
        }

        // Screen shake when stamp hits
        setTimeout(() => {
          const logoContainer = document.querySelector('.logo-container');
          if (logoContainer) {
            logoContainer.classList.add('stamp-hit');
            setTimeout(() => logoContainer.classList.remove('stamp-hit'), 300);
          }
        }, 50);
      };

      // Play impact sound with callback when it starts
      if (state.sounds.stampImpact) {
        state.sounds.stampImpact.once('play', playStampSequence);
        state.sounds.stampImpact.play();
      } else {
        // Fallback if no impact sound
        playStampSequence();
      }

      // Play voice simultaneously
      if (state.sounds.stamp) {
        state.sounds.stamp.play();
      }

      // Theme music starts after 2s, very quiet and gradually growing
      setTimeout(() => {
        if (state.sounds.bgMusic) {
          state.sounds.bgMusic.volume(0.02); // Start nearly silent
          state.sounds.bgMusic.play();
          // Fade in very slowly over 15 seconds to stay under narration
          state.sounds.bgMusic.fade(0.02, 0.15, 15000);
        }
      }, 2000);

      // Narration starts after 3.5s (music has started growing)
      setTimeout(() => {
        if (state.sounds.narration && !state.gameStarted) {
          state.sounds.narration.play();
        }
      }, 3500);

      // Play button is now always visible in sticky footer
    };

    // Overlay content click triggers the intro sequence
    // Note: overlay has pointer-events:none, content has pointer-events:auto
    const overlayContent = document.querySelector('.audio-unlock-content');
    if (overlayContent) {
      overlayContent.addEventListener('click', startExperience);
    }
    document.addEventListener('keydown', (e) => {
      // Only start experience with Enter key (no modifiers)
      // This avoids accidental activation from scrolling (Space), navigation (arrows), etc.
      if (!state.audioUnlocked && e.key === 'Enter' && !e.metaKey && !e.ctrlKey && !e.altKey) {
        startExperience();
      }
    });

    // Setup keyboard listener
    setupKeyboardListener();

    // Setup play button click handler
    setupPlayButton();

    // Setup scroll listener for logo shrinking
    setupScrollListener();

    // Fallback: show "DEFENDER" stamp after 1 second if user doesn't trigger animation
    // This prevents confusion about what the site is
    const stampFallbackTimer = setTimeout(() => {
      if (!state.stampAnimationFired) {
        showStampQuietly();
      }
    }, 1000);

    // Also show stamp immediately if user scrolls before triggering animation
    const scrollFallbackHandler = () => {
      if (!state.stampAnimationFired && window.scrollY > 50) {
        clearTimeout(stampFallbackTimer);
        showStampQuietly();
        window.removeEventListener('scroll', scrollFallbackHandler);
      }
    };
    window.addEventListener('scroll', scrollFallbackHandler, { passive: true });

    // Start asset preloading
    preloadAssets();

    // Check if we're in demo mode
    checkDemoMode();
  }

  // Scroll listener for logo shrinking (play button now always in sticky footer)
  function setupScrollListener() {
    const logoContainer = document.querySelector('.logo-container');
    const splash = document.getElementById('splash');
    if (!logoContainer || !splash) return;

    // Threshold: when splash section scrolls past 50% of viewport
    const scrollThreshold = window.innerHeight * 0.5;

    window.addEventListener('scroll', () => {
      const scrollY = window.scrollY;

      if (scrollY > scrollThreshold) {
        document.body.classList.add('scrolled');
        logoContainer.classList.add('scrolled');
      } else {
        document.body.classList.remove('scrolled');
        logoContainer.classList.remove('scrolled');
      }
    }, { passive: true });
  }

  // Show stamp quietly (no animation, just fade in) - for fallback display
  // Always runs after timeout to ensure "DEFENDER" is visible (avoid Omarchy site confusion)
  // NOTE: Does NOT hide the overlay - user can still click to start full experience
  function showStampQuietly() {
    const stamp = document.querySelector('.logo-stamp');
    if (!stamp) return;

    // Only show if stamp hasn't already been animated via slam
    if (!stamp.classList.contains('slam-now')) {
      // Add both classes for CSS rule matching
      stamp.classList.add('fade-in');
      stamp.classList.add('visible');
      // Use setProperty with 'important' to override CSS !important rules
      // Both opacity AND visibility must be set (inline CSS has both hidden)
      stamp.style.setProperty('opacity', '1', 'important');
      stamp.style.setProperty('visibility', 'visible', 'important');
    }

    state.stampShownQuietly = true;
    // Do NOT hide the overlay - user can still click to start audio experience
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

      // Check for Super+Enter (also Ctrl+Enter for remapped keyboards)
      if (e.key === 'Enter' && (superPressed || e.metaKey || e.ctrlKey)) {
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

  // Play button is a mouse trap - only Super+Enter works
  function setupPlayButton() {
    if (!elements.playButton) return;

    elements.playButton.addEventListener('click', (e) => {
      e.preventDefault();

      // Show warning - this is a keyboard-only game!
      if (state.sounds.warning) {
        state.sounds.warning.play();
      }

      // Visual feedback - shake and turn red
      elements.playButton.classList.add('shake');
      setTimeout(() => {
        elements.playButton.classList.remove('shake');
      }, 500);

      // Show hint if not already visible
      const hint = elements.playButton.querySelector('.play-hint');
      if (hint) {
        hint.style.opacity = '1';
      }
    });
  }


  // Initialize Howler audio
  function initAudio() {
    if (typeof Howl === 'undefined') {
      console.warn('Howler.js not loaded');
      return;
    }

    // Background music - epic/cinematic (plays once)
    state.sounds.bgMusic = new Howl({
      src: ['/assets/audio/intro-music.mp3'],
      volume: 0.3,
      loop: false,
      preload: true
    });

    // Intro narration
    state.sounds.narration = new Howl({
      src: ['/assets/audio/intro-narration.mp3'],
      volume: 0.9,
      preload: true
    });

    // Warning sound for mouse clicks
    state.sounds.warning = new Howl({
      src: ['/assets/audio/sfx-warning.mp3'],
      volume: 0.4,
      preload: true
    });

    // Stamp sound effect ("OMARCHY DEFENDER!" - dramatic MK-style)
    state.sounds.stamp = new Howl({
      src: ['/assets/audio/sfx-stamp.mp3'],
      volume: 0.7,
      preload: true
    });

    // Stamp impact sound (plays with voice for MK-style effect)
    state.sounds.stampImpact = new Howl({
      src: ['/assets/audio/sfx-stamp-impact.mp3'],
      volume: 0.6,
      preload: true
    });
  }


  // Stop intro audio with fade out
  function stopIntroAudio() {
    if (state.sounds.bgMusic) {
      state.sounds.bgMusic.fade(0.3, 0, 1000);
      setTimeout(() => {
        state.sounds.bgMusic.stop();
      }, 1000);
    }
    if (state.sounds.narration) {
      state.sounds.narration.fade(0.9, 0, 500);
      setTimeout(() => {
        state.sounds.narration.stop();
      }, 500);
    }
  }

  // Asset preloading
  async function preloadAssets() {
    // Preload images
    const imagePromises = assets.images.map((src) => {
      return new Promise((resolve) => {
        const img = new Image();
        img.onload = resolve;
        img.onerror = resolve; // Continue even if image fails
        img.src = src;
      });
    });

    // Preload audio
    const audioPromises = assets.audio.map((src) => {
      return new Promise((resolve) => {
        const audio = new Audio();
        audio.oncanplaythrough = resolve;
        audio.onerror = resolve; // Continue even if audio fails
        audio.src = src;
      });
    });

    // Wait for all assets
    await Promise.all([...imagePromises, ...audioPromises]);

    // Mark as loaded
    state.assetsLoaded = true;

    // Request additional audio caching via service worker
    if ('serviceWorker' in navigator && navigator.serviceWorker.controller) {
      navigator.serviceWorker.controller.postMessage({
        type: 'PRECACHE_AUDIO',
        urls: [
          // Stage 2 and 3 intros (cached in background)
          '/assets/audio/stage2-intro-1.mp3',
          '/assets/audio/stage2-intro-2.mp3',
          '/assets/audio/stage2-intro-3.mp3',
          '/assets/audio/stage2-intro-4.mp3',
          '/assets/audio/stage3-intro-1.mp3',
          '/assets/audio/stage3-intro-2.mp3',
          '/assets/audio/stage3-intro-3.mp3',
          '/assets/audio/stage3-intro-4.mp3',
          // More Stage 1 command audio
          '/assets/audio/cmd-enemy-left.mp3',
          '/assets/audio/cmd-threat-above.mp3',
          '/assets/audio/cmd-hold-position.mp3',
          '/assets/audio/cmd-clear-sector.mp3',
          '/assets/audio/cmd-maximize-firepower.mp3',
          '/assets/audio/cmd-evasive.mp3'
        ]
      });
    }
  }

  // Start the game - navigate to game.html
  function startGame() {
    if (state.gameStarted) return;
    state.gameStarted = true;

    // Stop intro audio
    stopIntroAudio();

    // Fade out splash
    elements.splash.style.transition = 'opacity 0.5s';
    elements.splash.style.opacity = '0';

    // Navigate to the game page after fade
    setTimeout(() => {
      window.location.href = 'game.html';
    }, 500);
  }

  // Check for demo mode (URL parameter)
  function checkDemoMode() {
    const params = new URLSearchParams(window.location.search);
    const demoScript = params.get('demo');

    if (demoScript) {
      console.log(`Demo mode: Loading ${demoScript}`);

      // Redirect directly to game.html with demo parameter
      window.location.href = `game.html?demo=${encodeURIComponent(demoScript)}`;
    }
  }

  // Expose start function for external calls
  window.startOmarchyDefender = startGame;

  // ============================================================
  // ARTICLE ANIMATIONS
  // ============================================================

  // Slide-in animation for article h3 headings using IntersectionObserver
  function setupArticleAnimations() {
    const h3Elements = document.querySelectorAll('.article-section h3');

    if (h3Elements.length === 0) return;

    const observer = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          entry.target.classList.add('visible');
          observer.unobserve(entry.target); // Only animate once
        }
      });
    }, {
      threshold: 0.2,
      rootMargin: '0px 0px -50px 0px'
    });

    h3Elements.forEach(h3 => observer.observe(h3));
  }

  // Typewriter effect for article title with rotating phrases
  function setupTypewriter() {
    const typewriterEl = document.querySelector('.typewriter-text');
    if (!typewriterEl) return;

    const phrases = [
      'Join the Cool Kids.',
      'Break Your Mouse Addiction.',
      'Master Omarchy in Minutes.',
      'Defeat the Gnome Army.',
      'Your Keyboard is Your Weapon.'
    ];

    let phraseIndex = 0;
    let charIndex = 0;
    let isDeleting = false;
    let typingSpeed = 80;

    function type() {
      const currentPhrase = phrases[phraseIndex];

      if (isDeleting) {
        typewriterEl.textContent = currentPhrase.substring(0, charIndex - 1);
        charIndex--;
        typewriterEl.classList.remove('typing');
        typewriterEl.classList.add('deleting');
        typingSpeed = 40;
      } else {
        typewriterEl.textContent = currentPhrase.substring(0, charIndex + 1);
        charIndex++;
        typewriterEl.classList.add('typing');
        typewriterEl.classList.remove('deleting');
        typingSpeed = 80;
      }

      if (!isDeleting && charIndex === currentPhrase.length) {
        // Pause at end of phrase
        typewriterEl.classList.remove('typing');
        typingSpeed = 2000;
        isDeleting = true;
      } else if (isDeleting && charIndex === 0) {
        // Move to next phrase
        isDeleting = false;
        phraseIndex = (phraseIndex + 1) % phrases.length;
        typewriterEl.classList.remove('deleting');
        typingSpeed = 500;
      }

      setTimeout(type, typingSpeed);
    }

    // Start typing after a short delay
    setTimeout(type, 1000);
  }

  // Initialize article animations when DOM is ready
  function initArticleAnimations() {
    setupArticleAnimations();
    setupTypewriter();
  }

  // Initialize on DOM ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
      init();
      initArticleAnimations();
    });
  } else {
    init();
    initArticleAnimations();
  }

})();
