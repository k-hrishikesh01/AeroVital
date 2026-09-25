/**
 * AeroVital Dashboard - Main Application Controller
 * Pure Front-End Vanilla JS Architecture (No Node, No Server, No Build Tool Required)
 */

class AeroVitalApp {
  constructor() {
    this.state = JSON.parse(JSON.stringify(window.INITIAL_DATA || {}));
    window.AeroVitalState = this.state; // Expose for chart live updates

    this.timerInterval = null;
    this.ecg = null;
    this.charts = null;

    // Load any saved custom pilots from localStorage
    this.loadSavedPilots();

    // Initialize components
    this.initTimer();
    this.initECG();
    this.initCharts();
    this.bindEvents();
    this.renderActivePilot();
    this.renderPilotsList();
    this.renderAlerts();
    this.renderTelemetryLogs();
    this.initTheme();
  }

  // ----------------------------------------------------
  // Session Timer (Starts at 02:45:32 as in screenshot)
  // ----------------------------------------------------
  initTimer() {
    const timerEl = document.getElementById('sessionTimerDisplay');
    if (!timerEl) return;

    this.updateTimerDisplay();

    this.timerInterval = setInterval(() => {
      if (this.state.session && this.state.session.isRunning) {
        this.state.session.totalSeconds++;
        this.updateTimerDisplay();
      }
    }, 1000);
  }

  updateTimerDisplay() {
    const timerEl = document.getElementById('sessionTimerDisplay');
    if (!timerEl || !this.state.session) return;

    const total = this.state.session.totalSeconds;
    const hrs = Math.floor(total / 3600);
    const mins = Math.floor((total % 3600) / 60);
    const secs = total % 60;

    const pad = (n) => String(n).padStart(2, '0');
    timerEl.textContent = `${pad(hrs)}:${pad(mins)}:${pad(secs)}`;
  }

  toggleTimer() {
    if (!this.state.session) return;
    this.state.session.isRunning = !this.state.session.isRunning;
    const btn = document.getElementById('btnToggleTimer');
    if (btn) {
      btn.innerHTML = this.state.session.isRunning 
        ? '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="6" y="4" width="4" height="16"></rect><rect x="14" y="4" width="4" height="16"></rect></svg> Pause'
        : '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="5 3 19 12 5 21 5 3"></polygon></svg> Resume';
    }
  }

  resetTimer() {
    if (!this.state.session) return;
    // Reset to screenshot initial time: 02:45:32
    this.state.session.totalSeconds = 2 * 3600 + 45 * 60 + 32;
    this.state.session.isRunning = true;
    this.updateTimerDisplay();
    this.showToast('Session timer reset to 02:45:32');
  }

  // ----------------------------------------------------
  // ECG & Charts
  // ----------------------------------------------------
  initECG() {
    try {
      if (window.ECGMonitor) {
        this.ecg = new window.ECGMonitor('ecgCanvas');
        this.ecg.setBPM(this.state.vitals.heartRate, this.state.vitals.condition);
      }
    } catch (e) {
      console.warn('ECG initialization note:', e);
    }
  }

  initCharts() {
    try {
      if (window.DashboardCharts) {
        this.charts = new window.DashboardCharts();
      }
    } catch (e) {
      console.warn('Charts initialization note:', e);
    }
  }

  // ----------------------------------------------------
  // Theme Management (Light AeroVital vs Cockpit Dark HUD)
  // ----------------------------------------------------
  initTheme() {
    const savedTheme = localStorage.getItem('aerovital_theme');
    if (savedTheme === 'dark') {
      document.body.classList.add('dark-theme');
      this.updateThemeIcon(true);
    } else {
      document.body.classList.remove('dark-theme');
      this.updateThemeIcon(false);
    }
  }

  toggleTheme() {
    const isDark = document.body.classList.toggle('dark-theme');
    localStorage.setItem('aerovital_theme', isDark ? 'dark' : 'light');
    this.updateThemeIcon(isDark);
    if (this.charts) {
      this.charts.updateTheme();
    }
  }

  updateThemeIcon(isDark) {
    const btn = document.getElementById('themeToggleBtn');
    if (!btn) return;
    btn.innerHTML = isDark
      ? `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="5"></circle><line x1="12" y1="1" x2="12" y2="3"></line><line x1="12" y1="21" x2="12" y2="23"></line><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"></line><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"></line><line x1="1" y1="12" x2="3" y2="12"></line><line x1="21" y1="12" x2="23" y2="12"></line><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"></line><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"></line></svg>`
      : `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"></path></svg>`;
    btn.title = isDark ? 'Switch to Standard Light Mode' : 'Switch to Cockpit Night HUD Mode';
  }

