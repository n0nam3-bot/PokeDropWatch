/**
 * PokéDrop Watch verification-code backend.
 * Deploy as a Google Apps Script web app owned by pokedropwatch.notify@gmail.com.
 * No Google Sheet is used: subscriber records are written directly to Firestore
 * through the Firestore REST API using the private service-account JSON.
 */
const OTP_TTL_SECONDS = 600;
const OTP_MAX_ATTEMPTS = 5;
const EMAIL_COOLDOWN_SECONDS = 60;
const EMAIL_MAX_PER_HOUR = 3;
const EMAIL_DAILY_CAP = 25;
const CATEGORIES = ['tcg', 'plush', 'collectibles', 'games', 'accessories', 'news'];
const RETAILERS = ['all', 'pokemon-center', 'target', 'walmart', 'best-buy', 'gamestop', 'amazon', 'pokebeach'];

function doGet() {
  const props = PropertiesService.getScriptProperties();
  const template = HtmlService.createTemplateFromFile('Index');
  template.siteOrigin = props.getProperty('SITE_ORIGIN') || 'https://n0nam3-bot.github.io';
  return template.evaluate()
    .setTitle('PokéDrop Watch Verification')
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
