// theme.js - Theme Manager for handling dark/light mode and color theme switching

document.addEventListener('DOMContentLoaded', () => {
    const themeManager = new ThemeManager();
    themeManager.initialize();
  });
  
  class ThemeManager {
    constructor() {
      this.THEME_KEY = 'user-theme-preference';
      this.COLOR_KEY = 'user-color-preference';
      this.DEFAULT_THEME = 'light';
      this.DEFAULT_COLOR = 'default';
  
      this.colorThemes = ['default', 'teal', 'blue', 'purple', 'coral', 'orange', 'gold'];
  
      this.themeSwitcher = null;
      this.colorToggle = null;
      this.colorSelector = null;
      this.colorSwatches = null;
    }
  
    initialize() {
      this.createControls();
      this.loadSavedPreferences();
      this.setupEventListeners();
  
      // Smooth transitions after load
      setTimeout(() => {
        document.documentElement.classList.add('theme-transition');
        document.body.classList.add('theme-transition');
      }, 100);
  
      // Listen for system theme changes
      const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
      mediaQuery.addEventListener('change', this.handleSystemThemeChange.bind(this));
      this.handleSystemThemeChange(mediaQuery);
    }
  
    createControls() {
      const controls = document.createElement('div');
      controls.className = 'theme-controls';
      document.body.appendChild(controls);
  
      this.themeSwitcher = document.createElement('button');
      this.themeSwitcher.className = 'theme-switcher';
      this.themeSwitcher.setAttribute('aria-label', 'Toggle dark mode');
      controls.appendChild(this.themeSwitcher);
  
      this.colorToggle = document.createElement('button');
      this.colorToggle.className = 'color-picker-toggle';
      this.colorToggle.setAttribute('aria-label', 'Toggle color picker');
      this.colorToggle.innerHTML = '<i class="fa-solid fa-palette"></i>';
      controls.appendChild(this.colorToggle);
  
      this.colorSelector = document.createElement('div');
      this.colorSelector.className = 'color-theme-selector';
      controls.appendChild(this.colorSelector);
  
      this.colorSwatches = document.createElement('div');
      this.colorSwatches.className = 'color-swatches';
      this.colorSelector.appendChild(this.colorSwatches);
  
      this.createColorSwatches();
    }
  
    createColorSwatches() {
      this.colorSwatches.innerHTML = '';
      this.colorThemes.forEach(color => {
        const swatch = document.createElement('button');
        swatch.className = `color-swatch ${color}`;
        swatch.setAttribute('data-color', color);
        swatch.setAttribute('aria-label', `${color} theme`);
        swatch.title = `${color.charAt(0).toUpperCase() + color.slice(1)} theme`;
        this.colorSwatches.appendChild(swatch);
      });
    }
  
    setupEventListeners() {
      this.themeSwitcher.addEventListener('click', () => this.toggleTheme());
      this.colorToggle.addEventListener('click', () => this.toggleColorSelector());
  
      this.colorSwatches.querySelectorAll('.color-swatch').forEach(swatch => {
        swatch.addEventListener('click', e => {
          const color = e.currentTarget.getAttribute('data-color');
          this.setColorTheme(color);
        });
      });
  
      document.addEventListener('click', e => {
        if (!e.target.closest('.color-theme-selector') && !e.target.closest('.color-picker-toggle')) {
          this.colorSelector.classList.remove('show');
        }
      });
    }
  
    loadSavedPreferences() {
      const savedTheme = localStorage.getItem(this.THEME_KEY) || this.DEFAULT_THEME;
      const savedColor = localStorage.getItem(this.COLOR_KEY) || this.DEFAULT_COLOR;
      this.setTheme(savedTheme);
      this.setColorTheme(savedColor);
      this.updateThemeSwitcherIcon();
    }
  
    toggleTheme() {
      const current = this.getCurrentTheme();
      const next = current === 'dark' ? 'light' : 'dark';
      this.setTheme(next);
    }
  
    setTheme(theme) {
      document.documentElement.setAttribute('data-theme', theme);
      localStorage.setItem(this.THEME_KEY, theme);
      this.updateThemeSwitcherIcon();
      document.dispatchEvent(new CustomEvent('themeChange', { detail: { theme } }));
    }
  
    updateThemeSwitcherIcon() {
      const isDark = this.getCurrentTheme() === 'dark';
      this.themeSwitcher.innerHTML = `<i class="fa-solid fa-${isDark ? 'sun' : 'moon'}"></i>`;
    }
  
    toggleColorSelector() {
      this.colorSelector.classList.toggle('show');
    }
  
    setColorTheme(color) {
      document.documentElement.setAttribute('data-color-theme', color);
      localStorage.setItem(this.COLOR_KEY, color);
      this.updateActiveColorSwatch(color);
      document.dispatchEvent(new CustomEvent('colorChange', { detail: { color } }));
    }
  
    updateActiveColorSwatch(activeColor) {
      this.colorSwatches.querySelectorAll('.color-swatch').forEach(swatch => {
        swatch.classList.toggle('active', swatch.getAttribute('data-color') === activeColor);
      });
    }
  
    handleSystemThemeChange(e) {
      const userPref = localStorage.getItem(this.THEME_KEY);
      if (!userPref) {
        const newTheme = e.matches ? 'dark' : 'light';
        this.setTheme(newTheme);
      }
    }
  
    getCurrentTheme() {
      return document.documentElement.getAttribute('data-theme') || this.DEFAULT_THEME;
    }
  
    getCurrentColor() {
      return document.documentElement.getAttribute('data-color-theme') || this.DEFAULT_COLOR;
    }
  }
  
  // Helper functions for external usage
  window.ThemeUtils = {
    toggleDarkMode: () => {
      document.querySelector('.theme-switcher')?.click();
    },
    setColorTheme: (color) => {
      const valid = ['default', 'teal', 'blue', 'purple', 'coral', 'orange', 'gold'];
      if (valid.includes(color)) {
        document.documentElement.setAttribute('data-color-theme', color);
        localStorage.setItem('user-color-preference', color);
  
        document.querySelectorAll('.color-swatch').forEach(swatch => {
          swatch.classList.toggle('active', swatch.getAttribute('data-color') === color);
        });
      }
    },
    getCurrentTheme: () => document.documentElement.getAttribute('data-theme') || 'light',
    getCurrentColor: () => document.documentElement.getAttribute('data-color-theme') || 'default',
  };
  