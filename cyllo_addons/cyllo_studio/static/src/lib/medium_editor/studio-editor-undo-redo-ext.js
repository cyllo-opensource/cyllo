// undo_redo_manager.js

/**
 * UndoRedoManager - Universal undo/redo library for any HTML element
 * Works standalone or with Medium Editor, Dragula, and other libraries
 *
 * @example
 * const undoManager = new UndoRedoManager('#my-editor');
 * undoManager.startTracking();
 */
class UndoRedoManager {
  constructor(elementSelector, options = {}) {
    // Get the element
    this.editor = typeof elementSelector === 'string'
      ? document.querySelector(elementSelector)
      : elementSelector;

    if (!this.editor) {
      throw new Error('UndoRedoManager: Element not found');
    }

    // Configuration
    this.maxStackSize = options.maxStackSize || 50;
    this.debounceTime = options.debounceTime || 500;
    this.autoTrack = options.autoTrack !== false; // Default true
    this.trackAttributes = options.trackAttributes !== false; // Default true
    this.keyboardShortcuts = options.keyboardShortcuts !== false; // Default true

    // State management
    this.undoStack = [];
    this.redoStack = [];
    this.debounceTimer = null;
    this.isRestoring = false;
    this.observers = [];
    this.eventListeners = [];

    // Save initial state
    this.saveState();

    // Auto-start tracking if enabled
    if (this.autoTrack) {
      this.startTracking();
    }
  }

  /**
   * Capture current state of the editor
   */
  getCurrentState() {
    return {
      html: this.editor.innerHTML,
      timestamp: Date.now()
    };
  }

  /**
   * Save state to undo stack
   */
  saveState() {
    if (this.isRestoring || !this.editor) return;

    const currentState = this.getCurrentState();

    // Don't save if nothing changed
    if (this.undoStack.length > 0) {
      const lastState = this.undoStack[this.undoStack.length - 1];
      if (lastState.html === currentState.html) return;
    }

    this.undoStack.push(currentState);

    // Clear redo stack when new action is performed
    this.redoStack = [];

    // Limit stack size
    if (this.undoStack.length > this.maxStackSize) {
      this.undoStack.shift();
    }

    this.updateUI();
    this.triggerEvent('stateChanged', { canUndo: this.canUndo(), canRedo: this.canRedo() });
  }

  /**
   * Debounced save (for rapid changes)
   */
  debouncedSave() {
    clearTimeout(this.debounceTimer);
    this.debounceTimer = setTimeout(() => {
      this.saveState();
    }, this.debounceTime);
  }

  /**
   * Undo last action
   */
  undo() {
    if (this.undoStack.length <= 1) return false;

    this.isRestoring = true;

    const currentState = this.undoStack.pop();
    this.redoStack.push(currentState);

    const previousState = this.undoStack[this.undoStack.length - 1];
    this.restoreState(previousState);

    this.isRestoring = false;
    this.updateUI();
    this.triggerEvent('undo', { state: previousState });

    return true;
  }

  /**
   * Redo last undone action
   */
  redo() {
    if (this.redoStack.length === 0) return false;

    this.isRestoring = true;

    const nextState = this.redoStack.pop();
    this.undoStack.push(nextState);
    this.restoreState(nextState);

    this.isRestoring = false;
    this.updateUI();
    this.triggerEvent('redo', { state: nextState });

    return true;
  }

  /**
   * Restore editor to a previous state
   */
  restoreState(state) {
    this.editor.innerHTML = state.html;
    this.triggerEvent('restored', { state });
  }

  /**
   * Check if can undo
   */
  canUndo() {
    return this.undoStack.length > 1;
  }

  /**
   * Check if can redo
   */
  canRedo() {
    return this.redoStack.length > 0;
  }

