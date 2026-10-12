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

def check_url_health(url, timeout=3.0):
    """
    Sub-second pre-flight check to catch 502/503/504 Bad Gateways and DNS crashes
    BEFORE opening the browser, saving 15-30s of wasted wait time.
    """
    if circuit_breaker.is_tripped(url):
        return False, "CIRCUIT_BREAKER_TRIPPED"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    try:
        # Try HEAD first for fast response
        res = requests.head(url, timeout=timeout, headers=headers, allow_redirects=True)
        if res.status_code == 405: # Method not allowed, fall back to streaming GET
            res = requests.get(url, timeout=timeout, headers=headers, stream=True)
            res.close()
            
        if res.status_code in [500, 502, 503, 504]:
            circuit_breaker.record_failure(url)
            return False, f"NET_BAD_GATEWAY_{res.status_code}"
            
        return True, "OK"
    except requests.exceptions.Timeout:
        circuit_breaker.record_failure(url)
        return False, "NET_TIMEOUT"
    except requests.exceptions.ConnectionError:
        circuit_breaker.record_failure(url)
        return False, "NET_CONNECTION_ERROR"
    except Exception as e:
        return False, f"NET_ERROR_{str(e)[:25]}"

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

def wait_for_visual_settle(max_timeout=8.0, check_interval=0.5, variance_threshold=0.008):
    """
    Adaptive Visual Settling Watchdog:
    Instead of fixed static sleep, dynamically detects when page finishes rendering
    or animating by measuring pixel variance. Proceeds immediately when settled!
    """
    start_time = time.time()
    last_frame = get_lowres_frame()
    time.sleep(check_interval)
    
    while time.time() - start_time < max_timeout:
        curr_frame = get_lowres_frame()
        if last_frame is not None and curr_frame is not None:
            diff = np.abs(curr_frame.astype("float") - last_frame.astype("float")).mean() / 255.0
            
            # If visual change is below threshold, DOM has stabilized
            if diff < variance_threshold:
                elapsed_ms = (time.time() - start_time) * 1000.0
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
