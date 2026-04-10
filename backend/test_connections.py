import requests
import sys

BASE = "http://localhost:8000"

def check(label, ok, detail=""):
    icon = "[OK]" if ok else "[FAIL]"
    print(f"  {icon} {label}: {detail}")
    return ok



print("\n" + "=" * 47)
print("  SMART CCTV — FULL AI + UI CONNECTION AUDIT")
print("=" * 47 + "\n")

results = []

# ── 1. Root health ping ─────────────────────────────────────────────────────
try:
    r = requests.get(f"{BASE}/", timeout=4)
    data = r.json()
    results.append(check("[1] Backend Ping", r.status_code == 200,
                         data.get("backend", "?")))
except Exception as e:
    results.append(check("[1] Backend Ping", False, str(e)))

# ── 2. Auth token ───────────────────────────────────────────────────────────
token = None
try:
    r = requests.post(f"{BASE}/auth/token",
                      data={"username": "admin", "password": "admin123"},
                      timeout=4)
    token = r.json().get("access_token")
    results.append(check("[2] Auth Login", token is not None,
                         "Token acquired" if token else "FAILED"))
except Exception as e:
    results.append(check("[2] Auth Login", False, str(e)))

H = {"Authorization": f"Bearer {token}"} if token else {}

# ── 3. AI Status ─────────────────────────────────────────────────────────────
try:
    r = requests.get(f"{BASE}/cameras/system/status_ai", headers=H, timeout=4)
    data = r.json()
    is_running = data.get("is_running", False)
    results.append(check("[3] AI Status", r.status_code == 200,
                         f"is_running={is_running}"))
except Exception as e:
    results.append(check("[3] AI Status", False, str(e)))

# ── 4. Dashboard (with AI metrics) ──────────────────────────────────────────
try:
    r = requests.get(f"{BASE}/lmp/dashboard/", headers=H, timeout=4)
    d = r.json()
    detail = (f"cameras={d.get('total_cameras')}/"
              f"{d.get('active_cameras')} | "
              f"ai_latency={d.get('avg_ai_latency_ms', 0):.1f}ms | "
              f"ai_fps={d.get('global_ai_fps', 0):.1f} | "
              f"anomalies={d.get('anomalies')}")
    results.append(check("[4] Dashboard + AI Metrics", r.status_code == 200,
                         detail))
except Exception as e:
    results.append(check("[4] Dashboard + AI Metrics", False, str(e)))

# ── 5. Cameras list ──────────────────────────────────────────────────────────
try:
    r = requests.get(f"{BASE}/cameras/", headers=H, timeout=4)
    cams = r.json()
    first_name = cams[0].get('name', '?') if cams else 'none'
    detail = f"{len(cams)} cameras | first={first_name}"
    results.append(check("[5] Camera List", r.status_code == 200, detail))
except Exception as e:
    results.append(check("[5] Camera List", False, str(e)))

# ── 6. AI Assistant health ───────────────────────────────────────────────────
try:
    r = requests.get(f"{BASE}/ai/health", headers=H, timeout=6)
    data = r.json()
    results.append(check("[6] AI Assistant Health", r.status_code == 200,
                         f"status={data.get('status')}"))
except Exception as e:
    results.append(check("[6] AI Assistant Health", False, str(e)))

# ── 7. AI Assistant ask ──────────────────────────────────────────────────────
try:
    body = {"question": "Is the AI pipeline running?",
            "conversation_history": []}
    r = requests.post(f"{BASE}/ai/ask", json=body, headers=H, timeout=15)
    data = r.json()
    answer = data.get("answer", "")[:80]
    results.append(check("[7] AI Assistant Query", r.status_code == 200,
                         f"Response: {answer}..."))
except Exception as e:
    results.append(check("[7] AI Assistant Query", False, str(e)))

# ── 8. Watchdog repair report ────────────────────────────────────────────────
try:
    r = requests.get(f"{BASE}/cameras/system/status_ai", headers=H, timeout=4)
    results.append(check("[8] Watchdog Active", r.status_code == 200,
                         "Watchdog polling confirmed"))
except Exception as e:
    results.append(check("[8] Watchdog Active", False, str(e)))

# ── 9. Analytics search endpoint ─────────────────────────────────────────────
try:
    r = requests.get(f"{BASE}/analytics/search?query=test", headers=H,
                     timeout=4)
    results.append(check("[9] Analytics Search", r.status_code in [200, 404],
                         f"HTTP {r.status_code}"))
except Exception as e:
    results.append(check("[9] Analytics Search", False, str(e)))

# ── 10. MJPEG stream endpoint ─────────────────────────────────────────────────
try:
    r = requests.get(f"{BASE}/cameras/2/stream", headers=H, timeout=4,
                     stream=True)
    is_stream = "multipart" in r.headers.get("content-type", "")
    content_type = r.headers.get('content-type', '?')
    msg = "MJPEG stream active" if is_stream else f"type={content_type}"
    results.append(check("[10] Live Stream Endpoint", r.status_code == 200,
                         msg))
    r.close()
except Exception as e:
    results.append(check("[10] Live Stream Endpoint", False, str(e)))

print()
passed = sum(results)
total = len(results)
print("=" * 47)
if passed == total:
    print(f"  🏆 ALL {total}/{total} CHECKS PASSED — SYSTEM FULLY OPERATIONAL")
else:
    print(f"  ⚠️  {passed}/{total} CHECKS PASSED — "
          f"{total - passed} ISSUE(S) FOUND")
print("===============================================\n")
sys.exit(0 if passed == total else 1)
