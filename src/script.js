  let currentData = null;
  let currentUrl  = null;
  let ws = null;
  let clientId = null;

  // Generate unique client ID
  function generateClientId() {
    return 'client_' + Math.random().toString(36).substr(2, 9) + '_' + Date.now();
  }

  // WebSocket connection
  function connectWebSocket() {
    if (!clientId) clientId = generateClientId();
    
    try {
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const wsUrl = `${protocol}//${window.location.host}/ws/${clientId}`;
      
      ws = new WebSocket(wsUrl);
      
      ws.onopen = () => {
        console.log('[WebSocket] Connected to', wsUrl);
      };
      
      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          console.log('[WebSocket] Received:', data);
          updateProgress(data);
        } catch (e) {
          console.error('[WebSocket] Error parsing message:', e);
        }
      };
      
      ws.onerror = (error) => {
        console.warn('[WebSocket] Not available, progress updates disabled');
      };
      
      ws.onclose = () => {
        console.log('[WebSocket] Disconnected');
        // Don't reconnect if server doesn't support WebSocket
      };
    } catch (e) {
      console.warn('[WebSocket] Not supported, progress updates disabled');
    }
  }

  // Update progress UI
  function updateProgress(data) {
    const progressBar = document.getElementById('progressBar');
    const progressText = document.getElementById('progressText');
    const progressPercent = document.getElementById('progressPercent');
    const progressFill = document.getElementById('progressFill');
    const progressDetails = document.getElementById('progressDetails');
    
    progressBar.classList.remove('hidden');
    progressText.textContent = data.message || 'Processing...';
    progressPercent.textContent = `${data.progress || 0}%`;
    progressFill.style.width = `${data.progress || 0}%`;
    
    if (data.total && data.completed) {
      progressDetails.textContent = `${data.completed} / ${data.total} files`;
    }
    
    // Hide progress bar when complete
    if (data.stage === 'complete') {
      setTimeout(() => {
        progressBar.classList.add('hidden');
      }, 2000);
    }
  }

  // Connect on page load
  connectWebSocket();

  // Auth state
  let authToken    = localStorage.getItem('token') || null;
  let authEmail    = localStorage.getItem('authEmail') || null;
  let authUsername = localStorage.getItem('authUsername') || null;
  let authMode     = 'signin';

  // Restore session on load
  if (authToken) setUser(authUsername, authEmail);

  function setUser(username, email) {
    authUsername = username;
    authEmail    = email;
    const loggedIn = !!username;
    document.getElementById('authGuest').classList.toggle('hidden', loggedIn);
    document.getElementById('authUser').classList.toggle('hidden', !loggedIn);
    if (loggedIn) {
      document.getElementById('authEmail').textContent = username || email;
      const emailDisplay = document.getElementById('authUsernameDisplay');
      if (emailDisplay) emailDisplay.textContent = '';
    }
    // Update share button visibility when auth state changes
    const shareBtn = document.getElementById('shareBtn');
    if (shareBtn) shareBtn.classList.toggle('hidden', !loggedIn || !currentData);
  }

  function getToken() { return authToken; }

  // Auth modal
  function openAuthModal() {
    document.getElementById('authModal').classList.remove('hidden');
    document.getElementById('authError').classList.add('hidden');
    document.getElementById('authUsernameInput').value = '';
    document.getElementById('authEmailInput').value = '';
    document.getElementById('authPasswordInput').value = '';
    document.getElementById('authConfirmInput').value = '';
  }

  function closeAuthModal() {
    document.getElementById('authModal').classList.add('hidden');
  }

  function setAuthTab(mode) {
    authMode = mode;
    const isSignIn = mode === 'signin';
    document.getElementById('tabSignIn').className = `flex-1 py-2 transition ${isSignIn ? 'bg-slate-700 text-white' : 'text-slate-400 hover:text-white'}`;
    document.getElementById('tabSignUp').className = `flex-1 py-2 transition ${!isSignIn ? 'bg-slate-700 text-white' : 'text-slate-400 hover:text-white'}`;
    document.getElementById('authSubmitBtn').textContent = isSignIn ? 'Sign in' : 'Sign up';
    // Username and confirm only shown on sign-up
    document.getElementById('authUsernameInput').classList.toggle('hidden', isSignIn);
    document.getElementById('authConfirmInput').classList.toggle('hidden', isSignIn);
    document.getElementById('authError').classList.add('hidden');
  }

  async function submitAuth() {
    const username = document.getElementById('authUsernameInput').value.trim();
    const email    = document.getElementById('authEmailInput').value.trim();
    const password = document.getElementById('authPasswordInput').value;
    const confirm  = document.getElementById('authConfirmInput').value;
    const errEl    = document.getElementById('authError');
    errEl.classList.add('hidden');

    if (authMode === 'signup') {
      if (!username) {
        errEl.textContent = 'Username is required.';
        errEl.classList.remove('hidden');
        return;
      }
      if (password !== confirm) {
        errEl.textContent = 'Passwords do not match.';
        errEl.classList.remove('hidden');
        return;
      }
    }

    const endpoint = authMode === 'signin' ? '/login' : '/register';
    const body = authMode === 'signin'
      ? { email, password }
      : { username, email, password };

    const res = await fetch(endpoint, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body)
    });
    const data = await res.json();

    if (!res.ok) {
      errEl.textContent = data.detail || 'Something went wrong.';
      errEl.classList.remove('hidden');
      return;
    }

    authToken = data.token;
    localStorage.setItem('token', authToken);
    localStorage.setItem('authEmail', data.email);
    localStorage.setItem('authUsername', data.username || data.email);
    setUser(data.username || data.email, data.email);
    closeAuthModal();
  }

  function signOut() {
    authToken    = null;
    authEmail    = null;
    authUsername = null;
    localStorage.removeItem('token');
    localStorage.removeItem('authEmail');
    localStorage.removeItem('authUsername');
    setUser(null, null);
  }

  // Export report
  async function exportReport(format) {
    if (!currentData) {
      showError('No analysis data to export');
      return;
    }
    
    try {
      const res = await fetch(`/export/${format}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(currentData)
      });
      
      if (!res.ok) {
        showError(`Export failed: ${res.status}`);
        return;
      }
      
      // Download file
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `analysis-report.${format}`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
    } catch (e) {
      showError('Export failed');
    }
  }

  // Theme toggle
  function toggleTheme() {
    const isLight = document.documentElement.classList.toggle('light');
    document.getElementById('themeToggle').textContent = isLight ? '☀️' : '🌙';
    localStorage.setItem('theme', isLight ? 'light' : 'dark');
  }

  // Apply saved theme on load
  (function() {
    const saved = localStorage.getItem('theme');
    if (saved === 'light') {
      document.documentElement.classList.add('light');
      document.addEventListener('DOMContentLoaded', () => {
        const btn = document.getElementById('themeToggle');
        if (btn) btn.textContent = '☀️';
      });
    }
  })();

  // Switch active view
  function setView(v) {
    ['analyze','history','analytics','shared'].forEach(x => {
      const el = document.getElementById(`view-${x}`);
      el.style.display = (x === v) ? '' : 'none';
      const btn = document.getElementById(`nav-${x}`);
      btn.className = x === v
        ? 'nav-btn active-nav text-left px-3 py-2 rounded-lg flex items-center gap-2'
        : 'nav-btn text-left px-3 py-2 rounded-lg flex items-center gap-2 text-slate-400 hover:text-white hover:bg-slate-800 transition';
    });
    if (v === 'history') loadHistory();
    if (v === 'analytics') loadAnalytics();
    if (v === 'shared') loadSharedReports();
  }

  // Switch branch without re-fetching repo metadata
  async function switchBranch(branch) {
    const url = currentUrl || document.getElementById('repoUrl').value.trim();
    if (!url) { showError('No repo loaded yet.'); return; }
    setLoading(true);
    showError('');
    try {
      const res = await fetch('/switch-branch', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: url, branch })
      });
      if (!res.ok) { showError(`Server error ${res.status}`); return; }
      const data = await res.json();
      // Preserve meta/tags/PRs/issues from the previous full analysis
      data.meta  = currentData.meta;
      data.tags  = currentData.tags;
      data.pull_requests = currentData.pull_requests;
      data.issues = currentData.issues;
      currentData = data;
      render(currentData);
    } catch(e) {
      showError('Branch switch failed.');
    } finally {
      setLoading(false);
    }
  }

  // Switch to a tag (checkout tag commit, re-analyze files)
  async function switchTag(tag) {
    const url = currentUrl || document.getElementById('repoUrl').value.trim();
    if (!url) { showError('No repo loaded yet.'); return; }
    setLoading(true);
    showError('');
    try {
      const res = await fetch('/switch-tag', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url, tag })
      });
      if (!res.ok) { showError(`Server error ${res.status}`); return; }
      const data = await res.json();
      // Preserve meta/tags/PRs/issues
      data.meta          = currentData.meta;
      data.tags          = currentData.tags;
      data.pull_requests = currentData.pull_requests;
      data.issues        = currentData.issues;
      currentData = data;
      render(currentData);
    } catch(e) {
      showError('Tag switch failed.');
    } finally {
      setLoading(false);
    }
  }

  // Run analysis
  async function analyze(branchOverride) {
    const url    = document.getElementById('repoUrl').value.trim();
    const branch = branchOverride || null;
    if (!url) return;

    currentUrl = url;
    setLoading(true);
    showError('');
    document.getElementById('progressBar').classList.remove('hidden');

    try {
      const token = getToken();
      const headers = { 'Content-Type': 'application/json' };
      if (token) headers['Authorization'] = `Bearer ${token}`;

      const res = await fetch('/analyze', {
        method: 'POST',
        headers,
        body: JSON.stringify({ url, branch, client_id: clientId })
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        showError(data.detail || `Server error ${res.status}`);
        return;
      }
      currentData = await res.json();
      render(currentData);
      // Hide progress bar after analysis completes
      setTimeout(() => {
        document.getElementById('progressBar').classList.add('hidden');
      }, 1000);
    } catch(e) {
      showError('Cannot reach backend. Is uvicorn running?');
    } finally {
      setLoading(false);
    }
  }

  // Render analysis results
  function render(d) {
    document.getElementById('emptyState').classList.add('hidden');
    document.getElementById('results').classList.remove('hidden');
    document.getElementById('repoPanel').classList.remove('hidden');

    // Meta card
    const mc = document.getElementById('metaContent');
    mc.innerHTML = d.meta && d.meta.full_name ? `
      <div class="flex-1">
        <a href="${d.meta.url}" target="_blank" class="text-blue-400 font-bold hover:underline">${d.meta.full_name}</a>
        <p class="text-slate-400 text-xs mt-1">${d.meta.description || ''}</p>
      </div>
      <div class="flex gap-4 text-xs text-slate-400 flex-wrap">
        <span>⭐ ${d.meta.stars}</span>
        <span>🍴 ${d.meta.forks}</span>
        <span> ${d.meta.open_issues} open issues</span>
        <span>🌐 ${d.meta.language || 'mixed'}</span>
      </div>` : '';

    // Summary stats
    document.getElementById('sumBranch').textContent = d.branch;
    document.getElementById('sumTotal').textContent  = d.summary.total;
    document.getElementById('sumCode').textContent   = d.summary.code;
    document.getElementById('sumDocs').textContent   = d.summary.docs;
    document.getElementById('sumIssues').textContent = d.summary.issues;

    // Sidebar branch list and top-bar dropdown
    const bl = document.getElementById('branchList');
    const dd = document.getElementById('branchDropdown');
    bl.innerHTML = '';
    dd.innerHTML = '';
    dd.classList.remove('hidden');

    d.branches.forEach(b => {
      const isActive = b.name === d.branch;

      // Sidebar button
      const btn = document.createElement('button');
      btn.className = `text-left px-2 py-1.5 rounded text-xs transition w-full flex items-center gap-1.5
        ${isActive ? 'bg-blue-700 text-white' : 'text-slate-400 hover:bg-slate-800 hover:text-white'}`;
      btn.innerHTML = `
        <span class="shrink-0">${b.is_default ? '⭐' : '🌿'}</span>
        <span class="truncate flex-1">${esc(b.name)}</span>
        <span class="shrink-0 ${b.merged ? 'text-green-400' : 'text-yellow-400'}" title="${b.merged ? 'merged' : 'unmerged'}">
          ${b.merged ? '✓' : '○'}
        </span>`;
      btn.title = `${b.name} · ${b.merged ? 'merged' : 'unmerged'} · ${b.sha}`;
      btn.id = `branch-btn-${b.name}`;
      btn.onclick = () => switchBranch(b.name);
      bl.appendChild(btn);

      // Dropdown option
      const opt = document.createElement('option');
      opt.value = b.name;
      opt.textContent = `${b.is_default ? '⭐ ' : ''}${b.name} ${b.merged ? '✓' : '○'}`;
      if (isActive) opt.selected = true;
      dd.appendChild(opt);
    });

      // Sidebar tags
    const tl = document.getElementById('tagList');
    if (d.tags.length) {
      tl.innerHTML = '';
      d.tags.forEach(t => {
        const isActive = d.branch === t.name;
        const btn = document.createElement('button');
        btn.className = `text-left px-2 py-1.5 rounded text-xs transition w-full flex items-center gap-1.5
          ${isActive ? 'bg-purple-700 text-white' : 'text-slate-400 hover:bg-slate-800 hover:text-white'}`;
        btn.innerHTML = `
          <span class="shrink-0">🏷</span>
          <span class="truncate flex-1">${esc(t.name)}</span>
          <span class="shrink-0 text-slate-500 font-mono">${esc(t.sha || '')}</span>`;
        btn.title = `Tag: ${t.name} · ${t.sha || ''}`;
        btn.onclick = () => switchTag(t.name);
        tl.appendChild(btn);
      });
    } else {
      tl.innerHTML = '<span class="text-xs text-slate-600 px-2">No tags</span>';
    }

    // File tabs
    renderFileTab('code',  d.code);
    renderFileTab('docs',  d.docs);
    renderFileTab('other', d.other);
    renderWarningsTab(d.code);

    // Commits — update tab label with count
    const commitCount = (d.commits || []).length;
    document.getElementById('tab-commits').innerHTML =
      `🔖 Commits${commitCount ? ` <span class="ml-1 bg-slate-700 text-slate-300 text-xs px-1.5 py-0.5 rounded-full">${commitCount}</span>` : ''}`;
    renderCommitsTab(d.commits);

    // PRs
    renderList('prs', d.pull_requests, pr => `
      <div class="bg-slate-800 border border-slate-700 rounded-lg px-4 py-3 flex gap-3 items-start">
        <span class="shrink-0 ${pr.state==='open' ? 'text-green-400' : 'text-purple-400'}">
          ${pr.state==='open' ? '🟢' : '🟣'}
        </span>
        <div class="flex-1 min-w-0">
          <a href="${pr.url}" target="_blank" class="text-blue-400 hover:underline truncate block">#${pr.number} ${esc(pr.title)}</a>
          <p class="text-slate-500 text-xs mt-0.5">${esc(pr.author)} · ${pr.branch} · ${pr.created_at.slice(0,10)}</p>
        </div>
      </div>`);

    showTab('code');

    // Auto-switch to warnings tab if there are issues
    if (d.summary && d.summary.issues > 0) {
      showTab('warnings');
    }

    // Update share button visibility
    const shareBtn = document.getElementById('shareBtn');
    if (shareBtn) shareBtn.classList.toggle('hidden', !authToken);

    // Load collaboration data if authenticated
    if (authToken && d.id) {
      loadCommentsAndAssignments(d.id);
    }
  }

  function renderCommitsTab(commits) {
    const c = document.getElementById('tab-commits-content');
    c.innerHTML = '';
    if (!commits || !commits.length) {
      c.innerHTML = '<p class="text-slate-500 py-4">No commits found.</p>';
      return;
    }

    // Search bar
    const bar = document.createElement('div');
    bar.className = 'flex gap-2 items-center mb-1';
    bar.innerHTML = `
      <input id="commitSearch" type="text" placeholder="Search commits, authors..."
        class="flex-1 bg-slate-800 border border-slate-700 rounded-lg px-3 py-1.5 text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500 text-xs"/>
      <span id="commitCount" class="text-slate-500 text-xs shrink-0">${commits.length} commits</span>`;
    c.appendChild(bar);

    const list = document.createElement('div');
    list.className = 'flex flex-col gap-1';
    c.appendChild(list);

    function renderCommitList(filter = '') {
      list.innerHTML = '';
      const fl = filter.toLowerCase();
      const filtered = fl
        ? commits.filter(cm => cm.message.toLowerCase().includes(fl) || cm.author.toLowerCase().includes(fl) || cm.sha.includes(fl))
        : commits;
      document.getElementById('commitCount').textContent = `${filtered.length} of ${commits.length} commits`;
      filtered.forEach(cm => {
        const div = document.createElement('div');
        div.className = 'bg-slate-800 border border-slate-700 rounded-lg px-4 py-2.5 flex gap-4 items-center hover:border-slate-500 transition';
        div.innerHTML = `
          <code class="text-yellow-400 shrink-0 text-xs font-mono">${esc(cm.sha)}</code>
          <div class="flex-1 min-w-0">
            <p class="text-slate-200 text-xs truncate">${esc(cm.message)}</p>
            <p class="text-slate-500 text-xs mt-0.5">${esc(cm.author)} · ${cm.date.slice(0,10)}</p>
          </div>`;
        list.appendChild(div);
      });
    }

    renderCommitList();
    document.getElementById('commitSearch').addEventListener('input', e => renderCommitList(e.target.value));
  }

  function renderWarningsTab(codeFiles) {
    const c = document.getElementById('tab-warnings-content');
    c.innerHTML = '';

    // Collect all issues across all files
    const allIssues = [];
    (codeFiles || []).forEach(f => {
      if (f.issues && f.issues.length) {
        f.issues.forEach(issue => allIssues.push({ file: f.path, lang: f.language, issue }));
      }
    });

    if (!allIssues.length) {
      c.innerHTML = `<div class="flex flex-col items-center py-16 gap-3 text-slate-500">
        <span class="text-4xl">✅</span>
        <p>No code issues found!</p>
      </div>`;
      // Update tab badge
      document.getElementById('tab-warnings').innerHTML = '⚠️ Code Issues';
      return;
    }

    // Update tab badge with count
    document.getElementById('tab-warnings').innerHTML = `⚠️ Code Issues <span class="ml-1 bg-yellow-700/60 text-yellow-300 text-xs px-1.5 py-0.5 rounded-full">${allIssues.length}</span>`;

    // Search/filter bar
    const filterBar = document.createElement('div');
    filterBar.className = 'flex gap-2 items-center mb-1';
    filterBar.innerHTML = `
      <input id="issueSearch" type="text" placeholder="Filter issues or files..."
        class="flex-1 bg-slate-800 border border-slate-700 rounded-lg px-3 py-1.5 text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-yellow-500 text-xs"/>
      <span class="text-slate-500 text-xs shrink-0" id="issueCount">${allIssues.length} issues in ${codeFiles.filter(f=>f.issues&&f.issues.length).length} files</span>`;
    c.appendChild(filterBar);

    // Group by file
    const byFile = {};
    allIssues.forEach(({ file, lang, issue }) => {
      if (!byFile[file]) byFile[file] = { lang, issues: [] };
      byFile[file].issues.push(issue);
    });

    const listContainer = document.createElement('div');
    listContainer.className = 'flex flex-col gap-2';
    listContainer.id = 'warningsList';
    c.appendChild(listContainer);

    function renderIssueList(filter = '') {
      listContainer.innerHTML = '';
      const fl = filter.toLowerCase();
      let shown = 0;
      Object.entries(byFile).forEach(([file, { lang, issues }]) => {
        const matched = issues.filter(i =>
          !fl || i.toLowerCase().includes(fl) || file.toLowerCase().includes(fl)
        );
        if (!matched.length) return;
        shown += matched.length;

        const card = document.createElement('div');
        card.className = 'bg-slate-800 border border-yellow-700/40 rounded-lg overflow-hidden';
        card.innerHTML = `
          <div class="flex items-center justify-between px-4 py-2 bg-yellow-900/20 cursor-pointer select-none"
               onclick="this.nextElementSibling.classList.toggle('hidden')">
            <span class="text-slate-200 text-xs truncate flex-1">${esc(file)}</span>
            <div class="flex items-center gap-2 ml-2 shrink-0">
              ${lang ? `<span class="text-slate-400 text-xs">${esc(lang)}</span>` : ''}
              <span class="bg-yellow-700/50 text-yellow-300 text-xs px-2 py-0.5 rounded-full">${matched.length} issue${matched.length>1?'s':''}</span>
              <span class="text-slate-400 text-xs">▼</span>
            </div>
          </div>
          <ul class="px-4 py-2 flex flex-col gap-1.5">
            ${matched.map((i, idx) => `
              <li class="flex items-start gap-2 text-xs" data-issue-key="${esc(file)}::${idx}">
                <span class="text-yellow-500 shrink-0 mt-0.5">${idx+1}.</span>
                <div class="flex-1 min-w-0">
                  <span class="text-yellow-200">${esc(i)}</span>
                  <div class="flex items-center gap-2 mt-1 flex-wrap">
                    <span class="assignee-badge hidden text-purple-400 text-xs"></span>
                    <span class="comment-count text-slate-500 text-xs"></span>
                  </div>
                  <div class="comment-thread mt-1 hidden flex flex-col gap-1"></div>
                  <button class="text-xs text-slate-500 hover:text-slate-300 mt-1" onclick="this.nextElementSibling.classList.toggle('hidden');this.classList.add('hidden')">💬 discuss / assign</button>
                  <div class="collab-panel hidden mt-1"></div>
                </div>
              </li>`).join('')}
          </ul>`;
        listContainer.appendChild(card);
      });
      document.getElementById('issueCount').textContent =
        `${shown} issues in ${listContainer.children.length} files`;
    }

    renderIssueList();
    document.getElementById('issueSearch').addEventListener('input', e => renderIssueList(e.target.value));
  }

  function renderFileTab(type, files) {
    const c = document.getElementById(`tab-${type}-content`);
    c.innerHTML = '';
    if (!files.length) {
      c.innerHTML = `<p class="text-slate-500 py-4">No ${type} files.</p>`; return;
    }
    files.forEach(f => {
      const hasIssues = f.issues && f.issues.length > 0;
      const border = type==='code' ? (hasIssues ? 'border-yellow-600/50' : 'border-green-700/40') : type==='docs' ? 'border-sky-700/40' : 'border-slate-700';
      const hbg    = type==='code' ? (hasIssues ? 'bg-yellow-900/20' : 'bg-green-900/20') : type==='docs' ? 'bg-sky-900/20' : 'bg-slate-800';
      const badge  = type==='code'
        ? (hasIssues ? `<span class="text-xs px-2 py-0.5 rounded-full bg-yellow-700/50 text-yellow-300">${f.issues.length} issue${f.issues.length>1?'s':''}</span>`
                     : `<span class="text-xs px-2 py-0.5 rounded-full bg-green-700/50 text-green-300">clean</span>`)
        : `<span class="text-xs px-2 py-0.5 rounded-full bg-slate-700 text-slate-300">${esc(f.ext||'?')}</span>`;

      const div = document.createElement('div');
      div.className = `bg-slate-800 border ${border} rounded-lg overflow-hidden`;
      div.innerHTML = `
        <div class="flex items-center justify-between px-4 py-2 ${hbg}">
          <span class="truncate text-slate-200">${esc(f.path)}</span>
          <div class="flex items-center gap-2 ml-3 shrink-0">
            ${f.language ? `<span class="text-slate-400 text-xs">${esc(f.language)}</span>` : ''}
            ${badge}
          </div>
        </div>
        ${hasIssues ? `<ul class="px-4 py-2 flex flex-col gap-1">
          ${f.issues.map(i=>`<li class="text-yellow-300 text-xs">⚠️ ${esc(i)}</li>`).join('')}
        </ul>` : ''}`;
      c.appendChild(div);
    });
  }

  function renderList(tab, items, tpl) {
    const c = document.getElementById(`tab-${tab}-content`);
    c.innerHTML = items.length
      ? items.map(tpl).join('')
      : `<p class="text-slate-500 py-4">No ${tab} found.</p>`;
  }

  //  tabs
  function showTab(tab) {
    ['code','warnings','docs','other','commits','prs'].forEach(t => {
      document.getElementById(`tab-${t}-content`).classList.toggle('hidden', t !== tab);
      const btn = document.getElementById(`tab-${t}`);
      btn.className = t === tab
        ? 'inner-tab active-tab px-4 py-2 rounded-t-lg'
        : 'inner-tab px-4 py-2 rounded-t-lg text-slate-400 hover:text-white transition';
    });
  }

  //history 
  async function loadHistory() {
    const token = getToken();
    if (!token) {
      document.getElementById('historyList').innerHTML =
        `<div class="text-center py-8 flex flex-col items-center gap-3">
          <p class="text-slate-500 text-sm">Sign in to view your history</p>
          <button onclick="openAuthModal()" class="bg-blue-600 hover:bg-blue-500 transition text-white text-xs px-4 py-2 rounded-lg">Sign in / Sign up</button>
        </div>`;
      return;
    }
    const res  = await fetch('/history', { headers: { 'Authorization': `Bearer ${token}` } });
    const data = await res.json();
    const list = document.getElementById('historyList');
    list.innerHTML = '';
    if (!data.length) {
      list.innerHTML = '<p class="text-slate-500">No history yet.</p>'; return;
    }
    data.forEach(h => {
      const div = document.createElement('div');
      div.className = 'bg-slate-800 border border-slate-700 rounded-lg px-4 py-3 flex items-center justify-between gap-4 cursor-pointer hover:border-blue-500 transition';
      div.innerHTML = `
        <div class="flex-1 min-w-0">
          <p class="text-blue-400 truncate">${esc(h.repo_url)}</p>
          <p class="text-slate-400 text-xs mt-0.5">🌿 ${esc(h.branch)} · 📁 ${h.summary.total} files · ⚠️ ${h.summary.issues} issues · ${h.id.slice(0,10)}</p>
        </div>
        <button class="text-xs bg-blue-700 hover:bg-blue-600 text-white px-3 py-1 rounded-lg transition shrink-0">Re-run</button>`;
      div.querySelector('button').onclick = () => {
        document.getElementById('repoUrl').value = h.repo_url;
        setView('analyze');
        analyze(h.branch);
      };
      list.appendChild(div);
    });
  }

  async function clearHistory() {
    const token = getToken();
    const headers = token ? { 'Authorization': `Bearer ${token}` } : {};
    await fetch('/history', { method: 'DELETE', headers });
    loadHistory();
  }

  // utils
  function setLoading(on) {
    document.getElementById('btnIcon').textContent = on ? '⏳' : '🚀';
    document.getElementById('btnText').textContent = on ? 'Analyzing...' : 'Analyze';
    const btn = document.getElementById('analyzeBtn') || document.querySelector('button[onclick="analyze()"]');
    if (btn) { btn.disabled = on; btn.classList.toggle('opacity-60', on); }
  }

  function showError(msg) {
    const b = document.getElementById('errorBox');
    b.textContent = msg;
    b.classList.toggle('hidden', !msg);
  }

  function get_score_color_class(score) {
    if (score >= 80) return 'text-green-400';
    if (score >= 50) return 'text-yellow-400';
    return 'text-red-400';
  }

  function esc(s) {
    return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
  }

  // ── Analytics ─────────────────────────────────────────────────────────────

  let trendChartInstance = null;

  async function loadAnalytics() {
    const token = getToken();
    if (!token) {
      document.getElementById('analyticsSignInPrompt').classList.remove('hidden');
      document.getElementById('analyticsEmpty').classList.add('hidden');
      document.getElementById('analyticsContent').classList.add('hidden');
      return;
    }

    document.getElementById('analyticsSignInPrompt').classList.add('hidden');

    try {
      const res = await fetch('/analytics/leaderboard', {
        headers: { 'Authorization': `Bearer ${token}` }
      });

      if (res.status === 401) {
        openAuthModal();
        return;
      }

      if (!res.ok) {
        document.getElementById('leaderboardError').textContent = `Failed to load leaderboard (${res.status})`;
        document.getElementById('leaderboardError').classList.remove('hidden');
        return;
      }

      const leaderboard = await res.json();

      if (!leaderboard.length) {
        document.getElementById('analyticsEmpty').classList.remove('hidden');
        document.getElementById('analyticsContent').classList.add('hidden');
        return;
      }

      document.getElementById('analyticsEmpty').classList.add('hidden');
      document.getElementById('analyticsContent').classList.remove('hidden');

      renderLeaderboard(leaderboard);
      populateRepoSelector(leaderboard);

      // Auto-load trend for first repo
      if (leaderboard.length) {
        loadTrend(leaderboard[0].repo_url);
      }

    } catch (e) {
      document.getElementById('leaderboardError').textContent = 'Network error loading analytics';
      document.getElementById('leaderboardError').classList.remove('hidden');
    }
  }

  function renderLeaderboard(data) {
    const tbody = document.getElementById('leaderboardTable');
    tbody.innerHTML = '';
    data.forEach((row, idx) => {
      const rank = idx + 1;
      const isTop = rank === 1;
      const tr = document.createElement('tr');
      tr.className = `border-b border-slate-700 hover:bg-slate-700/30 transition ${isTop ? 'bg-yellow-900/10' : ''}`;
      tr.innerHTML = `
        <td class="py-2 pr-4 ${isTop ? 'font-bold text-yellow-400' : 'text-slate-400'}">#${rank}</td>
        <td class="py-2 pr-4 text-slate-200 truncate overflow-hidden">${esc(row.repo_name)}</td>
        <td class="py-2 text-center font-bold ${get_score_color_class(row.latest_quality_score)}">${row.latest_quality_score}</td>
        <td class="py-2 text-center text-slate-400">${row.analyses_count}</td>
        <td class="py-2 text-center text-slate-500 text-xs">${row.last_analyzed.slice(0,10)}</td>`;
      tbody.appendChild(tr);
    });
  }

  function populateRepoSelector(leaderboard) {
    const sel = document.getElementById('repoSelector');
    sel.innerHTML = '';
    leaderboard.forEach(row => {
      const opt = document.createElement('option');
      opt.value = row.repo_url;
      opt.textContent = row.repo_name;
      sel.appendChild(opt);
    });
  }

  async function loadTrend(repoUrl) {
    const token = getToken();
    if (!token) return;

    document.getElementById('trendError').classList.add('hidden');
    document.getElementById('trendMessage').classList.add('hidden');
    document.getElementById('trendChartWrapper').classList.remove('hidden');

    try {
      const res = await fetch(`/analytics/trends?repo_url=${encodeURIComponent(repoUrl)}`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });

      if (res.status === 401) {
        openAuthModal();
        return;
      }

      if (!res.ok) {
        document.getElementById('trendError').textContent = `Failed to load trend (${res.status})`;
        document.getElementById('trendError').classList.remove('hidden');
        return;
      }

      const data = await res.json();

      if (data.length < 2) {
        document.getElementById('trendMessage').textContent = 'Run more analyses to see a trend';
        document.getElementById('trendMessage').classList.remove('hidden');
        document.getElementById('trendChartWrapper').classList.add('hidden');
        return;
      }

      renderTrendChart(data);

    } catch (e) {
      document.getElementById('trendError').textContent = 'Network error loading trend';
      document.getElementById('trendError').classList.remove('hidden');
    }
  }

  function renderTrendChart(data) {
    const canvas = document.getElementById('trendChart');
    const ctx = canvas.getContext('2d');

    // Destroy previous chart instance
    if (trendChartInstance) {
      trendChartInstance.destroy();
    }

    trendChartInstance = new Chart(ctx, {
      type: 'line',
      data: {
        labels: data.map(p => p.timestamp.slice(0,10)),
        datasets: [{
          label: 'Quality Score',
          data: data.map(p => p.quality_score),
          borderColor: '#3b82f6',
          backgroundColor: 'rgba(59, 130, 246, 0.1)',
          tension: 0.3,
          fill: true,
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          y: {
            beginAtZero: true,
            max: 100,
            ticks: { color: '#94a3b8' },
            grid: { color: '#334155' }
          },
          x: {
            ticks: { color: '#94a3b8' },
            grid: { color: '#334155' }
          }
        },
        plugins: {
          legend: { labels: { color: '#cbd5e1' } }
        }
      }
    });
  }

  document.getElementById('repoUrl').addEventListener('keydown', e => { if(e.key==='Enter') analyze(); });

  // ── Team Collaboration ─────────────────────────────────────────────────────

  // Share modal
  function openShareModal() {
    document.getElementById('shareModal').classList.remove('hidden');
    document.getElementById('shareEmailsInput').value = '';
    document.getElementById('shareError').classList.add('hidden');
  }

  function closeShareModal() {
    document.getElementById('shareModal').classList.add('hidden');
  }

  async function submitShare() {
    const raw = document.getElementById('shareEmailsInput').value.trim();
    const errEl = document.getElementById('shareError');
    errEl.classList.add('hidden');
    if (!raw) return;

    const emails = raw.split(',').map(e => e.trim()).filter(Boolean);
    const reportId = currentData && currentData.id;
    if (!reportId) { errEl.textContent = 'No report loaded.'; errEl.classList.remove('hidden'); return; }

    const res = await fetch(`/reports/${encodeURIComponent(reportId)}/share`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${authToken}` },
      body: JSON.stringify({ emails })
    });

    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      errEl.textContent = data.detail || `Error ${res.status}`;
      errEl.classList.remove('hidden');
      return;
    }

    closeShareModal();
  }

  // Shared with Me view
  async function loadSharedReports() {
    const prompt = document.getElementById('sharedSignInPrompt');
    const list   = document.getElementById('sharedList');

    if (!authToken) {
      prompt.style.display = '';
      list.innerHTML = '';
      return;
    }
    prompt.style.display = 'none';

    const res = await fetch('/shared-with-me', {
      headers: { 'Authorization': `Bearer ${authToken}` }
    });

    if (!res.ok) {
      list.innerHTML = `<p class="text-red-400 text-xs">Failed to load shared reports (${res.status})</p>`;
      return;
    }

    const items = await res.json();
    list.innerHTML = '';

    if (!items.length) {
      list.innerHTML = '<p class="text-slate-500 text-sm py-8 text-center">No reports have been shared with you yet.</p>';
      return;
    }

    items.forEach(item => {
      const scoreColor = item.quality_score >= 80 ? 'text-green-400' : item.quality_score >= 50 ? 'text-yellow-400' : 'text-red-400';
      const div = document.createElement('div');
      div.className = 'bg-slate-800 border border-slate-700 rounded-lg px-4 py-3 flex items-center justify-between gap-4';
      div.innerHTML = `
        <div class="flex-1 min-w-0">
          <p class="text-blue-400 truncate text-sm">${esc(item.repo_url)}</p>
          <p class="text-slate-400 text-xs mt-0.5">🌿 ${esc(item.branch)} · shared by ${esc(item.owner_email)} · ${item.shared_at.slice(0,10)}</p>
        </div>
        <div class="flex items-center gap-3 shrink-0">
          <span class="font-bold text-sm ${scoreColor}">${item.quality_score}</span>
          <button class="text-xs bg-blue-700 hover:bg-blue-600 text-white px-3 py-1 rounded-lg transition">View</button>
        </div>`;
      div.querySelector('button').onclick = () => {
        document.getElementById('repoUrl').value = item.repo_url;
        setView('analyze');
        analyze(item.branch);
      };
      list.appendChild(div);
    });
  }

  // Load comments and assignments for a report
  async function loadCommentsAndAssignments(reportId) {
    if (!authToken) return;

    const [cRes, aRes] = await Promise.all([
      fetch(`/reports/${encodeURIComponent(reportId)}/comments`, { headers: { 'Authorization': `Bearer ${authToken}` } }),
      fetch(`/reports/${encodeURIComponent(reportId)}/assignments`, { headers: { 'Authorization': `Bearer ${authToken}` } })
    ]);

    const comments    = cRes.ok    ? await cRes.json()    : [];
    const assignments = aRes.ok    ? await aRes.json()    : [];

    // Index by file_path + issue_index
    const commentMap    = {};
    const assignmentMap = {};

    comments.forEach(c => {
      const key = `${c.file_path}::${c.issue_index}`;
      if (!commentMap[key]) commentMap[key] = [];
      commentMap[key].push(c);
    });

    assignments.forEach(a => {
      assignmentMap[`${a.file_path}::${a.issue_index}`] = a;
    });

    // Inject into rendered issue cards
    document.querySelectorAll('[data-issue-key]').forEach(card => {
      const key = card.dataset.issueKey;
      const assignment = assignmentMap[key];
      const cardComments = commentMap[key] || [];

      const assigneeEl = card.querySelector('.assignee-badge');
      if (assigneeEl) {
        assigneeEl.textContent = assignment ? `👤 ${assignment.assignee_email}` : '';
        assigneeEl.classList.toggle('hidden', !assignment);
      }

      const countEl = card.querySelector('.comment-count');
      if (countEl) countEl.textContent = cardComments.length ? `💬 ${cardComments.length}` : '';

      const threadEl = card.querySelector('.comment-thread');
      if (threadEl) renderCommentThread(threadEl, reportId, key, cardComments);
    });
  }

  function renderCommentThread(container, reportId, issueKey, comments) {
    const [filePath, issueIndex] = issueKey.split('::');
    container.innerHTML = '';

    comments.forEach(c => {
      const div = document.createElement('div');
      div.className = 'flex items-start gap-2 text-xs py-1 border-b border-slate-700';
      div.dataset.commentId = c.comment_id;
      div.innerHTML = `
        <div class="flex-1 min-w-0">
          <span class="text-blue-400 font-medium">${esc(c.author_email)}</span>
          <span class="text-slate-500 ml-1">${c.created_at.slice(0,10)}</span>
          <p class="text-slate-300 mt-0.5">${esc(c.text)}</p>
        </div>
        ${c.author_email === authEmail ? `<button onclick="deleteComment('${reportId}','${c.comment_id}',this)" class="text-red-400 hover:text-red-300 shrink-0 text-xs">✕</button>` : ''}`;
      container.appendChild(div);
    });

    // New comment input
    const form = document.createElement('div');
    form.className = 'flex gap-2 mt-2';
    form.innerHTML = `
      <input type="text" placeholder="Add a comment..." class="flex-1 bg-slate-700 border border-slate-600 rounded px-2 py-1 text-xs text-white placeholder-slate-500 focus:outline-none focus:ring-1 focus:ring-blue-500"/>
      <button class="text-xs bg-blue-600 hover:bg-blue-500 text-white px-2 py-1 rounded transition">Post</button>`;
    const input = form.querySelector('input');
    form.querySelector('button').onclick = () => postComment(reportId, filePath, parseInt(issueIndex), input.value, container, issueKey);
    container.appendChild(form);

    // Assign input
    const assignForm = document.createElement('div');
    assignForm.className = 'flex gap-2 mt-1';
    assignForm.innerHTML = `
      <input type="text" placeholder="Assign to email..." class="flex-1 bg-slate-700 border border-slate-600 rounded px-2 py-1 text-xs text-white placeholder-slate-500 focus:outline-none focus:ring-1 focus:ring-purple-500"/>
      <button class="text-xs bg-purple-600 hover:bg-purple-500 text-white px-2 py-1 rounded transition">Assign</button>`;
    const assignInput = assignForm.querySelector('input');
    assignForm.querySelector('button').onclick = () => assignIssue(reportId, filePath, parseInt(issueIndex), assignInput.value, container.closest('[data-issue-key]'));
    container.appendChild(assignForm);
  }

  async function postComment(reportId, filePath, issueIndex, text, container, issueKey) {
    if (!text.trim()) return;
    const res = await fetch(`/reports/${encodeURIComponent(reportId)}/comments`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${authToken}` },
      body: JSON.stringify({ file_path: filePath, issue_index: issueIndex, text })
    });
    if (!res.ok) return;
    const comment = await res.json();
    // Re-render thread
    const allComments = [...container.querySelectorAll('[data-comment-id]')].map(el => ({
      comment_id: el.dataset.commentId,
      author_email: el.querySelector('.text-blue-400').textContent,
      created_at: el.querySelector('.text-slate-500').textContent,
      text: el.querySelector('.text-slate-300').textContent
    }));
    allComments.push(comment);
    renderCommentThread(container, reportId, issueKey, allComments);
    // Update count badge
    const card = container.closest('[data-issue-key]');
    if (card) {
      const countEl = card.querySelector('.comment-count');
      if (countEl) countEl.textContent = `💬 ${allComments.length}`;
    }
  }

  async function deleteComment(reportId, commentId, btn) {
    const res = await fetch(`/reports/${encodeURIComponent(reportId)}/comments/${commentId}`, {
      method: 'DELETE',
      headers: { 'Authorization': `Bearer ${authToken}` }
    });
    if (res.ok) {
      const row = btn.closest('[data-comment-id]');
      if (row) row.remove();
    }
  }

  async function assignIssue(reportId, filePath, issueIndex, email, card) {
    if (!email.trim()) return;
    const res = await fetch(`/reports/${encodeURIComponent(reportId)}/assignments`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${authToken}` },
      body: JSON.stringify({ file_path: filePath, issue_index: issueIndex, assignee_email: email })
    });
    if (!res.ok) return;
    if (card) {
      const badge = card.querySelector('.assignee-badge');
      if (badge) { badge.textContent = `👤 ${email}`; badge.classList.remove('hidden'); }
    }
  }