  /**
   * Start automatic tracking of changes
   */
  startTracking() {
    this.stopTracking(); // Clean up any existing tracking

    // Track input events (typing, paste, etc.)
    const inputHandler = () => this.debouncedSave();
    this.editor.addEventListener('input', inputHandler);
    this.eventListeners.push({ element: this.editor, event: 'input', handler: inputHandler });

    // Track attribute changes if enabled
    if (this.trackAttributes) {
      const observer = new MutationObserver((mutations) => {
        if (this.isRestoring) return;

        let shouldSave = false;
        for (const mutation of mutations) {
          if (mutation.type === 'childList' || mutation.type === 'attributes') {
            shouldSave = true;
            break;
          }
        }

        if (shouldSave) {
          this.debouncedSave();
        }
      });

      observer.observe(this.editor, {
        childList: true,
        subtree: true,
        attributes: true,
        attributeOldValue: true
      });

      this.observers.push(observer);
    }

    // Setup keyboard shortcuts if enabled
    if (this.keyboardShortcuts) {
      this.setupKeyboardShortcuts();
    }

    // Setup buttons if they exist
    this.setupButtons();

    return this;
  }

  /**
   * Stop tracking changes
   */
  stopTracking() {
    // Remove event listeners
    this.eventListeners.forEach(({ element, event, handler }) => {
      element.removeEventListener(event, handler);
    });
    this.eventListeners = [];

    // Disconnect observers
    this.observers.forEach(observer => observer.disconnect());
    this.observers = [];

    return this;
  }

  /**
   * Setup keyboard shortcuts
   */
  setupKeyboardShortcuts() {
    const keyHandler = (e) => {
      // Only trigger if the editor or its children are focused
      if (!this.editor.contains(document.activeElement)) return;

      // Ctrl+Z or Cmd+Z (Undo)
      if ((e.ctrlKey || e.metaKey) && !e.shiftKey && e.key === 'z') {
        e.preventDefault();
        this.undo();
      }
      // Ctrl+Y or Ctrl+Shift+Z or Cmd+Shift+Z (Redo)
      else if ((e.ctrlKey || e.metaKey) && (e.shiftKey && e.key === 'z' || e.key === 'y')) {
        e.preventDefault();
        this.redo();
      }
    };

    document.addEventListener('keydown', keyHandler);
    this.eventListeners.push({ element: document, event: 'keydown', handler: keyHandler });
  }

  /**
   * Setup undo/redo buttons (if they exist in the DOM)
   */
  setupButtons() {
    const undoBtn = document.querySelector('[data-undo]');
    const redoBtn = document.querySelector('[data-redo]');

    if (undoBtn) {
      const undoHandler = () => this.undo();
      undoBtn.addEventListener('click', undoHandler);
      this.eventListeners.push({ element: undoBtn, event: 'click', handler: undoHandler });
    }

    if (redoBtn) {
      const redoHandler = () => this.redo();
      redoBtn.addEventListener('click', redoHandler);
      this.eventListeners.push({ element: redoBtn, event: 'click', handler: redoHandler });
    }

    this.updateUI();
  }

  /**
   * Update UI elements (buttons)
   */
  updateUI() {
    const undoBtn = document.querySelector('[data-undo]');
    const redoBtn = document.querySelector('[data-redo]');

    if (undoBtn) {
      undoBtn.disabled = !this.canUndo();
      undoBtn.classList.toggle('disabled', !this.canUndo());
    }
    if (redoBtn) {
      redoBtn.disabled = !this.canRedo();
      redoBtn.classList.toggle('disabled', !this.canRedo());
    }
  }

  /**
   * Trigger custom events
   */
  triggerEvent(eventName, detail = {}) {
    this.editor.dispatchEvent(new CustomEvent(`undoredo:${eventName}`, {
      detail,
      bubbles: true
    }));
  }

  /**
   * Clear all history
   */
  clear() {
    this.undoStack = [];
    this.redoStack = [];
    this.saveState();
    return this;
  }

  /**
   * Get stack info
   */
  getInfo() {
    return {
      undoCount: this.undoStack.length - 1,
      redoCount: this.redoStack.length,
      canUndo: this.canUndo(),
      canRedo: this.canRedo()
    };
  }

  /**
   * Destroy the manager and clean up
   */
  destroy() {
    clearTimeout(this.debounceTimer);
    this.stopTracking();
    this.clear();
    this.editor = null;
  }
}

