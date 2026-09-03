/**
 * Omarchy Defender - Game Engine
 * Phaser 3 game teaching ACTUAL Hyprland/Omarchy keybindings
 * Uses proper dwindle binary tree layout
 */

(function() {
  'use strict';

  // ============================================================
  // CONFIGURATION
  // ============================================================

  // Responsive margin calculator based on viewport height
  // Top margin must clear HUD elements (stage text y=15, challenge y=35, score y=45, shield meter y=55)
  function getResponsiveMargins() {
    const vh = window.innerHeight;
    if (vh <= 600) {
      return { top: 60, bottom: 45, side: 15, gap: 4 };
    } else if (vh <= 700) {
      return { top: 65, bottom: 55, side: 18, gap: 5 };
    } else if (vh <= 800) {
      return { top: 70, bottom: 65, side: 18, gap: 5 };
    }
    return { top: 75, bottom: 80, side: 20, gap: 6 };
  }

  const CONFIG = {
    // Layout - responsive margins for different screen sizes
    get topMargin() { return getResponsiveMargins().top; },
    get bottomMargin() { return getResponsiveMargins().bottom; },
    get sideMargin() { return getResponsiveMargins().side; },
    get windowGap() { return getResponsiveMargins().gap; },

    // Workspace settings
    workspaceCount: 4,

    // Timing
    hintDelay: 2500,
    urgentDelay: 5000,
    angryDelay: 7000,
    failDelay: 10000,   // Auto-fail after this many ms
    challengeDelay: 1200,

    // Shield system
    shieldDamage: 15, // Shield damage % per failed challenge
    shieldWarnings: [50, 25, 10], // Voice warning thresholds

    // Scoring
    baseScore: 100,
    comboMultiplier: 1.5,
    perfectBonus: 500,
    stageBonus: 2000,

    // Audio
    maxRecentVoices: 3,
    voiceVolume: 0.6,
    sfxVolume: 0.4,

    // Sticky note hints
    stickyNoteMastery: 3 // Uses before note falls off
  };

  // Sticky note definitions per stage - shortcuts to teach
  const STICKY_NOTES = {
    1: [
      { id: 'spawn', key: 'Super+Return', label: 'Deploy Terminal', side: 'left' },
      { id: 'close', key: 'Super+W', label: 'Close Window', side: 'left' },
      { id: 'nav-left', key: 'Super+←', label: 'Focus Left', side: 'right' },
      { id: 'nav-right', key: 'Super+→', label: 'Focus Right', side: 'right' },
      { id: 'nav-up', key: 'Super+↑', label: 'Focus Up', side: 'left' },
      { id: 'nav-down', key: 'Super+↓', label: 'Focus Down', side: 'right' },
      { id: 'fullscreen', key: 'Super+F', label: 'Fullscreen', side: 'left' },
      { id: 'float', key: 'Super+T', label: 'Toggle Float', side: 'right' }
    ],
    2: [
      { id: 'ws-1', key: 'Super+1', label: 'Sector 1', side: 'left' },
      { id: 'ws-2', key: 'Super+2', label: 'Sector 2', side: 'left' },
      { id: 'ws-3', key: 'Super+3', label: 'Sector 3', side: 'right' },
      { id: 'ws-4', key: 'Super+4', label: 'Sector 4', side: 'right' },
      { id: 'move-ws', key: 'Super+Shift+#', label: 'Send to Sector', side: 'left' },
      { id: 'swap', key: 'Super+Shift+Arrow', label: 'Swap Windows', side: 'right' }
    ],
    3: [
      { id: 'app-browser', key: 'Super+Shift+B', label: 'Browser', side: 'left' },
      { id: 'app-files', key: 'Super+Shift+F', label: 'Files', side: 'left' },
      { id: 'app-ai', key: 'Super+Shift+A', label: 'AI Chat', side: 'right' },
      { id: 'app-music', key: 'Super+Shift+M', label: 'Music', side: 'right' },
      { id: 'app-obsidian', key: 'Super+Shift+O', label: 'Obsidian', side: 'left' },
      { id: 'app-neovim', key: 'Super+Shift+N', label: 'Neovim', side: 'right' },
      { id: 'app-email', key: 'Super+Shift+E', label: 'Email', side: 'left' }
    ]
  };

  // Application definitions
  const APPLICATIONS = {
    terminal: { name: 'Terminal', icon: '⌨', color: 0x00ff41 },
    browser: { name: 'Browser', icon: '🌐', color: 0x4488ff },
    files: { name: 'Files', icon: '📁', color: 0xffaa00 },
    email: { name: 'Email', icon: '✉', color: 0xff4444 },
    ai: { name: 'AI Chat', icon: '🤖', color: 0x88ff44 },
    music: { name: 'Music', icon: '🎵', color: 0x1db954 },
    obsidian: { name: 'Obsidian', icon: '📝', color: 0x7c3aed },
    neovim: { name: 'Neovim', icon: '📟', color: 0x57a143 }
  };

  // ============================================================
  // DWINDLE TREE - Binary Space Partitioning
  // ============================================================

  class DwindleNode {
    constructor(x, y, width, height) {
      this.x = x;
      this.y = y;
      this.width = width;
      this.height = height;
      this.window = null;      // Window data if leaf
      this.left = null;        // Left/top child
      this.right = null;       // Right/bottom child
      this.splitVertical = null; // true = left/right, false = top/bottom
    }

    isLeaf() {
      return this.left === null && this.right === null;
    }

    hasWindow() {
      return this.window !== null;
    }

    // Add a window to this node (splits if needed)
    addWindow(windowData) {
      if (this.isLeaf()) {
        if (!this.hasWindow()) {
          // Empty leaf - place window here
          this.window = windowData;
          return this;
        } else {
          // Occupied leaf - split and add to new child
          this.split();
          return this.right.addWindow(windowData);
        }
      } else {
        // Not a leaf - add to the focused side
        // For simplicity, always add to right (new windows go right/bottom)
        return this.right.addWindow(windowData);
      }
    }

    // Split this node into two children
    split() {
      // Determine split direction based on aspect ratio (like Hyprland dwindle)
      this.splitVertical = this.width >= this.height;

      if (this.splitVertical) {
        // Split left/right
        const halfWidth = this.width / 2;
        this.left = new DwindleNode(this.x, this.y, halfWidth, this.height);
        this.right = new DwindleNode(this.x + halfWidth, this.y, halfWidth, this.height);
      } else {
        // Split top/bottom
        const halfHeight = this.height / 2;
        this.left = new DwindleNode(this.x, this.y, this.width, halfHeight);
        this.right = new DwindleNode(this.x, this.y + halfHeight, this.width, halfHeight);
      }

      // Move existing window to left child
      this.left.window = this.window;
      this.window = null;
    }

    // Get all windows as flat array with their bounds
    getAllWindows() {
      const windows = [];
      this._collectWindows(windows);
      return windows;
    }

    _collectWindows(windows) {
      if (this.isLeaf() && this.hasWindow()) {
        windows.push({
          window: this.window,
          bounds: { x: this.x, y: this.y, width: this.width, height: this.height },
          node: this
        });
      }
      if (this.left) this.left._collectWindows(windows);
      if (this.right) this.right._collectWindows(windows);
    }

    // Find window in given direction from focused node
    findInDirection(fromNode, dx, dy) {
      const all = this.getAllWindows();
      if (all.length < 2) return null;

      const from = all.find(w => w.node === fromNode);
      if (!from) return null;

      const fromCenterX = from.bounds.x + from.bounds.width / 2;
      const fromCenterY = from.bounds.y + from.bounds.height / 2;

      let best = null;
      let bestDist = Infinity;

      for (const w of all) {
        if (w.node === fromNode) continue;

        const centerX = w.bounds.x + w.bounds.width / 2;
        const centerY = w.bounds.y + w.bounds.height / 2;

        const deltaX = centerX - fromCenterX;
        const deltaY = centerY - fromCenterY;

        // Check if this window is in the correct direction
        let inDirection = false;
        if (dx > 0 && deltaX > 0) inDirection = true;
        if (dx < 0 && deltaX < 0) inDirection = true;
        if (dy > 0 && deltaY > 0) inDirection = true;
        if (dy < 0 && deltaY < 0) inDirection = true;

        if (inDirection) {
          const dist = Math.abs(deltaX) + Math.abs(deltaY);
          if (dist < bestDist) {
            bestDist = dist;
            best = w;
          }
        }
      }

      return best?.node || null;
    }

    // Remove a window and restructure tree
    removeWindow(targetNode) {
      return this._removeNode(targetNode, null, null);
    }

    _removeNode(targetNode, parent, isLeftChild) {
      if (this === targetNode) {
        if (parent) {
          // Replace parent with sibling
          const sibling = isLeftChild ? parent.right : parent.left;
          parent.x = parent.x;
          parent.y = parent.y;
          parent.width = parent.width;
          parent.height = parent.height;
          parent.window = sibling.window;
          parent.left = sibling.left;
          parent.right = sibling.right;
          parent.splitVertical = sibling.splitVertical;
          return true;
        }
        // Root node - just clear window
        this.window = null;
        return true;
      }

      if (this.left && this.left._removeNode(targetNode, this, true)) return true;
      if (this.right && this.right._removeNode(targetNode, this, false)) return true;
      return false;
    }

    // Recalculate bounds for all nodes
    recalculateBounds(x, y, width, height) {
      this.x = x;
      this.y = y;
      this.width = width;
      this.height = height;

      if (!this.isLeaf()) {
        if (this.splitVertical) {
          const halfWidth = width / 2;
          this.left.recalculateBounds(x, y, halfWidth, height);
          this.right.recalculateBounds(x + halfWidth, y, halfWidth, height);
        } else {
          const halfHeight = height / 2;
          this.left.recalculateBounds(x, y, width, halfHeight);
          this.right.recalculateBounds(x, y + halfHeight, width, halfHeight);
        }
      }
    }

    // Swap two nodes
    static swap(node1, node2) {
      const temp = node1.window;
      node1.window = node2.window;
      node2.window = temp;
    }
  }

  // ============================================================
  // GAME STATE
  // ============================================================

  const gameState = {
    stage: 1,
    challenge: 1,
    maxChallenges: { 1: 15, 2: 20, 3: 25 },
    score: 0,
    combo: 0,
    maxCombo: 0,
    isPaused: false,
    isGameOver: false,
    isDemoMode: false,
    isRecordMode: false,

    // Dwindle tree state
    root: null,
    focusedNode: null,
    windowCount: 0,

    // Workspace state
    currentWorkspace: 1,
    workspaces: {},

    // Current challenge
    currentChallenge: null,
    challengeStartTime: 0,
    hintShown: false,
    urgentShown: false,

    // Shield health (100-0%)
    shield: 100,
    lastShieldWarning: 100, // Track which warnings have been played
    failTimer: null,

    // Sticky note mastery tracking
    shortcutMastery: {}, // { 'spawn': 2, 'close': 1, ... }

    // Audio
    recentVoices: [],
    audioEnabled: true,
    currentVoiceAudio: null,

    // Demo
    demoEvents: [],
    demoIndex: 0,
    demoStartTime: 0,
    demoDuration: 0
  };

  // ============================================================
  // CHALLENGE DEFINITIONS - Using CORRECT Omarchy keybindings
  // ============================================================

  const CHALLENGES = {
    // Stage 1: Basic Window Management (15 challenges)
    1: [
      { action: 'spawn', command: 'Breach detected! Deploy terminal!', hint: 'Super+Return', audio: 'cmd-deploy-terminal' },
      { action: 'spawn', command: 'They\'re splitting forces! Deploy another!', hint: 'Super+Return', audio: 'cmd-reinforce' },
      { action: 'navigate', command: 'Hostiles RIGHT! Move focus!', hint: 'Super+→', dir: 'right', audio: 'cmd-hostiles-right' },
      { action: 'navigate', command: 'Threat LEFT! Shift focus!', hint: 'Super+←', dir: 'left', audio: 'cmd-enemy-left' },
      { action: 'close', command: 'Breach contained! Close window!', hint: 'Super+W', audio: 'cmd-breach-contained' },
      { action: 'spawn', command: 'Hold position! Deploy terminal!', hint: 'Super+Return', audio: 'cmd-hold-position' },
      { action: 'spawn', command: 'Third line defense! Deploy!', hint: 'Super+Return', audio: 'cmd-central-breach' },
      { action: 'navigate', command: 'Focus DOWN! New threat below!', hint: 'Super+↓', dir: 'down', audio: 'cmd-threat-below' },
      { action: 'navigate', command: 'Focus UP! Threat above!', hint: 'Super+↑', dir: 'up', audio: 'cmd-threat-above' },
      { action: 'swap', command: 'Swap positions! Exchange windows!', hint: 'Super+Shift+→', dir: 'right', audio: 'cmd-reposition-right' },
      { action: 'close', command: 'Clear sector! Close window!', hint: 'Super+W', audio: 'cmd-clear-sector' },
      { action: 'fullscreen', command: 'Maximum firepower! Fullscreen!', hint: 'Super+F', audio: 'cmd-maximize-firepower' },
      { action: 'float', command: 'Evasive maneuver! Toggle floating!', hint: 'Super+T', audio: 'cmd-evasive' },
      { action: 'spawn', command: 'Final reinforcement! Deploy!', hint: 'Super+Return', audio: 'cmd-final-wave' },
      { action: 'close', command: 'Victory! Close it down!', hint: 'Super+W', audio: 'cmd-neutralize' }
    ],

    // Stage 2: Workspace Operations (20 challenges)
    2: [
      { action: 'spawn', command: 'Secure base! Deploy terminal!', hint: 'Super+Return', audio: 'cmd-fortify' },
      { action: 'workspace', command: 'Gnomes in Sector 2! Switch now!', hint: 'Super+2', target: 2, audio: 'cmd-sector-switch' },
      { action: 'spawn', command: 'Establish presence! Deploy!', hint: 'Super+Return', audio: 'cmd-establish' },
      { action: 'workspace', command: 'Return to base! Sector 1!', hint: 'Super+1', target: 1, audio: 'cmd-fall-back' },
      { action: 'moveToWorkspace', command: 'Send reinforcements to Sector 2!', hint: 'Super+Shift+2', target: 2, audio: 'cmd-reinforce-sector' },
      { action: 'workspace', command: 'Verify Sector 2!', hint: 'Super+2', target: 2, audio: 'cmd-verify' },
      { action: 'spawn', command: 'Bolster defenses! Deploy!', hint: 'Super+Return', audio: 'cmd-outpost' },
      { action: 'workspace', command: 'Sector 3 alert! Switch!', hint: 'Super+3', target: 3, audio: 'cmd-breach-respond' },
      { action: 'spawn', command: 'New outpost! Deploy!', hint: 'Super+Return', audio: 'cmd-secure' },
      { action: 'navigate', command: 'Focus right!', hint: 'Super+→', dir: 'right', audio: 'cmd-flank-right' },
      { action: 'moveToWorkspace', command: 'Evacuate to Sector 4!', hint: 'Super+Shift+4', target: 4, audio: 'cmd-evacuate' },
      { action: 'workspace', command: 'Pursue to Sector 4!', hint: 'Super+4', target: 4, audio: 'cmd-pursue' },
      { action: 'workspace', command: 'Regroup Sector 1!', hint: 'Super+1', target: 1, audio: 'cmd-regroup' },
      { action: 'spawn', command: 'Double defense!', hint: 'Super+Return', audio: 'cmd-double-defense' },
      { action: 'workspace', command: 'Sector 2 status!', hint: 'Super+2', target: 2, audio: 'cmd-rapid-response' },
      { action: 'workspace', command: 'Sector 3 check!', hint: 'Super+3', target: 3, audio: 'cmd-intel' },
      { action: 'workspace', command: 'Command center! Sector 1!', hint: 'Super+1', target: 1, audio: 'cmd-command-center' },
      { action: 'spawn', command: 'Final defense line!', hint: 'Super+Return', audio: 'cmd-final-defense' },
      { action: 'close', command: 'Stand down!', hint: 'Super+W', audio: 'cmd-victory-protocol' },
      { action: 'workspace', command: 'All clear! Return to base!', hint: 'Super+1', target: 1, audio: 'cmd-return-base' }
    ],

    // Stage 3: Full Arsenal (25 challenges)
    3: [
      { action: 'spawn', command: 'Deploy command terminal!', hint: 'Super+Return', audio: 'cmd-command-post' },
      { action: 'app', command: 'Launch Browser for recon!', hint: 'Super+Shift+B', app: 'browser', audio: 'cmd-recon' },
      { action: 'navigate', command: 'Focus left!', hint: 'Super+←', dir: 'left', audio: 'cmd-enemy-left' },
      { action: 'close', command: 'Intel secured! Close!', hint: 'Super+W', audio: 'cmd-intel-secured' },
      { action: 'app', command: 'Open Files for data!', hint: 'Super+Shift+F', app: 'files', audio: 'cmd-retrieve-intel' },
      { action: 'close', command: 'Data retrieved! Close!', hint: 'Super+W', audio: 'cmd-acknowledged' },
      { action: 'app', command: 'Tactical AI analysis!', hint: 'Super+Shift+A', app: 'ai', audio: 'cmd-tactical-analysis' },
      { action: 'workspace', command: 'Split to Sector 2!', hint: 'Super+2', target: 2, audio: 'cmd-split-ops' },
      { action: 'app', command: 'Music for morale!', hint: 'Super+Shift+M', app: 'music', audio: 'cmd-morale' },
      { action: 'workspace', command: 'Sector 3 ops!', hint: 'Super+3', target: 3, audio: 'cmd-third-front' },
      { action: 'app', command: 'War journal! Obsidian!', hint: 'Super+Shift+O', app: 'obsidian', audio: 'cmd-war-journal' },
      { action: 'app', command: 'Code weapons! Neovim!', hint: 'Super+Shift+N', app: 'neovim', audio: 'cmd-code-weapons' },
      { action: 'navigate', command: 'Focus down!', hint: 'Super+↓', dir: 'down', audio: 'cmd-threat-below' },
      { action: 'swap', command: 'Swap positions!', hint: 'Super+Shift+↑', dir: 'up', audio: 'cmd-push-up' },
      { action: 'close', command: 'Close window!', hint: 'Super+W', audio: 'cmd-mission-focus' },
      { action: 'workspace', command: 'Return Sector 1!', hint: 'Super+1', target: 1, audio: 'cmd-command-center' },
      { action: 'app', command: 'Check Email!', hint: 'Super+Shift+E', app: 'email', audio: 'cmd-transmission' },
      { action: 'close', command: 'Message received! Close!', hint: 'Super+W', audio: 'cmd-comms-secured' },
      { action: 'spawn', command: 'Deploy terminal!', hint: 'Super+Return', audio: 'cmd-deploy-terminal' },
      { action: 'fullscreen', command: 'Go fullscreen!', hint: 'Super+F', audio: 'cmd-maximize-firepower' },
      { action: 'float', command: 'Toggle floating!', hint: 'Super+T', audio: 'cmd-evasive' },
      { action: 'workspace', command: 'Final check Sector 4!', hint: 'Super+4', target: 4, audio: 'cmd-far-perimeter' },
      { action: 'spawn', command: 'Last deployment!', hint: 'Super+Return', audio: 'cmd-establish' },
      { action: 'close', command: 'Stand down!', hint: 'Super+W', audio: 'cmd-victory-protocol' },
      { action: 'workspace', command: 'VICTORY! Return to base!', hint: 'Super+1', target: 1, audio: 'cmd-return-base' }
    ]
  };

  // Stage intro messages
  const STAGE_INTROS = {
    1: [
      "CADET! The Gnomes have breached our shields!",
      "They're targeting Sector 7... YOUR sector.",
      "Deploy defensive terminals on my mark.",
      "Let's see what you're made of..."
    ],
    2: [
      "EXCELLENT WORK, Commander!",
      "But the Gnomes are spreading across all workspaces.",
      "You'll need to defend multiple sectors now.",
      "Switch between workspaces. Don't let them through!"
    ],
    3: [
      "You've proven yourself, Elite Defender.",
      "Now we unleash the FULL ARSENAL.",
      "Every application at your command.",
      "This is the final stand. Make it count!"
    ]
  };

  // Voice line categories
  const VOICE_VARIANTS = {
    calm: ['calm-1', 'calm-2'],
    hint: ['hint-1', 'hint-2'],
    urgent: ['urgent-1', 'urgent-2'],
    angry: ['angry-1', 'angry-2'],
    victory: ['victory-1', 'victory-2'],
    combo: ['combo-2', 'combo-3']
  };

  // ============================================================
  // PHASER SCENES
  // ============================================================

  class BootScene extends Phaser.Scene {
    constructor() {
      super({ key: 'Boot' });
    }

    preload() {
      const width = this.cameras.main.width;
      const height = this.cameras.main.height;

      const progressBar = this.add.graphics();
      const progressBox = this.add.graphics();
      progressBox.fillStyle(0x001400, 0.8);
      progressBox.fillRect(width / 2 - 160, height / 2 - 15, 320, 30);

      this.load.on('progress', (value) => {
        progressBar.clear();
        progressBar.fillStyle(0x00ff41, 1);
        progressBar.fillRect(width / 2 - 155, height / 2 - 10, 310 * value, 20);
      });
    }

    create() {
      resetGameState();

      const params = new URLSearchParams(window.location.search);
      const stage = parseInt(params.get('stage'));
      if (stage >= 1 && stage <= 3) {
        gameState.stage = stage;
      }

      if (params.has('record')) {
        gameState.isRecordMode = true;
        gameState.audioEnabled = false;
        window.gameReady = false;
        window.recordingComplete = false;
      }

      const demoParam = params.get('demo');
      if (demoParam) {
        window.demoScript = demoParam;
      }

      if (window.demoScript) {
        loadDemoScript(window.demoScript).then(() => {
          this.scene.start('Game');
        });
      } else {
        this.scene.start('Game');
      }
    }
  }

  class GameScene extends Phaser.Scene {
    constructor() {
      super({ key: 'Game' });
    }

    create() {
      // Calculate workspace bounds - FULL SCREEN
      this.workspaceBounds = {
        x: CONFIG.sideMargin,
        y: CONFIG.topMargin,
        width: this.cameras.main.width - CONFIG.sideMargin * 2,
        height: this.cameras.main.height - CONFIG.topMargin - CONFIG.bottomMargin
      };

      // Initialize dwindle tree for current workspace
      this.initWorkspace();

      this.createBackground();
      this.createHUD();
      this.createWorkspaceUI();
      this.createStickyNotes();
      this.setupKeyboard();

      // Container for window graphics
      this.windowContainer = this.add.container(0, 0);

      // Start intro sequence
      this.time.delayedCall(500, () => {
        this.playStageIntro(() => {
          this.startChallenge(1);
        });
      });

      if (gameState.isDemoMode) {
        this.createDemoIndicator();
        this.startDemoPlayback();
      }

      if (gameState.isRecordMode) {
        window.gameReady = true;
        gameState.demoStartTime = Date.now();
      }

      // Handle resize - recalculate bounds and re-render
      this.scale.on('resize', this.handleResize, this);
    }

    handleResize(gameSize) {
      // Recalculate workspace bounds with responsive margins
      this.workspaceBounds = {
        x: CONFIG.sideMargin,
        y: CONFIG.topMargin,
        width: gameSize.width - CONFIG.sideMargin * 2,
        height: gameSize.height - CONFIG.topMargin - CONFIG.bottomMargin
      };

      // Update all workspace trees to new bounds
      for (const wsKey of Object.keys(gameState.workspaces)) {
        const workspace = gameState.workspaces[wsKey];
        if (workspace && workspace.root) {
          workspace.root.recalculateBounds(
            this.workspaceBounds.x,
            this.workspaceBounds.y,
            this.workspaceBounds.width,
            this.workspaceBounds.height
          );
        }
      }

      // Re-render windows
      if (this.windowContainer) {
        this.renderWindows();
      }

      // Update workspace border if exists
      if (this.workspaceBorder) {
        this.workspaceBorder.clear();
        this.workspaceBorder.lineStyle(2, 0x00ff41, 0.5);
        this.workspaceBorder.strokeRect(
          this.workspaceBounds.x - 2,
          this.workspaceBounds.y - 2,
          this.workspaceBounds.width + 4,
          this.workspaceBounds.height + 4
        );
      }
    }

    initWorkspace() {
      const ws = gameState.currentWorkspace;
      if (!gameState.workspaces[ws]) {
        gameState.workspaces[ws] = {
          root: new DwindleNode(
            this.workspaceBounds.x,
            this.workspaceBounds.y,
            this.workspaceBounds.width,
            this.workspaceBounds.height
          ),
          focusedNode: null,
          windowCount: 0
        };
      }
      const workspace = gameState.workspaces[ws];
      gameState.root = workspace.root;
      gameState.focusedNode = workspace.focusedNode;
      gameState.windowCount = workspace.windowCount;
    }

    saveWorkspace() {
      const ws = gameState.currentWorkspace;
      gameState.workspaces[ws] = {
        root: gameState.root,
        focusedNode: gameState.focusedNode,
        windowCount: gameState.windowCount
      };
    }

    createBackground() {
      const bg = this.add.graphics();
      bg.fillGradientStyle(0x0a0a0a, 0x0a0a0a, 0x001400, 0x001400, 1);
      bg.fillRect(0, 0, this.cameras.main.width, this.cameras.main.height);

      // Scanlines
      for (let y = 0; y < this.cameras.main.height; y += 3) {
        bg.fillStyle(0x000000, 0.08);
        bg.fillRect(0, y, this.cameras.main.width, 1);
      }

      // Workspace area - subtle fill to distinguish from outer area
      bg.fillStyle(0x001a00, 0.6);
      bg.fillRect(
        this.workspaceBounds.x,
        this.workspaceBounds.y,
        this.workspaceBounds.width,
        this.workspaceBounds.height
      );

      // Grid overlay for workspace - tiling WM aesthetic
      const gridSize = 40; // Grid cell size in pixels
      const wb = this.workspaceBounds;

      // Draw vertical grid lines
      bg.lineStyle(1, 0x00ff41, 0.08);
      for (let x = wb.x; x <= wb.x + wb.width; x += gridSize) {
        bg.moveTo(x, wb.y);
        bg.lineTo(x, wb.y + wb.height);
      }

      // Draw horizontal grid lines
      for (let y = wb.y; y <= wb.y + wb.height; y += gridSize) {
        bg.moveTo(wb.x, y);
        bg.lineTo(wb.x + wb.width, y);
      }
      bg.strokePath();

      // Workspace border - brighter for visibility
      bg.lineStyle(2, 0x00ff41, 0.6);
      bg.strokeRect(
        this.workspaceBounds.x - 2,
        this.workspaceBounds.y - 2,
        this.workspaceBounds.width + 4,
        this.workspaceBounds.height + 4
      );

      // Corner markers for workspace bounds
      const cornerSize = 10;
      bg.lineStyle(2, 0x00ff41, 0.8);
      // Top-left
      bg.moveTo(wb.x - 2, wb.y + cornerSize);
      bg.lineTo(wb.x - 2, wb.y - 2);
      bg.lineTo(wb.x + cornerSize, wb.y - 2);
      // Top-right
      bg.moveTo(wb.x + wb.width - cornerSize, wb.y - 2);
      bg.lineTo(wb.x + wb.width + 2, wb.y - 2);
      bg.lineTo(wb.x + wb.width + 2, wb.y + cornerSize);
      // Bottom-left
      bg.moveTo(wb.x - 2, wb.y + wb.height - cornerSize);
      bg.lineTo(wb.x - 2, wb.y + wb.height + 2);
      bg.lineTo(wb.x + cornerSize, wb.y + wb.height + 2);
      // Bottom-right
      bg.moveTo(wb.x + wb.width - cornerSize, wb.y + wb.height + 2);
      bg.lineTo(wb.x + wb.width + 2, wb.y + wb.height + 2);
      bg.lineTo(wb.x + wb.width + 2, wb.y + wb.height - cornerSize);
      bg.strokePath();

      // === 80s ARCADE DECORATIONS ===

      // Sector numbers along top edge (defense zone labels)
      const sectorWidth = wb.width / 8;
      for (let i = 0; i < 8; i++) {
        const x = wb.x + sectorWidth * i + sectorWidth / 2;
        this.add.text(x, wb.y - 18, String(i + 1), {
          fontFamily: 'Courier New',
          fontSize: '12px',
          color: '#006622'
        }).setOrigin(0.5);
      }

      // Sector numbers along left edge (row labels A-F)
      const rowLabels = ['A', 'B', 'C', 'D', 'E', 'F'];
      const rowHeight = wb.height / 6;
      for (let i = 0; i < 6; i++) {
        const y = wb.y + rowHeight * i + rowHeight / 2;
        this.add.text(wb.x - 18, y, rowLabels[i], {
          fontFamily: 'Courier New',
          fontSize: '12px',
          color: '#006622'
        }).setOrigin(0.5);
      }

      // 80s pixelated border - outer frame with notches
      const screenW = this.cameras.main.width;
      const screenH = this.cameras.main.height;
      const borderG = this.add.graphics();

      // Outer frame lines
      borderG.lineStyle(2, 0x00ff41, 0.3);
      borderG.strokeRect(8, 8, screenW - 16, screenH - 16);

      // Corner brackets (80s arcade style)
      borderG.lineStyle(3, 0x00ff41, 0.5);
      const bracketSize = 30;

      // Top-left bracket
      borderG.moveTo(4, bracketSize + 4);
      borderG.lineTo(4, 4);
      borderG.lineTo(bracketSize + 4, 4);

      // Top-right bracket
      borderG.moveTo(screenW - bracketSize - 4, 4);
      borderG.lineTo(screenW - 4, 4);
      borderG.lineTo(screenW - 4, bracketSize + 4);

      // Bottom-left bracket
      borderG.moveTo(4, screenH - bracketSize - 4);
      borderG.lineTo(4, screenH - 4);
      borderG.lineTo(bracketSize + 4, screenH - 4);

      // Bottom-right bracket
      borderG.moveTo(screenW - bracketSize - 4, screenH - 4);
      borderG.lineTo(screenW - 4, screenH - 4);
      borderG.lineTo(screenW - 4, screenH - bracketSize - 4);

      borderG.strokePath();

      // Chevron indicators along top (80s radar style)
      for (let i = 0; i < 5; i++) {
        const chevronX = 80 + i * 40;
        borderG.lineStyle(2, 0x00ff41, 0.25);
        borderG.moveTo(chevronX, 20);
        borderG.lineTo(chevronX + 8, 12);
        borderG.lineTo(chevronX + 16, 20);
        borderG.strokePath();
      }

      // Mirror chevrons on right side
      for (let i = 0; i < 5; i++) {
        const chevronX = screenW - 80 - i * 40 - 16;
        borderG.lineStyle(2, 0x00ff41, 0.25);
        borderG.moveTo(chevronX, 20);
        borderG.lineTo(chevronX + 8, 12);
        borderG.lineTo(chevronX + 16, 20);
        borderG.strokePath();
      }

      // Small centered terminal only needs ~80px clearance
      const terminalTop = screenH - 80;

      // === RETRO 80s ARCADE DECORATIONS ===

      // Pixelated barrier blocks along left edge (Space Invaders style)
      const blockSize = 6;
      for (let i = 0; i < 12; i++) {
        const y = 80 + i * 35;
        // Staggered pixel pattern
        borderG.fillStyle(0x00ff41, 0.15 + (i % 3) * 0.1);
        borderG.fillRect(12, y, blockSize, blockSize);
        borderG.fillRect(12 + blockSize, y + blockSize, blockSize, blockSize);
        borderG.fillRect(12, y + blockSize * 2, blockSize, blockSize);
      }

      // Mirror on right edge
      for (let i = 0; i < 12; i++) {
        const y = 80 + i * 35;
        borderG.fillStyle(0x00ff41, 0.15 + (i % 3) * 0.1);
        borderG.fillRect(screenW - 12 - blockSize, y, blockSize, blockSize);
        borderG.fillRect(screenW - 12 - blockSize * 2, y + blockSize, blockSize, blockSize);
        borderG.fillRect(screenW - 12 - blockSize, y + blockSize * 2, blockSize, blockSize);
      }

      // Horizontal scan line indicators (radar sweep style)
      for (let i = 0; i < 3; i++) {
        const y = terminalTop - 15 - i * 8;
        borderG.fillStyle(0x00ff41, 0.1 + i * 0.05);
        borderG.fillRect(20, y, 60, 2);
        borderG.fillRect(screenW - 80, y, 60, 2);
      }

      // Defense barrier labels with retro brackets
      this.add.text(8, screenH / 2, '◄◄ WEST', {
        fontFamily: 'Courier New',
        fontSize: '8px',
        color: '#004411'
      }).setAngle(-90).setOrigin(0.5);

      this.add.text(screenW - 8, screenH / 2, 'EAST ►►', {
        fontFamily: 'Courier New',
        fontSize: '8px',
        color: '#004411'
      }).setAngle(90).setOrigin(0.5);

      // Corner status boxes (retro LED style)
      const corners = [
        { x: 15, y: 55 },
        { x: screenW - 25, y: 55 },
        { x: 15, y: terminalTop - 30 },
        { x: screenW - 25, y: terminalTop - 30 }
      ];

      corners.forEach((pos, i) => {
        // LED box outline
        borderG.lineStyle(1, 0x00ff41, 0.4);
        borderG.strokeRect(pos.x, pos.y, 10, 10);
        // Inner LED
        const led = this.add.graphics();
        led.fillStyle(0x00ff41, 0.6);
        led.fillRect(2, 2, 6, 6);
        led.setPosition(pos.x, pos.y);

        // Blink animation
        this.tweens.add({
          targets: led,
          alpha: 0.15,
          duration: 600 + i * 150,
          yoyo: true,
          repeat: -1,
          ease: 'Steps(2)'
        });
      });

      // Retro pixel art dividers above terminal
      const dividerY = terminalTop - 5;
      for (let i = 0; i < 8; i++) {
        borderG.fillStyle(0x00ff41, 0.2);
        borderG.fillRect(30 + i * 15, dividerY, 8, 3);
        borderG.fillRect(screenW - 30 - i * 15 - 8, dividerY, 8, 3);
      }

      // "PERIMETER STATUS" label
      this.add.text(screenW / 2, terminalTop - 12, '═══ PERIMETER STATUS ═══', {
        fontFamily: 'Courier New',
        fontSize: '8px',
        color: '#003311'
      }).setOrigin(0.5);
    }

    createHUD() {
      const width = this.cameras.main.width;

      // Stage indicator
      this.stageText = this.add.text(20, 15,
        `STAGE ${gameState.stage}: ${['', 'TERMINAL WARFARE', 'SECTOR COMMAND', 'FULL ARSENAL'][gameState.stage]}`,
        { fontFamily: 'Courier New', fontSize: '14px', color: '#00ff41' }
      );

      this.challengeText = this.add.text(20, 35,
        `Challenge ${gameState.challenge}/${gameState.maxChallenges[gameState.stage]}`,
        { fontFamily: 'Courier New', fontSize: '11px', color: '#00aa2b' }
      );

      // Score
      this.scoreText = this.add.text(width / 2, 20, '0',
        { fontFamily: 'Courier New', fontSize: '28px', color: '#00ff41' }
      ).setOrigin(0.5);

      this.add.text(width / 2, 45, 'SCORE',
        { fontFamily: 'Courier New', fontSize: '9px', color: '#00aa2b' }
      ).setOrigin(0.5);

      // Combo
      this.comboText = this.add.text(width - 20, 25, '',
        { fontFamily: 'Courier New', fontSize: '18px', color: '#00ff41' }
      ).setOrigin(1, 0.5);

      // Shield meter - retro bar indicator
      this.shieldLabel = this.add.text(width - 20, 42, 'SHIELDS',
        { fontFamily: 'Courier New', fontSize: '8px', color: '#00ff41' }
      ).setOrigin(1, 0.5);
      this.shieldText = this.add.text(width - 20, 55, this.getShieldDisplay(),
        { fontFamily: 'Courier New', fontSize: '12px', color: '#00ff41' }
      ).setOrigin(1, 0.5);

      // Command panel - use DOM CRT terminal (not Phaser text)
      this.commandPanel = document.getElementById('command-panel');
      this.commandTextEl = document.getElementById('command-text');
      this.hintTextEl = document.getElementById('command-hint');

      // Show command panel when game is active
      if (this.commandPanel) {
        this.commandPanel.classList.add('active');
      }

      // Wrapper methods for compatibility with existing code
      this.commandText = {
        setText: (text) => {
          if (this.commandTextEl) this.commandTextEl.textContent = text;
        },
        setColor: (color) => {
          if (this.commandTextEl) this.commandTextEl.style.color = color;
        }
      };

      this.hintText = {
        setText: (text) => {
          if (this.hintTextEl) this.hintTextEl.textContent = text;
        },
        setColor: (color) => {
          if (this.hintTextEl) this.hintTextEl.style.color = color;
        }
      };

      // Restart button above command terminal (Super+Shift+R follows Omarchy app launch pattern)
      const height = this.cameras.main.height;
      const terminalTop = height - 80; // Match createBackground terminal reservation
      this.restartBtn = this.add.text(20, terminalTop - 5, '[Super+Shift+R] RESTART',
        { fontFamily: 'Courier New', fontSize: '11px', color: '#00aa2b' }
      ).setOrigin(0, 1);
      this.restartBtn.setInteractive({ useHandCursor: true });
      this.restartBtn.on('pointerover', () => {
        this.restartBtn.setColor('#00ff41');
        this.restartBtn.setStyle({ backgroundColor: '#001400' });
      });
      this.restartBtn.on('pointerout', () => {
        this.restartBtn.setColor('#00aa2b');
        this.restartBtn.setStyle({ backgroundColor: 'transparent' });
      });
      this.restartBtn.on('pointerdown', () => {
        resetGameState();
        this.scene.restart();
      });

      // Super+Shift+R keyboard shortcut for restart (Omarchy style)
      this.input.keyboard.on('keydown-R', (event) => {
        if (event.metaKey && event.shiftKey) {
          resetGameState();
          this.scene.restart();
        }
      });
    }

    createWorkspaceUI() {
      if (gameState.stage < 2) return;

      const x = this.cameras.main.width - 80;
      const y = 100;

      this.add.text(x, y - 15, 'SECTORS',
        { fontFamily: 'Courier New', fontSize: '8px', color: '#00aa2b' }
      ).setOrigin(0.5);

      this.workspaceCells = [];
      for (let i = 0; i < CONFIG.workspaceCount; i++) {
        const wx = x - 20 + (i % 2) * 40;
        const wy = y + Math.floor(i / 2) * 25;

        const cell = this.add.rectangle(wx, wy, 35, 20, 0x001400, 0.8);
        cell.setStrokeStyle(1, 0x00aa2b);

        const num = this.add.text(wx, wy, `${i + 1}`,
          { fontFamily: 'Courier New', fontSize: '11px', color: '#00aa2b' }
        ).setOrigin(0.5);

        this.workspaceCells.push({ rect: cell, text: num });
      }

      this.updateWorkspaceUI();

      this.workspaceFlash = this.add.text(
        this.cameras.main.width / 2,
        this.cameras.main.height / 2,
        '',
        { fontFamily: 'Courier New', fontSize: '180px', color: '#00ff41' }
      ).setOrigin(0.5).setAlpha(0);
    }

    updateWorkspaceUI() {
      if (!this.workspaceCells) return;

      this.workspaceCells.forEach((cell, i) => {
        const isActive = i + 1 === gameState.currentWorkspace;
        const hasWindows = gameState.workspaces[i + 1]?.windowCount > 0;

        cell.rect.setFillStyle(isActive ? 0x00aa2b : 0x001400, isActive ? 1 : 0.8);
        cell.rect.setStrokeStyle(1, isActive ? 0x00ff41 : 0x00aa2b);
        cell.text.setColor(isActive ? '#000000' : (hasWindows ? '#00ff41' : '#00aa2b'));
      });
    }

    // ============================================================
    // STICKY NOTES - Visual hints that fall off when mastered
    // ============================================================

    createStickyNotes() {
      const notes = STICKY_NOTES[gameState.stage];
      if (!notes) return;

      this.stickyNotes = {};
      const leftNotes = notes.filter(n => n.side === 'left');
      const rightNotes = notes.filter(n => n.side === 'right');

      // Position notes on left and right bezels
      const leftX = 8;
      const rightX = this.cameras.main.width - 8;
      const startY = 120;
      const noteSpacing = 75;

      leftNotes.forEach((note, i) => {
        this.createSingleNote(note, leftX, startY + i * noteSpacing, 'left');
      });

      rightNotes.forEach((note, i) => {
        this.createSingleNote(note, rightX, startY + i * noteSpacing, 'right');
      });
    }

    createSingleNote(note, x, y, side) {
      // Skip if already mastered
      if ((gameState.shortcutMastery[note.id] || 0) >= CONFIG.stickyNoteMastery) {
        return;
      }

      const noteWidth = 90;
      const noteHeight = 55;

      // Create container for the note
      const container = this.add.container(x, y);

      // Yellow sticky note background with slight rotation
      const rotation = (Math.random() - 0.5) * 0.15;
      container.setRotation(rotation);

      // Note shadow
      const shadow = this.add.rectangle(2, 2, noteWidth, noteHeight, 0x000000, 0.2);
      container.add(shadow);

      // Note background - yellow post-it color
      const bg = this.add.rectangle(0, 0, noteWidth, noteHeight, 0xffeb3b, 1);
      bg.setStrokeStyle(1, 0xe6d335);
      container.add(bg);

      // Tape strip at top
      const tape = this.add.rectangle(0, -noteHeight / 2 + 5, 35, 10, 0xcccccc, 0.6);
      container.add(tape);

      // Key shortcut text (hand-written style)
      const keyText = this.add.text(0, -8, note.key, {
        fontFamily: '"Comic Sans MS", "Marker Felt", cursive',
        fontSize: '13px',
        color: '#1a1a1a',
        fontStyle: 'bold'
      }).setOrigin(0.5);
      container.add(keyText);

      // Label text below
      const labelText = this.add.text(0, 12, note.label, {
        fontFamily: '"Comic Sans MS", "Marker Felt", cursive',
        fontSize: '9px',
        color: '#444444'
      }).setOrigin(0.5);
      container.add(labelText);

      // Set origin based on side
      if (side === 'left') {
        container.setX(x + noteWidth / 2 + 5);
      } else {
        container.setX(x - noteWidth / 2 - 5);
      }

      // Add gentle wiggle animation
      this.tweens.add({
        targets: container,
        rotation: rotation + (Math.random() > 0.5 ? 0.03 : -0.03),
        duration: 2000 + Math.random() * 1000,
        yoyo: true,
        repeat: -1,
        ease: 'Sine.easeInOut'
      });

      // Store reference
      this.stickyNotes[note.id] = {
        container,
        note,
        side
      };
    }

    // Map challenge action to sticky note ID
    getChallengeNoteId(challenge) {
      if (!challenge) return null;

      // Navigate actions map to directional notes
      if (challenge.action === 'navigate') {
        return `nav-${challenge.dir}`;
      }

      // Workspace switches
      if (challenge.action === 'workspace') {
        return `ws-${challenge.workspace}`;
      }

      // Move to workspace
      if (challenge.action === 'move-to-workspace') {
        return 'move-ws';
      }

      // App launches
      if (challenge.action === 'launch') {
        return `app-${challenge.app}`;
      }

      // Direct mapping for spawn, close, fullscreen, float, swap
      return challenge.action;
    }

    // Track mastery and animate note falling when mastered
    trackShortcutMastery(challenge) {
      const noteId = this.getChallengeNoteId(challenge);
      if (!noteId) return;

      // Increment mastery count
      gameState.shortcutMastery[noteId] = (gameState.shortcutMastery[noteId] || 0) + 1;

      // Check if mastered
      if (gameState.shortcutMastery[noteId] >= CONFIG.stickyNoteMastery) {
        this.animateNoteFalling(noteId);
      }
    }

    animateNoteFalling(noteId) {
      const noteData = this.stickyNotes?.[noteId];
      if (!noteData) return;

      const { container, side } = noteData;

      // Stop wiggle animation
      this.tweens.killTweensOf(container);

      // Dramatic peel-off and fall animation
      this.tweens.add({
        targets: container,
        rotation: side === 'left' ? -0.8 : 0.8,
        y: container.y + this.cameras.main.height + 100,
        x: container.x + (side === 'left' ? -50 : 50),
        alpha: 0,
        duration: 1200,
        ease: 'Quad.easeIn',
        onComplete: () => {
          container.destroy();
          delete this.stickyNotes[noteId];
        }
      });

      // Visual feedback - brief flash
      this.flashScreen(0x00ff41, 0.1);
    }

    createDemoIndicator() {
      this.add.rectangle(this.cameras.main.width / 2, 80, 120, 24, 0xff4444, 0.9);
      this.add.text(this.cameras.main.width / 2, 80, 'DEMO',
        { fontFamily: 'Courier New', fontSize: '12px', color: '#ffffff' }
      ).setOrigin(0.5);
    }

    // ============================================================
    // KEYBOARD HANDLING - CORRECT OMARCHY BINDINGS
    // ============================================================

    setupKeyboard() {
      this.game.canvas.setAttribute('tabindex', '0');
      this.game.canvas.focus();

      this._keyHandler = (event) => this.handleKeyDown(event);
      window.addEventListener('keydown', this._keyHandler);
    }

    handleKeyDown(event) {
      if (gameState.isPaused || gameState.isGameOver) return;
      if (event._handled) return;
      event._handled = true;

      const isMeta = event.metaKey || event.ctrlKey;
      const isShift = event.shiftKey;
      const isAlt = event.altKey;
      const key = event.key;

      // Escape: Pause
      if (key === 'Escape') {
        this.togglePause();
        return;
      }

      if (!isMeta) return;
      event.preventDefault();

      // Track if any valid action was taken
      let actionTaken = false;
      const challengeBefore = gameState.currentChallenge;

      // Super+Return: Spawn terminal
      if (key === 'Enter' && !isShift) {
        this.spawnWindow('terminal');
        actionTaken = true;
      }

      // Super+W: Close window (CORRECT Omarchy binding!)
      else if (key.toLowerCase() === 'w' && !isShift) {
        this.closeWindow();
        actionTaken = true;
      }

      // Super+F: Fullscreen
      else if (key.toLowerCase() === 'f' && !isShift) {
        this.toggleFullscreen();
        actionTaken = true;
      }

      // Super+T: Toggle floating
      else if (key.toLowerCase() === 't' && !isShift) {
        this.toggleFloat();
        actionTaken = true;
      }

      // Navigation: Super+Arrow (CORRECT Omarchy binding!)
      else if (!isShift) {
        const arrowDirs = {
          'ArrowLeft': 'left',
          'ArrowRight': 'right',
          'ArrowUp': 'up',
          'ArrowDown': 'down'
        };
        if (arrowDirs[key]) {
          this.moveFocus(arrowDirs[key]);
          actionTaken = true;
        }
      }

      // Swap windows: Super+Shift+Arrow (CORRECT Omarchy binding!)
      if (!actionTaken && isShift) {
        const arrowDirs = {
          'ArrowLeft': 'left',
          'ArrowRight': 'right',
          'ArrowUp': 'up',
          'ArrowDown': 'down'
        };
        if (arrowDirs[key]) {
          this.swapWindow(arrowDirs[key]);
          actionTaken = true;
        }
      }

      // Workspace switching: Super+1-4
      if (!actionTaken && !isShift && !isAlt && key >= '1' && key <= '4') {
        this.switchWorkspace(parseInt(key));
        actionTaken = true;
      }

      // Move to workspace: Super+Shift+1-4
      if (!actionTaken && isShift && !isAlt && key >= '1' && key <= '4') {
        this.moveToWorkspace(parseInt(key));
        actionTaken = true;
      }

      // Stage 3: Application shortcuts
      if (!actionTaken && gameState.stage >= 3) {
        const appShortcuts = {
          'b': 'browser',
          'f': 'files',
          'e': 'email',
          'a': 'ai',
          'm': 'music',
          'o': 'obsidian',
          'n': 'neovim'
        };
        if (isShift && appShortcuts[key.toLowerCase()]) {
          this.spawnWindow(appShortcuts[key.toLowerCase()]);
          actionTaken = true;
        }
      }

      // If an action was taken but the challenge wasn't completed, it was the wrong key
      if (actionTaken && challengeBefore && gameState.currentChallenge === challengeBefore) {
        this.wrongKeyPressed();
      }
    }

    // ============================================================
    // WINDOW OPERATIONS
    // ============================================================

    spawnWindow(type = 'terminal') {
      const app = APPLICATIONS[type] || APPLICATIONS.terminal;

      // Add window to dwindle tree
      const windowData = {
        type: type,
        app: app,
        id: Date.now()
      };

      const node = gameState.root.addWindow(windowData);
      gameState.focusedNode = node;
      gameState.windowCount++;

      // Re-render all windows
      this.renderWindows();

      // Visual spawn effect - flash where new window appeared
      const bounds = node.bounds;
      if (bounds) {
        const flash = this.add.rectangle(
          bounds.x + bounds.width / 2,
          bounds.y + bounds.height / 2,
          bounds.width,
          bounds.height,
          0x00ff41,
          0.5
        );
        flash.setStrokeStyle(3, 0x00ff41);
        this.tweens.add({
          targets: flash,
          alpha: 0,
          scaleX: 1.05,
          scaleY: 1.05,
          duration: 300,
          ease: 'Power2',
          onComplete: () => flash.destroy()
        });
      }

      playSound('spawn');
      this.checkChallenge('spawn');
      if (type !== 'terminal') {
        this.checkChallenge('app', { app: type });
      }
    }

    closeWindow() {
      if (!gameState.focusedNode || !gameState.focusedNode.hasWindow()) return;

      const windows = gameState.root.getAllWindows();
      if (windows.length === 0) return;

      // Find next window to focus
      let nextFocus = null;
      const idx = windows.findIndex(w => w.node === gameState.focusedNode);
      if (windows.length > 1) {
        nextFocus = windows[idx === 0 ? 1 : idx - 1]?.node;
      }

      // Remove from tree
      gameState.root.removeWindow(gameState.focusedNode);
      gameState.windowCount--;
      gameState.focusedNode = nextFocus;

      // Recalculate bounds and re-render
      gameState.root.recalculateBounds(
        this.workspaceBounds.x,
        this.workspaceBounds.y,
        this.workspaceBounds.width,
        this.workspaceBounds.height
      );

      this.renderWindows();

      playSound('close');
      this.checkChallenge('close');
    }

    moveFocus(direction) {
      if (!gameState.focusedNode) return;

      const dirMap = {
        'left': [-1, 0],
        'right': [1, 0],
        'up': [0, -1],
        'down': [0, 1]
      };

      const [dx, dy] = dirMap[direction];
      const next = gameState.root.findInDirection(gameState.focusedNode, dx, dy);

      if (next) {
        gameState.focusedNode = next;
        this.renderWindows();
        playSound('nav');
        this.checkChallenge('navigate', { dir: direction });
      }
    }

    swapWindow(direction) {
      if (!gameState.focusedNode || !gameState.focusedNode.hasWindow()) return;

      const dirMap = {
        'left': [-1, 0],
        'right': [1, 0],
        'up': [0, -1],
        'down': [0, 1]
      };

      const [dx, dy] = dirMap[direction];
      const other = gameState.root.findInDirection(gameState.focusedNode, dx, dy);

      if (other && other.hasWindow()) {
        DwindleNode.swap(gameState.focusedNode, other);
        this.renderWindows();
        playSound('move');
        this.checkChallenge('swap', { dir: direction });
      }
    }

    toggleFullscreen() {
      if (!gameState.focusedNode || !gameState.focusedNode.hasWindow()) return;

      // Flash effect
      this.flashScreen(0x00ff41, 0.2);
      playSound('fullscreen');
      this.checkChallenge('fullscreen');
    }

    toggleFloat() {
      if (!gameState.focusedNode || !gameState.focusedNode.hasWindow()) return;

      // Visual wobble
      this.flashScreen(0x00aaff, 0.15);
      playSound('float');
      this.checkChallenge('float');
    }

    // ============================================================
    // WORKSPACE OPERATIONS
    // ============================================================

    switchWorkspace(num) {
      if (num < 1 || num > CONFIG.workspaceCount || num === gameState.currentWorkspace) return;

      // Flash workspace number
      if (this.workspaceFlash) {
        this.workspaceFlash.setText(num.toString());
        this.workspaceFlash.setAlpha(1);
        this.tweens.add({
          targets: this.workspaceFlash,
          alpha: 0,
          scale: { from: 1, to: 1.5 },
          duration: 400,
          ease: 'Power2'
        });
      }

      // Save current workspace
      this.saveWorkspace();

      // Switch
      gameState.currentWorkspace = num;
      this.initWorkspace();

      this.renderWindows();
      this.updateWorkspaceUI();

      playSound('workspace');
      this.checkChallenge('workspace', { target: num });
    }

    moveToWorkspace(num) {
      if (num < 1 || num > CONFIG.workspaceCount) return;
      if (!gameState.focusedNode || !gameState.focusedNode.hasWindow()) return;

      const windowData = gameState.focusedNode.window;

      // Remove from current workspace
      gameState.root.removeWindow(gameState.focusedNode);
      gameState.windowCount--;

      // Recalculate current workspace
      gameState.root.recalculateBounds(
        this.workspaceBounds.x,
        this.workspaceBounds.y,
        this.workspaceBounds.width,
        this.workspaceBounds.height
      );

      // Get next focus
      const windows = gameState.root.getAllWindows();
      gameState.focusedNode = windows[0]?.node || null;

      // Add to target workspace
      if (!gameState.workspaces[num]) {
        gameState.workspaces[num] = {
          root: new DwindleNode(
            this.workspaceBounds.x,
            this.workspaceBounds.y,
            this.workspaceBounds.width,
            this.workspaceBounds.height
          ),
          focusedNode: null,
          windowCount: 0
        };
      }
      const targetWs = gameState.workspaces[num];
      targetWs.root.addWindow(windowData);
      targetWs.windowCount++;

      this.renderWindows();
      this.updateWorkspaceUI();

      playSound('send');
      this.checkChallenge('moveToWorkspace', { target: num });
    }

    // ============================================================
    // RENDERING
    // ============================================================

    renderWindows() {
      // Clear existing window graphics
      this.windowContainer.removeAll(true);

      const windows = gameState.root.getAllWindows();
      const gap = CONFIG.windowGap;

      for (const w of windows) {
        const { bounds, node } = w;
        const isFocused = node === gameState.focusedNode;
        const app = node.window.app;

        // Apply gap
        const x = bounds.x + gap;
        const y = bounds.y + gap;
        const width = bounds.width - gap * 2;
        const height = bounds.height - gap * 2;

        // Window container
        const container = this.add.container(x, y);

        // Background - slightly brighter for visibility against grid
        const bgColor = isFocused ? 0x0d1a0d : 0x0a120a;
        const bg = this.add.rectangle(width / 2, height / 2, width, height, bgColor);

        // All windows get a border - focused is bright, unfocused is dim
        if (isFocused) {
          bg.setStrokeStyle(3, 0x00ff41);
        } else {
          bg.setStrokeStyle(1, 0x00aa2b, 0.5);
        }

        // Header bar - dimmed for unfocused
        const headerHeight = Math.min(24, height * 0.15);
        const headerColor = isFocused ? app.color : Phaser.Display.Color.ValueToColor(app.color).darken(60).color;
        const header = this.add.rectangle(width / 2, headerHeight / 2, width, headerHeight, headerColor);
        header.setAlpha(isFocused ? 1 : 0.4);

        // Title - dimmed for unfocused
        const title = this.add.text(8, headerHeight / 2, app.name,
          { fontFamily: 'Courier New', fontSize: '11px', color: isFocused ? '#000000' : '#444444' }
        ).setOrigin(0, 0.5);

        // Icon (centered in window body) - dimmed for unfocused
        const iconSize = Math.min(60, Math.min(width, height - headerHeight) * 0.6);
        const icon = this.add.text(width / 2, headerHeight + (height - headerHeight) / 2, app.icon,
          { fontSize: `${iconSize}px` }
        ).setOrigin(0.5);
        icon.setAlpha(isFocused ? 1 : 0.3);

        // Focus indicator - pulsing glow for focused window
        if (isFocused) {
          this.tweens.add({
            targets: bg,
            alpha: { from: 0.9, to: 1 },
            duration: 500,
            yoyo: true,
            repeat: -1
          });
        } else {
          // Unfocused windows are dimmed overall
          container.setAlpha(0.5);
        }

        container.add([bg, header, title, icon]);
        this.windowContainer.add(container);
      }
    }

    flashScreen(color, alpha) {
      const flash = this.add.rectangle(
        this.cameras.main.width / 2,
        this.cameras.main.height / 2,
        this.cameras.main.width,
        this.cameras.main.height,
        color, alpha
      ).setDepth(1000);

      this.tweens.add({
        targets: flash,
        alpha: 0,
        duration: 200,
        onComplete: () => flash.destroy()
      });
    }

    // ============================================================
    // CHALLENGE SYSTEM
    // ============================================================

    playStageIntro(onComplete) {
      const messages = STAGE_INTROS[gameState.stage] || STAGE_INTROS[1];
      let messageIndex = 0;
      let introSkipped = false;

      // Store for skip functionality
      this.introOnComplete = onComplete;
      this.introActive = true;

      // Skip intro with Super+Enter
      const skipHandler = (e) => {
        if (e.metaKey && e.key === 'Enter' && this.introActive && !introSkipped) {
          introSkipped = true;
          this.introActive = false;
          stopCurrentVoice();
          this.commandText.setText('');
          this.hintText.setText('');
          this.commandText.setColor('#00ff41');
          document.removeEventListener('keydown', skipHandler);
          if (this.introOnComplete) this.introOnComplete();
        }
      };
      document.addEventListener('keydown', skipHandler);

      const showNextMessage = () => {
        if (introSkipped) return;

        if (messageIndex >= messages.length) {
          this.introActive = false;
          document.removeEventListener('keydown', skipHandler);
          this.commandText.setText('');
          this.hintText.setText('');

          this.time.delayedCall(300, () => {
            if (introSkipped) return;
            this.commandText.setText('READY...');
            this.commandText.setColor('#ffaa00');

            this.time.delayedCall(800, () => {
              if (introSkipped) return;
              this.commandText.setText('ENGAGE!');
              this.commandText.setColor('#00ff41');
              playSound('success');

              this.time.delayedCall(600, () => {
                if (introSkipped) return;
                if (onComplete) onComplete();
              });
            });
          });
          return;
        }

        const message = messages[messageIndex];
        playIntroAudio(gameState.stage, messageIndex);

        this.typewriterText(message, 25, () => {
          if (introSkipped) return;
          messageIndex++;
          this.time.delayedCall(700, showNextMessage);
        });
      };

      // Show skip hint
      this.hintText.setText('Press Super+Enter to skip intro');

      showNextMessage();
    }

    typewriterText(fullText, charDelay, onComplete) {
      let currentText = '';
      let charIndex = 0;

      const typeNext = () => {
        if (charIndex >= fullText.length) {
          if (onComplete) onComplete();
          return;
        }

        currentText += fullText[charIndex];
        this.commandText.setText(currentText);
        charIndex++;

        this.time.delayedCall(charDelay, typeNext);
      };

      typeNext();
    }

    startChallenge(num) {
      gameState.challenge = num;
      gameState.hintShown = false;
      gameState.urgentShown = false;
      gameState.wrongKeyCount = 0;

      const maxChallenges = gameState.maxChallenges[gameState.stage];
      this.challengeText.setText(`Challenge ${num}/${maxChallenges}`);

      if (num > maxChallenges) {
        this.completeStage();
        return;
      }

      const challenge = CHALLENGES[gameState.stage][num - 1];
      if (!challenge) {
        this.completeStage();
        return;
      }

      gameState.currentChallenge = challenge;
      gameState.challengeStartTime = Date.now();

      // Typewriter effect for command text (like a terminal)
      this.commandText.setText('');
      this.hintText.setText('');
      this.hintText.setColor('#00aa2b');

      // Play audio first, then typewriter syncs roughly with speech
      if (challenge.audio) {
        playCommandAudio(challenge.audio);
      }

      // Typewriter the command text
      this.typewriterText(challenge.command, 30);

      // Hint timing (audio only - no text hint displayed)
      this.time.delayedCall(CONFIG.hintDelay, () => {
        if (gameState.currentChallenge === challenge && !gameState.hintShown) {
          gameState.hintShown = true;
          playVoice('hint');
        }
      });

      this.time.delayedCall(CONFIG.urgentDelay, () => {
        if (gameState.currentChallenge === challenge && !gameState.urgentShown) {
          gameState.urgentShown = true;
          this.hintText.setColor('#ffaa00');
          playVoice('urgent');
        }
      });

      this.time.delayedCall(CONFIG.angryDelay, () => {
        if (gameState.currentChallenge === challenge) {
          this.hintText.setColor('#ff4444');
          playVoice('angry');
        }
      });

      // Fail timer - lose a life if too slow
      gameState.failTimer = this.time.delayedCall(CONFIG.failDelay, () => {
        if (gameState.currentChallenge === challenge) {
          this.challengeFailed();
        }
      });
    }

    checkChallenge(action, data = {}) {
      const challenge = gameState.currentChallenge;
      if (!challenge) return false;

      let success = false;

      if (challenge.action === action) {
        success = true;

        if (challenge.target !== undefined && data.target !== challenge.target) {
          success = false;
        }
        if (challenge.app && data.app !== challenge.app) {
          success = false;
        }
        if (challenge.dir && data.dir !== challenge.dir) {
          success = false;
        }
      }

      if (success) {
        this.challengeSuccess();
      }
      return success;
    }

    // Called when wrong key is pressed
    wrongKeyPressed() {
      if (!gameState.currentChallenge) return;

      gameState.wrongKeyCount = (gameState.wrongKeyCount || 0) + 1;
      gameState.combo = 0; // Reset combo on wrong key
      this.comboText.setText('');

      // Flash red
      this.flashScreen(0xff4444, 0.2);
      playSound('error');

      // Play angry bark after multiple wrong keys or immediately if hint already shown
      if (gameState.wrongKeyCount >= 2 || gameState.hintShown) {
        playVoice('angry');
        // Yell the hint in the terminal after wrong key
        if (!gameState.hintShown && gameState.currentChallenge) {
          gameState.hintShown = true;
          // Typewrite hint to terminal: "USE [shortcut]!"
          this.typewriterText(`USE ${gameState.currentChallenge.hint}!`, 20);
        }
      }
    }

    // Get shield display as retro bar meter [████████░░] 80% (filled = remaining shields)
    getShieldDisplay() {
      const pct = Math.max(0, Math.min(100, gameState.shield));
      const filled = Math.round(pct / 10);
      const empty = 10 - filled;
      const bar = '█'.repeat(filled) + '░'.repeat(empty);
      return `[${bar}] ${pct}%`;
    }

    // Update shield display with color-coded warning states
    updateShieldDisplay() {
      if (this.shieldText) {
        this.shieldText.setText(this.getShieldDisplay());
        // Color changes based on shield level (inverted from breach - low = danger)
        const pct = gameState.shield;
        if (pct <= 10) {
          // CRITICAL - flashing red
          this.shieldText.setColor('#ff0000');
          this.shieldLabel.setColor('#ff0000');
        } else if (pct <= 25) {
          // DANGER - red
          this.shieldText.setColor('#ff4444');
          this.shieldLabel.setColor('#ff4444');
        } else if (pct <= 50) {
          // WARNING - orange
          this.shieldText.setColor('#ff6600');
          this.shieldLabel.setColor('#ff6600');
        } else {
          // OK - green
          this.shieldText.setColor('#00ff41');
          this.shieldLabel.setColor('#00ff41');
        }
        // Pulse animation on shield damage
        this.tweens.add({
          targets: this.shieldText,
          scale: { from: 1.3, to: 1 },
          duration: 300,
          ease: 'Bounce'
        });
      }
    }

    // Play shield warning voice at thresholds
    playShieldWarning() {
      const shield = gameState.shield;
      const lastWarning = gameState.lastShieldWarning;

      // Check each threshold (50, 25, 10) and play appropriate warning
      for (const threshold of CONFIG.shieldWarnings) {
        if (shield <= threshold && lastWarning > threshold) {
          gameState.lastShieldWarning = threshold;

          // Play escalating warning based on severity
          if (threshold === 50) {
            // "SHIELDS AT 50%!"
            playVoice('urgent');
            this.commandText.setText('SHIELDS WEAKENING!');
            this.commandText.setColor('#ff6600');
          } else if (threshold === 25) {
            // "SHIELD FAILURE IMMINENT!"
            playVoice('angry');
            this.commandText.setText('SHIELD FAILURE IMMINENT!');
            this.commandText.setColor('#ff4444');
            // Screen shake
            this.cameras.main.shake(200, 0.01);
          } else if (threshold === 10) {
            // "CRITICAL! SHIELDS FAILING!"
            playVoice('angry');
            this.commandText.setText('CRITICAL! SHIELDS FAILING!');
            this.commandText.setColor('#ff0000');
            // Bigger shake + flash
            this.cameras.main.shake(400, 0.02);
            this.flashScreen(0xff0000, 0.3);
          }
          break; // Only trigger one warning per damage event
        }
      }
    }

    // Called when player fails a challenge (timeout)
    challengeFailed() {
      // Cancel fail timer
      if (gameState.failTimer) {
        gameState.failTimer.remove();
        gameState.failTimer = null;
      }

      // Decrease shield health
      gameState.shield -= CONFIG.shieldDamage;
      this.updateShieldDisplay();

      // Check for shield warning thresholds (commander yells warnings)
      this.playShieldWarning();

      // Reset combo
      gameState.combo = 0;
      this.comboText.setText('');

      // Big red flash
      this.flashScreen(0xff0000, 0.4);
      playSound('error');

      // Show failure message (unless warning override)
      if (gameState.shield > 50) {
        this.commandText.setText('TOO SLOW!');
        this.commandText.setColor('#ff4444');
        playVoice('angry');
      }
      this.hintText.setText('');

      // Check for game over - shields depleted
      if (gameState.shield <= 0) {
        gameState.isGameOver = true;
        this.shieldFailureSequence();
        return;
      }

      // Clear current challenge and start next
      gameState.currentChallenge = null;

      this.time.delayedCall(CONFIG.challengeDelay, () => {
        this.startChallenge(gameState.challenge + 1);
      });
    }

    // Dramatic shield failure animation for game over
    shieldFailureSequence() {
      // Stop all current audio
      stopCurrentVoice();

      // Screen goes red with heavy shake
      this.cameras.main.shake(800, 0.03);
      this.flashScreen(0xff0000, 0.6);

      // Series of flashing "SHIELD FAILURE" messages
      const messages = [
        { text: 'SHIELD', color: '#ff0000', delay: 0 },
        { text: 'FAILURE', color: '#ff4444', delay: 300 },
        { text: 'TOTAL', color: '#ff0000', delay: 600 },
        { text: 'SHIELD FAILURE!', color: '#ff0000', delay: 900 }
      ];

      messages.forEach(msg => {
        this.time.delayedCall(msg.delay, () => {
          this.commandText.setText(msg.text);
          this.commandText.setColor(msg.color);
          playSound('error');
        });
      });

      // Play dramatic failure sound
      playVoice('angry');

      // Flash the restart button to draw attention
      this.highlightRestartButton();

      // Show results after dramatic pause
      this.time.delayedCall(2500, () => {
        this.showResults(false);
      });
    }

    // Highlight the restart button with pulsing glow
    highlightRestartButton() {
      if (!this.restartBtn) return;

      // Make it bright and pulsing
      this.restartBtn.setColor('#00ff41');
      this.restartBtn.setStyle({
        backgroundColor: '#002200',
        padding: { x: 8, y: 4 }
      });

      // Pulsing animation
      this.tweens.add({
        targets: this.restartBtn,
        alpha: { from: 1, to: 0.4 },
        scale: { from: 1.1, to: 1 },
        duration: 400,
        yoyo: true,
        repeat: -1,
        ease: 'Sine.easeInOut'
      });
    }

    challengeSuccess() {
      // Cancel fail timer
      if (gameState.failTimer) {
        gameState.failTimer.remove();
        gameState.failTimer = null;
      }

      gameState.combo++;
      gameState.maxCombo = Math.max(gameState.maxCombo, gameState.combo);

      const timeBonus = Math.max(0, 1 - (Date.now() - gameState.challengeStartTime) / 10000);
      const comboMultiplier = Math.pow(CONFIG.comboMultiplier, Math.min(gameState.combo - 1, 10));

      const points = Math.round(CONFIG.baseScore * comboMultiplier * (1 + timeBonus));
      gameState.score += points;

      this.scoreText.setText(gameState.score.toString());
      this.comboText.setText(gameState.combo > 1 ? `${gameState.combo}x` : '');

      this.tweens.add({
        targets: this.scoreText,
        scale: { from: 1.3, to: 1 },
        duration: 200
      });

      this.flashScreen(0x00ff41, 0.15);
      playSound('success');

      if (gameState.combo >= 5 && gameState.combo % 5 === 0) {
        playVoice('combo');
      } else if (Math.random() < 0.25) {
        playVoice('calm');
      }

      // Track shortcut mastery for sticky notes
      this.trackShortcutMastery(gameState.currentChallenge);

      gameState.currentChallenge = null;

      this.time.delayedCall(CONFIG.challengeDelay, () => {
        this.startChallenge(gameState.challenge + 1);
      });
    }

    completeStage() {
      gameState.isGameOver = true;
      gameState.score += CONFIG.stageBonus;
      this.scoreText.setText(gameState.score.toString());

      playVoice('victory');
      playSound('victory');

      this.commandText.setText('STAGE COMPLETE!');
      this.hintText.setText('');

      this.time.delayedCall(2500, () => {
        this.showResults(true);
      });
    }

    showResults(victory) {
      const overlay = this.add.rectangle(
        this.cameras.main.width / 2,
        this.cameras.main.height / 2,
        this.cameras.main.width,
        this.cameras.main.height,
        0x000000, 0.92
      ).setDepth(2000);

      const title = victory ? 'VICTORY!' : 'DEFEATED';
      const titleColor = victory ? '#00ff41' : '#ff4444';

      this.add.text(this.cameras.main.width / 2, 120, title,
        { fontFamily: 'Courier New', fontSize: '48px', color: titleColor }
      ).setOrigin(0.5).setDepth(2001);

      this.add.text(this.cameras.main.width / 2, 180,
        `Stage ${gameState.stage} Complete`,
        { fontFamily: 'Courier New', fontSize: '18px', color: '#00aa2b' }
      ).setOrigin(0.5).setDepth(2001);

      const stats = [
        `Score: ${gameState.score}`,
        `Max Combo: ${gameState.maxCombo}x`,
        `Challenges: ${gameState.challenge - 1}/${gameState.maxChallenges[gameState.stage]}`
      ].join('\n');

      this.add.text(this.cameras.main.width / 2, 280, stats,
        { fontFamily: 'Courier New', fontSize: '16px', color: '#00ff41', align: 'center', lineSpacing: 6 }
      ).setOrigin(0.5).setDepth(2001);

      const nextAction = victory && gameState.stage < 3
        ? 'Press SPACE for Stage ' + (gameState.stage + 1)
        : 'Press SPACE to play again';

      this.add.text(this.cameras.main.width / 2, 380, nextAction,
        { fontFamily: 'Courier New', fontSize: '14px', color: '#00aa2b' }
      ).setOrigin(0.5).setDepth(2001);

      this.input.keyboard.once('keydown-SPACE', () => {
        if (victory && gameState.stage < 3) {
          gameState.stage++;
        }
        resetGameState();
        this.scene.restart();
      });

      this.input.keyboard.once('keydown-R', () => {
        resetGameState();
        this.scene.restart();
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
          0x000000, 0.85
        ).setDepth(3000);

        this.pauseText = this.add.text(
          this.cameras.main.width / 2,
          this.cameras.main.height / 2 - 30,
          'PAUSED',
          { fontFamily: 'Courier New', fontSize: '42px', color: '#00ff41' }
        ).setOrigin(0.5).setDepth(3001);

        this.pauseHint = this.add.text(
          this.cameras.main.width / 2,
          this.cameras.main.height / 2 + 25,
          'Press ESC to resume\nPress R to restart',
          { fontFamily: 'Courier New', fontSize: '14px', color: '#00aa2b', align: 'center' }
        ).setOrigin(0.5).setDepth(3001);
      } else {
        this.pauseOverlay?.destroy();
        this.pauseText?.destroy();
        this.pauseHint?.destroy();
      }
    }

    // Demo playback (simplified)
    startDemoPlayback() {
      if (!gameState.demoEvents.length) return;

      const playNext = () => {
        if (gameState.demoIndex >= gameState.demoEvents.length) {
          if (gameState.isRecordMode) window.recordingComplete = true;
          return;
        }

        const event = gameState.demoEvents[gameState.demoIndex];
        this.executeDemoEvent(event);
        gameState.demoIndex++;

        const next = gameState.demoEvents[gameState.demoIndex];
        if (next) {
          const delay = next.time - event.time;
          this.time.delayedCall(Math.max(delay, 50), playNext);
        } else if (gameState.isRecordMode) {
          this.time.delayedCall(500, () => { window.recordingComplete = true; });
        }
      };

      const first = gameState.demoEvents[0];
      this.time.delayedCall(first.time || 0, playNext);
    }

    executeDemoEvent(event) {
      if (event.type === 'keydown') {
        const keyEvent = {
          key: event.key,
          metaKey: event.modifiers?.includes('Meta') || false,
          shiftKey: event.modifiers?.includes('Shift') || false,
          altKey: event.modifiers?.includes('Alt') || false,
          ctrlKey: event.modifiers?.includes('Ctrl') || false,
          preventDefault: () => {}
        };
        this.handleKeyDown(keyEvent);
      }
    }
  }

  // ============================================================
  // AUDIO SYSTEM
  // ============================================================

  function playSound(name) {
    if (!gameState.audioEnabled) return;
    try {
      const audio = new Audio(`/assets/audio/sfx-${name}.mp3`);
      audio.volume = CONFIG.sfxVolume;
      audio.play().catch(() => {});
    } catch (e) {}
  }

  function playVoice(category) {
    if (!gameState.audioEnabled) return;

    const variants = VOICE_VARIANTS[category];
    if (!variants?.length) return;

    const available = variants.filter(v => !gameState.recentVoices.includes(v));
    const pool = available.length ? available : variants;
    const variant = pool[Math.floor(Math.random() * pool.length)];

    gameState.recentVoices.push(variant);
    if (gameState.recentVoices.length > CONFIG.maxRecentVoices) {
      gameState.recentVoices.shift();
    }

    // Use bark audio (angry radio filter) for hint/urgent/angry categories
    const barkCategories = ['hint', 'urgent', 'angry'];
    if (barkCategories.includes(category)) {
      playBarkAudio(variant);
    } else {
      playCommandAudio(variant, false);
    }
  }

  function stopCurrentVoice() {
    if (gameState.currentVoiceAudio) {
      try {
        gameState.currentVoiceAudio.pause();
        gameState.currentVoiceAudio.currentTime = 0;
      } catch (e) {}
      gameState.currentVoiceAudio = null;
    }
  }

  function playRadioStatic(duration = 120, onEnd) {
    if (!gameState.audioEnabled) {
      if (onEnd) onEnd();
      return;
    }

    try {
      const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
      const bufferSize = audioCtx.sampleRate * (duration / 1000);
      const buffer = audioCtx.createBuffer(1, bufferSize, audioCtx.sampleRate);
      const data = buffer.getChannelData(0);

      for (let i = 0; i < bufferSize; i++) {
        const t = i / bufferSize;
        const envelope = Math.sin(t * Math.PI);
        data[i] = (Math.random() * 2 - 1) * envelope * 0.25;
      }

      const source = audioCtx.createBufferSource();
      source.buffer = buffer;

      const filter = audioCtx.createBiquadFilter();
      filter.type = 'bandpass';
      filter.frequency.value = 2000;
      filter.Q.value = 0.5;

      const gainNode = audioCtx.createGain();
      gainNode.gain.value = CONFIG.sfxVolume * 0.5;

      source.connect(filter);
      filter.connect(gainNode);
      gainNode.connect(audioCtx.destination);

      source.start();
      source.onended = () => {
        audioCtx.close();
        if (onEnd) onEnd();
      };
    } catch (e) {
      if (onEnd) onEnd();
    }
  }

  // Shared audio context for radio effects
  let radioAudioContext = null;

  function getRadioAudioContext() {
    if (!radioAudioContext || radioAudioContext.state === 'closed') {
      radioAudioContext = new (window.AudioContext || window.webkitAudioContext)();
    }
    return radioAudioContext;
  }

  function playCommandAudio(audioId, isAngryBark = false) {
    if (!gameState.audioEnabled) return;

    stopCurrentVoice();

    playRadioStatic(100, () => {
      try {
        const audioCtx = getRadioAudioContext();
        const audio = new Audio(`/assets/audio/${audioId}.mp3`);
        audio.crossOrigin = 'anonymous';

        audio.addEventListener('canplaythrough', () => {
          try {
            // Create source from audio element
            const source = audioCtx.createMediaElementSource(audio);

            // Bandpass filter - telephone/radio quality (300Hz - 3kHz)
            const bandpass = audioCtx.createBiquadFilter();
            bandpass.type = 'bandpass';
            bandpass.frequency.value = isAngryBark ? 1200 : 1500; // Lower freq for angrier sound
            bandpass.Q.value = 0.7;

            // High-pass to remove rumble
            const highpass = audioCtx.createBiquadFilter();
            highpass.type = 'highpass';
            highpass.frequency.value = 300;

            // Low-pass to cut high frequencies (more muffled)
            const lowpass = audioCtx.createBiquadFilter();
            lowpass.type = 'lowpass';
            lowpass.frequency.value = isAngryBark ? 2500 : 3000;

            // Compressor for that "squashed" radio sound
            const compressor = audioCtx.createDynamicsCompressor();
            compressor.threshold.value = -24;
            compressor.knee.value = 12;
            compressor.ratio.value = 8;
            compressor.attack.value = 0.003;
            compressor.release.value = 0.1;

            // Gain node for volume control
            const gainNode = audioCtx.createGain();
            gainNode.gain.value = CONFIG.voiceVolume * (isAngryBark ? 1.2 : 1.0);

            // Connect the chain: source → highpass → lowpass → bandpass → compressor → gain → output
            source.connect(highpass);
            highpass.connect(lowpass);
            lowpass.connect(bandpass);
            bandpass.connect(compressor);
            compressor.connect(gainNode);
            gainNode.connect(audioCtx.destination);

            // Add fade-out tail to prevent harsh cutoff
            audio.addEventListener('ended', () => {
              // Quick fade out
              gainNode.gain.linearRampToValueAtTime(0, audioCtx.currentTime + 0.1);
              // Add trailing static
              playRadioStatic(80);
            });

            gameState.currentVoiceAudio = audio;
            audio.play().catch(() => {});
          } catch (e) {
            // Fallback to basic playback if Web Audio fails
            audio.volume = CONFIG.voiceVolume;
            gameState.currentVoiceAudio = audio;
            audio.play().catch(() => {});
          }
        }, { once: true });

        // Trigger load
        audio.load();
      } catch (e) {}
    });
  }

  function playIntroAudio(stage, lineIndex) {
    if (!gameState.audioEnabled) return;
    const audioId = `stage${stage}-intro-${lineIndex + 1}`;
    playCommandAudio(audioId, false);
  }

  // Play angry drill sergeant bark for wrong answer/timeout hints
  function playBarkAudio(audioId) {
    if (!gameState.audioEnabled) return;
    playCommandAudio(audioId, true); // true = angry bark mode (lower freq, louder)
  }

  // ============================================================
  // UTILITIES
  // ============================================================

  function resetGameState() {
    gameState.challenge = 1;
    gameState.score = 0;
    gameState.combo = 0;
    gameState.maxCombo = 0;
    gameState.isPaused = false;
    gameState.isGameOver = false;
    gameState.shield = 100;
    gameState.lastShieldWarning = 100;
    gameState.failTimer = null;
    gameState.root = null;
    gameState.focusedNode = null;
    gameState.windowCount = 0;
    gameState.currentWorkspace = 1;
    gameState.workspaces = {};
    gameState.currentChallenge = null;
    gameState.recentVoices = [];
    gameState.demoIndex = 0;
  }

  async function loadDemoScript(path) {
    try {
      // Construct proper demo URL: /demos/path.json
      let demoUrl = path;
      if (!demoUrl.startsWith('/')) {
        demoUrl = '/demos/' + demoUrl;
      }
      if (!demoUrl.endsWith('.json')) {
        demoUrl += '.json';
      }

      const response = await fetch(demoUrl);
      if (!response.ok) return;

      const demo = await response.json();
      gameState.isDemoMode = true;
      gameState.demoEvents = demo.events || [];
      gameState.demoDuration = demo.duration || 60000;

      if (demo.stage) {
        gameState.stage = demo.stage;
      } else if (demo.meta?.stage) {
        gameState.stage = demo.meta.stage;
      }
    } catch (e) {
      console.error('Demo load error:', e);
    }
  }

  // ============================================================
  // INITIALIZATION
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
      }
    };

    new Phaser.Game(config);
  };

  if (typeof Phaser !== 'undefined' && document.getElementById('game')?.hidden === false) {
    window.initGame();
  }

})();
