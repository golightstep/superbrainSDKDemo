import time
import json
import os
import threading
from config import FACT_CHECKER_KEY, PRODUCER_KEY, CONTEXT_NAME, MARKET_DATA_FILE
from superbrain_util import get_fabric

# Simple global lock file to prevent overlapping audio (echo)
AUDIO_LOCK = "/tmp/anchor_audio.lock"

HAS_TTS = False # Disabled per user request to prevent audio-related lags

class Anchor:
    def __init__(self, mode="traditional"):
        self.mode = mode
        self.fabric = get_fabric()
        self.ctx = self.fabric.attach_context(CONTEXT_NAME)
        self.last_announced_ts = 0
        
        # Initialize engine on start
        self._init_engine()

    def _init_engine(self):
        if not HAS_TTS: return
        try:
            self.engine = pyttsx3.init()
            self.engine.setProperty('rate', 150) # Slower, clearer
            self.engine.setProperty('volume', 0.9)
            # Find a non-default voice if possible (Mac specific)
            voices = self.engine.getProperty('voices')
            for voice in voices:
                if "Samantha" in voice.name or "Alex" in voice.name:
                    self.engine.setProperty('voice', voice.id)
                    break
        except:
            self.engine = None

    def speak(self, text):
        if not self.engine: return
        
        # Try to acquire audio lock
        # If someone else is speaking, we just wait or skip
        # For a live news studio, waiting is better
        start_wait = time.time()
        while os.path.exists(AUDIO_LOCK):
            if time.time() - start_wait > 10: # Timeout
                return 
            time.sleep(0.5)
            
        try:
            # Create lock
            with open(AUDIO_LOCK, "w") as f:
                f.write(str(os.getpid()))
            
            print(f"🎙️ [Anchor-{self.mode}] Speaking: {text}")
            self.engine.say(text)
            self.engine.runAndWait()
        except:
            # If it's "stuck", re-init next time
            self._init_engine()
        finally:
            # Release lock
            if os.path.exists(AUDIO_LOCK):
                try: os.remove(AUDIO_LOCK)
                except: pass

    def run_loop(self):
        print(f"📺 [Anchor-{self.mode}] Online.")
        while True:
            report, cue = None, None
            if self.mode == "traditional":
                path_cue = MARKET_DATA_FILE.replace(".json", "_cue.json")
                path_rep = MARKET_DATA_FILE.replace(".json", "_verified.json")
                if os.path.exists(path_cue) and os.path.exists(path_rep):
                    try:
                        with open(path_cue, "r") as f: cue = json.load(f)
                        with open(path_rep, "r") as f: report = json.load(f)
                    except: pass
            else:
                raw_c = self.ctx.read(PRODUCER_KEY)
                raw_r = self.ctx.read(FACT_CHECKER_KEY)
                if raw_c: cue = json.loads(raw_c)
                if raw_r: report = json.loads(raw_r)

            if cue and cue.get("ready") and report:
                ts = report.get("source_ts", 0)
                if ts > self.last_announced_ts:
                    ticker = report.get("ticker", "Market")
                    sentiment = report.get("sentiment", "Neutral")
                    # Differentiate the announcement slightly by mode
                    prefix = "Traditional Relay reports: " if self.mode == "traditional" else "Superbrain Fabric confirms: "
                    self.speak(f"{prefix} Breaking news on {ticker}. Sentiment is {sentiment}.")
                    self.last_announced_ts = ts
                    
            from config import TRADITIONAL_POLL_INTERVAL
            time.sleep(TRADITIONAL_POLL_INTERVAL)

if __name__ == "__main__":
    import sys
    mode = sys.argv[1] if len(sys.argv) > 1 else "traditional"
    Anchor(mode).run_loop()