/**
 * MediumEditor Extensions for Cyllo Studio
 */
if (typeof MediumEditor !== 'undefined') {
  const DeleteButton = MediumEditor.Extension.extend({
    name: 'deleteElement',
    init: function () {
      this.button = this.document.createElement('button');
      this.button.classList.add('medium-editor-action');
      this.button.innerHTML = `<svg xmlns="http://www.w3.org/2000/svg" width="13" height="13"
             viewBox="0 0 24 24" fill="none" stroke="currentColor"
             stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
          <polyline points="3 6 5 6 21 6"/>
          <path d="M19 6l-1 14H6L5 6"/>
          <path d="M10 11v6M14 11v6"/>
          <path d="M9 6V4h6v2"/>
        </svg>`;
      this.button.title = 'Delete Element';

      this.on(this.button, 'click', this.handleClick.bind(this));
    },
    getButton: function () {
      return this.button;
    },
    handleClick: function (event) {
      event.preventDefault();
      event.stopPropagation();

      const el = this.base.getSelectedParentElement();
      if (el && !el.classList.contains('page')) {
        el.remove();
        this.base.checkContentChanged();
      }
    }
  });

  const UndoButton = MediumEditor.Extension.extend({
    name: 'undoButton',
    init: function () {
      this.button = this.document.createElement('button');
      this.button.classList.add('medium-editor-action');
      this.button.innerHTML = '<i class="fa fa-undo"></i>';
      this.button.title = 'Undo';
      this.on(this.button, 'click', this.handleClick.bind(this));
    },
    getButton: function () { return this.button; },
    handleClick: function (event) {
      event.preventDefault();
      if (this.base.options.owner && typeof this.base.options.owner.undo === 'function') {
        this.base.options.owner.undo();
      }
    }
  });

  const RedoButton = MediumEditor.Extension.extend({
    name: 'redoButton',
    init: function () {
      this.button = this.document.createElement('button');
      this.button.classList.add('medium-editor-action');
      this.button.innerHTML = '<i class="fa fa-repeat"></i>';
      this.button.title = 'Redo';
      this.on(this.button, 'click', this.handleClick.bind(this));
    },
    getButton: function () { return this.button; },
    handleClick: function (event) {
      event.preventDefault();
      if (this.base.options.owner && typeof this.base.options.owner.redo === 'function') {
        this.base.options.owner.redo();
      }
    }
  });

  const SettingsButton = MediumEditor.Extension.extend({
    name: 'settingsButton',
    init: function () {
      this.button = this.document.createElement('button');
      this.button.classList.add('medium-editor-action');
      this.button.innerHTML = '⚙';
      this.button.title = 'Settings';
      this.on(this.button, 'click', this.handleClick.bind(this));
    },
    getButton: function () { return this.button; },
    handleClick: function (event) {
      event.preventDefault();
      event.stopPropagation();

      const el = this.base.getSelectedParentElement();
      if (!el) return;

      let targetEl = el.closest('.box-section-wrapper, .table-wrapper, .field-block, .qr_block, .sign-wrapper') || el;
      this.showPopup(targetEl);
    },
    showPopup: function (targetEl, anchorEl = null) {
      const existing = document.getElementById('cy-medium-settings-popup');
      if (existing) existing.remove();

      const popup = document.createElement('div');
      popup.id = 'cy-medium-settings-popup';
      popup.className = 'cy-medium-settings-popup cy-studio';

      let cfg = {};
      try { cfg = JSON.parse(targetEl.dataset.boxConfig || '{}'); } catch (e) { }
      if (!cfg.style) cfg.style = {};
      const s = cfg.style;

      const visible = targetEl.classList.contains('cy-block-hidden') ? false : true;
      const active = targetEl.getAttribute('t-if') === 'False' ? false : true;
      const pbBefore = targetEl.classList.contains('page-break-before');
      const pbAfter = targetEl.classList.contains('page-break-after');

      popup.innerHTML = `
        <div class="settings-header">
            <h4>Block Settings</h4>
            <button class="close-btn">&times;</button>
        </div>
        <div class="settings-body">
            <div class="settings-section">
                <h5>General</h5>
                <label><input type="checkbox" id="cy-set-visible" ${visible ? 'checked' : ''}> Visible</label>
                <label><input type="checkbox" id="cy-set-active" ${active ? 'checked' : ''}> Active</label>
<!--                <label><input type="checkbox" id="cy-set-lock" ${cfg.locked ? 'checked' : ''}> Lock Block</label>-->
            </div>
            <div class="settings-section">
                <h5>Layout</h5>
                <div><label>Width:</label><input type="text" id="cy-set-w" value="${s.width || ''}"></div>
                <div><label>Height:</label><input type="text" id="cy-set-h" value="${s.height || ''}"></div>
                <div><label>Padding:</label><input type="text" id="cy-set-p" value="${s.padding || ''}"></div>
                <div><label>Margin:</label><input type="text" id="cy-set-m" value="${s.margin || ''}"></div>
            </div>
            <div class="settings-section">
                <h5>Appearance</h5>
                <div><label>Bg Color:</label><input type="color" id="cy-set-bg" value="${s.backgroundColor || '#ffffff'}"></div>
                <div><label>Color:</label><input type="color" id="cy-set-color" value="${s.color || '#000000'}"></div>
                <div><label>Border:</label><input type="text" id="cy-set-b" value="${s.border || ''}"></div>
                <div><label>Radius:</label><input type="text" id="cy-set-br" value="${s.borderRadius || ''}"></div>
            </div>
<!--            <div class="settings-section">-->
<!--                <h5>Report Settings</h5>-->
<!--                <label><input type="checkbox" id="cy-set-pbb" ${pbBefore ? 'checked' : ''}> Page Break Before</label>-->
<!--                <label><input type="checkbox" id="cy-set-pba" ${pbAfter ? 'checked' : ''}> Page Break After</label>-->
<!--            </div>-->
            <div class="settings-section">
                <h5>Advanced</h5>
                <div><label>Class:</label><input type="text" id="cy-set-cls" value="${targetEl.className.replace(/cy-block-hidden|d-print-none/g, '').trim()}"></div>
            </div>
        </div>
      `;

      let toolbarEl = null;
      try {
        toolbarEl = this.base.getExtensionByName('toolbar').getToolbarElement();
      } catch(e) {}

      if (anchorEl) {
        const rect = anchorEl.getBoundingClientRect();
        popup.style.top = (rect.bottom + window.scrollY + 10) + 'px';
        popup.style.left = (rect.left + window.scrollX) + 'px';
      } else if (toolbarEl && toolbarEl.classList.contains('medium-editor-toolbar-active')) {
        const rect = toolbarEl.getBoundingClientRect();
        popup.style.top = (rect.bottom + window.scrollY + 10) + 'px';
        popup.style.left = (rect.left + window.scrollX) + 'px';
      } else {
        const rect = targetEl.getBoundingClientRect();
        popup.style.top = (rect.top + window.scrollY - 10) + 'px';
        popup.style.left = (rect.left + window.scrollX + 10) + 'px';
      }

      document.body.appendChild(popup);

      // Keep the popup inside the iframe viewport. The iframe body has
      // overflow:hidden, so a popup opened from a right-edge or bottom-edge field
      // (e.g. Salesperson) would be clipped and look broken. Clamp it back in.
      const _doc = popup.ownerDocument;
      const _vw = _doc.documentElement.clientWidth;
      const _vh = _doc.documentElement.clientHeight;
      const _rect = popup.getBoundingClientRect();
      if (_rect.right > _vw - 8) {
        popup.style.left = Math.max(8, (parseFloat(popup.style.left) || 0) - (_rect.right - (_vw - 8))) + 'px';
      }
      if (_rect.bottom > _vh - 8) {
        popup.style.top = Math.max(8, (parseFloat(popup.style.top) || 0) - (_rect.bottom - (_vh - 8))) + 'px';
      }

      popup.querySelector('.close-btn').addEventListener('click', () => popup.remove());

      const updateConfig = () => {
        targetEl.dataset.boxConfig = JSON.stringify(cfg);
        if (this.base.options.owner && this.base.options.owner.undoManager) {
          this.base.options.owner.undoManager.debouncedSave();
        }
      };

      popup.querySelector('#cy-set-visible').addEventListener('change', (e) => {
        if (!e.target.checked) {
          targetEl.classList.add('cy-block-hidden');
        } else {
          targetEl.classList.remove('cy-block-hidden');
        }
        if (this.base.options.owner) this.base.options.owner.undoManager.debouncedSave();
      });

      popup.querySelector('#cy-set-active').addEventListener('change', (e) => {
        if (!e.target.checked) {
          targetEl.setAttribute('t-if', 'False');
        } else {
          targetEl.removeAttribute('t-if');
        }
        if (this.base.options.owner) this.base.options.owner.undoManager.debouncedSave();
      });

      // popup.querySelector('#cy-set-lock').addEventListener('change', (e) => {
      //   cfg.locked = e.target.checked;
      //   updateConfig();
      // });

      const applyStyle = (id, prop, field) => {
        const el = popup.querySelector(id);
        if (!el) return;
        el.addEventListener('input', (e) => {
          let val = e.target.value;
          if (val && !isNaN(val) && field !== 'backgroundColor' && field !== 'color' && field !== 'border') val += 'px';
          targetEl.style[prop] = val;
          cfg.style[field] = val;
          updateConfig();
        });
      };

      applyStyle('#cy-set-w', 'width', 'width');
      applyStyle('#cy-set-h', 'height', 'height');
      applyStyle('#cy-set-p', 'padding', 'padding');
      applyStyle('#cy-set-m', 'margin', 'margin');
      applyStyle('#cy-set-bg', 'backgroundColor', 'backgroundColor');
      applyStyle('#cy-set-color', 'color', 'color');
      applyStyle('#cy-set-b', 'border', 'border');
      applyStyle('#cy-set-br', 'borderRadius', 'borderRadius');

      // popup.querySelector('#cy-set-pbb').addEventListener('change', (e) => {
      //   if (e.target.checked) targetEl.classList.add('page-break-before');
      //   else targetEl.classList.remove('page-break-before');
      //   if (this.base.options.owner) this.base.options.owner.undoManager.debouncedSave();
      // });
      // popup.querySelector('#cy-set-pba').addEventListener('change', (e) => {
      //   if (e.target.checked) targetEl.classList.add('page-break-after');
      //   else targetEl.classList.remove('page-break-after');
      //   if (this.base.options.owner) this.base.options.owner.undoManager.debouncedSave();
      // });
      popup.querySelector('#cy-set-cls').addEventListener('change', (e) => {
        const baseCls = ['cy-block-hidden'].filter(c => targetEl.classList.contains(c));
        targetEl.className = e.target.value + ' ' + baseCls.join(' ');
        if (this.base.options.owner) this.base.options.owner.undoManager.debouncedSave();
      });

      // Close when clicking outside
      setTimeout(() => {
        const clickOutside = (e) => {
          if (!popup.contains(e.target) && !e.target.closest('.medium-editor-action')) {
            popup.remove();
            document.removeEventListener('click', clickOutside);
          }
        };
        document.addEventListener('click', clickOutside);
      }, 0);
    }
  });

  // Global exposure for explicit instantiation
  window.SettingsButton = SettingsButton;
  window.DeleteButton = DeleteButton;
  window.UndoButton = UndoButton;
  window.RedoButton = RedoButton;

  MediumEditor.extensions.settingsButton = SettingsButton;
  MediumEditor.extensions.deleteElement = DeleteButton;
  MediumEditor.extensions.undoButton = UndoButton;
  MediumEditor.extensions.redoButton = RedoButton;
}

// Export for different module systems
if (typeof module !== 'undefined' && module.exports) {
  module.exports = UndoRedoManager;
}

if (typeof window !== 'undefined') {
  window.UndoRedoManager = UndoRedoManager;
}