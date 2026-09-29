import tkinter as tk
import time
import pyautogui
import threading
import os

class VLMOverlay:
    def __init__(self):
        self.root = tk.Tk()
        self.root.attributes('-topmost', True)
        self.root.overrideredirect(True) # Remove window decorations
        
        # Make the background fully transparent (Windows only trick)
        self.root.attributes("-transparentcolor", "black")
        self.root.config(bg="black")
        
        self.screen_width = self.root.winfo_screenwidth()
        self.screen_height = self.root.winfo_screenheight()
        self.root.geometry(f"{self.screen_width}x{self.screen_height}+0+0")
        
        # 1. Top Status Bar
        self.status_frame = tk.Frame(self.root, bg="#0d1117", highlightbackground="#30363d", highlightthickness=2)
        self.status_frame.place(relx=0.5, rely=0.02, anchor='n', width=700, height=50)
        
        self.status_label = tk.Label(self.status_frame, 
                                     text="🤭 VLM BENCHMARK ENGINE | Model: gemini-1.5-pro | Status: INIT...", 
                                     fg="#58a6ff", bg="#0d1117", font=("Consolas", 14, "bold"))
        self.status_label.pack(expand=True)
        
        # 2. Edge Lighting Frame (Hidden by default)
        # Using a transparent center with thick blue borders
        self.border_frame = tk.Frame(self.root, bg="black", highlightbackground="#00f2fe", highlightthickness=12)
        
    def update_status(self, text, color="#58a6ff"):
        self.status_label.config(text=text, fg=color)
        self.root.update()
        
    def flash_capture_effect(self):
        # Show border
        self.border_frame.place(x=0, y=0, width=self.screen_width, height=self.screen_height)
        self.root.update()
        time.sleep(0.15) # Flash duration
        # Hide border
        self.border_frame.place_forget()
        self.root.update()

def test_sequence(overlay):
    time.sleep(1)
    overlay.update_status("🤭 VLM BENCHMARK | Model: gemini-1.5-pro | Status: TAKING SCREENSHOT...", "#f2cc60")
    time.sleep(1)
    
    # Trigger visual effect
    overlay.flash_capture_effect()
    
    # Take screenshot with PyAutoGUI
    sct_img = pyautogui.screenshot()
    sct_img.save("full_screen_test.png")
        
    overlay.update_status("🤭 VLM BENCHMARK | Model: gemini-1.5-pro | Status: SCREENSHOT SAVED TO DISK", "#3fb950")
    time.sleep(3)
    
    overlay.update_status("🤭 VLM BENCHMARK | Model: gemini-1.5-pro | Status: SHUTTING DOWN", "#ff7b72")
    time.sleep(2)
    overlay.root.quit()

if __name__ == "__main__":
    app = VLMOverlay()
    # Run the test sequence in a background thread so the UI thread doesn't freeze
    threading.Thread(target=test_sequence, args=(app,), daemon=True).start()
    app.root.mainloop()
