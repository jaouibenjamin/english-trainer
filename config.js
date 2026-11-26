// Paste the Google Apps Script web-app URL between the quotes. Empty = the app runs without login, progress stays on the device.
window.API_URL = 'https://script.google.com/macros/s/AKfycbxlV1HQJM7JOR13wI7hI5SrFGX3DvkjGBZm7M_cHbAL8YbJF_ReYuE5ZDELAHNQY6WN5Q/exec';
// The new backend (docs/PHASE3.md, docs/PHASE4.md A), as a TRIAL: only a device opened once with ?new=1 uses it; every
// other device stays on the Sheet above (there is no everyone key, on purpose). The key is the project's publishable key
// (public by design), pasted here once, deliberately, by the lead: while it is empty, no device uses the project at all.
window.BACKEND = {mode: 'supabase', url: 'https://sgzzsixokgohshdpkvkr.supabase.co', key: ''};
