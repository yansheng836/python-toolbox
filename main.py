import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from PyQt6.QtWidgets import QApplication
from toolbox import ToolboxWindow

def main():
    app = QApplication(sys.argv)
    window = ToolboxWindow(app)
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
