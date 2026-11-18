/**
 * PokéDrop Watch verification-code backend.
 * Deploy as a Google Apps Script web app owned by pokedropwatch.notify@gmail.com.
 * No Google Sheet is used: subscriber records are written directly to Firestore
 * through the Firestore REST API using the private service-account JSON.
 *
 * This is the COMPLETE Code.gs file. Replace the entire Apps Script Code.gs
 * contents with this file; do not paste individual function fragments.
 */
const OTP_TTL_SECONDS = 600;
const OTP_MAX_ATTEMPTS = 5;
const EMAIL_COOLDOWN_SECONDS = 60;
const EMAIL_MAX_PER_HOUR = 3;
const EMAIL_DAILY_CAP = 25;
const CATEGORIES = ['tcg', 'plush', 'collectibles', 'games', 'accessories', 'news'];
const RETAILERS = ['all', 'pokemon-center', 'target', 'walmart', 'best-buy', 'gamestop', 'amazon', 'pokebeach'];

function doGet(e) {
  const page = String(e && e.parameter && e.parameter.page || '').trim().toLowerCase();
  if (page === 'admin') {
    const admin = HtmlService.createHtmlOutputFromFile('Admin');
    return pokedropPortalOutput_(admin, 'PokéDrop Watch · Gym Leader', 'admin');
  }
  if (page === 'subscribe' || page === 'notify') {
    const notify = HtmlService.createHtmlOutputFromFile('Subscribe');
    return pokedropPortalOutput_(notify, 'PokéDrop Watch · Pokémon Center', 'notify');
  }

  const props = PropertiesService.getScriptProperties();
  const template = HtmlService.createTemplateFromFile('Index');
  template.siteOrigin = props.getProperty('SITE_ORIGIN') || 'https://n0nam3-bot.github.io';
  return template.evaluate()
    .setTitle('PokéDrop Watch Verification')
    .setXFrameOptionsMode(HtmlService.XFrameOptionsMode.ALLOWALL);
}

/**
 * Applies the page-specific 8-bit cursor, click-to-throw animation, and the
 * final form/admin layout directly to the HTML returned inside GitHub Pages.
 * The outer website owns the page header and bottom navigation.
 */
