import time
import requests
import pyautogui
import numpy as np
import cv2
from urllib.parse import urlparse

class DomainCircuitBreaker:
    """Prevents the benchmark from hanging on a persistently broken or rate-limiting website."""
    def __init__(self, failure_threshold=2):
        self.failure_threshold = failure_threshold
        self.failures = {} # domain -> consecutive count

    def get_domain(self, url):
        try:
            return urlparse(url).netloc.lower()
        except Exception:
            return url

    def is_tripped(self, url):
        dom = self.get_domain(url)
        return self.failures.get(dom, 0) >= self.failure_threshold

    def record_failure(self, url):
        dom = self.get_domain(url)
        self.failures[dom] = self.failures.get(dom, 0) + 1
        print(f"[CIRCUIT BREAKER] Domain '{dom}' failure count: {self.failures[dom]}/{self.failure_threshold}")

    def record_success(self, url):
        dom = self.get_domain(url)
        if dom in self.failures:
            self.failures[dom] = 0

circuit_breaker = DomainCircuitBreaker(failure_threshold=2)

def check_url_health(url, timeout=3.5):
    """
    Sub-second pre-flight check to catch true server outages (500, 502, 503, 504)
    or unreachable DNS. If the endpoint simply blocks Python requests (bot protection),
    we gracefully proceed so the real browser can load it.
    """
    if circuit_breaker.is_tripped(url):
        return False, "CIRCUIT_BREAKER_TRIPPED"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9"
    }
    try:
        # Use lightweight streaming GET with short connect/read timeout
        res = requests.get(url, timeout=(2.5, 3.5), headers=headers, stream=True, allow_redirects=True)
        status_code = res.status_code
        res.close()
        
        if status_code in [500, 502, 503, 504]:
            circuit_breaker.record_failure(url)
            return False, f"NET_BAD_GATEWAY_{status_code}"
            
        return True, "OK"
    except requests.exceptions.SSLError:
        circuit_breaker.record_failure(url)
        return False, "NET_SSL_ERROR"
    except requests.exceptions.ConnectionError as e:
        if "getaddrinfo failed" in str(e).lower() or "name resolution" in str(e).lower():
            circuit_breaker.record_failure(url)
            return False, "NET_DNS_FAILURE"
        print(f"[PRE-FLIGHT INFO] Endpoint reset raw Python handshake; handing off to Chrome.")
        return True, "OK"
    except requests.exceptions.Timeout:
        print(f"[PRE-FLIGHT INFO] Pre-flight ping hit read delay; handing off to browser watchdog.")
        return True, "OK"
    except Exception:
        return True, "OK"

def get_lowres_frame():
    """Captures a lightweight downsampled grayscale frame for fast visual variance analysis."""
    try:
        shot = pyautogui.screenshot()
        img = np.array(shot)
        gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
        lowres = cv2.resize(gray, (320, 180), interpolation=cv2.INTER_AREA)
        return lowres
    except Exception:
        return None

def wait_for_visual_settle(max_timeout=8.0, check_interval=0.5, variance_threshold=0.012, min_observe_s=1.2):
    """
    Adaptive Visual Settling Watchdog:
    Detects when the live page finishes rendering/animating by measuring pixel variance.
    Guards against falsely triggering on blank white/unrendered initial tabs.
    """
    start_time = time.time()
    last_frame = get_lowres_frame()
    time.sleep(check_interval)
    
    while time.time() - start_time < max_timeout:
        curr_frame = get_lowres_frame()
        elapsed = time.time() - start_time
        
        if last_frame is not None and curr_frame is not None:
            # If the screen is completely flat/blank (std < 6.0), the page hasn't rendered content yet
            if curr_frame.std() < 6.0:
                last_frame = curr_frame
                time.sleep(check_interval)
                continue
                
            diff = np.abs(curr_frame.astype("float") - last_frame.astype("float")).mean() / 255.0
            
            # If visual change is below threshold AND minimum observation time elapsed, DOM has stabilized
            if diff < variance_threshold and elapsed >= min_observe_s:
                elapsed_ms = elapsed * 1000.0
                return True, elapsed_ms
                
        last_frame = curr_frame
        time.sleep(check_interval)
        
    elapsed_ms = (time.time() - start_time) * 1000.0
    return False, elapsed_ms

def trigger_f5_recovery():
    """Triggers browser reload to self-heal client-side render lag or white screens."""
    print("[AUTO-HEAL] Executing F5 browser refresh...")
    pyautogui.press('f5')
    time.sleep(2.5)