  // ----------------------------------------------------
  // Simulation Controls (Demoing different flight states)
  // ----------------------------------------------------
  setSimulationMode(mode) {
    document.querySelectorAll('.sim-pill').forEach(p => p.classList.remove('active'));
    const btn = document.getElementById(`sim-${mode}`);
    if (btn) btn.classList.add('active');

    const card = document.getElementById('conditionCard');
    const conditionTitle = document.getElementById('conditionTitle');
    const conditionPill = document.getElementById('conditionPill');
    const conditionSubtext = document.getElementById('conditionSubtext');
    const sScoreVal = document.getElementById('sScoreVal');
    const hrVal = document.getElementById('heartRateVal');
    const hrVal2 = document.getElementById('heartRateVal2');
    const fatigueVal = document.getElementById('fatigueVal');

    if (mode === 'normal') {
      // Return precisely to screenshot state
      this.state.vitals.sScore = 78;
      this.state.vitals.conference = 50;
      this.state.vitals.condition = 'NORMAL';
      this.state.vitals.heartRate = 78;
      this.state.vitals.fatigueState = 'Low';
      this.state.vitals.lastEstimated = 'Last estimated 2 minutes ago';

      if (card) card.className = 'condition-card';
      if (conditionTitle) conditionTitle.textContent = 'NORMAL';
      if (conditionPill) {
        conditionPill.textContent = 'Stable';
        conditionPill.style.background = 'var(--color-normal-bg)';
        conditionPill.style.color = 'var(--color-normal)';
      }
      if (conditionSubtext) conditionSubtext.textContent = 'Last estimated 2 minutes ago';
      if (sScoreVal) sScoreVal.textContent = '78%';
      if (hrVal) hrVal.textContent = '78 BPM';
      if (hrVal2) hrVal2.textContent = '78';
      if (fatigueVal) fatigueVal.textContent = 'Low';

      if (this.ecg) this.ecg.setBPM(78, 'NORMAL');
      if (this.charts) this.charts.updateConditionState('NORMAL', 78, 78);
      this.showToast('Reset to Baseline: Normal Flight Condition (78 BPM, 78% S-Score)');

    } else if (mode === 'turbulence') {
      // Elevated stress due to clear-air turbulence
      this.state.vitals.sScore = 65;
      this.state.vitals.condition = 'WARNING';
      this.state.vitals.heartRate = 104;
      this.state.vitals.fatigueState = 'Moderate';
      this.state.vitals.lastEstimated = 'Last estimated just now';

      if (card) card.className = 'condition-card warning';
      if (conditionTitle) conditionTitle.textContent = 'ELEVATED STRESS';
      if (conditionPill) {
        conditionPill.textContent = 'Caution';
        conditionPill.style.background = 'var(--color-warning-bg)';
        conditionPill.style.color = 'var(--color-warning)';
      }
      if (conditionSubtext) conditionSubtext.textContent = 'Turbulence detected - HRV indicates sympathetic response';
      if (sScoreVal) sScoreVal.textContent = '65%';
      if (hrVal) hrVal.textContent = '104 BPM';
      if (hrVal2) hrVal2.textContent = '104';
      if (fatigueVal) fatigueVal.textContent = 'Moderate';

      if (this.ecg) this.ecg.setBPM(104, 'WARNING');
      if (this.charts) this.charts.updateConditionState('WARNING', 65, 104);
      this.showToast('Simulating: CAT Turbulence & Stress Spike (104 BPM)');

    } else if (mode === 'fatigue') {
      // Fatigue onset
      this.state.vitals.sScore = 52;
      this.state.vitals.condition = 'ALERT';
      this.state.vitals.heartRate = 61;
      this.state.vitals.fatigueState = 'High (PERCLOS 8.4%)';
      this.state.vitals.lastEstimated = 'Last estimated just now';

      if (card) card.className = 'condition-card alert';
      if (conditionTitle) conditionTitle.textContent = 'FATIGUE ALERT';
      if (conditionPill) {
        conditionPill.textContent = 'Relief Required';
        conditionPill.style.background = 'var(--color-alert-bg)';
        conditionPill.style.color = 'var(--color-alert)';
      }
      if (conditionSubtext) conditionSubtext.textContent = 'Prolonged micro-fixations detected. Recommend relief swap.';
      if (sScoreVal) sScoreVal.textContent = '52%';
      if (hrVal) hrVal.textContent = '61 BPM';
      if (hrVal2) hrVal2.textContent = '61';
      if (fatigueVal) fatigueVal.textContent = 'High';

      if (this.ecg) this.ecg.setBPM(61, 'ALERT');
      if (this.charts) this.charts.updateConditionState('FATIGUE', 52, 61);
      this.showToast('Simulating: Pilot Fatigue Advisory - Alert triggered');
    }
  }