function pokedropPortalOutput_(sourceOutput, title, page) {
  const assetRoot = 'https://n0nam3-bot.github.io/PokeDropWatch/assets/icons/';
  const cursorFile = page === 'admin' ? 'masterball-8bit.png' : 'ultraball-8bit.png';
  const cursorData = page === 'admin'
    ? 'data:image/png;base64,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'
    : 'data:image/png;base64,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';
  const cursorCss = `
    <style>
      @font-face {
        font-family: "PKMN RBYGSC";
        src: url("https://n0nam3-bot.github.io/PokeDropWatch/assets/fonts/PKMN-RBYGSC.ttf") format("truetype");
        font-style: normal;
        font-weight: 400;
        font-display: swap;
      }
      :root { --pd-portal-asset-root: "${assetRoot}"; }
      html, body, body *, body *::before, body *::after, body *::placeholder {
        font-family: "PKMN RBYGSC", "Courier New", monospace !important;
      }
      html, body, body * {
        cursor: url("${cursorData}") 8 8, auto !important;
      }
      input, textarea, select, [contenteditable="true"] { cursor: text !important; }
      [hidden] { display:none !important; }
      .honeypot { position:absolute !important; left:-10000px !important; top:auto !important; width:1px !important; height:1px !important; overflow:hidden !important; }
      .pd-help-guide { margin:18px 0 20px; border:1px solid #e9e8e3; border-radius:10px; background:#fff; box-shadow:0 12px 30px rgba(28,28,24,.055); }
      .pd-help-guide summary { padding:14px 17px; cursor:pointer; list-style:none; font-size:11px; font-weight:800; color:#4b4c46; }
      .pd-help-guide summary::-webkit-details-marker { display:none; }
      .pd-help-guide summary:after { content:'＋'; float:right; color:#c83232; }
      .pd-help-guide[open] summary:after { content:'−'; }
      .pd-help-content { padding:0 17px 16px; border-top:1px solid #e9e8e3; }
      .pd-help-content h2 { margin:14px 0 6px; font-size:15px; line-height:1.45; }
      .pd-help-content p,.pd-help-content li { color:#686961; font-size:10px; line-height:1.7; }
      .pd-help-content ul { margin:7px 0; padding-left:19px; }
      .pd-help-content a { color:#c83232; font-weight:800; }
      body.page-notify .layout { grid-template-columns:minmax(0,1fr) !important; }
      body.page-notify .panel { min-width:0; }
      body.page-notify #verificationPanel { margin-top:12px; }
      body.page-notify #verificationPanel:focus-within { scroll-margin:18px; }
      body.page-notify .intro p { max-width:760px; }
      body.page-admin .wrap { width:min(100% - 40px,1120px); }
      body.page-admin #loginStatus:empty { display:none; }
      .pd-throw-ball { position:fixed; z-index:99999; left:0; top:0; width:36px; height:36px; object-fit:contain; image-rendering:pixelated; pointer-events:none; opacity:0; filter:drop-shadow(0 3px 0 rgba(0,0,0,.3)); }
      .pd-throw-ball.is-throwing { opacity:1; animation:pd-ball-flight .72s cubic-bezier(.16,.72,.25,1) forwards; }
      @keyframes pd-ball-flight {
        0% { transform:translate3d(0,0,0) rotate(0deg) scale(1); opacity:1; }
        60% { transform:translate3d(var(--pd-dx),var(--pd-dy),0) rotate(440deg) scale(.92); opacity:1; }
        74% { transform:translate3d(calc(var(--pd-dx) - 3px),calc(var(--pd-dy) + 8px),0) rotate(500deg) scale(.9); opacity:1; }
        84% { transform:translate3d(var(--pd-dx),var(--pd-dy),0) rotate(540deg) scale(.82); opacity:1; }
        100% { transform:translate3d(var(--pd-dx),var(--pd-dy),0) rotate(560deg) scale(.45); opacity:0; }
      }
      .pd-capture-flash { position:fixed; z-index:99998; width:20px; height:20px; border:3px solid rgba(255,255,255,.9); border-radius:50%; transform:translate(-50%,-50%) scale(.2); opacity:0; pointer-events:none; animation:pd-capture-flash .46s ease-out .46s forwards; }
      @keyframes pd-capture-flash { 0% { transform:translate(-50%,-50%) scale(.2); opacity:.95; } 100% { transform:translate(-50%,-50%) scale(3.4); opacity:0; } }
      @media(max-width:620px) { .pd-help-guide summary { padding:12px 13px; } .pd-help-content { padding:0 13px 13px; } }
      @media(prefers-reduced-motion:reduce) { .pd-throw-ball { animation:none !important; } }
    </style>
  `;

  let html = sourceOutput.getContent();
  if (page === 'admin') {
    // Remove legacy branding/footer and the administrator setup hint.
    html = html.replace(/<header class="top">[\s\S]*?<\/header>/i, '');
    html = html.replace(
      '<p class="foot">PokéDrop Watch · Administrator sessions expire after one hour.</p>',
      '<p class="foot">Administrator sessions expire after one hour.</p>'
    );
    html = html.replace('Use the administrator credentials configured in Apps Script.', '');

    const adminGuide = `
      <details class="pd-help-guide">
        <summary>How administrator tools work</summary>
        <div class="pd-help-content">
          <h2>Reviewing applications</h2>
          <p>Only visitors who verify their email address appear as applications. New applications start as <strong>Pending</strong>; they do not receive alert emails until approved.</p>
          <ul>
            <li><strong>Approve</strong> activates a pending application.</li>
            <li><strong>Reject</strong> closes a pending application without enabling alerts.</li>
            <li><strong>Suspend</strong> pauses an active subscription; <strong>Reactivate</strong> turns it back on.</li>
            <li><strong>Remove</strong> marks a record as removed from the notification list.</li>
          </ul>
          <h2>Subscriber preferences</h2>
          <p>Each application stores the product categories and retailer/source choices made during signup. Active subscribers are matched against those preferences before an alert email is sent.</p>
          <h2>Security and sessions</h2>
          <p>Administrator sign-in and subscriber changes run through the private Apps Script backend. Firestore service-account credentials stay on the server. Administrator sessions expire after one hour.</p>
          <p><a href="https://n0nam3-bot.github.io/PokeDropWatch/SOURCE_HEALTH.html" target="_top">Read the full PokéDrop Watch guide ↗</a></p>
        </div>
      </details>`;
    if (html.indexOf('pd-help-guide') < 0) {
      html = html.replace(/(<section class="hero">[\s\S]*?<\/section>)/i, '$1' + adminGuide);
    }
    html = html.replace(/<body([^>]*)>/i, function (_match, attrs) {
      attrs = attrs.replace(/\sclass=(["'])[^"']*\1/i, '');
      return '<body class="page-admin"' + attrs + '>';
    });
  } else {
    // Remove the invisible label and its empty space but preserve the honeypot input.
    html = html.replace(
      /<label class="honeypot"[^>]*>[\s\S]*?<input([^>]*)>[\s\S]*?<\/label>/i,
      '<div class="honeypot" aria-hidden="true"><input id="websiteTrap" type="text" tabindex="-1" autocomplete="off"></div>'
    );

    // Place code entry immediately below the main application request button.
    const codePanelMatch = html.match(/<section id="verificationPanel"[\s\S]*?<\/section>/i);
    if (codePanelMatch) {
      const codePanel = codePanelMatch[0];
      html = html.replace(codePanel, '');
      html = html.replace(/(<\/form>\s*)(<div class="divider">)/i, '$1' + codePanel + '\n\n        $2');
    }

    // Use first-person confirmation copy; do not mention Google Apps Script to applicants.
    html = html.replace('Google Apps Script accepted the email request for ', 'Accepted the email request for ');
    html = html.replace('Google Apps Script accepted the verification email request. Check your inbox and spam folder.', 'Email request accepted. Check your inbox and spam folder.');
    html = html.replace('Google Apps Script sends a one-time code, and your application is saved only after you enter it.', 'A one-time code is sent to your mailbox, and your application is saved only after you enter it.');
    html = html.replace('Sending the verification request directly to Google Apps Script…', 'Sending your verification email…');
    html = html.replace('Ready. Submitting this form sends the request directly to Google Apps Script.', 'Ready. Enter your email address and choose what you want to follow.');
    // Reposition the shared code panel beneath the button for whichever form requested a code.
    html = html.replace("$('verificationPanel').hidden = false;", function () {
      return "const codePanel = $('verificationPanel'); const requestForm = flow.operation === 'unsubscribe' ? $('unsubscribeForm') : $('subscribeForm'); requestForm.insertAdjacentElement('afterend', codePanel); codePanel.hidden = false;";
    });

    // Replace the old dark HOW IT WORKS aside with a practical collapsible guide below the form.
    html = html.replace(/<aside class="panel side">[\s\S]*?<\/aside>/i, '');
    const notifyGuide = `
      <details class="pd-help-guide">
        <summary>How notifications work</summary>
        <div class="pd-help-content">
          <h2>Choose what to follow</h2>
          <p>Select one or more product categories and retailer/news sources. <strong>All retailers</strong> overrides individual retailer choices.</p>
          <h2>Verify your email</h2>
          <p>Request a six-digit code. It is sent to the mailbox you entered, expires after 10 minutes, and can only be used once. The code entry panel appears directly beneath the application button.</p>
          <h2>Application review</h2>
          <p>After the code is accepted, your application is saved with <strong>Pending</strong> status. An administrator must approve it before email alerts begin. Only <strong>Active</strong> subscribers receive matching notifications.</p>
          <h2>Unsubscribing</h2>
          <p>Use the secure unsubscribe form and verify that you control the mailbox before the subscription is changed.</p>
          <p><a href="https://n0nam3-bot.github.io/PokeDropWatch/SOURCE_HEALTH.html" target="_top">See how scans, alerts, and source statuses work ↗</a></p>
        </div>
      </details>`;
    if (html.indexOf('pd-help-guide') < 0) {
      html = html.replace(/<p class="footnote">/i, notifyGuide + '\n    <p class="footnote">');
    }
    html = html.replace(/<body([^>]*)>/i, function (_match, attrs) {
      attrs = attrs.replace(/\sclass=(["'])[^"']*\1/i, '');
      return '<body class="page-notify"' + attrs + '>';
    });
  }

  const throwSprite = page === 'admin' ? 'masterball-8bit.png' : 'ultraball-8bit.png';
  const throwScript = `
    <script>
      (() => {
        const sprite = "${assetRoot}${throwSprite}";
        const reduced = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
        document.addEventListener('pointerdown', event => {
          if (reduced || (event.pointerType === 'mouse' && event.button !== 0)) return;
          if (event.target && event.target.closest('input,textarea,select,option,[contenteditable="true"]')) return;
          const sx = Math.round(window.innerWidth * .5 - 18);
          const sy = Math.round(window.innerHeight + 18);
          const ball = document.createElement('img');
          ball.className = 'pd-throw-ball'; ball.src = sprite; ball.alt = ''; ball.setAttribute('aria-hidden','true');
          ball.style.left = sx + 'px'; ball.style.top = sy + 'px';
          ball.style.setProperty('--pd-dx', (Math.round(event.clientX)-sx) + 'px');
          ball.style.setProperty('--pd-dy', (Math.round(event.clientY)-sy) + 'px');
          document.body.append(ball); requestAnimationFrame(() => ball.classList.add('is-throwing'));
          const flash = document.createElement('span'); flash.className = 'pd-capture-flash';
          flash.style.left = Math.round(event.clientX) + 'px'; flash.style.top = Math.round(event.clientY) + 'px';
          document.body.append(flash); setTimeout(() => { ball.remove(); flash.remove(); }, 1550);
        }, { passive:true });
      })();
    </script>`;
  html = html.replace('</head>', cursorCss + '</head>');
  html = html.replace('</body>', throwScript + '</body>');

  return HtmlService.createHtmlOutput(html)
    .setTitle(title)
    .setXFrameOptionsMode(HtmlService.XFrameOptionsMode.ALLOWALL);
}

// Run this once from the Apps Script editor as the notification Gmail account
// to grant MailApp and UrlFetchApp permissions before publishing the web app.
function authorizeOwnerAccess() {
  const remaining = MailApp.getRemainingDailyQuota();
  UrlFetchApp.fetch('https://www.google.com/generate_204', { muteHttpExceptions: true });
  return 'Authorization complete. Remaining daily email recipients: ' + remaining;
}

// Public google.script.run endpoint. Helpers are suffixed with _ and are not
// exposed as callable client functions by Apps Script.
function requestVerificationCode(payload) {
  try {
    const input = validateRequest_(payload);
    const props = PropertiesService.getScriptProperties();
    const cache = CacheService.getScriptCache();
    const secret = requiredProperty_('EMAIL_HMAC_SECRET');
    const emailHash = hmacHex_(input.email, secret);
    enforceRateLimit_(emailHash, cache, props);

    const token = Utilities.getUuid().replace(/-/g, '');
    const code = makeCode_(secret, token);
    const codeHash = hmacHex_(token + ':' + code, secret);
    const session = {
      email: input.email,
      emailHash: emailHash,
      operation: input.operation,
      categories: input.categories,
      retailers: input.retailers,
      codeHash: codeHash,
      attempts: 0,
      createdAt: Date.now(),
      expiresAt: Date.now() + OTP_TTL_SECONDS * 1000
    };

    const previousToken = cache.get('otp_latest_' + emailHash);
    if (previousToken) cache.remove('otp_session_' + previousToken);
    cache.put('otp_session_' + token, JSON.stringify(session), OTP_TTL_SECONDS);
    cache.put('otp_latest_' + emailHash, token, OTP_TTL_SECONDS);

    sendVerificationEmail_(input.email, code, input.operation);
    return {
      ok: true,
      sessionToken: token,
      message: 'A six-digit verification code has been sent. Enter it on this page within 10 minutes.'
    };
  } catch (error) {
    console.error('requestVerificationCode failed: ' + safeError_(error));
    return { ok: false, message: publicError_(error) };
  }
}

function verifyVerificationCode(payload) {
  try {
    const token = String(payload && payload.sessionToken || '').trim();
    const code = String(payload && payload.code || '').replace(/\s/g, '');
    if (!/^[a-f0-9]{32}$/.test(token)) throw new Error('The verification session is invalid. Request a new code.');
    if (!/^\d{6}$/.test(code)) throw new Error('Enter the six-digit code from the email.');

    const cache = CacheService.getScriptCache();
    const raw = cache.get('otp_session_' + token);
    if (!raw) throw new Error('That code expired or was already used. Request a new code.');
    const session = JSON.parse(raw);
    const remainingSeconds = Math.ceil((Number(session.expiresAt || 0) - Date.now()) / 1000);
    if (remainingSeconds <= 0) {
      cache.remove('otp_session_' + token);
      cache.remove('otp_latest_' + session.emailHash);
      throw new Error('That code expired or was already used. Request a new code.');
    }
    const secret = requiredProperty_('EMAIL_HMAC_SECRET');
    const expected = hmacHex_(token + ':' + code, secret);
    if (expected !== session.codeHash) {
      session.attempts = Number(session.attempts || 0) + 1;
      if (session.attempts >= OTP_MAX_ATTEMPTS) {
        cache.remove('otp_session_' + token);
        cache.remove('otp_latest_' + session.emailHash);
      } else {
        cache.put('otp_session_' + token, JSON.stringify(session), remainingSeconds);
      }
      throw new Error(session.attempts >= OTP_MAX_ATTEMPTS
        ? 'Too many incorrect codes. Request a new code.'
        : 'That code is incorrect. Check the email and try again.');
    }

    const latest = cache.get('otp_latest_' + session.emailHash);
    if (latest !== token) throw new Error('A newer code was requested. Use the newest email.');
    cache.remove('otp_session_' + token);
    cache.remove('otp_latest_' + session.emailHash);

    let message;
    if (session.operation === 'subscribe') {
      message = saveSubscription_(session);
    } else if (session.operation === 'unsubscribe') {
      message = unsubscribeSubscription_(session);
    } else {
      throw new Error('Unsupported verification action.');
    }
    return { ok: true, message: message };
  } catch (error) {
    console.error('verifyVerificationCode failed: ' + safeError_(error));
    return { ok: false, message: publicError_(error) };
  }
}

/**
 * Initialize the administrator password exactly once from the Apps Script editor.
 * Required Script Properties: ADMIN_EMAIL, ADMIN_INITIAL_PASSWORD,
 * ADMIN_PASSWORD_PEPPER. The plaintext initial password is deleted after hashing.
 */
function initializeAdminCredentials() {
  const props = PropertiesService.getScriptProperties();
  const email = String(props.getProperty('ADMIN_EMAIL') || '').trim().toLowerCase();
  const initialPassword = String(props.getProperty('ADMIN_INITIAL_PASSWORD') || '');
  const pepper = String(props.getProperty('ADMIN_PASSWORD_PEPPER') || '');
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) throw new Error('Set ADMIN_EMAIL to the administrator email address first.');
  if (initialPassword.length < 12) throw new Error('ADMIN_INITIAL_PASSWORD must contain at least 12 characters.');
  if (pepper.length < 32) throw new Error('ADMIN_PASSWORD_PEPPER must be a random secret of at least 32 characters.');
  props.setProperty('ADMIN_PASSWORD_HASH', hmacHex_(initialPassword, pepper));
  props.setProperty('ADMIN_SESSION_VERSION', '1');
  props.setProperty('ADMIN_CREDENTIALS_INITIALIZED_AT', new Date().toISOString());
  props.deleteProperty('ADMIN_INITIAL_PASSWORD');
  return 'Administrator credentials initialized. The plaintext initial password property was deleted.';
}

function adminLogin(payload) {
  try {
    const input = payload || {};
    const email = String(input.email || '').trim().toLowerCase();
    const password = String(input.password || '');
    const props = PropertiesService.getScriptProperties();
    const configuredEmail = String(props.getProperty('ADMIN_EMAIL') || '').trim().toLowerCase();
    const storedHash = String(props.getProperty('ADMIN_PASSWORD_HASH') || '');
    const pepper = requiredProperty_('ADMIN_PASSWORD_PEPPER');
    if (!configuredEmail || !storedHash) throw new Error('Administrator login has not been initialized. Open owner-docs/SETUP.md.');
    if (email.length > 254 || password.length > 128) throw new Error('Email or password is incorrect.');

    const cache = CacheService.getScriptCache();
    const failureKey = 'admin_login_' + hmacHex_(email || 'empty', pepper).slice(0, 32);
    const failure = JSON.parse(cache.get(failureKey) || '{"count":0,"lockedUntil":0}');
    if (Number(failure.lockedUntil || 0) > Date.now()) {
      throw new Error('Too many sign-in attempts. Wait 15 minutes before trying again.');
    }

    const suppliedHash = hmacHex_(password, pepper);
    const valid = email === configuredEmail && timingSafeEqual_(suppliedHash, storedHash);
    if (!valid) {
      const count = Number(failure.count || 0) + 1;
      const next = count >= 5 ? { count: 0, lockedUntil: Date.now() + 15 * 60 * 1000 } : { count: count, lockedUntil: 0 };
      cache.put(failureKey, JSON.stringify(next), 900);
      throw new Error('Email or password is incorrect.');
    }

    cache.remove(failureKey);
    const token = Utilities.getUuid().replace(/-/g, '') + Utilities.getUuid().replace(/-/g, '');
    const version = String(props.getProperty('ADMIN_SESSION_VERSION') || '1');
    cache.put('admin_session_' + hmacHex_(token, pepper), JSON.stringify({ email: configuredEmail, version: version }), 3600);
    return { ok: true, sessionToken: token, email: configuredEmail, expiresIn: 3600 };
  } catch (error) {
    console.error('adminLogin failed: ' + safeError_(error));
    return { ok: false, message: publicAdminError_(error) };
  }
}

function adminListSubscribers(payload) {
  try {
    const session = requireAdminSession_(payload && payload.sessionToken);
    const records = firestoreListSubscribers_();
    records.sort((a, b) => String(b.createdAt || '').localeCompare(String(a.createdAt || '')));
    return { ok: true, email: session.email, subscribers: records.slice(0, 2000) };
  } catch (error) {
    console.error('adminListSubscribers failed: ' + safeError_(error));
    return { ok: false, message: publicAdminError_(error) };
  }
}

function adminUpdateSubscriber(payload) {
  try {
    requireAdminSession_(payload && payload.sessionToken);
    const uid = String(payload && payload.uid || '').trim();
    const status = String(payload && payload.status || '').trim();
    const note = String(payload && payload.note || '').trim().slice(0, 240);
    if (!/^[A-Za-z0-9_-]{1,160}$/.test(uid)) throw new Error('Invalid subscriber record.');
    if (!['pending', 'active', 'suspended', 'rejected', 'unsubscribed', 'removed'].includes(status)) throw new Error('Invalid subscriber status.');
    firestorePatchSubscriber_(uid, {
      status: status,
      adminNote: note,
      adminActionAt: new Date().toISOString(),
      updatedAt: new Date().toISOString()
    });
    return { ok: true, message: 'Subscriber status updated.' };
  } catch (error) {
    console.error('adminUpdateSubscriber failed: ' + safeError_(error));
    return { ok: false, message: publicAdminError_(error) };
  }
}

function adminLogout(payload) {
  try {
    const token = String(payload && payload.sessionToken || '');
    const pepper = requiredProperty_('ADMIN_PASSWORD_PEPPER');
    if (token) CacheService.getScriptCache().remove('admin_session_' + hmacHex_(token, pepper));
    return { ok: true };
  } catch (_error) {
    return { ok: true };
  }
}

function requestAdminPasswordReset(payload) {
  try {
    const email = String(payload && payload.email || '').trim().toLowerCase();
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email) || email.length > 254) {
      throw new Error('Enter a valid administrator email address.');
    }
    const props = PropertiesService.getScriptProperties();
    const configuredEmail = String(props.getProperty('ADMIN_EMAIL') || '').trim().toLowerCase();
    const pepper = requiredProperty_('ADMIN_PASSWORD_PEPPER');
    const token = Utilities.getUuid().replace(/-/g, '') + Utilities.getUuid().replace(/-/g, '');
    const validAccount = email === configuredEmail && Boolean(props.getProperty('ADMIN_PASSWORD_HASH'));
    const cache = CacheService.getScriptCache();
    const session = {
      email: email,
      emailHash: hmacHex_(email, pepper),
      validAccount: validAccount,
      attempts: 0,
      createdAt: Date.now(),
      expiresAt: Date.now() + OTP_TTL_SECONDS * 1000
    };
    if (validAccount) {
      enforceRateLimit_(session.emailHash, cache, props);
      const latestKey = 'admin_reset_latest_' + session.emailHash;
      const previousToken = cache.get(latestKey);
      if (previousToken) cache.remove('admin_reset_' + hmacHex_(previousToken, pepper));
      const code = makeCode_(pepper, token);
      session.codeHash = hmacHex_(token + ':' + code, pepper);
      // Store before sending so a successful email always has a corresponding
      // one-time session, while a failed send is cleaned up below.
      const resetKey = 'admin_reset_' + hmacHex_(token, pepper);
      cache.put(resetKey, JSON.stringify(session), OTP_TTL_SECONDS);
      cache.put(latestKey, token, OTP_TTL_SECONDS);
      try {
        sendVerificationEmail_(email, code, 'admin_reset');
      } catch (mailError) {
        cache.remove(resetKey);
        cache.remove(latestKey);
        throw mailError;
      }
      return {
        ok: true,
        sessionToken: token,
        message: 'If this address is the configured administrator account, a reset code has been sent. Enter it here with your new password.'
      };
    }
    // Return the same response without sending mail to avoid disclosing which
    // address is configured as the administrator.
    cache.put('admin_reset_' + hmacHex_(token, pepper), JSON.stringify(session), OTP_TTL_SECONDS);
    return {
      ok: true,
      sessionToken: token,
      message: 'If this address is the configured administrator account, a reset code has been sent. Enter it here with your new password.'
    };
  } catch (error) {
    console.error('requestAdminPasswordReset failed: ' + safeError_(error));
    return { ok: false, message: publicAdminError_(error) };
  }
}

function completeAdminPasswordReset(payload) {
  try {
    const token = String(payload && payload.sessionToken || '').trim();
    const code = String(payload && payload.code || '').replace(/\s/g, '');
    const newPassword = String(payload && payload.newPassword || '');
    if (!/^[a-f0-9]{64}$/.test(token)) throw new Error('Request a new administrator reset code.');
    if (!/^\d{6}$/.test(code)) throw new Error('Enter the six-digit code from the email.');
    if (newPassword.length < 12 || newPassword.length > 128) throw new Error('Use a new password containing 12 to 128 characters.');
    const pepper = requiredProperty_('ADMIN_PASSWORD_PEPPER');
    const cache = CacheService.getScriptCache();
    const key = 'admin_reset_' + hmacHex_(token, pepper);
    const raw = cache.get(key);
    if (!raw) throw new Error('That reset code expired or was already used. Request a new one.');
    const session = JSON.parse(raw);
    const remainingSeconds = Math.ceil((Number(session.expiresAt || 0) - Date.now()) / 1000);
    const latestKey = session.emailHash ? 'admin_reset_latest_' + session.emailHash : '';
    const isLatest = latestKey && cache.get(latestKey) === token;
    if (remainingSeconds <= 0 || !isLatest) {
      cache.remove(key);
      if (latestKey) cache.remove(latestKey);
      throw new Error('That reset code expired or was replaced by a newer request. Request a new code.');
    }
    const expected = hmacHex_(token + ':' + code, pepper);
    if (!session.validAccount || !session.codeHash || !timingSafeEqual_(expected, session.codeHash)) {
      session.attempts = Number(session.attempts || 0) + 1;
      if (session.attempts >= OTP_MAX_ATTEMPTS) {
        cache.remove(key);
        if (latestKey) cache.remove(latestKey);
      } else {
        cache.put(key, JSON.stringify(session), remainingSeconds);
      }
      throw new Error(session.attempts >= OTP_MAX_ATTEMPTS
        ? 'Too many incorrect codes. Request a new reset code.'
        : 'The code is invalid or expired. Check the email and try again.');
    }
    const props = PropertiesService.getScriptProperties();
    props.setProperty('ADMIN_PASSWORD_HASH', hmacHex_(newPassword, pepper));
    props.setProperty('ADMIN_PASSWORD_CHANGED_AT', new Date().toISOString());
    props.setProperty('ADMIN_SESSION_VERSION', String(Number(props.getProperty('ADMIN_SESSION_VERSION') || 1) + 1));
    cache.remove(key);
    if (latestKey) cache.remove(latestKey);
    return { ok: true, message: 'Administrator password changed. Return to the login form and sign in with the new password.' };
  } catch (error) {
    console.error('completeAdminPasswordReset failed: ' + safeError_(error));
    return { ok: false, message: publicAdminError_(error) };
  }
}

function requireAdminSession_(token) {
  token = String(token || '').trim();
  if (!/^[a-f0-9]{64}$/.test(token)) throw new Error('Your administrator session expired. Sign in again.');
  const props = PropertiesService.getScriptProperties();
  const pepper = requiredProperty_('ADMIN_PASSWORD_PEPPER');
  const raw = CacheService.getScriptCache().get('admin_session_' + hmacHex_(token, pepper));
  if (!raw) throw new Error('Your administrator session expired. Sign in again.');
  const session = JSON.parse(raw);
  if (session.version !== String(props.getProperty('ADMIN_SESSION_VERSION') || '1')
      || session.email !== String(props.getProperty('ADMIN_EMAIL') || '').trim().toLowerCase()) {
    throw new Error('Your administrator session expired. Sign in again.');
  }
  return session;
}

function firestoreListSubscribers_() {
  const projectId = requiredProperty_('FIREBASE_PROJECT_ID');
  const base = 'https://firestore.googleapis.com/v1/projects/' + encodeURIComponent(projectId) + '/databases/(default)/documents/subscribers';
  const token = firestoreAccessToken_();
  const records = [];
  let pageToken = '';
  for (let page = 0; page < 4; page++) {
    const url = base + '?pageSize=500' + (pageToken ? '&pageToken=' + encodeURIComponent(pageToken) : '');
    const response = UrlFetchApp.fetch(url, { headers: { Authorization: 'Bearer ' + token }, muteHttpExceptions: true });
    if (response.getResponseCode() < 200 || response.getResponseCode() >= 300) {
      throw new Error('Subscriber database could not be read (' + response.getResponseCode() + ').');
    }
    const result = JSON.parse(response.getContentText());
    (result.documents || []).forEach(document => {
      const parts = String(document.name || '').split('/');
      const record = decodeFirestoreFields_(document.fields || {});
      records.push(Object.assign({ uid: parts[parts.length - 1] }, record));
    });
    pageToken = result.nextPageToken || '';
    if (!pageToken) break;
  }
  return records;
}

function decodeFirestoreFields_(fields) {
  const result = {};
  Object.keys(fields || {}).forEach(key => { result[key] = decodeFirestoreValue_(fields[key]); });
  return result;
}

function decodeFirestoreValue_(value) {
  if (!value || typeof value !== 'object') return null;
  if ('stringValue' in value) return value.stringValue;
  if ('integerValue' in value) return Number(value.integerValue);
  if ('doubleValue' in value) return Number(value.doubleValue);
  if ('booleanValue' in value) return Boolean(value.booleanValue);
  if ('timestampValue' in value) return value.timestampValue;
  if ('nullValue' in value) return null;
  if ('arrayValue' in value) return (value.arrayValue.values || []).map(decodeFirestoreValue_);
  if ('mapValue' in value) return decodeFirestoreFields_(value.mapValue.fields || {});
  if ('referenceValue' in value) return value.referenceValue;
  return null;
}

function timingSafeEqual_(left, right) {
  left = String(left || '');
  right = String(right || '');
  if (left.length !== right.length) return false;
  let difference = 0;
  for (let index = 0; index < left.length; index++) difference |= left.charCodeAt(index) ^ right.charCodeAt(index);
  return difference === 0;
}

function publicAdminError_(error) {
  const message = String(error && error.message || 'The request could not be completed.');
  if (/administrator|sign-in attempts|session expired|reset code|six-digit|12 to 128|valid administrator|Too many codes|daily verification-email limit|mailbox has reached|Firestore|service-account|not configured/i.test(message)) return message;
  if (/Email or password is incorrect/.test(message)) return message;
  return 'The administrator request could not be completed. Check the owner setup guide and Apps Script execution log.';
}

function validateRequest_(payload) {
  const input = payload || {};
  if (String(input.website || '').trim()) throw new Error('Unable to process this request.');
  const email = String(input.email || '').trim().toLowerCase();
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email) || email.length > 254) {
    throw new Error('Enter a valid email address.');
  }
  const operation = String(input.operation || '');
  if (!['subscribe', 'unsubscribe'].includes(operation)) throw new Error('Unsupported verification action.');

  let categories = [];
  let retailers = ['all'];
  if (operation === 'subscribe') {
    categories = uniqueAllowed_(input.categories, CATEGORIES);
    retailers = uniqueAllowed_(input.retailers, RETAILERS);
    if (!categories.length) throw new Error('Choose at least one notification category.');
    if (!retailers.length || retailers.includes('all')) retailers = ['all'];
  }
  return { email: email, operation: operation, categories: categories, retailers: retailers };
}

function uniqueAllowed_(values, allowed) {
  if (!Array.isArray(values)) return [];
  return [...new Set(values.map(value => String(value)))].filter(value => allowed.includes(value)).slice(0, allowed.length);
}

function enforceRateLimit_(emailHash, cache, props) {
  const lock = LockService.getScriptLock();
  lock.waitLock(10000);
  try {
    const now = Date.now();
    const rateKey = 'otp_rate_' + emailHash;
    const previous = JSON.parse(cache.get(rateKey) || '{"times":[]}');
    const recent = (previous.times || []).filter(value => now - value < 3600000);
    if (recent.length && now - recent[recent.length - 1] < EMAIL_COOLDOWN_SECONDS * 1000) {
      throw new Error('Please wait one minute before requesting another code.');
    }
    if (recent.length >= EMAIL_MAX_PER_HOUR) {
      throw new Error('Too many codes were requested for this address. Try again later.');
    }
    const day = Utilities.formatDate(new Date(), 'UTC', 'yyyy-MM-dd');
    const dailyKey = 'OTP_DAILY_' + day;
    const count = Number(props.getProperty(dailyKey) || 0);
    if (count >= EMAIL_DAILY_CAP) throw new Error('PokéDrop Watch has reached its daily verification-email limit. Please try again tomorrow.');
    if (MailApp.getRemainingDailyQuota() < 1) throw new Error('The notification mailbox has reached its daily email limit. Please try again tomorrow.');
    recent.push(now);
    cache.put(rateKey, JSON.stringify({ times: recent }), 21600);
    // Reserve the daily slot while holding the script lock so concurrent requests
    // cannot overrun the application-level send cap.
    props.setProperty(dailyKey, String(count + 1));
  } finally {
    lock.releaseLock();
  }
}

function sendVerificationEmail_(email, code, operation) {
  const props = PropertiesService.getScriptProperties();
  const brand = props.getProperty('EMAIL_FROM_NAME') || 'PokéDrop Watch';
  const replyTo = props.getProperty('EMAIL_REPLY_TO') || 'pokedropwatch.notify@gmail.com';
  const isAdminReset = operation === 'admin_reset';
  const action = isAdminReset
    ? 'reset your PokéDrop Watch administrator password'
    : operation === 'unsubscribe' ? 'confirm an unsubscribe request' : 'verify your subscription application';
  const subject = isAdminReset ? 'Your PokéDrop Watch administrator reset code' : 'Your PokéDrop Watch verification code';
  const heading = isAdminReset ? 'Reset your administrator password' : 'Verify your email';
  const body = 'Your PokéDrop Watch code is ' + code + '.\n\nUse this code to ' + action + '. It expires in 10 minutes and can only be used once. If you did not request it, ignore this email.\n\nPokéDrop Watch';
  const htmlBody = '<div style="font-family:Arial,sans-serif;max-width:560px;margin:24px auto;padding:24px;border:1px solid #e9e5e0;border-radius:16px;background:#fff;color:#262626">' +
    '<div style="font-size:12px;letter-spacing:2px;font-weight:700;color:#b73535">POKÉDROP WATCH</div>' +
    '<h2 style="margin:16px 0 8px">' + escapeHtml_(heading) + '</h2>' +
    '<p style="color:#666">Use this code to ' + escapeHtml_(action) + '.</p>' +
    '<div style="margin:22px 0;padding:18px;text-align:center;background:#faf4f2;border-radius:12px;font-size:32px;font-weight:800;letter-spacing:8px;color:#b73535">' + code + '</div>' +
    '<p style="color:#666">This code expires in 10 minutes and can only be used once. If you did not request it, ignore this email.</p>' +
    '<p style="font-size:12px;color:#999;margin-top:24px">PokéDrop Watch · Fan-made Pokémon product alerts</p></div>';
  MailApp.sendEmail({
    to: email,
    subject: subject,
    body: body,
    htmlBody: htmlBody,
    name: brand,
    replyTo: replyTo
  });
}

function saveSubscription_(session) {
  const found = firestoreFindSubscriberByEmail_(session.email);
  const docId = found ? found.id : subscriberDocumentId_(session.email);
  const existing = found ? found.record : null;
  const previousStatus = existing && existing.status || '';
  if (previousStatus === 'removed') {
    return 'Your email was previously removed by the site administrator. Contact the administrator if you believe this was a mistake.';
  }
  let status = previousStatus || 'pending';
  if (['unsubscribed', 'rejected'].includes(status)) status = 'pending';
  const now = new Date().toISOString();
  const record = {
    email: session.email,
    status: status,
    categories: session.categories,
    retailers: session.retailers,
    createdAt: existing && existing.createdAt || now,
    updatedAt: now,
    verificationMethod: 'email-code'
  };
  if (status === 'pending' && previousStatus && ['unsubscribed', 'rejected'].includes(previousStatus)) record.reappliedAt = now;
  firestorePatchSubscriber_(docId, record);
  if (status === 'active') return 'Your email is verified and your notification preferences have been updated.';
  if (status === 'suspended') return 'Your email is verified, but notifications remain paused by the administrator.';
  if (status === 'pending') return 'Your email is verified. Your application is now pending administrator approval.';
  return 'Your email is verified. Your subscription preferences have been saved.';
}

function unsubscribeSubscription_(session) {
  const found = firestoreFindSubscriberByEmail_(session.email);
  const docId = found ? found.id : subscriberDocumentId_(session.email);
  const existing = found ? found.record : null;
  if (!existing || !['active', 'pending', 'suspended'].includes(existing.status)) {
    return 'Email ownership was verified. No active subscription needed to be changed.';
  }
  const now = new Date().toISOString();
  firestorePatchSubscriber_(docId, { status: 'unsubscribed', unsubscribedAt: now, updatedAt: now });
  return 'You have been unsubscribed. No further product alerts will be sent to this address.';
}

function subscriberDocumentId_(email) {
  return Utilities.base64EncodeWebSafe(Utilities.computeHmacSha256Signature(
    email,
    requiredProperty_('EMAIL_HMAC_SECRET')
  )).replace(/=+$/g, '');
}

function firestoreFindSubscriberByEmail_(email) {
  const projectId = requiredProperty_('FIREBASE_PROJECT_ID');
  const url = 'https://firestore.googleapis.com/v1/projects/' + encodeURIComponent(projectId) + '/databases/(default)/documents:runQuery';
  const response = UrlFetchApp.fetch(url, {
    method: 'post',
    contentType: 'application/json',
    payload: JSON.stringify({ structuredQuery: {
      from: [{ collectionId: 'subscribers' }],
      where: { fieldFilter: {
        field: { fieldPath: 'email' },
        op: 'EQUAL',
        value: { stringValue: email }
      } },
      limit: 1
    } }),
    headers: { Authorization: 'Bearer ' + firestoreAccessToken_() },
    muteHttpExceptions: true
  });
  if (response.getResponseCode() < 200 || response.getResponseCode() >= 300) {
    throw new Error('Firestore subscriber lookup failed (' + response.getResponseCode() + ').');
  }
  const rows = JSON.parse(response.getContentText());
  const document = (rows || []).map(row => row.document).find(Boolean);
  if (!document) return null;
  const parts = String(document.name || '').split('/');
  const id = parts[parts.length - 1];
  const fields = document.fields || {};
  return { id: id, record: {
    email: fields.email && fields.email.stringValue || '',
    status: fields.status && fields.status.stringValue || '',
    createdAt: fields.createdAt && fields.createdAt.timestampValue || ''
  } };
}

function firestorePatchSubscriber_(docId, record) {
  const projectId = requiredProperty_('FIREBASE_PROJECT_ID');
  const updateMask = Object.keys(record).map(key => 'updateMask.fieldPaths=' + encodeURIComponent(key)).join('&');
  const url = 'https://firestore.googleapis.com/v1/projects/' + encodeURIComponent(projectId) + '/databases/(default)/documents/subscribers/' + encodeURIComponent(docId) + '?' + updateMask;
  const fields = {};
  Object.keys(record).forEach(key => { fields[key] = firestoreValue_(record[key]); });
  const response = UrlFetchApp.fetch(url, {
    method: 'patch',
    contentType: 'application/json',
    payload: JSON.stringify({ fields: fields }),
    headers: { Authorization: 'Bearer ' + firestoreAccessToken_() },
    muteHttpExceptions: true
  });
  const status = response.getResponseCode();
  if (status < 200 || status >= 300) throw new Error('Firestore write failed (' + status + ').');
}

function firestoreValue_(value) {
  if (Array.isArray(value)) return { arrayValue: { values: value.map(item => ({ stringValue: String(item) })) } };
  if (typeof value === 'boolean') return { booleanValue: value };
  if (typeof value === 'number') return { integerValue: String(value) };
  if (value === null || value === undefined) return { nullValue: null };
  if (typeof value === 'string' && /^\d{4}-\d\d-\d\dT/.test(value)) return { timestampValue: value };
  return { stringValue: String(value) };
}

function firestoreAccessToken_() {
  const cache = CacheService.getScriptCache();
  const cached = cache.get('firestore_access_token');
  if (cached) return cached;
  const service = JSON.parse(requiredProperty_('FIREBASE_SERVICE_ACCOUNT_JSON'));
  const now = Math.floor(Date.now() / 1000);
  const header = base64Url_(JSON.stringify({ alg: 'RS256', typ: 'JWT' }));
  const claims = base64Url_(JSON.stringify({
    iss: service.client_email,
    scope: 'https://www.googleapis.com/auth/datastore',
    aud: service.token_uri || 'https://oauth2.googleapis.com/token',
    iat: now,
    exp: now + 3600
  }));
  const unsigned = header + '.' + claims;
  const signature = Utilities.computeRsaSha256Signature(unsigned, service.private_key);
  const assertion = unsigned + '.' + base64Url_(signature);
  const response = UrlFetchApp.fetch(service.token_uri || 'https://oauth2.googleapis.com/token', {
    method: 'post',
    payload: {
      grant_type: 'urn:ietf:params:oauth:grant-type:jwt-bearer',
      assertion: assertion
    },
    muteHttpExceptions: true
  });
  if (response.getResponseCode() < 200 || response.getResponseCode() >= 300) throw new Error('Google service-account authentication failed.');
  const result = JSON.parse(response.getContentText());
  cache.put('firestore_access_token', result.access_token, 3300);
  return result.access_token;
}

function base64Url_(value) {
  return Utilities.base64EncodeWebSafe(value).replace(/=+$/g, '');
}

function makeCode_(secret, token) {
  const digest = Utilities.computeHmacSha256Signature(token, secret);
  const unsigned = ((digest[0] & 127) * 0x1000000) + ((digest[1] & 255) * 0x10000) + ((digest[2] & 255) * 0x100) + (digest[3] & 255);
  return String(unsigned % 1000000).padStart(6, '0');
}

function hmacHex_(value, secret) {
  return Utilities.computeHmacSha256Signature(value, secret).map(byte => ('0' + ((byte + 256) % 256).toString(16)).slice(-2)).join('');
}

function requiredProperty_(name) {
  const value = PropertiesService.getScriptProperties().getProperty(name);
  if (!value) throw new Error('The Apps Script owner has not configured ' + name + '.');
  return value;
}

function publicError_(error) {
  const message = String(error && error.message || 'The request could not be completed.');
  if (/Please wait|Too many codes|daily verification-email limit|mailbox has reached|Enter a valid|Choose at least|incorrect|expired|newer code|six-digit|not configured|Firestore|service-account|Unsupported|removed by the site administrator/i.test(message)) return message;
  return 'The request could not be completed. Please try again later.';
}

function safeError_(error) {
  return String(error && error.message || error || 'Unknown error').replace(/[\r\n]/g, ' ').slice(0, 180);
}

function escapeHtml_(value) {
  return String(value).replace(/[&<>"']/g, character => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[character]);
}
