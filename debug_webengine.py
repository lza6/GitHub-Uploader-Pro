
import sys
try:
    print("Attempting to import PyQt6...")
    import PyQt6
    print(f"PyQt6 path: {PyQt6.__file__}")
    
    print("Attempting to import PyQt6.QtWebEngineWidgets...")
    from PyQt6.QtWebEngineWidgets import QWebEngineView
    print("Successfully imported QWebEngineView")
except ImportError as e:
    print(f"ImportError caught: {e}")
except Exception as e:
    print(f"Other error caught: {e}")
