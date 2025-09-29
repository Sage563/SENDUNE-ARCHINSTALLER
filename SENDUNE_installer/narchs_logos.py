

import sys
import time
import math
import threading

import os

class RGB3DLogo:
    def __init__(self, logo=None, top=2, left=2, speed=0.1):
        self.logo = logo or [
            "███    ██  ██████  ███████     ██     ██  ██████  ██████  ██   ██ ██ ███    ██  ██████  ",
            "████   ██ ██    ██ ██          ██     ██ ██    ██ ██   ██ ██  ██  ██ ████   ██ ██    ██ ",
            "██ ██  ██ ██    ██ █████       ██  █  ██ ██    ██ ██████  █████   ██ ██ ██  ██ ██    ██ ",
            "██  ██ ██ ██    ██ ██          ██ ███ ██ ██    ██ ██   ██ ██  ██  ██ ██  ██ ██ ██    ██ ",
            "██   ████  ██████  ███████      ███ ███   ██████  ██   ██ ██   ██ ██ ██   ████  ██████  "
        ]
        self.not_working_logo = [
           "███    ██  ██████  ███████     ██     ██  ██████  ██████  ██   ██ ██ ███    ██  ██████  ",
            "████   ██ ██    ██ ██          ██     ██ ██    ██ ██   ██ ██  ██  ██ ████   ██ ██    ██ ",
            "██ ██  ██ ██    ██ █████       ██  █  ██ ██    ██ ██████  █████   ██ ██ ██  ██ ██    ██ ",
            "██  ██ ██ ██    ██ ██          ██ ███ ██ ██    ██ ██   ██ ██  ██  ██ ██  ██ ██ ██    ██ ",
            "██   ████  ██████  ███████      ███ ███   ██████  ██   ██ ██   ██ ██ ██   ████  ██████  "
        ]
        self.top = top
        self.left = left
        self.speed = speed
        self._shift = 0
        self._running = False
        self._thread = None
        self._saved_lines = []

    def _rgb(self, r, g, b):
        return f"\033[38;2;{r};{g};{b}m"

    def _carving_text(self, line, shift=0):
        result = ""
        for i, char in enumerate(line):
            if char == " ":
                result += " "
            else:
                brightness = int((math.sin((i + shift) * 0.3) + 1) * 127)
                r = min(255, brightness + 128)
                g = min(255, brightness + 100)
                b = min(255, brightness + 50)
                result += self._rgb(r, g, b) + char
        return result + "\033[0m"

    def _save_area(self):
        """Save the current content of the logo area"""
        self._saved_lines = []
        for i in range(len(self.logo)):
            sys.stdout.write(f"\0337")  # Save cursor
            sys.stdout.write(f"\033[{self.top + i};0H")  # Move to start of line
            line = sys.stdin.readline().rstrip("\n") if False else " " * 80
            self._saved_lines.append(line[:80])
            sys.stdout.write(f"\0338")  # Restore cursor

    def _restore_area(self):
        """Restore the saved terminal content"""
        for i, line in enumerate(self._saved_lines):
            sys.stdout.write(f"\033[{self.top + i};0H")
            sys.stdout.write(line + "\033[0m")
        sys.stdout.flush()

    def _print_logo(self):
        for i, line in enumerate(self.logo):
            sys.stdout.write(f"\033[{self.top + i};{self.left}H")
            sys.stdout.write(self._carving_text(line, self._shift + i))
        sys.stdout.flush()

    def _run_loop(self):
        while self._running:
            self._print_logo()
            self._shift += 1
            time.sleep(self.speed)

    def start(self):
        """Start the animation in a separate thread"""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def switch_to_not_working(self, new_logo=None):
        """Switch to 'not working' logo safely"""
        self._save_area()
        self.logo = new_logo or self.not_working_logo
        self._shift = 0
        # Let it draw for a moment
        time.sleep(0.5)
        self._restore_area()

    def stop(self):
        """Stop animation and reset colors"""
        self._running = False
        if self._thread:
            self._thread.join()
        sys.stdout.write("\033[0m\n")
        sys.stdout.flush()


def input_with_pause(prompt, logo_animation):
    """Pauses the logo animation, takes input, then resumes animation."""
    logo_animation._running = False  # Pause animation
    sys.stdout.write("\033[0m\n")  # Reset colors and move to a new line
    user_input = input(prompt)
    logo_animation._running = True  # Resume animation
    return user_input


# Example usage
if __name__ == "__main__":
    logo = [
        "   ███████╗███████╗███╗   ██╗██████╗ ██    ██ ██╗   ██╗███╗   ██╗███████╗",
        "   ██╔════╝██╔════╝████╗  ██║██╔══██╗██║   ██║██║   ██║████╗  ██║██╔════╝",
        "   ███████╗█████╗  ██╔██╗ ██║██║  ██║██║   ██║██║   ██║██╔██╗ ██║█████╗  ",
        "   ╚════██║██╔══╝  ██║╚██╗██║██║  ██║██║   ██║██║   ██║██║╚██╗██║██╔══╝  ",
        "   ███████║███████╗██║ ╚████║██████╔╝╚██████╔╝╚██████╔╝██║ ╚████║███████╗",
        "   ╚══════╝╚══════╝╚═╝  ╚═══╝╚═════╝  ╚═════╝  ╚═════╝ ╚═╝  ╚═══╝╚══════╝"
    ]

    logo_animation = RGB3DLogo(logo=logo)
    logo_animation.start()

    # You can do other things while the logo animates
    time.sleep(5)
    print("\nSwitching to NOT WORKING logo...\n")
    logo_animation.switch_to_not_working()
    os.system('cls')  # Clear screen to see the effect better
    # Keep it running for demonstration
    try:
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        logo_animation.stop()