  // ----------------------------------------------------
  // Pilot Profile & Account Management (Matching Image 2)
  // ----------------------------------------------------
  loadSavedPilots() {
    try {
      const saved = localStorage.getItem('aerovital_pilots');
      if (saved) {
        const parsed = JSON.parse(saved);
        if (Array.isArray(parsed) && parsed.length > 0) {
          this.state.pilotsList = parsed;
        }
      }
    } catch (e) {
      console.warn('Error reading saved pilots', e);
    }
  }

  savePilotsToStorage() {
    try {
      localStorage.setItem('aerovital_pilots', JSON.stringify(this.state.pilotsList));
    } catch (e) {
      console.warn('Error saving pilots', e);
    }
  }

  renderActivePilot() {
    const p = this.state.activePilot;
    if (!p) return;
    const nameEl = document.getElementById('activePilotName');
    const roleEl = document.getElementById('activePilotRole');
    const avatarEl = document.getElementById('activePilotAvatar');

    if (nameEl) nameEl.textContent = p.name;
    if (roleEl) roleEl.textContent = `${p.role} • ${p.id}`;
    if (avatarEl) avatarEl.textContent = p.avatar || p.name.substring(0, 2).toUpperCase();
  }

  renderPilotsList() {
    const listEl = document.getElementById('pilotsListContainer');
    if (!listEl || !this.state.pilotsList) return;

    listEl.innerHTML = this.state.pilotsList.map((pilot) => {
      const isSelected = pilot.id === this.state.activePilot.id;
      return `
        <div class="pilot-selection-card ${isSelected ? 'selected' : ''}" data-pilot-id="${pilot.id}">
          <div class="pilot-info-left">
            <div class="pilot-avatar-lg">${pilot.avatar || pilot.name.substring(0, 2).toUpperCase()}</div>
            <div>
              <div style="font-weight: 700; font-size: 14px; color: var(--text-primary);">${pilot.name}</div>
              <div style="font-size: 12px; color: var(--text-secondary);">${pilot.role} • ${pilot.id}</div>
              <div style="font-size: 11px; color: var(--text-muted); margin-top: 2px;">Rating: ${pilot.aircraftRating || 'B787-9'}</div>
            </div>
          </div>
          ${isSelected ? `<span style="color: var(--color-normal);"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"></polyline></svg></span>` : ''}
        </div>
      `;
    }).join('');

    // Bind click to switch pilot
    listEl.querySelectorAll('.pilot-selection-card').forEach(card => {
      card.addEventListener('click', () => {
        const id = card.getAttribute('data-pilot-id');
        this.selectPilot(id);
      });
    });
  }

  selectPilot(id) {
    const pilot = this.state.pilotsList.find(p => p.id === id);
    if (!pilot) return;

    this.state.activePilot = pilot;
    this.renderActivePilot();
    this.renderPilotsList();
    this.closeAllDrawers();
    this.showToast(`Switched active profile to ${pilot.name} (${pilot.id})`);
  }

  handleCreatePilotAccount(event) {
    event.preventDefault();
    const nameInput = document.getElementById('inputPilotName');
    const idInput = document.getElementById('inputPilotId');
    const passInput = document.getElementById('inputPassword');

    const name = nameInput ? nameInput.value.trim() : '';
    const id = idInput ? idInput.value.trim().toUpperCase() : '';
    const pass = passInput ? passInput.value : '';

    if (!name || !id || !pass) {
      alert('Please fill out all required fields (Pilot Name, Pilot ID, and Password).');
      return;
    }

    // Generate avatar initials
    const parts = name.replace(/^(Capt\.|F\/O|Captain)\s+/i, '').trim().split(' ');
    const avatar = parts.length > 1 
      ? (parts[0][0] + parts[1][0]).toUpperCase() 
      : name.substring(0, 2).toUpperCase();

    const newPilot = {
      name: name.startsWith('Capt.') || name.startsWith('F/O') ? name : `Capt. ${name}`,
      id: id.startsWith('AV-') ? id : `AV-${id}`,
      role: 'Captain / PIC',
      aircraftRating: 'B787-9 Dreamliner',
      flightHours: '4,200 hrs',
      avatar: avatar
    };

    // Add to list if not already existing
    const existingIndex = this.state.pilotsList.findIndex(p => p.id === newPilot.id);
    if (existingIndex >= 0) {
      this.state.pilotsList[existingIndex] = newPilot;
    } else {
      this.state.pilotsList.unshift(newPilot);
    }

    this.state.activePilot = newPilot;
    this.savePilotsToStorage();
    this.renderActivePilot();
    this.renderPilotsList();

    // Reset form
    if (nameInput) nameInput.value = '';
    if (idInput) idInput.value = '';
    if (passInput) passInput.value = '';

    this.closeModal('pilotAccountModal');
    this.showToast(`Pilot Account Created: ${newPilot.name} (${newPilot.id})`);
  }

  // ----------------------------------------------------
  // Modals & Drawers
  // ----------------------------------------------------
  openModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) modal.classList.add('active');
  }

  closeModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) modal.classList.remove('active');
  }

  openDrawer(drawerId) {
    const drawer = document.getElementById(drawerId);
    if (drawer) drawer.classList.add('active');
  }

  closeDrawer(drawerId) {
    const drawer = document.getElementById(drawerId);
    if (drawer) drawer.classList.remove('active');
  }

  closeAllDrawers() {
    document.querySelectorAll('.drawer-backdrop').forEach(d => d.classList.remove('active'));
    document.querySelectorAll('.modal-backdrop').forEach(m => m.classList.remove('active'));
  }

  // ----------------------------------------------------
  // Alerts & Telemetry Logs
  // ----------------------------------------------------
  renderAlerts() {
    const container = document.getElementById('alertsContainer');
    if (!container || !this.state.alerts) return;

    container.innerHTML = this.state.alerts.map(a => `
      <div class="alert-card-item ${a.type === 'success' ? 'alert-success' : (a.type === 'notice' ? 'alert-warning' : '')}">
        <div class="alert-top">
          <span>${a.title}</span>
          <span>${a.time}</span>
        </div>
        <div class="alert-desc">${a.desc}</div>
      </div>
    `).join('');
  }

  renderTelemetryLogs() {
    const tbody = document.getElementById('telemetryTableBody');
    if (!tbody || !this.state.historicalLogs) return;

    tbody.innerHTML = this.state.historicalLogs.map(log => `
      <tr>
        <td style="font-weight: 600;">${log.time}</td>
        <td>${log.phase}</td>
        <td><strong style="color: var(--primary-navy);">${log.hr} BPM</strong></td>
        <td><span style="font-weight: 700; color: var(--color-normal);">${log.sScore}%</span></td>
        <td>${log.fatigue}</td>
        <td><span class="live-badge" style="font-size: 10px; padding: 2px 8px;">● ${log.status}</span></td>
      </tr>
    `).join('');
  }

  exportTelemetryCSV() {
    const headers = ['Time', 'Phase', 'HeartRate_BPM', 'SScore_Percent', 'FatigueState', 'Status'];
    const rows = this.state.historicalLogs.map(l => [l.time, `"${l.phase}"`, l.hr, l.sScore, l.fatigue, l.status].join(','));
    const csvContent = 'data:text/csv;charset=utf-8,' + [headers.join(','), ...rows].join('\n');
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement('a');
    link.setAttribute('href', encodedUri);
    link.setAttribute('download', `AeroVital_Session_${this.state.session.flightNo}_${new Date().toISOString().split('T')[0]}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    this.showToast('Biometric Telemetry CSV Exported successfully.');
  }

  // ----------------------------------------------------
  // Mobile Frame View Toggle
  // ----------------------------------------------------
  toggleMobileView() {
    const isMobileMode = document.body.classList.toggle('mobile-view-mode');
    const btn = document.getElementById('btnToggleMobileView');
    if (btn) {
      btn.innerHTML = isMobileMode
        ? `<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="3" width="20" height="14" rx="2" ry="2"></rect><line x1="8" y1="21" x2="16" y2="21"></line><line x1="12" y1="17" x2="12" y2="21"></line></svg> Desktop View`
        : `<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="5" y="2" width="14" height="20" rx="2" ry="2"></rect><line x1="12" y1="18" x2="12.01" y2="18"></line></svg> Mobile View`;
    }
    // Resize charts and ecg canvas
    setTimeout(() => {
      if (this.ecg) this.ecg.resize();
      if (this.charts) {
        if (this.charts.timelineChart) this.charts.timelineChart.resize();
        if (this.charts.streamChart) this.charts.streamChart.resize();
        if (this.charts.radarChart) this.charts.radarChart.resize();
        if (this.charts.circadianChart) this.charts.circadianChart.resize();
      }
    }, 200);
  }

  // ----------------------------------------------------
  // Toast notifications
  // ----------------------------------------------------
  showToast(message) {
    const container = document.getElementById('toastContainer');
    if (!container) return;

    const toast = document.createElement('div');
    toast.className = 'toast';
    toast.innerHTML = `
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"></polyline></svg>
      <span>${message}</span>
    `;
    container.appendChild(toast);

    setTimeout(() => {
      toast.style.opacity = '0';
      toast.style.transition = 'opacity 0.3s ease';
      setTimeout(() => toast.remove(), 300);
    }, 3200);
  }

  // ----------------------------------------------------
  // Event Listeners Binding
  // ----------------------------------------------------
  bindEvents() {
    // Theme toggle
    document.getElementById('themeToggleBtn')?.addEventListener('click', () => this.toggleTheme());

    // Mobile Preview View toggle
    document.getElementById('btnToggleMobileView')?.addEventListener('click', () => this.toggleMobileView());

    // Session Timer Controls
    document.getElementById('btnToggleTimer')?.addEventListener('click', () => this.toggleTimer());
    document.getElementById('btnResetTimer')?.addEventListener('click', () => this.resetTimer());

    // Simulation pills
    document.getElementById('sim-normal')?.addEventListener('click', () => this.setSimulationMode('normal'));
    document.getElementById('sim-turbulence')?.addEventListener('click', () => this.setSimulationMode('turbulence'));
    document.getElementById('sim-fatigue')?.addEventListener('click', () => this.setSimulationMode('fatigue'));

    // Open Pilot Modal / Switcher
    document.getElementById('headerPilotBtn')?.addEventListener('click', () => this.openDrawer('pilotsDrawer'));
    document.getElementById('btnOpenCreatePilot')?.addEventListener('click', () => {
      this.closeDrawer('pilotsDrawer');
      this.openModal('pilotAccountModal');
    });
    document.getElementById('btnOpenCreatePilotFromHeader')?.addEventListener('click', () => this.openModal('pilotAccountModal'));

    // Notifications Drawer
    document.getElementById('notificationsBtn')?.addEventListener('click', () => this.openDrawer('notificationsDrawer'));

    // Mobile Hamburger button (shows navigation drawer)
    document.getElementById('btnHamburger')?.addEventListener('click', () => this.openDrawer('navDrawer'));

    // Git instructions modal
    document.getElementById('btnOpenGitModal')?.addEventListener('click', () => this.openModal('gitModal'));

    // Export CSV
    document.getElementById('btnExportCSV')?.addEventListener('click', () => this.exportTelemetryCSV());

    // Form submission for Create Pilot Account (Image 2)
    document.getElementById('pilotAccountForm')?.addEventListener('submit', (e) => this.handleCreatePilotAccount(e));

    // "Back to Login" link inside Create Pilot Account modal
    document.getElementById('linkBackToLogin')?.addEventListener('click', (e) => {
      e.preventDefault();
      this.closeModal('pilotAccountModal');
      this.openDrawer('pilotsDrawer');
    });

    // Close buttons for modals
    document.querySelectorAll('[data-close-modal]').forEach(btn => {
      btn.addEventListener('click', () => {
        const id = btn.getAttribute('data-close-modal');
        this.closeModal(id);
      });
    });

    // Close buttons for drawers
    document.querySelectorAll('[data-close-drawer]').forEach(btn => {
      btn.addEventListener('click', () => {
        const id = btn.getAttribute('data-close-drawer');
        this.closeDrawer(id);
      });
    });

    // Backdrop clicks to close
    document.querySelectorAll('.modal-backdrop').forEach(backdrop => {
      backdrop.addEventListener('click', (e) => {
        if (e.target === backdrop) backdrop.classList.remove('active');
      });
    });
    document.querySelectorAll('.drawer-backdrop').forEach(backdrop => {
      backdrop.addEventListener('click', (e) => {
        if (e.target === backdrop) backdrop.classList.remove('active');
      });
    });

    // Timeline Chart filter pills (30m, 1h, Full)
    document.querySelectorAll('.filter-btn[data-range]').forEach(btn => {
      btn.addEventListener('click', () => {
        document.querySelectorAll('.filter-btn[data-range]').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        const range = btn.getAttribute('data-range');
        if (this.charts) this.charts.updateFilterRange(range);
      });
    });
  }
}

// Instantiate on DOMContentLoaded
document.addEventListener('DOMContentLoaded', () => {
  window.AeroVitalAppInstance = new AeroVitalApp();
});
