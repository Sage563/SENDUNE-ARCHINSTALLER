from pathlib import Path
import time



class LogFile():
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.file = self.path.open('a')
    def write(self, message: str) -> None:
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        self.file.write(f"[{timestamp}] {message}\n")
        self.file.flush()
    def warn(self, message: str) -> None:
        self.write(f"WARNING: {message}")
    def error(self, message: str) -> None:
        self.write(f"ERROR: {message}")
    def info(self, message: str) -> None:
        self.write(f"INFO: {message}")

    def close(self) -> None:
        self.file.close()