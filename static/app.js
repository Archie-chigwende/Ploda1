(() => {
  'use strict';

  const app = document.getElementById('app');
  const toastRegion = document.getElementById('toast-region');
  const state = {
    user: null,
    csrf: '',
    paymentMethods: null,
    bank: null,
    chatTimer: null,
  };

  const provinces = [
    'Bulawayo', 'Harare', 'Manicaland', 'Mashonaland Central', 'Mashonaland East',
    'Mashonaland West', 'Masvingo', 'Matabeleland North', 'Matabeleland South', 'Midlands'
  ];

  const pageMeta = {
    '/dashboard': ['Dashboard', 'Your membership and financial overview'],
    '/projects': ['Projects', 'PLODA programmes and development opportunities'],
    '/payments': ['My payments', 'Your complete payment history'],
    '/deposit': ['Deposit funds', 'Use verified PLODA payment channels'],
    '/statements': ['Statements', 'Review and export your financial activity'],
    '/documents': ['Documents', 'Official forms and member resources'],
    '/news': ['News & updates', 'Latest notices from PLODA'],
    '/support': ['Support chat', 'Secure assistance from the PLODA team'],
    '/profile': ['Profile', 'Manage your personal and contact information'],
    '/constitution': ['Constitution', 'Our mandate, structure and governing principles'],
    '/member-registration': ['Member registration', 'Complete your formal member information'],
  };

  const navGroups = [
    {
      label: 'Overview',
      items: [
        ['/dashboard', 'DB', 'Dashboard'],
        ['/projects', 'PR', 'Projects'],
        ['/news', 'NW', 'News & updates'],
      ],
    },
    {
      label: 'Finance',
      items: [
        ['/payments', 'PY', 'My payments'],
        ['/deposit', 'DP', 'Deposit funds'],
        ['/statements', 'ST', 'Statements'],
      ],
    },
    {
      label: 'Membership',
      items: [
        ['/documents', 'DC', 'Documents'],
        ['/constitution', 'CN', 'Constitution'],
        ['/member-registration', 'MR', 'Member registration'],
        ['/support', 'CH', 'Support chat'],
        ['/profile', 'PF', 'Profile'],
      ],
    },
  ];

  const escapeHTML = (value) => String(value ?? '').replace(/[&<>'"]/g, (character) => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;'
  })[character]);

  const initials = (name) => String(name || 'PLODA Member')
    .split(/\s+/).filter(Boolean).slice(0, 2).map((part) => part[0]).join('').toUpperCase();

  const formatDate = (value) => {
    if (!value) return '—';
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return escapeHTML(value);
    return new Intl.DateTimeFormat('en-ZW', { day: '2-digit', month: 'short', year: 'numeric' }).format(date);
  };

  const formatDateTime = (value) => {
    if (!value) return '—';
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return escapeHTML(value);
    return new Intl.DateTimeFormat('en-ZW', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' }).format(date);
  };

  const formatMoney = (amount, currency = 'USD') => {
    const value = Number(amount || 0);
    if (currency === 'USD') {
      return new Intl.NumberFormat('en-ZW', { style: 'currency', currency: 'USD' }).format(value);
    }
    return `${escapeHTML(currency)} ${new Intl.NumberFormat('en-ZW', { minimumFractionDigits: 2 }).format(value)}`;
  };

  const statusBadge = (status) => {
    const value = String(status || 'Pending');
    const normalized = value.toLowerCase();
    let style = 'neutral';
    if (normalized.includes('complete') || normalized.includes('verified') || normalized.includes('success')) style = 'success';
    else if (normalized.includes('fail') || normalized.includes('declin') || normalized.includes('error')) style = 'danger';
    else if (normalized.includes('initiat') || normalized.includes('review') || normalized.includes('approval')) style = 'info';
    else if (normalized.includes('pending') || normalized.includes('awaiting') || normalized.includes('submitted')) style = 'warning';
    return `<span class="badge badge-${style}">${escapeHTML(value)}</span>`;
  };

  const brand = (inverse = false) => `
    <span class="brand ${inverse ? 'brand-inverse' : ''}">
      <span class="brand-seal" aria-hidden="true"><span>PL</span></span>
      <span class="brand-name"><strong>PLODA</strong><small>Land • Development • Prosperity</small></span>
    </span>`;

  function toast(message, type = 'success', title = '') {
    const item = document.createElement('div');
    item.className = `toast ${type === 'error' ? 'toast-error' : ''}`;
    item.innerHTML = `
      <div><strong>${escapeHTML(title || (type === 'error' ? 'Please check' : 'Done'))}</strong><span>${escapeHTML(message)}</span></div>
      <button type="button" aria-label="Dismiss notification">×</button>`;
    item.querySelector('button').addEventListener('click', () => item.remove());
    toastRegion.appendChild(item);
    setTimeout(() => item.remove(), 6200);
  }

  async function api(path, options = {}) {
    const request = { method: 'GET', credentials: 'same-origin', ...options };
    request.headers = { Accept: 'application/json', ...(options.headers || {}) };
    if (request.body && typeof request.body !== 'string') {
      request.headers['Content-Type'] = 'application/json';
      request.body = JSON.stringify(request.body);
    }
    if (request.method !== 'GET' && state.csrf) request.headers['X-CSRF-Token'] = state.csrf;
    const response = await fetch(path, request);
    let data = {};
    try { data = await response.json(); } catch (_) { data = { error: 'The server returned an unexpected response.' }; }
    if (!response.ok) {
      const error = new Error(data.error || 'The request could not be completed.');
      error.status = response.status;
      throw error;
    }
    return data;
  }

  const provinceOptions = (selected = '') => `
    <option value="">Select province</option>
    ${provinces.map((province) => `<option value="${escapeHTML(province)}" ${province === selected ? 'selected' : ''}>${escapeHTML(province)}</option>`).join('')}`;

  function publicHeader() {
    return `
      <header class="public-header">
        <div class="container public-nav">
          <a href="/" aria-label="PLODA home">${brand(true)}</a>
          <button class="public-menu-toggle" id="public-menu-toggle" type="button" aria-expanded="false" aria-controls="public-links" aria-label="Open navigation"><span></span></button>
          <nav class="public-links" id="public-links" aria-label="Public navigation">
            <a href="#about">About</a>
            <a href="#portal">Member portal</a>
            <a href="#security">Security</a>
            <a href="/signin">Sign in</a>
            <a class="button button-gold button-sm" href="/create-account">Create account</a>
          </nav>
        </div>
      </header>`;
  }

  function publicFooter() {
    return `
      <footer class="public-footer">
        <div class="container">
          <div class="public-footer-main">
            ${brand(true)}
            <nav class="footer-links" aria-label="Footer navigation">
              <a href="/signin">Member sign in</a>
              <a href="/create-account">Create account</a>
              <a href="mailto:info@ploda.org">Contact</a>
              <a href="/privacy">Privacy</a>
            </nav>
          </div>
          <div class="public-footer-bottom"><span>© ${new Date().getFullYear()} PLODA. All rights reserved.</span><span>23 Richwell Avenue, Meyrick Park, Mabelreign, Harare, Zimbabwe</span></div>
        </div>
      </footer>`;
  }

  function renderLanding() {
    document.title = 'PLODA | Land, Development & Prosperity';
    app.innerHTML = `
      ${publicHeader()}
      <section class="landing-hero">
        <div class="container landing-grid">
          <div class="landing-copy">
            <p class="eyebrow eyebrow-light">People's Land Ownership & Development Association</p>
            <h1>Ownership that builds <em>lasting prosperity.</em></h1>
            <p>PLODA brings membership, land-development projects, payments, statements and official resources together in one secure digital community.</p>
            <div class="landing-actions">
              <a class="button button-gold" href="/create-account">Create member account <span aria-hidden="true">→</span></a>
              <a class="button" style="color:#fff;border-color:rgba(255,255,255,.26)" href="/signin">Sign in to portal</a>
            </div>
            <div class="landing-proof"><span>Secure member access</span><span>Verified payment channels</span><span>Responsive support</span></div>
          </div>
          <div class="portal-preview" id="portal" aria-label="PLODA portal preview">
            <div class="preview-top"><span class="preview-label">Member portal</span><span class="preview-chip">Secure access</span></div>
            <div class="preview-welcome"><small>Welcome to your member space</small><h2>Everything in one place.</h2></div>
            <div class="preview-balance"><span>Member contributions</span><strong>Clear. Traceable. Secure.</strong></div>
            <div class="preview-grid">
              <div class="preview-tile"><b>Projects</b><span>Track PLODA development initiatives</span></div>
              <div class="preview-tile"><b>Payments</b><span>Use approved payment methods</span></div>
              <div class="preview-tile"><b>Documents</b><span>Access forms and resources</span></div>
              <div class="preview-tile"><b>Support</b><span>Message the PLODA team</span></div>
            </div>
          </div>
        </div>
      </section>

      <section class="landing-section" id="about">
        <div class="container">
          <div class="section-head">
            <div><p class="eyebrow">A people-centred platform</p><h2 class="section-title">Land access connected to responsible development.</h2></div>
            <p class="section-intro">PLODA advances inclusive ownership, agro-residential development, food security, enterprise, empowerment, social protection and balanced regional growth.</p>
          </div>
          <div class="feature-grid">
            <article class="feature-card feature-dark"><span class="feature-number">01</span><h3>Inclusive ownership</h3><p>Structured pathways that support eligible members in pursuing secure access to land.</p></article>
            <article class="feature-card"><span class="feature-number">02</span><h3>Productive communities</h3><p>Development that combines dignified living with agriculture, livestock and household resilience.</p></article>
            <article class="feature-card"><span class="feature-number">03</span><h3>Member empowerment</h3><p>Skills, enterprise and job-creation opportunities that strengthen local participation.</p></article>
          </div>
        </div>
      </section>

      <section class="landing-section landing-section-alt">
        <div class="container">
          <div class="section-head">
            <div><p class="eyebrow">The member experience</p><h2 class="section-title">Designed around transparency and participation.</h2></div>
            <p class="section-intro">The portal follows a familiar group-purchase member journey while keeping PLODA's identity, governance and member needs at the centre.</p>
          </div>
          <div class="feature-grid">
            <article class="feature-card"><span class="feature-number">A</span><h3>Track activity</h3><p>Review projects, deposits, payment history and downloadable statements from your dashboard.</p></article>
            <article class="feature-card feature-dark"><span class="feature-number">B</span><h3>Stay informed</h3><p>Receive official news, constitutional guidance, documents and programme updates.</p></article>
            <article class="feature-card"><span class="feature-number">C</span><h3>Get support</h3><p>Use secure support chat and keep your membership registration details current.</p></article>
          </div>
        </div>
      </section>

      <section class="security-band" id="security">
        <div class="container security-grid">
          <h2>Security built into every member journey.</h2>
          <div class="security-items">
            <div class="security-item"><strong>Protected accounts</strong><span>Strong password policy and secure server-side sessions.</span></div>
            <div class="security-item"><strong>Safer payments</strong><span>No card details are stored by the PLODA portal.</span></div>
            <div class="security-item"><strong>Private records</strong><span>Member information is separated by authenticated account.</span></div>
          </div>
        </div>
      </section>
      ${publicFooter()}`;
    setupPublicMenu();
  }

  function setupPublicMenu() {
    const button = document.getElementById('public-menu-toggle');
    const links = document.getElementById('public-links');
    if (!button || !links) return;
    button.addEventListener('click', () => {
      const open = button.getAttribute('aria-expanded') === 'true';
      button.setAttribute('aria-expanded', String(!open));
      links.classList.toggle('open', !open);
    });
  }

  function authAside(title, emphasis, copy) {
    return `
      <aside class="auth-aside">
        <a href="/" aria-label="PLODA home">${brand(true)}</a>
        <div class="auth-aside-copy"><p class="eyebrow eyebrow-light">PLODA member portal</p><h1>${title}<br><em>${emphasis}</em></h1><p>${copy}</p></div>
        <div class="auth-assurances"><span>Encrypted sessions</span><span>Protected records</span><span>Verified channels</span></div>
      </aside>`;
  }

  function renderSignIn() {
    document.title = 'Sign in | PLODA Member Portal';
    app.innerHTML = `
      <div class="auth-layout">
        ${authAside('Welcome', 'back.', 'Access your PLODA projects, payments, statements, documents and member support from one secure portal.')}
        <section class="auth-main">
          <div class="auth-card">
            <a class="back-home" href="/">← Return to PLODA</a>
            <p class="eyebrow">Member access</p>
            <h2>Sign in to your account</h2>
            <p>Use the email address and password registered with PLODA.</p>
            <form id="signin-form" class="form-stack" novalidate>
              <div class="field"><label for="signin-email">Email address</label><input id="signin-email" name="email" type="email" autocomplete="email" placeholder="name@example.com" required></div>
              <div class="field"><label for="signin-password">Password</label><div class="input-wrap"><input id="signin-password" name="password" type="password" autocomplete="current-password" required><button class="input-action" type="button" data-toggle-password="signin-password">Show</button></div></div>
              <p class="inline-error" id="signin-error" role="alert"></p>
              <button class="button button-primary button-block" type="submit">Sign in securely <span aria-hidden="true">→</span></button>
            </form>
            <p class="auth-switch">Do not have an account? <a class="text-link" href="/create-account">Create one here</a></p>
          </div>
        </section>
      </div>`;
    setupPasswordToggles();
    document.getElementById('signin-form').addEventListener('submit', handleSignIn);
  }

  function renderCreateAccount() {
    document.title = 'Create account | PLODA Member Portal';
    app.innerHTML = `
      <div class="auth-layout">
        ${authAside('Begin your', 'member journey.', 'Create your secure portal account, complete formal member registration and connect with PLODA programmes and support.')}
        <section class="auth-main">
          <div class="auth-card">
            <a class="back-home" href="/">← Return to PLODA</a>
            <p class="eyebrow">New member account</p>
            <h2>Create your portal account</h2>
            <p>Your account gives you secure access to the complete membership portal.</p>
            <form id="register-form" class="form-stack" novalidate>
              <div class="form-grid">
                <div class="field field-full"><label for="register-name">Full name</label><input id="register-name" name="fullName" autocomplete="name" required></div>
                <div class="field"><label for="register-email">Email address</label><input id="register-email" name="email" type="email" autocomplete="email" required></div>
                <div class="field"><label for="register-phone">Phone number</label><input id="register-phone" name="phone" type="tel" autocomplete="tel" placeholder="+263..." required></div>
                <div class="field field-full"><label for="register-province">Province</label><select id="register-province" name="province" required>${provinceOptions()}</select></div>
                <div class="field field-full"><label for="register-password">Create password</label><div class="input-wrap"><input id="register-password" name="password" type="password" autocomplete="new-password" minlength="10" required><button class="input-action" type="button" data-toggle-password="register-password">Show</button></div><div class="password-meter" id="password-meter" data-strength="0"><span></span><span></span><span></span><span></span></div><p class="field-hint">At least 10 characters with uppercase, lowercase, one number and one special character.</p></div>
                <div class="field field-full"><label for="confirm-password">Confirm password</label><div class="input-wrap"><input id="confirm-password" name="confirmPassword" type="password" autocomplete="new-password" required><button class="input-action" type="button" data-toggle-password="confirm-password">Show</button></div></div>
              </div>
              <label class="checkbox-field"><input name="acceptedTerms" type="checkbox" required><span>I agree to the PLODA portal terms, privacy notice and responsible use of official payment channels.</span></label>
              <p class="inline-error" id="register-error" role="alert"></p>
              <button class="button button-primary button-block" type="submit">Create secure account <span aria-hidden="true">→</span></button>
            </form>
            <p class="auth-switch">Already registered? <a class="text-link" href="/signin">Sign in here</a></p>
          </div>
        </section>
      </div>`;
    setupPasswordToggles();
    document.getElementById('register-password').addEventListener('input', updatePasswordMeter);
    document.getElementById('register-form').addEventListener('submit', handleRegister);
  }

  function setupPasswordToggles() {
    document.querySelectorAll('[data-toggle-password]').forEach((button) => {
      button.addEventListener('click', () => {
        const input = document.getElementById(button.dataset.togglePassword);
        const show = input.type === 'password';
        input.type = show ? 'text' : 'password';
        button.textContent = show ? 'Hide' : 'Show';
      });
    });
  }

  function passwordStrength(value) {
    let score = 0;
    if (value.length >= 10) score += 1;
    if (/[a-z]/.test(value) && /[A-Z]/.test(value)) score += 1;
    if (/\d/.test(value)) score += 1;
    if (/[^A-Za-z0-9]/.test(value)) score += 1;
    return score;
  }

  function updatePasswordMeter(event) {
    document.getElementById('password-meter').dataset.strength = String(passwordStrength(event.target.value));
  }

  async function handleSignIn(event) {
    event.preventDefault();
    const form = event.currentTarget;
    const error = document.getElementById('signin-error');
    error.textContent = '';
    if (!form.checkValidity()) { form.reportValidity(); return; }
    const button = form.querySelector('button[type="submit"]');
    button.disabled = true;
    button.textContent = 'Signing in…';
    try {
      const data = await api('/api/login', { method: 'POST', body: { email: form.email.value, password: form.password.value } });
      state.user = data.user;
      state.csrf = data.csrfToken;
      const next = new URLSearchParams(location.search).get('next');
      location.href = next && next.startsWith('/') ? next : '/dashboard';
    } catch (reason) {
      error.textContent = reason.message;
      button.disabled = false;
      button.innerHTML = 'Sign in securely <span aria-hidden="true">→</span>';
    }
  }

  async function handleRegister(event) {
    event.preventDefault();
    const form = event.currentTarget;
    const error = document.getElementById('register-error');
    error.textContent = '';
    if (!form.checkValidity()) { form.reportValidity(); return; }
    if (passwordStrength(form.password.value) < 4) { error.textContent = 'Your password does not meet all security requirements.'; return; }
    if (form.password.value !== form.confirmPassword.value) { error.textContent = 'The password confirmation does not match.'; return; }
    const button = form.querySelector('button[type="submit"]');
    button.disabled = true;
    button.textContent = 'Creating account…';
    try {
      const data = await api('/api/register', {
        method: 'POST',
        body: {
          fullName: form.fullName.value,
          email: form.email.value,
          phone: form.phone.value,
          province: form.province.value,
          password: form.password.value,
          acceptedTerms: form.acceptedTerms.checked,
        },
      });
      state.user = data.user;
      state.csrf = data.csrfToken;
      location.href = '/member-registration';
    } catch (reason) {
      error.textContent = reason.message;
      button.disabled = false;
      button.innerHTML = 'Create secure account <span aria-hidden="true">→</span>';
    }
  }

  function renderInfoPage(type) {
    const privacy = type === 'privacy';
    document.title = `${privacy ? 'Privacy' : 'Terms'} | PLODA`;
    app.innerHTML = `
      ${publicHeader()}
      <section class="landing-hero" style="min-height:500px;padding-bottom:70px">
        <div class="container landing-copy" style="position:relative;z-index:2;max-width:850px">
          <p class="eyebrow eyebrow-light">PLODA member portal</p>
          <h1 style="font-size:clamp(3rem,7vw,5.5rem)">${privacy ? 'Privacy notice.' : 'Portal terms.'}</h1>
          <p>${privacy ? 'PLODA protects member information and uses it only for legitimate membership, project, payment and support administration.' : 'Members must provide accurate information, protect their account credentials and use only verified PLODA payment channels.'}</p>
        </div>
      </section>
      <section class="landing-section"><div class="container" style="max-width:850px">
        <p class="eyebrow">Plain-language summary</p>
        <h2 class="section-title">${privacy ? 'How member information is handled.' : 'Responsible use of the portal.'}</h2>
        <div class="panel panel-pad" style="margin-top:30px">
          ${privacy ? `<p>Information entered in the portal is used to create and manage your membership account, support verification, maintain transaction records and respond to enquiries. Access is limited to authorised administration. Payment-card details are processed only by configured hosted payment providers and are not stored by this portal.</p><p>For privacy enquiries, contact <a class="text-link" href="mailto:info@ploda.org">info@ploda.org</a>.</p>` : `<p>Do not share your password or allow another person to transact through your account. Confirm payment instructions inside the authenticated portal and retain all references and receipts. Membership and project participation remain subject to PLODA's approved constitution, policies and verification requirements.</p><p>Unauthorised access, false registrations and misuse of payment channels may result in account suspension and further action.</p>`}
        </div>
      </div></section>
      ${publicFooter()}`;
    setupPublicMenu();
  }

  function sidebarMarkup(path) {
    const links = navGroups.map((group) => `
      <p class="nav-section">${escapeHTML(group.label)}</p>
      ${group.items.map(([href, icon, label]) => `<a class="side-link ${href === path ? 'active' : ''}" href="${href}"><span class="nav-icon" aria-hidden="true">${icon}</span><span>${escapeHTML(label)}</span></a>`).join('')}`
    ).join('');
    return `
      <aside class="sidebar" id="sidebar">
        <a class="sidebar-brand" href="/dashboard">${brand(true)}</a>
        <nav class="sidebar-nav" aria-label="Member navigation">${links}</nav>
        <div class="sidebar-foot">
          <div class="member-mini"><span class="member-avatar">${escapeHTML(initials(state.user.fullName))}</span><span><strong>${escapeHTML(state.user.fullName)}</strong><small>${escapeHTML(state.user.memberNo)}</small></span></div>
          <button class="sidebar-logout" id="signout-button" type="button">Sign out securely →</button>
        </div>
      </aside>`;
  }

  function renderPortal(path) {
    const meta = pageMeta[path] || pageMeta['/dashboard'];
    document.title = `${meta[0]} | PLODA Member Portal`;
    app.innerHTML = `
      <div class="portal-shell">
        ${sidebarMarkup(path)}
        <div class="portal-main">
          <header class="portal-topbar">
            <div style="display:flex;align-items:center;gap:13px"><button class="mobile-menu" id="mobile-menu" type="button" aria-label="Open member navigation"><span></span></button><div class="topbar-title"><small>Member portal</small><strong>${escapeHTML(meta[0])}</strong></div></div>
            <div class="topbar-tools"><span class="status-pill">${escapeHTML(state.user.membershipStatus)}</span><a class="member-avatar" href="/profile" aria-label="Open profile">${escapeHTML(initials(state.user.fullName))}</a></div>
          </header>
          <main class="portal-content" id="portal-content"><div class="loading-card">Loading ${escapeHTML(meta[0].toLowerCase())}…</div></main>
        </div>
      </div>`;
    setupPortalShell();
    loadPortalPage(path).catch((reason) => {
      document.getElementById('portal-content').innerHTML = `<div class="loading-card">${escapeHTML(reason.message || 'This page could not be loaded.')}</div>`;
      toast(reason.message || 'This page could not be loaded.', 'error');
    });
  }

  function setupPortalShell() {
    const sidebar = document.getElementById('sidebar');
    document.getElementById('mobile-menu').addEventListener('click', () => {
      sidebar.classList.toggle('open');
      document.body.classList.toggle('no-scroll', sidebar.classList.contains('open'));
    });
    document.getElementById('signout-button').addEventListener('click', signOut);
  }

  async function signOut() {
    try { await api('/api/logout', { method: 'POST', body: {} }); }
    catch (reason) { toast(reason.message, 'error'); return; }
    state.user = null;
    state.csrf = '';
    location.href = '/signin';
  }

  function pageHead(title, copy, actions = '') {
    return `<div class="page-head"><div><p class="eyebrow">PLODA member portal</p><h1>${escapeHTML(title)}</h1><p>${escapeHTML(copy)}</p></div>${actions ? `<div class="page-actions">${actions}</div>` : ''}</div>`;
  }

  async function loadPortalPage(path) {
    clearInterval(state.chatTimer);
    state.chatTimer = null;
    const loaders = {
      '/dashboard': renderDashboard,
      '/projects': renderProjects,
      '/payments': renderPayments,
      '/deposit': renderDeposit,
      '/statements': renderStatements,
      '/documents': renderDocuments,
      '/news': renderNews,
      '/support': renderSupport,
      '/profile': renderProfile,
      '/constitution': renderConstitution,
      '/member-registration': renderMemberRegistration,
    };
    await (loaders[path] || renderDashboard)();
  }

  async function renderDashboard() {
    const data = await api('/api/dashboard');
    const summary = data.summary;
    document.getElementById('portal-content').innerHTML = `
      ${pageHead(`Welcome, ${state.user.fullName.split(' ')[0]}`, 'Here is your latest membership and portal activity.', '<a class="button button-primary" href="/deposit">Deposit funds <span aria-hidden="true">→</span></a>')}
      <div class="dashboard-grid">
        <article class="metric-card metric-dark"><div class="metric-label"><span>Completed payments</span><span class="metric-mark">$</span></div><strong class="metric-value">${formatMoney(summary.totalPaid)}</strong><span class="metric-foot">Across ${summary.paymentCount} payment record${summary.paymentCount === 1 ? '' : 's'}</span></article>
        <article class="metric-card"><div class="metric-label"><span>Membership status</span><span class="metric-mark">ID</span></div><strong class="metric-value" style="font-size:1.5rem">${escapeHTML(summary.membershipStatus)}</strong><span class="metric-foot">Member no. ${escapeHTML(state.user.memberNo)}</span></article>
        <article class="metric-card"><div class="metric-label"><span>Active projects</span><span class="metric-mark">PR</span></div><strong class="metric-value">${summary.projects}</strong><span class="metric-foot">Development programmes available</span></article>
        <article class="metric-card"><div class="metric-label"><span>Updates</span><span class="metric-mark">NW</span></div><strong class="metric-value">${summary.news}</strong><span class="metric-foot">Official member notices</span></article>
      </div>
      <div class="dashboard-lower">
        <section class="panel">
          <div class="panel-header"><div><h2>Recent payment activity</h2><p>Your latest portal transaction records</p></div><a class="text-link small" href="/payments">View all</a></div>
          <div class="table-wrap"><table class="data-table"><thead><tr><th>Reference</th><th>Method</th><th>Amount</th><th>Status</th><th>Date</th></tr></thead><tbody>
            ${data.recentPayments.length ? data.recentPayments.map((item) => `<tr><td><strong>${escapeHTML(item.reference)}</strong></td><td>${escapeHTML(item.method)}</td><td class="amount">${formatMoney(item.amount, item.currency)}</td><td>${statusBadge(item.status)}</td><td>${formatDate(item.created_at)}</td></tr>`).join('') : '<tr><td class="table-empty" colspan="5">No payment activity yet. Your records will appear here.</td></tr>'}
          </tbody></table></div>
        </section>
        <section class="panel"><div class="panel-header"><div><h2>Quick actions</h2><p>Common member tasks</p></div></div><div class="quick-actions">
          <a class="quick-action" href="/member-registration"><span>Complete member registration</span><span>→</span></a>
          <a class="quick-action" href="/documents"><span>Download joining form</span><span>→</span></a>
          <a class="quick-action" href="/constitution"><span>View constitution</span><span>→</span></a>
          <a class="quick-action" href="/support"><span>Contact support</span><span>→</span></a>
        </div></section>
      </div>`;
  }

  async function renderProjects() {
    const data = await api('/api/projects');
    document.getElementById('portal-content').innerHTML = `
      ${pageHead('Projects', 'Explore current PLODA programmes and their development progress.')}
      <div class="project-grid">${data.projects.map((project) => `
        <article class="project-card">
          <div class="project-meta"><span class="project-category">${escapeHTML(project.category)}</span>${statusBadge(project.status)}</div>
          <h2>${escapeHTML(project.title)}</h2><p>${escapeHTML(project.description)}</p>
          <div class="project-progress"><div class="progress-top"><span>${escapeHTML(project.location)}</span><strong>${Number(project.progress)}%</strong></div><div class="progress-track"><span style="width:${Math.max(0, Math.min(100, Number(project.progress)))}%"></span></div></div>
        </article>`).join('')}</div>`;
  }

  async function renderPayments() {
    const data = await api('/api/payments');
    const query = new URLSearchParams(location.search).get('payment');
    if (query === 'success') toast('Your PayPal payment was completed and recorded.');
    if (query === 'review') toast('Your payment has been recorded for verification.');
    if (query === 'error') toast('The payment could not be matched to your account.', 'error');
    document.getElementById('portal-content').innerHTML = `
      ${pageHead('My payments', 'Review every deposit request and payment status linked to your member account.', '<a class="button button-primary" href="/deposit">New deposit <span aria-hidden="true">→</span></a>')}
      <section class="panel"><div class="panel-header"><div><h2>Payment history</h2><p>${data.payments.length} transaction record${data.payments.length === 1 ? '' : 's'}</p></div></div>
        <div class="table-wrap"><table class="data-table"><thead><tr><th>Reference</th><th>Date</th><th>Method</th><th>Amount</th><th>Status</th><th>Note</th></tr></thead><tbody>
          ${data.payments.length ? data.payments.map((item) => `<tr><td><strong>${escapeHTML(item.reference)}</strong></td><td>${formatDate(item.created_at)}</td><td>${escapeHTML(item.method)}</td><td class="amount">${formatMoney(item.amount, item.currency)}</td><td>${statusBadge(item.status)}</td><td>${escapeHTML(item.note || '—')}</td></tr>`).join('') : '<tr><td class="table-empty" colspan="6">No payments have been recorded. Use Deposit funds to begin.</td></tr>'}
        </tbody></table></div>
      </section>`;
  }

  async function renderDeposit() {
    const data = await api('/api/payment-methods');
    state.paymentMethods = data.methods;
    state.bank = data.bank;
    const methodDescriptions = {
      'EcoCash': ['EC', 'Mobile money prompt'],
      'Bank transfer': ['BK', 'Use your unique reference'],
      'Visa': ['VI', 'Hosted secure card checkout'],
      'Cash': ['CS', 'Authorised PLODA office only'],
      'PayPal': ['PP', 'Pay through PayPal'],
    };
    const options = Object.entries(methodDescriptions).map(([method, info], index) => {
      const available = Boolean(data.methods[method]);
      return `<div class="method-option ${available ? '' : 'method-unavailable'}"><input id="method-${index}" name="method" type="radio" value="${escapeHTML(method)}" ${index === 0 ? 'checked' : ''}><label for="method-${index}"><span class="method-icon">${info[0]}</span><span class="method-copy"><strong>${escapeHTML(method)}</strong><small>${available ? info[1] : 'Awaiting merchant configuration'}</small></span></label></div>`;
    }).join('');
    document.getElementById('portal-content').innerHTML = `
      ${pageHead('Deposit funds', 'Choose a verified payment method. The portal never collects or stores card numbers.')}
      <div class="deposit-layout">
        <section class="panel deposit-card">
          <form id="deposit-form" class="form-stack" novalidate>
            <div class="form-grid">
              <div class="field"><label for="deposit-amount">Amount</label><input id="deposit-amount" name="amount" type="number" min="1" step="0.01" placeholder="0.00" required></div>
              <div class="field"><label for="deposit-currency">Currency</label><select id="deposit-currency" name="currency"><option>USD</option><option>ZiG</option></select></div>
              <div class="field field-full"><label>Payment method</label><div class="method-grid">${options}</div></div>
              <div class="field field-full"><label for="deposit-note">Payment note or bank reference</label><textarea id="deposit-note" name="note" placeholder="Add an optional note, payer name or transfer reference."></textarea></div>
            </div>
            <p class="inline-error" id="deposit-error" role="alert"></p>
            <button class="button button-primary" type="submit">Continue securely <span aria-hidden="true">→</span></button>
          </form>
        </section>
        <aside class="form-stack">
          <div class="panel panel-pad"><p class="eyebrow">Bank transfer details</p><div class="bank-details">
            <div class="bank-row"><span>Bank</span><strong>${escapeHTML(data.bank.bankName)}</strong></div>
            <div class="bank-row"><span>Account name</span><strong>${escapeHTML(data.bank.accountName)}</strong></div>
            <div class="bank-row"><span>Account number</span><strong>${escapeHTML(data.bank.accountNumber)}</strong></div>
            <div class="bank-row"><span>Branch</span><strong>${escapeHTML(data.bank.branch)}</strong></div>
          </div></div>
          <div class="payment-note"><strong>Payment protection:</strong> confirm that the method is marked available, never share an OTP or portal password, and retain your PLODA reference and provider receipt.</div>
        </aside>
      </div>`;
    document.getElementById('deposit-form').addEventListener('submit', handleDeposit);
  }

  async function handleDeposit(event) {
    event.preventDefault();
    const form = event.currentTarget;
    const error = document.getElementById('deposit-error');
    error.textContent = '';
    if (!form.checkValidity()) { form.reportValidity(); return; }
    const method = new FormData(form).get('method');
    if (!state.paymentMethods[method]) {
      error.textContent = `${method} is awaiting secure merchant configuration. No payment has been started.`;
      return;
    }
    const button = form.querySelector('button[type="submit"]');
    button.disabled = true;
    button.textContent = 'Preparing secure payment…';
    try {
      const data = await api('/api/deposits', { method: 'POST', body: { amount: form.amount.value, currency: form.currency.value, method, note: form.note.value } });
      showPaymentModal(data, method);
      form.reset();
    } catch (reason) {
      error.textContent = reason.message;
      button.disabled = false;
      button.innerHTML = 'Continue securely <span aria-hidden="true">→</span>';
    }
  }

  function showPaymentModal(data, method) {
    const backdrop = document.createElement('div');
    backdrop.className = 'modal-backdrop';
    backdrop.innerHTML = `<div class="modal" role="dialog" aria-modal="true" aria-labelledby="payment-modal-title"><p class="eyebrow">Payment reference</p><h2 id="payment-modal-title">${escapeHTML(data.reference)}</h2><p>${escapeHTML(data.message)}</p><p class="payment-note">Keep this reference with your provider receipt. PLODA Support may request it during verification.</p><div class="modal-actions"><a class="button button-soft" href="/payments">View payments</a>${data.redirectUrl ? `<a class="button button-primary" href="${escapeHTML(data.redirectUrl)}">Continue to ${escapeHTML(method)} →</a>` : '<button class="button button-primary" type="button" data-close-modal>Done</button>'}</div></div>`;
    document.body.appendChild(backdrop);
    document.body.classList.add('no-scroll');
    const close = () => { backdrop.remove(); document.body.classList.remove('no-scroll'); };
    backdrop.addEventListener('click', (event) => { if (event.target === backdrop || event.target.matches('[data-close-modal]')) close(); });
  }

  async function renderStatements() {
    const data = await api('/api/statements');
    document.getElementById('portal-content').innerHTML = `
      ${pageHead('Statements', 'A clear record of transactions linked to your membership account.', '<button class="button button-primary" id="download-statement" type="button">Download CSV statement</button>')}
      <section class="panel"><div class="panel-header"><div><h2>Member statement</h2><p>Member no. ${escapeHTML(state.user.memberNo)}</p></div><span class="small muted">Generated ${formatDate(new Date())}</span></div>
        <div class="table-wrap"><table class="data-table"><thead><tr><th>Date</th><th>Reference</th><th>Description</th><th>Debit/Credit</th><th>Status</th><th>Running total</th></tr></thead><tbody>
          ${data.entries.length ? data.entries.map((item) => `<tr><td>${formatDate(item.created_at)}</td><td><strong>${escapeHTML(item.reference)}</strong></td><td>${escapeHTML(item.method)}</td><td class="amount">${formatMoney(item.amount, item.currency)}</td><td>${statusBadge(item.status)}</td><td class="amount">${formatMoney(item.balance, item.currency)}</td></tr>`).join('') : '<tr><td class="table-empty" colspan="6">No statement entries are available.</td></tr>'}
        </tbody></table></div>
      </section>`;
    document.getElementById('download-statement').addEventListener('click', () => downloadStatement(data.entries));
  }

  function downloadStatement(entries) {
    const cells = (value) => `"${String(value ?? '').replace(/"/g, '""')}"`;
    const rows = [['Date', 'Reference', 'Method', 'Amount', 'Currency', 'Status', 'Note']]
      .concat(entries.map((item) => [item.created_at, item.reference, item.method, item.amount, item.currency, item.status, item.note]));
    const csv = rows.map((row) => row.map(cells).join(',')).join('\r\n');
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = `PLODA_Statement_${state.user.memberNo}.csv`;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(link.href);
  }

  async function renderDocuments() {
    document.getElementById('portal-content').innerHTML = `
      ${pageHead('Documents', 'Download PLODA membership resources and governing information.')}
      <div class="document-grid">
        <article class="document-card"><span class="doc-type">PDF</span><h2>PLODA constitution reference</h2><p>A professionally formatted portal reference edition covering PLODA's mandate, values and member governance.</p><a class="button button-soft button-sm" href="/downloads/PLODA_Constitution_Portal_Reference.pdf">Download document</a></article>
        <article class="document-card"><span class="doc-type">PDF</span><h2>Member joining form</h2><p>A printable form for personal details, membership interests, declarations and office verification.</p><a class="button button-soft button-sm" href="/downloads/PLODA_Member_Joining_Form.pdf">Download form</a></article>
        <article class="document-card"><span class="doc-type">WEB</span><h2>Online member registration</h2><p>Complete the secure digital registration form and submit it directly through your portal account.</p><a class="button button-soft button-sm" href="/member-registration">Complete online</a></article>
        <article class="document-card"><span class="doc-type">CSV</span><h2>Financial statement</h2><p>Export your personal payment history for independent record-keeping and reconciliation.</p><a class="button button-soft button-sm" href="/statements">Open statements</a></article>
      </div>`;
  }

  async function renderNews() {
    const data = await api('/api/news');
    document.getElementById('portal-content').innerHTML = `
      ${pageHead('News & updates', 'Official announcements and guidance for PLODA members.')}
      <div class="news-grid">${data.news.map((item) => `<article class="news-card"><div class="news-meta"><span class="badge badge-neutral">${escapeHTML(item.category)}</span><time>${formatDate(item.published_at)}</time></div><h2>${escapeHTML(item.title)}</h2><p>${escapeHTML(item.excerpt)}</p></article>`).join('')}</div>`;
  }

  async function renderSupport() {
    document.getElementById('portal-content').innerHTML = `
      ${pageHead('Support chat', 'Send a secure message to the PLODA membership support team.')}
      <div class="chat-layout">
        <aside class="panel support-intro"><p class="eyebrow eyebrow-light">Member assistance</p><h2>How can we help?</h2><p>Use this chat for membership, project, document and payment-reference queries. Never send passwords, OTPs or full card details.</p><div class="support-hours"><strong>PLODA Office</strong><span>23 Richwell Avenue, Meyrick Park, Mabelreign, Harare</span><strong style="margin-top:17px">Email</strong><span>info@ploda.org</span></div></aside>
        <section class="panel chat-panel"><div class="panel-header"><div><h2>Secure support conversation</h2><p>Messages are linked to ${escapeHTML(state.user.memberNo)}</p></div><span class="status-pill">Available</span></div><div class="chat-messages" id="chat-messages"><div class="chat-empty">Loading conversation…</div></div><form class="chat-compose" id="chat-form"><label class="sr-only" for="chat-message">Message</label><input id="chat-message" name="message" autocomplete="off" maxlength="1000" placeholder="Write a message to PLODA Support…" required><button class="button button-primary button-sm" type="submit">Send message</button></form></section>
      </div>`;
    document.getElementById('chat-form').addEventListener('submit', handleSupportMessage);
    await refreshSupportMessages();
    state.chatTimer = setInterval(refreshSupportMessages, 8000);
  }

  async function refreshSupportMessages() {
    try {
      const data = await api('/api/support/messages');
      const container = document.getElementById('chat-messages');
      if (!container) return;
      container.innerHTML = data.messages.length ? data.messages.map((item) => `<div class="message message-${item.sender === 'member' ? 'member' : 'support'}"><div class="message-bubble">${escapeHTML(item.body)}</div><span class="message-time">${item.sender === 'member' ? 'You' : 'PLODA Support'} • ${formatDateTime(item.created_at)}</span></div>`).join('') : '<div class="chat-empty">Start a secure conversation with PLODA Support.</div>';
      container.scrollTop = container.scrollHeight;
    } catch (_) {}
  }

  async function handleSupportMessage(event) {
    event.preventDefault();
    const form = event.currentTarget;
    const button = form.querySelector('button');
    button.disabled = true;
    try {
      await api('/api/support/messages', { method: 'POST', body: { message: form.message.value } });
      form.reset();
      await refreshSupportMessages();
    } catch (reason) { toast(reason.message, 'error'); }
    button.disabled = false;
  }

  async function renderProfile() {
    const user = state.user;
    document.getElementById('portal-content').innerHTML = `
      ${pageHead('Profile', 'Keep your personal and contact information current.')}
      <div class="profile-layout">
        <aside class="panel profile-summary"><span class="profile-avatar">${escapeHTML(initials(user.fullName))}</span><h2>${escapeHTML(user.fullName)}</h2><p>${escapeHTML(user.email)}</p><div class="profile-id">${escapeHTML(user.memberNo)}</div><div style="margin-top:14px">${statusBadge(user.membershipStatus)}</div></aside>
        <section class="panel profile-form"><form id="profile-form" class="form-stack"><div class="form-grid">
          <div class="field field-full"><label for="profile-name">Full name</label><input id="profile-name" name="fullName" autocomplete="name" value="${escapeHTML(user.fullName)}" required></div>
          <div class="field"><label for="profile-email">Email address</label><input id="profile-email" value="${escapeHTML(user.email)}" disabled><p class="field-hint">Contact support to change your login email.</p></div>
          <div class="field"><label for="profile-phone">Phone number</label><input id="profile-phone" name="phone" autocomplete="tel" value="${escapeHTML(user.phone)}" required></div>
          <div class="field"><label for="profile-province">Province</label><select id="profile-province" name="province" required>${provinceOptions(user.province)}</select></div>
          <div class="field"><label for="profile-occupation">Occupation</label><input id="profile-occupation" name="occupation" value="${escapeHTML(user.occupation)}"></div>
          <div class="field field-full"><label for="profile-address">Residential address</label><textarea id="profile-address" name="address">${escapeHTML(user.address)}</textarea></div>
        </div><p class="inline-error" id="profile-error" role="alert"></p><button class="button button-primary" type="submit">Save profile changes</button></form></section>
      </div>`;
    document.getElementById('profile-form').addEventListener('submit', handleProfileUpdate);
  }

  async function handleProfileUpdate(event) {
    event.preventDefault();
    const form = event.currentTarget;
    const error = document.getElementById('profile-error');
    error.textContent = '';
    if (!form.checkValidity()) { form.reportValidity(); return; }
    const button = form.querySelector('button[type="submit"]');
    button.disabled = true;
    try {
      const data = await api('/api/profile', { method: 'POST', body: { fullName: form.fullName.value, phone: form.phone.value, province: form.province.value, occupation: form.occupation.value, address: form.address.value } });
      state.user = data.user;
      toast(data.message);
      renderPortal('/profile');
    } catch (reason) { error.textContent = reason.message; button.disabled = false; }
  }

  async function renderConstitution() {
    document.getElementById('portal-content').innerHTML = `
      <section class="constitution-hero"><p class="eyebrow eyebrow-light">PLODA governing framework</p><h1>Constitution & member mandate.</h1><p>PLODA's constitution guides our purpose, governance, membership obligations and commitment to responsible land ownership and development.</p><div class="constitution-actions"><a class="button button-gold" href="/downloads/PLODA_Constitution_Portal_Reference.pdf">Download constitution reference</a><a class="button" style="color:#fff;border-color:rgba(255,255,255,.24)" href="/documents">All documents</a></div></section>
      <p class="reference-notice"><strong>Document status:</strong> The downloadable file is a portal reference edition based on the current PLODA mandate and branding. It is not represented as the signed legal master constitution. The signed master should replace it before formal public launch.</p>
      <div class="constitution-grid">
        <article class="constitution-section"><b>01</b><h2>Identity & purpose</h2><p>Defines the People's Land Ownership and Development Association and its commitment to inclusive ownership, dignity and sustainable development.</p></article>
        <article class="constitution-section"><b>02</b><h2>Membership</h2><p>Sets membership eligibility, registration responsibilities, conduct expectations and the applicable non-refundable joining fee.</p></article>
        <article class="constitution-section"><b>03</b><h2>Governance</h2><p>Establishes accountable leadership, the distinct offices of Founder and Patron, decision-making responsibilities and institutional integrity.</p></article>
        <article class="constitution-section"><b>04</b><h2>Development mandate</h2><p>Connects land access with agro-residential development, food security, livestock, job creation, empowerment and social protection.</p></article>
        <article class="constitution-section"><b>05</b><h2>National development</h2><p>Promotes productive participation, balanced regional development, sustainable communities and alignment with national development aspirations.</p></article>
        <article class="constitution-section"><b>06</b><h2>Member accountability</h2><p>Requires truthful information, responsible use of resources, verified payments, lawful conduct and respect for PLODA policies.</p></article>
      </div>`;
  }

  async function renderMemberRegistration() {
    const user = state.user;
    document.getElementById('portal-content').innerHTML = `
      ${pageHead('Member registration', 'Complete the information required for formal PLODA membership verification.', '<a class="button button-soft" href="/downloads/PLODA_Member_Joining_Form.pdf">Download printable form</a>')}
      <div class="registration-layout">
        <aside class="panel registration-note"><p class="eyebrow eyebrow-light">Registration process</p><h2>Accurate details support efficient verification.</h2><p>Complete every field using information that can be supported by valid identification and contact records.</p><div class="registration-list"><span><b>1</b>Provide identification and residential details.</span><span><b>2</b>Record next-of-kin and occupation information.</span><span><b>3</b>Select your membership and programme interests.</span><span><b>4</b>Submit for PLODA office verification.</span></div><div class="payment-note" style="margin-top:26px"><strong>Joining fee:</strong> US$200 non-refundable, payable only through officially verified channels after guidance from PLODA.</div></aside>
        <section class="panel registration-form"><form id="member-registration-form" class="form-stack"><div class="form-grid">
          <div class="field"><label for="reg-member">Member number</label><input id="reg-member" value="${escapeHTML(user.memberNo)}" disabled></div>
          <div class="field"><label for="reg-status">Current status</label><input id="reg-status" value="${escapeHTML(user.membershipStatus)}" disabled></div>
          <div class="field"><label for="reg-national-id">National ID / Passport number</label><input id="reg-national-id" name="nationalId" value="${escapeHTML(user.nationalId)}" required></div>
          <div class="field"><label for="reg-occupation">Occupation</label><input id="reg-occupation" name="occupation" value="${escapeHTML(user.occupation)}" required></div>
          <div class="field field-full"><label for="reg-address">Residential address</label><textarea id="reg-address" name="address" required>${escapeHTML(user.address)}</textarea></div>
          <div class="field field-full"><label for="reg-next-of-kin">Next of kin - full name, relationship and phone</label><input id="reg-next-of-kin" name="nextOfKin" value="${escapeHTML(user.nextOfKin)}" required></div>
          <div class="field field-full"><label for="reg-interests">Membership and programme interests</label><textarea id="reg-interests" name="interests" placeholder="Land ownership, agro-residential development, agriculture, livestock, enterprise…" required>${escapeHTML(user.interests)}</textarea></div>
        </div><label class="checkbox-field"><input id="registration-declaration" type="checkbox" required><span>I declare that the information provided is true and consent to PLODA verification for membership administration.</span></label><p class="inline-error" id="registration-error" role="alert"></p><button class="button button-primary" type="submit">Submit for verification <span aria-hidden="true">→</span></button></form></section>
      </div>`;
    document.getElementById('member-registration-form').addEventListener('submit', handleMemberRegistration);
  }

  async function handleMemberRegistration(event) {
    event.preventDefault();
    const form = event.currentTarget;
    const error = document.getElementById('registration-error');
    error.textContent = '';
    if (!form.checkValidity()) { form.reportValidity(); return; }
    const button = form.querySelector('button[type="submit"]');
    button.disabled = true;
    try {
      const data = await api('/api/member-registration', { method: 'POST', body: { nationalId: form.nationalId.value, address: form.address.value, nextOfKin: form.nextOfKin.value, occupation: form.occupation.value, interests: form.interests.value } });
      state.user = data.user;
      toast(data.message);
      renderPortal('/member-registration');
    } catch (reason) { error.textContent = reason.message; button.disabled = false; }
  }

  async function initialise() {
    const path = location.pathname.replace(/\/$/, '') || '/';
    try {
      const session = await api('/api/me');
      if (session.authenticated) {
        state.user = session.user;
        state.csrf = session.csrfToken;
      }
    } catch (_) {}

    if (state.user && ['/signin', '/create-account'].includes(path)) {
      location.replace('/dashboard');
      return;
    }
    if (!state.user && pageMeta[path]) {
      location.replace(`/signin?next=${encodeURIComponent(path)}`);
      return;
    }
    if (path === '/') renderLanding();
    else if (path === '/signin') renderSignIn();
    else if (path === '/create-account') renderCreateAccount();
    else if (path === '/privacy') renderInfoPage('privacy');
    else if (path === '/terms') renderInfoPage('terms');
    else if (pageMeta[path]) renderPortal(path);
    else renderLanding();
  }

  window.addEventListener('beforeunload', () => clearInterval(state.chatTimer));
  initialise();
})();
