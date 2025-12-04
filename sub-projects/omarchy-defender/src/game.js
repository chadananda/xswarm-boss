/**
 * Omarchy Defender - Game Engine
 * Phaser 3 game with keyboard-only controls
 */

(function() {
  'use strict';

  // ============================================================
  // CONFIGURATION
  // ============================================================

  const CONFIG = {
    // Game settings
    gridSize: 3,
    cellSize: 150,
    cellGap: 10,

    // Timing
    gnomeApproachTime: 3000, // ms before gnome reaches target
    hintDelay: 2000,         // ms before first hint
    urgentDelay: 4000,       // ms before urgent hint
    angryDelay: 6000,        // ms before angry hint

    // Scoring
    baseScore: 100,
    comboMultiplier: 1.5,
    perfectBonus: 500,

    // Mouse contamination
    mouseDecayRate: 0.5,      // Purity recovery per second
    mouseContactPenalty: 25,  // Purity loss per mouse contact
    purityLevels: {
      warning: 70,
      danger: 40,
      critical: 20
    },

    // Voice variants
    maxRecentVoices: 3        // Avoid repeating recent voice lines
  };

  // ============================================================
  // GAME STATE
  // ============================================================

  const gameState = {
    stage: 1,
    challenge: 1,
    score: 0,
    combo: 0,
    maxCombo: 0,
    purity: 100,
    isPaused: false,
    isDemoMode: false,

    // Grid state
    grid: [],
    focusedCell: { x: 1, y: 1 },
    windows: [],

    // Current challenge
    currentTarget: null,
    gnomeTimer: null,
    hintTimer: null,

    // Audio
    recentVoices: [],
    audioEnabled: true,

    // Demo playback
    demoEvents: [],
    demoIndex: 0
  };

  // ============================================================
  // PHASER SCENES
  // ============================================================

  // Boot Scene - Load core assets
  class BootScene extends Phaser.Scene {
    constructor() {
      super({ key: 'Boot' });
    }

    preload() {
      // Load essential assets
      // In production, these would be actual image files
      // For now, we'll generate them procedurally
    }

    create() {
      // Initialize game state
      initializeGrid();

      // Check for demo mode
      if (window.demoScript) {
        loadDemoScript(window.demoScript).then(() => {
          this.scene.start('Game');
        });
      } else {
        this.scene.start('Game');
      }
    }
  }

  // Main Game Scene
  class GameScene extends Phaser.Scene {
    constructor() {
      super({ key: 'Game' });
    }

    create() {
      // Create game grid
      this.createGrid();

      // Create HUD
      this.createHUD();

      // Setup keyboard input
      this.setupKeyboard();

      // Setup mouse contamination tracking
      this.setupMouseTracking();

      // Start first challenge
      this.startChallenge(1);

      // Start demo playback if in demo mode
      if (gameState.isDemoMode) {
        this.startDemoPlayback();
      }
    }

    createGrid() {
      const startX = (this.cameras.main.width - (CONFIG.gridSize * CONFIG.cellSize + (CONFIG.gridSize - 1) * CONFIG.cellGap)) / 2;
      const startY = (this.cameras.main.height - (CONFIG.gridSize * CONFIG.cellSize + (CONFIG.gridSize - 1) * CONFIG.cellGap)) / 2;

      this.gridContainer = this.add.container(startX, startY);
      this.cells = [];

      for (let y = 0; y < CONFIG.gridSize; y++) {
        this.cells[y] = [];
        for (let x = 0; x < CONFIG.gridSize; x++) {
          const cellX = x * (CONFIG.cellSize + CONFIG.cellGap);
          const cellY = y * (CONFIG.cellSize + CONFIG.cellGap);

          // Cell background
          const cell = this.add.rectangle(
            cellX + CONFIG.cellSize / 2,
            cellY + CONFIG.cellSize / 2,
            CONFIG.cellSize,
            CONFIG.cellSize,
            0x001400,
            0.6
          );
          cell.setStrokeStyle(2, 0x00aa2b);

          this.cells[y][x] = {
            rect: cell,
            x: cellX,
            y: cellY,
            gridX: x,
            gridY: y,
            hasWindow: false,
            windowSprite: null
          };

          this.gridContainer.add(cell);
        }
      }

      // Highlight initial focused cell
      this.updateFocus();
    }

    createHUD() {
      // Stage indicator (top left)
      this.stageText = this.add.text(20, 20, `STAGE ${gameState.stage}`, {
        fontFamily: 'Courier New',
        fontSize: '18px',
        color: '#00ff41'
      });

      this.challengeText = this.add.text(20, 45, `Challenge ${gameState.challenge}/20`, {
        fontFamily: 'Courier New',
        fontSize: '14px',
        color: '#00aa2b'
      });

      // Score (top center)
      this.scoreText = this.add.text(
        this.cameras.main.width / 2,
        30,
        '0',
        {
          fontFamily: 'Courier New',
          fontSize: '36px',
          color: '#00ff41'
        }
      ).setOrigin(0.5);

      // Combo (top right)
      this.comboText = this.add.text(
        this.cameras.main.width - 20,
        30,
        '',
        {
          fontFamily: 'Courier New',
          fontSize: '24px',
          color: '#00ff41'
        }
      ).setOrigin(1, 0.5);

      // Command panel (bottom)
      this.commandText = this.add.text(
        this.cameras.main.width / 2,
        this.cameras.main.height - 60,
        '',
        {
          fontFamily: 'Courier New',
          fontSize: '18px',
          color: '#00ff41'
        }
      ).setOrigin(0.5);

      this.hintText = this.add.text(
        this.cameras.main.width / 2,
        this.cameras.main.height - 30,
        '',
        {
          fontFamily: 'Courier New',
          fontSize: '14px',
          color: '#00aa2b'
        }
      ).setOrigin(0.5);

      // Purity meter (bottom right)
      this.createPurityMeter();

      // Demo mode indicator
      if (gameState.isDemoMode) {
        this.add.text(
          this.cameras.main.width / 2,
          80,
          'DEMO MODE',
          {
            fontFamily: 'Courier New',
            fontSize: '14px',
            color: '#ff4444',
            backgroundColor: '#ff444433',
            padding: { x: 10, y: 5 }
          }
        ).setOrigin(0.5);
      }
    }

    createPurityMeter() {
      const x = this.cameras.main.width - 220;
      const y = this.cameras.main.height - 50;

      this.add.text(x, y - 15, 'KEYBOARD PURITY', {
        fontFamily: 'Courier New',
        fontSize: '10px',
        color: '#00aa2b'
      });

      // Background bar
      this.add.rectangle(x + 100, y + 5, 200, 8, 0x0a0a0a)
        .setStrokeStyle(1, 0x00aa2b);

      // Fill bar
      this.purityBar = this.add.rectangle(x + 1, y + 1, 198, 6, 0x00ff41)
        .setOrigin(0, 0.5);

      this.purityText = this.add.text(x + 205, y, '100%', {
        fontFamily: 'Courier New',
        fontSize: '12px',
        color: '#00ff41'
      }).setOrigin(0, 0.5);
    }

    setupKeyboard() {
      // Navigation (Super + H/J/K/L)
      this.input.keyboard.on('keydown', (event) => {
        if (gameState.isPaused) return;

        const isMeta = event.metaKey || event.ctrlKey; // Support both Super and Ctrl

        // Super+Enter: Spawn terminal
        if (event.key === 'Enter' && isMeta) {
          event.preventDefault();
          this.spawnTerminal();
          return;
        }

        // Super+Q: Close window
        if (event.key === 'q' && isMeta) {
          event.preventDefault();
          this.closeWindow();
          return;
        }

        // Super+H/J/K/L: Navigate
        if (isMeta && !event.shiftKey) {
          switch (event.key.toLowerCase()) {
            case 'h':
              event.preventDefault();
              this.moveFocus(-1, 0);
              break;
            case 'j':
              event.preventDefault();
              this.moveFocus(0, 1);
              break;
            case 'k':
              event.preventDefault();
              this.moveFocus(0, -1);
              break;
            case 'l':
              event.preventDefault();
              this.moveFocus(1, 0);
              break;
          }
        }

        // Super+Shift+H/J/K/L: Move window
        if (isMeta && event.shiftKey) {
          switch (event.key.toLowerCase()) {
            case 'h':
              event.preventDefault();
              this.moveWindow(-1, 0);
              break;
            case 'j':
              event.preventDefault();
              this.moveWindow(0, 1);
              break;
            case 'k':
              event.preventDefault();
              this.moveWindow(0, -1);
              break;
            case 'l':
              event.preventDefault();
              this.moveWindow(1, 0);
              break;
          }
        }

        // Super+F: Fullscreen toggle
        if (event.key === 'f' && isMeta) {
          event.preventDefault();
          this.toggleFullscreen();
        }

        // Escape: Pause
        if (event.key === 'Escape') {
          this.togglePause();
        }
      });
    }

    setupMouseTracking() {
      // Track mouse movement for contamination
      this.input.on('pointermove', () => {
        this.applyMousePenalty(5);
      });

      this.input.on('pointerdown', () => {
        this.applyMousePenalty(CONFIG.mouseContactPenalty);
        this.flashRed();
        playVoice('mouse_warning');
      });

      // Purity recovery over time
      this.time.addEvent({
        delay: 100,
        callback: () => {
          if (gameState.purity < 100) {
            gameState.purity = Math.min(100, gameState.purity + CONFIG.mouseDecayRate * 0.1);
            this.updatePurityMeter();
          }
        },
        loop: true
      });
    }

    applyMousePenalty(amount) {
      gameState.purity = Math.max(0, gameState.purity - amount * 0.1);
      this.updatePurityMeter();
    }

    updatePurityMeter() {
      const width = (gameState.purity / 100) * 198;
      this.purityBar.width = width;

      // Color based on level
      if (gameState.purity <= CONFIG.purityLevels.critical) {
        this.purityBar.setFillStyle(0xff4444);
        this.purityText.setColor('#ff4444');
      } else if (gameState.purity <= CONFIG.purityLevels.danger) {
        this.purityBar.setFillStyle(0xff8844);
        this.purityText.setColor('#ff8844');
      } else if (gameState.purity <= CONFIG.purityLevels.warning) {
        this.purityBar.setFillStyle(0xffaa00);
        this.purityText.setColor('#ffaa00');
      } else {
        this.purityBar.setFillStyle(0x00ff41);
        this.purityText.setColor('#00ff41');
      }

      this.purityText.setText(Math.round(gameState.purity) + '%');
    }

    flashRed() {
      const flash = this.add.rectangle(
        this.cameras.main.width / 2,
        this.cameras.main.height / 2,
        this.cameras.main.width,
        this.cameras.main.height,
        0xff0000,
        0.3
      );

      this.tweens.add({
        targets: flash,
        alpha: 0,
        duration: 200,
        onComplete: () => flash.destroy()
      });
    }

    // ============================================================
    // GRID OPERATIONS
    // ============================================================

    updateFocus() {
      // Remove focus from all cells
      for (let y = 0; y < CONFIG.gridSize; y++) {
        for (let x = 0; x < CONFIG.gridSize; x++) {
          this.cells[y][x].rect.setStrokeStyle(2, 0x00aa2b);
        }
      }

      // Highlight focused cell
      const { x, y } = gameState.focusedCell;
      this.cells[y][x].rect.setStrokeStyle(3, 0x00ff41);

      // Add glow effect
      this.tweens.add({
        targets: this.cells[y][x].rect,
        alpha: { from: 0.8, to: 1 },
        duration: 500,
        yoyo: true,
        repeat: -1
      });
    }

    moveFocus(dx, dy) {
      const newX = Math.max(0, Math.min(CONFIG.gridSize - 1, gameState.focusedCell.x + dx));
      const newY = Math.max(0, Math.min(CONFIG.gridSize - 1, gameState.focusedCell.y + dy));

      if (newX !== gameState.focusedCell.x || newY !== gameState.focusedCell.y) {
        gameState.focusedCell.x = newX;
        gameState.focusedCell.y = newY;
        this.updateFocus();
        this.checkChallengeProgress('navigate');
      }
    }

    spawnTerminal() {
      const { x, y } = gameState.focusedCell;
      const cell = this.cells[y][x];

      if (cell.hasWindow) {
        // Cell already has a window
        return;
      }

      // Create terminal window sprite
      const windowSprite = this.add.container(
        cell.x + CONFIG.cellSize / 2,
        cell.y + CONFIG.cellSize / 2
      );

      // Terminal background
      const bg = this.add.rectangle(0, 0, 120, 100, 0x0a0a0a)
        .setStrokeStyle(1, 0x00ff41);

      // Terminal header
      const header = this.add.rectangle(0, -42, 120, 16, 0x00aa2b);
      const title = this.add.text(-55, -45, 'kitty', {
        fontFamily: 'Courier New',
        fontSize: '10px',
        color: '#000000'
      });

      // Cursor
      const cursor = this.add.rectangle(0, 20, 8, 14, 0x00ff41);
      this.tweens.add({
        targets: cursor,
        alpha: { from: 1, to: 0 },
        duration: 500,
        yoyo: true,
        repeat: -1
      });

      windowSprite.add([bg, header, title, cursor]);
      this.gridContainer.add(windowSprite);

      // Spawn animation
      windowSprite.setScale(0);
      this.tweens.add({
        targets: windowSprite,
        scale: 1,
        duration: 200,
        ease: 'Back.easeOut'
      });

      cell.hasWindow = true;
      cell.windowSprite = windowSprite;
      gameState.windows.push({ x, y, sprite: windowSprite });

      // Play sound
      playSound('terminal-spawn');

      // Check challenge progress
      this.checkChallengeProgress('spawn');
    }

    closeWindow() {
      const { x, y } = gameState.focusedCell;
      const cell = this.cells[y][x];

      if (!cell.hasWindow) {
        return;
      }

      // Close animation
      this.tweens.add({
        targets: cell.windowSprite,
        scale: 0,
        alpha: 0,
        duration: 150,
        ease: 'Power2',
        onComplete: () => {
          cell.windowSprite.destroy();
          cell.windowSprite = null;
        }
      });

      cell.hasWindow = false;

      // Remove from windows array
      const idx = gameState.windows.findIndex(w => w.x === x && w.y === y);
      if (idx >= 0) {
        gameState.windows.splice(idx, 1);
      }

      // Play sound
      playSound('terminal-close');

      // Check challenge progress
      this.checkChallengeProgress('close');
    }

    moveWindow(dx, dy) {
      const { x, y } = gameState.focusedCell;
      const cell = this.cells[y][x];

      if (!cell.hasWindow) {
        return;
      }

      const newX = Math.max(0, Math.min(CONFIG.gridSize - 1, x + dx));
      const newY = Math.max(0, Math.min(CONFIG.gridSize - 1, y + dy));

      if (newX === x && newY === y) {
        return;
      }

      const targetCell = this.cells[newY][newX];
      if (targetCell.hasWindow) {
        return; // Target cell occupied
      }

      // Move window sprite
      const windowSprite = cell.windowSprite;
      const targetX = targetCell.x + CONFIG.cellSize / 2;
      const targetY = targetCell.y + CONFIG.cellSize / 2;

      this.tweens.add({
        targets: windowSprite,
        x: targetX - this.gridContainer.x,
        y: targetY - this.gridContainer.y,
        duration: 150,
        ease: 'Power2'
      });

      // Update cell states
      cell.hasWindow = false;
      cell.windowSprite = null;
      targetCell.hasWindow = true;
      targetCell.windowSprite = windowSprite;

      // Update windows array
      const idx = gameState.windows.findIndex(w => w.x === x && w.y === y);
      if (idx >= 0) {
        gameState.windows[idx].x = newX;
        gameState.windows[idx].y = newY;
      }

      // Move focus to follow window
      gameState.focusedCell.x = newX;
      gameState.focusedCell.y = newY;
      this.updateFocus();

      // Check challenge progress
      this.checkChallengeProgress('move');
    }

    toggleFullscreen() {
      // Toggle fullscreen state for current window
      // This is a simplified version
      this.checkChallengeProgress('fullscreen');
    }

    // ============================================================
    // CHALLENGE SYSTEM
    // ============================================================

    startChallenge(challengeNum) {
      gameState.challenge = challengeNum;
      this.challengeText.setText(`Challenge ${challengeNum}/20`);

      // Get challenge definition
      const challenge = CHALLENGES[gameState.stage]?.[challengeNum - 1];
      if (!challenge) {
        this.completeStage();
        return;
      }

      this.currentChallenge = challenge;

      // Display command
      this.commandText.setText(challenge.command);
      this.hintText.setText('');

      // Play intro voice if first challenge or new type
      if (challengeNum === 1) {
        playVoice('stage1_intro');
      }

      // Set target cell if needed
      if (challenge.targetCell) {
        this.setTargetCell(challenge.targetCell.x, challenge.targetCell.y);
      }

      // Start hint timer
      this.startHintTimer(challenge.hint);
    }

    setTargetCell(x, y) {
      gameState.currentTarget = { x, y };

      // Highlight target cell
      const cell = this.cells[y][x];
      cell.rect.setStrokeStyle(3, 0xffaa00);

      // Pulse animation
      this.tweens.add({
        targets: cell.rect,
        alpha: { from: 0.5, to: 1 },
        duration: 500,
        yoyo: true,
        repeat: -1
      });
    }

    clearTargetCell() {
      if (gameState.currentTarget) {
        const { x, y } = gameState.currentTarget;
        const cell = this.cells[y][x];
        this.tweens.killTweensOf(cell.rect);
        cell.rect.setAlpha(1);
        cell.rect.setStrokeStyle(2, 0x00aa2b);
        gameState.currentTarget = null;
      }
    }

    startHintTimer(hint) {
      // Cancel existing timers
      if (gameState.hintTimer) {
        gameState.hintTimer.remove();
      }

      // First hint
      gameState.hintTimer = this.time.delayedCall(CONFIG.hintDelay, () => {
        this.hintText.setText(hint);
        playVoice('hint');
      });

      // Urgent hint
      this.time.delayedCall(CONFIG.urgentDelay, () => {
        this.hintText.setColor('#ffaa00');
        playVoice('urgent');
      });

      // Angry hint
      this.time.delayedCall(CONFIG.angryDelay, () => {
        this.hintText.setColor('#ff4444');
        playVoice('angry');
      });
    }

    checkChallengeProgress(action) {
      if (!this.currentChallenge) return;

      const challenge = this.currentChallenge;

      // Check if action matches expected action
      if (challenge.action === action) {
        // Check additional conditions
        let success = true;

        if (challenge.targetCell) {
          const { x, y } = gameState.focusedCell;
          if (x !== challenge.targetCell.x || y !== challenge.targetCell.y) {
            success = false;
          }
        }

        if (success) {
          this.challengeSuccess();
        }
      }
    }

    challengeSuccess() {
      // Clear timers
      if (gameState.hintTimer) {
        gameState.hintTimer.remove();
      }

      // Award score
      gameState.combo++;
      const scoreGain = CONFIG.baseScore * Math.pow(CONFIG.comboMultiplier, gameState.combo - 1);
      gameState.score += Math.round(scoreGain);
      gameState.maxCombo = Math.max(gameState.maxCombo, gameState.combo);

      // Update display
      this.scoreText.setText(gameState.score);
      this.comboText.setText(`${gameState.combo}x COMBO`);

      // Success animation
      this.tweens.add({
        targets: this.scoreText,
        scale: { from: 1.3, to: 1 },
        duration: 200
      });

      // Play success sound and voice
      playSound('success');
      if (gameState.combo >= 5) {
        playVoice('combo');
      } else {
        playVoice('calm');
      }

      // Clear target
      this.clearTargetCell();

      // Reset hint text
      this.hintText.setText('');
      this.hintText.setColor('#00aa2b');

      // Next challenge
      this.time.delayedCall(1000, () => {
        this.startChallenge(gameState.challenge + 1);
      });
    }

    challengeFail() {
      // Reset combo
      gameState.combo = 0;
      this.comboText.setText('');

      // Play fail sound
      playSound('fail');
      playVoice('urgent');

      // Flash cell red
      if (gameState.currentTarget) {
        const { x, y } = gameState.currentTarget;
        const cell = this.cells[y][x];
        cell.rect.setFillStyle(0x330000);
        this.time.delayedCall(300, () => {
          cell.rect.setFillStyle(0x001400);
        });
      }
    }

    completeStage() {
      // Stage complete!
      this.commandText.setText('STAGE COMPLETE!');
      this.hintText.setText('');

      playVoice('victory');
      playSound('victory');

      // Show results after delay
      this.time.delayedCall(3000, () => {
        this.showResults(true);
      });
    }

    showResults(victory) {
      gameState.isPaused = true;

      // Create overlay
      const overlay = this.add.rectangle(
        this.cameras.main.width / 2,
        this.cameras.main.height / 2,
        this.cameras.main.width,
        this.cameras.main.height,
        0x000000,
        0.9
      );

      // Title
      const titleText = victory ? 'VICTORY!' : 'DEFEATED';
      const titleColor = victory ? '#00ff41' : '#ff4444';

      this.add.text(
        this.cameras.main.width / 2,
        150,
        titleText,
        {
          fontFamily: 'Courier New',
          fontSize: '64px',
          color: titleColor
        }
      ).setOrigin(0.5);

      // Stats
      this.add.text(
        this.cameras.main.width / 2,
        280,
        `Score: ${gameState.score}\nMax Combo: ${gameState.maxCombo}x\nChallenges: ${gameState.challenge - 1}/20`,
        {
          fontFamily: 'Courier New',
          fontSize: '24px',
          color: '#00ff41',
          align: 'center'
        }
      ).setOrigin(0.5);

      // Buttons
      this.add.text(
        this.cameras.main.width / 2,
        450,
        'Press SPACE to continue',
        {
          fontFamily: 'Courier New',
          fontSize: '18px',
          color: '#00aa2b'
        }
      ).setOrigin(0.5);

      this.input.keyboard.once('keydown-SPACE', () => {
        if (victory && gameState.stage < 3) {
          // Next stage
          gameState.stage++;
          gameState.challenge = 1;
          gameState.score = 0;
          gameState.combo = 0;
          this.scene.restart();
        } else {
          // Restart current stage
          gameState.challenge = 1;
          gameState.score = 0;
          gameState.combo = 0;
          this.scene.restart();
        }
      });
    }

    togglePause() {
      gameState.isPaused = !gameState.isPaused;

      if (gameState.isPaused) {
        this.pauseOverlay = this.add.rectangle(
          this.cameras.main.width / 2,
          this.cameras.main.height / 2,
          this.cameras.main.width,
          this.cameras.main.height,
          0x000000,
          0.8
        );

        this.pauseText = this.add.text(
          this.cameras.main.width / 2,
          this.cameras.main.height / 2,
          'PAUSED\n\nPress ESC to resume',
          {
            fontFamily: 'Courier New',
            fontSize: '32px',
            color: '#00ff41',
            align: 'center'
          }
        ).setOrigin(0.5);
      } else {
        this.pauseOverlay?.destroy();
        this.pauseText?.destroy();
      }
    }

    // ============================================================
    // DEMO PLAYBACK
    // ============================================================

    startDemoPlayback() {
      if (!gameState.demoEvents.length) return;

      const playNextEvent = () => {
        if (gameState.demoIndex >= gameState.demoEvents.length) {
          return;
        }

        const event = gameState.demoEvents[gameState.demoIndex];
        const nextEvent = gameState.demoEvents[gameState.demoIndex + 1];

        // Execute event
        this.executeDemoEvent(event);
        gameState.demoIndex++;

        // Schedule next event
        if (nextEvent) {
          const delay = nextEvent.timestamp - event.timestamp;
          this.time.delayedCall(delay, playNextEvent);
        }
      };

      // Start first event
      const firstEvent = gameState.demoEvents[0];
      this.time.delayedCall(firstEvent.timestamp, playNextEvent);
    }

    executeDemoEvent(event) {
      switch (event.type) {
        case 'keypress':
          this.simulateKeypress(event.key);
          break;
        case 'mouse':
          if (event.action === 'erratic') {
            this.simulateErraticMouse(event.duration);
          }
          break;
        case 'delay':
          // Just wait
          break;
      }
    }

    simulateKeypress(keyCombo) {
      // Parse and simulate keypress
      const parts = keyCombo.toLowerCase().split('+');
      const key = parts[parts.length - 1];
      const hasSuper = parts.includes('super');
      const hasShift = parts.includes('shift');

      // Create synthetic event
      const event = {
        key: key === 'return' ? 'Enter' : key,
        metaKey: hasSuper,
        shiftKey: hasShift,
        preventDefault: () => {}
      };

      // Trigger via keyboard handler
      this.input.keyboard.emit('keydown', event);
    }

    simulateErraticMouse(duration) {
      const startTime = Date.now();

      const moveMouse = () => {
        if (Date.now() - startTime > duration) return;

        // Random movement
        const x = Math.random() * this.cameras.main.width;
        const y = Math.random() * this.cameras.main.height;

        this.input.emit('pointermove', { x, y });

        this.time.delayedCall(100 + Math.random() * 100, moveMouse);
      };

      moveMouse();
    }
  }

  // ============================================================
  // CHALLENGES DEFINITION
  // ============================================================

  const CHALLENGES = {
    1: [
      // Stage 1: Terminal Warfare (20 challenges)
      { action: 'spawn', command: 'Spawn a terminal', hint: 'Press Super+Enter', targetCell: { x: 1, y: 1 } },
      { action: 'spawn', command: 'Spawn another terminal', hint: 'Press Super+Enter', targetCell: { x: 0, y: 0 } },
      { action: 'navigate', command: 'Navigate to the right', hint: 'Press Super+L', targetCell: { x: 2, y: 0 } },
      { action: 'navigate', command: 'Navigate down', hint: 'Press Super+J', targetCell: { x: 2, y: 1 } },
      { action: 'close', command: 'Close the focused window', hint: 'Press Super+Q' },
      { action: 'spawn', command: 'Spawn a terminal', hint: 'Press Super+Enter', targetCell: { x: 1, y: 1 } },
      { action: 'navigate', command: 'Navigate left', hint: 'Press Super+H', targetCell: { x: 0, y: 1 } },
      { action: 'navigate', command: 'Navigate up', hint: 'Press Super+K', targetCell: { x: 0, y: 0 } },
      { action: 'spawn', command: 'Spawn a terminal here', hint: 'Press Super+Enter' },
      { action: 'move', command: 'Move window right', hint: 'Press Super+Shift+L' },
      { action: 'move', command: 'Move window down', hint: 'Press Super+Shift+J' },
      { action: 'close', command: 'Close this window', hint: 'Press Super+Q' },
      { action: 'navigate', command: 'Navigate to center', hint: 'Press Super+H or Super+K', targetCell: { x: 1, y: 1 } },
      { action: 'spawn', command: 'Spawn terminal', hint: 'Press Super+Enter' },
      { action: 'move', command: 'Move window left', hint: 'Press Super+Shift+H' },
      { action: 'move', command: 'Move window up', hint: 'Press Super+Shift+K' },
      { action: 'spawn', command: 'Spawn in bottom-right', hint: 'Navigate then Super+Enter', targetCell: { x: 2, y: 2 } },
      { action: 'close', command: 'Close all windows', hint: 'Press Super+Q repeatedly' },
      { action: 'spawn', command: 'Speed round: Spawn 3 terminals!', hint: 'Super+Enter x3' },
      { action: 'close', command: 'Close them all!', hint: 'Super+Q x3' }
    ],
    2: [
      // Stage 2 challenges would go here
    ],
    3: [
      // Stage 3 challenges would go here
    ]
  };

  // ============================================================
  // AUDIO SYSTEM
  // ============================================================

  const audioCache = {};

  function playSound(name) {
    if (!gameState.audioEnabled) return;

    try {
      const audio = new Audio(`/assets/audio/sfx-${name}.mp3`);
      audio.volume = 0.5;
      audio.play().catch(() => {});
    } catch (e) {
      // Audio not available
    }
  }

  function playVoice(category) {
    if (!gameState.audioEnabled) return;

    // Get available variants for this category
    const variants = VOICE_VARIANTS[category] || [];
    if (variants.length === 0) return;

    // Filter out recently played
    const available = variants.filter(v => !gameState.recentVoices.includes(v));
    if (available.length === 0) {
      // All variants recently played, reset
      gameState.recentVoices = [];
      available.push(...variants);
    }

    // Pick random variant
    const variant = available[Math.floor(Math.random() * available.length)];

    // Track recently played
    gameState.recentVoices.push(variant);
    if (gameState.recentVoices.length > CONFIG.maxRecentVoices) {
      gameState.recentVoices.shift();
    }

    // Play audio
    try {
      const audio = new Audio(`/assets/audio/${variant}.mp3`);
      audio.volume = 0.7;
      audio.play().catch(() => {});
    } catch (e) {
      // Audio not available
    }
  }

  const VOICE_VARIANTS = {
    stage1_intro: ['stage1-intro-1', 'stage1-intro-2', 'stage1-intro-3'],
    calm: ['calm-1', 'calm-2', 'calm-3', 'calm-4', 'calm-5'],
    hint: ['hint-1', 'hint-2', 'hint-3', 'hint-4', 'hint-5'],
    urgent: ['urgent-1', 'urgent-2', 'urgent-3', 'urgent-4', 'urgent-5'],
    angry: ['angry-1', 'angry-2', 'angry-3', 'angry-4', 'angry-5'],
    mouse_warning: ['mouse-1', 'mouse-2', 'mouse-3', 'mouse-4', 'mouse-5'],
    victory: ['victory-1', 'victory-2', 'victory-3', 'victory-4', 'victory-5'],
    defeat: ['defeat-1', 'defeat-2', 'defeat-3', 'defeat-4', 'defeat-5'],
    combo: ['combo-2', 'combo-3', 'combo-5']
  };

  // ============================================================
  // UTILITY FUNCTIONS
  // ============================================================

  function initializeGrid() {
    gameState.grid = [];
    for (let y = 0; y < CONFIG.gridSize; y++) {
      gameState.grid[y] = [];
      for (let x = 0; x < CONFIG.gridSize; x++) {
        gameState.grid[y][x] = { hasWindow: false };
      }
    }
  }

  async function loadDemoScript(path) {
    try {
      const response = await fetch(path);
      if (!response.ok) {
        console.error('Failed to load demo script');
        return;
      }

      const demo = await response.json();
      gameState.isDemoMode = true;
      gameState.demoEvents = demo.events || [];

      // Apply demo settings
      if (demo.meta) {
        gameState.stage = demo.meta.stage || 1;
        gameState.challenge = demo.meta.startChallenge || 1;
      }
    } catch (e) {
      console.error('Error loading demo:', e);
    }
  }

  // ============================================================
  // GAME INITIALIZATION
  // ============================================================

  window.initGame = function() {
    const config = {
      type: Phaser.AUTO,
      parent: 'game',
      width: window.innerWidth,
      height: window.innerHeight,
      backgroundColor: '#0a0a0a',
      scene: [BootScene, GameScene],
      scale: {
        mode: Phaser.Scale.RESIZE,
        autoCenter: Phaser.Scale.CENTER_BOTH
      },
      audio: {
        disableWebAudio: false
      }
    };

    new Phaser.Game(config);
  };

})();
