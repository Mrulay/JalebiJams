# YouTube Extraction Reliability Guide

Persistent `Sign in to confirm you're not a bot` errors mean YouTube is blocking anonymous API-style requests. Follow the steps below to harden extraction and leverage fallbacks.

## 1. Export Proper Cookies

1. Log into YouTube in your desktop browser (Chrome/Firefox).
2. Install a cookie export extension (e.g. "Get cookies.txt" or "Cookie-Editor").
3. Navigate to https://www.youtube.com (main homepage, not studio). Refresh once.
4. Export cookies *for youtube.com* only.
5. Save as `cookies.txt` and copy to the bot directory on the VPS:
   ```bash
   scp cookies.txt root@your-vps-ip:/root/JalebiJams/
   ```

### Critical Cookies Checklist
Ensure these appear in the file (names may have `__Secure-` prefixes):
- SID
- SSID
- HSID
- SAPISID
- PREF
- LOGIN_INFO
- __Secure-3PSID / __Secure-1PSID

If most are missing, repeat export using a different extension or manually via DevTools Application > Storage if needed.

## 2. Verify Bot Sees Cookies
In Discord run:
```
!!status
```
You want:
```
Cookies loaded: True
Critical cookies missing: False
```
If critical cookies missing = True, re-export.

## 3. Upgrade yt-dlp
```bash
source venv/bin/activate
pip install -U yt-dlp
systemctl restart jalebi-bot
```

## 4. Install Node.js (Optional but Recommended)
Improves handling of signature deciphering for cutting-edge YouTube changes.
```bash
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt-get install -y nodejs
```
Restart the service afterwards.

## 5. Adjust Environment Variables
Edit `.env` to tune behavior:
```
INVIDIOUS_HOST=https://invidious.flokinet.to
MAX_PLAYLIST_ITEMS=40
PLAYLIST_MODE=fast
YTDLP_VERBOSE=0
YTDLP_USER_AGENT=Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0 Safari/537.36
```
Then restart:
```bash
systemctl restart jalebi-bot
```

## 6. Fallback Logic
Order of attempts when playing a track:
1. yt-dlp extraction (multi player_client + cookies)
2. Simplified player_client fallback
3. Forced download fallback
4. Invidious API lookup (adaptive audio selection)
5. (Future) Piped API audio stream fallback

Failures are logged with `[play] primary extraction failed:` or `[next] primary extraction failed:` in `journalctl`.

## 7. Verbose Debugging
Temporarily enable:
```
YTDLP_VERBOSE=1
```
Look for format selection and error tracebacks, then set back to 0 to reduce noise.

## 8. Common Issues
| Symptom | Cause | Fix |
|--------|-------|-----|
| `Sign in to confirm you're not a bot` | Missing/weak cookies | Re-export cookies.txt with critical set |
| Playlist appears but no songs play | First item fails extraction | Test single video URL; check !!status; inspect logs |
| Fallback never triggers | Unhandled exception before fallback path | Ensure latest bot.py deployed & restart service |
| Slow playlist enqueue | `PLAYLIST_MODE=full` set | Switch to `PLAYLIST_MODE=fast` |

## 9. Rotating Invidious Host
If current host is slow or returns errors, change `INVIDIOUS_HOST` in `.env` to another public instance, then restart.

## 10. Future Enhancements
- Automatic rotation across Invidious hosts
- Piped API secondary fallback
- Structured logging with severity levels

---
For persistent issues, capture the last 60 lines:
```bash
journalctl -u jalebi-bot -n 60 --no-pager | sed -e 's/\x1b\[[0-9;]*m//g'
```
Share those lines for deeper analysis.
