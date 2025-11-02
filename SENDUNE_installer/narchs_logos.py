import sys
import sys
import time
import math
import threading
import shutil
import os


class RGB3DLogo:
    """Animated ASCII logo with RGB gradient.

    - start/stop with a threading.Event for pause/resume during input
    - automatic horizontal centering
    - smoother RGB gradient and optional bold
    - safe pause/resume for use with blocking input()
    """

    def __init__(self, logo=None, top=1, speed=0.08, bold=True):
        self.logo = logo or [
            "███    ██  ██████  ███████     ██     ██  ██████  ██████  ██   ██ ██ ███    ██  ██████  ",
            "████   ██ ██    ██ ██          ██     ██ ██    ██ ██   ██ ██  ██  ██ ████   ██ ██    ██ ",
            "██ ██  ██ ██    ██ █████       ██  █  ██ ██    ██ ██████  █████   ██ ██ ██  ██ ██    ██ ",
            "██  ██ ██ ██    ██ ██          ██ ███ ██ ██    ██ ██   ██ ██  ██  ██ ██  ██ ██ ██    ██ ",
            "██   ████  ██████  ███████      ███ ███   ██████  ██   ██ ██   ██ ██ ██   ████  ██████  "
        ]

        # A simple ASCII 'not working' banner (escaped backslashes)
        self.not_working_logo = [
            "  _   _  _____ _____ _   _  _____ _    _ ",
            " | \\ | |/ ____|_   _| \\ | |/ ____| |  | |",
            " |  \\| | (___   | | |  \\| | (___ | |  | |",
            " | . ` |\\___ \\  | | | . ` |\\___ \\| |  | |",
            " | |\\  |____) |_| |_| |\\  |____) | |__| |",
            " |_| \\_|_____/|_____|_| \\_|_____/ \\____/ "
        ]

        self.top = top
        self.speed = speed
        self.bold = bold

        self._shift = 0
        self._stop_event = threading.Event()
        self._pause_event = threading.Event()
        self._pause_event.set()  # not paused by default
        self._thread = None

    def _rgb(self, r, g, b, bold=False):
        code = f"\033[38;2;{r};{g};{b}m"
        if bold:
            code = "\033[1m" + code
        return code

    def _carving_text(self, line, shift=0):
        cols = shutil.get_terminal_size((80, 20)).columns
        # compute start column for centering
        start_col = max(1, (cols - len(line)) // 2)
        result = ""
        for i, char in enumerate(line):
            if char == " ":
                result += " "
            else:
                # use a moving sine wave to get colors
                t = (i + shift) * 0.18
                brightness = int((math.sin(t) + 1) * 127)
                r = min(255, brightness + 60)
                g = min(255, 255 - brightness // 2)
                b = min(255, 200 - brightness // 3)
                result += self._rgb(r, g, b, bold=self.bold) + char + "\033[0m"
        return start_col, result

    def _print_logo(self):
        cols = shutil.get_terminal_size((80, 20)).columns
        for i, line in enumerate(self.logo):
            # clear the full target line first so previous frames don't leave artifacts
            sys.stdout.write(f"\033[{self.top + i};1H\033[K")
            start_col, painted = self._carving_text(line, self._shift + i)
            sys.stdout.write(f"\033[{self.top + i};{start_col}H")
            sys.stdout.write(painted)
        sys.stdout.flush()

    def _run_loop(self):
        while not self._stop_event.is_set():
            # if paused, wait until resumed
            self._pause_event.wait()
            self._print_logo()
            self._shift += 1
            time.sleep(self.speed)

    def start(self):
        """Start the animation thread."""
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._pause_event.set()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def pause(self):
        """Pause the animation (useful before blocking input)."""
        self._pause_event.clear()

    def resume(self):
        """Resume a paused animation."""
        self._pause_event.set()

    def switch_to_not_working(self, new_logo=None):
        """Switch to a static 'not working' logo and redraw once."""
        self.pause()
        self.logo = new_logo or self.not_working_logo
        self._shift = 0
        self.resume()

    def stop(self):
        """Stop animation and clear the area used by the logo."""
        self._stop_event.set()
        # ensure not blocked on pause so thread can exit
        self._pause_event.set()
        if self._thread:
            self._thread.join(timeout=1)
        # Reset color and move cursor below logo
        sys.stdout.write("\033[0m\n")
        sys.stdout.flush()


def input_with_pause(prompt, logo_animation):
    """Pauses the logo animation, takes input, then resumes animation."""
    logo_animation.pause()
    try:
        # Move cursor below the logo to avoid overwriting; place prompt at column 1
        import shutil
        size = shutil.get_terminal_size((80, 24))
        rows = size.lines
        sys.stdout.write(f"\033[{rows};1H\033[K")
        sys.stdout.flush()
        return input(prompt)
    finally:
        logo_animation.resume()


if __name__ == "__main__":
    # Demonstration logo (centered automatically)
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

    # Let it animate a little
    time.sleep(2)

    # Ask user for a name while the logo is paused
    name = input_with_pause("Enter your name: ", logo_animation)
    print(f"Hello, {name}!")

    # Show the 'not working' logo for a bit
    time.sleep(1)
    print("Switching to NOT WORKING logo...\n")
    logo_animation.switch_to_not_working()

    try:
        # keep running until interrupted
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logo_animation.stop()
