from __future__ import annotations

from PySide6.QtCore import QObject, QThread, Signal
from PySide6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QTextEdit, QLineEdit, QPushButton, QLabel

from .agent import Agent


class Worker(QObject):
    done = Signal(str)

    def __init__(self, agent: Agent, text: str):
        super().__init__()
        self.agent = agent
        self.text = text

    def run(self):
        try:
            self.done.emit(self.agent.ask(self.text))
        except Exception as exc:
            self.done.emit(f"Помилка ALVIS: {exc}")


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ALVIS")
        self.resize(900, 650)
        self.agent = Agent()
        self.thread = None
        self.worker = None

        root = QWidget()
        layout = QVBoxLayout(root)
        title = QLabel("ALVIS  •  Windows AI Assistant")
        title.setStyleSheet("font-size: 22px; font-weight: 700; padding: 8px;")
        self.chat = QTextEdit()
        self.chat.setReadOnly(True)
        self.input = QLineEdit()
        self.input.setPlaceholderText("Напиши команду українською або англійською…")
        self.send = QPushButton("Виконати")
        self.send.clicked.connect(self.submit)
        self.input.returnPressed.connect(self.submit)
        layout.addWidget(title)
        layout.addWidget(self.chat, 1)
        layout.addWidget(self.input)
        layout.addWidget(self.send)
        self.setCentralWidget(root)
        self.chat.append("<b>ALVIS:</b> Онлайн. Чим допомогти?")

    def submit(self):
        text = self.input.text().strip()
        if not text or self.thread:
            return
        self.input.clear()
        self.chat.append(f"<b>Ти:</b> {text}")
        self.send.setEnabled(False)
        self.thread = QThread()
        self.worker = Worker(self.agent, text)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.done.connect(self.reply)
        self.worker.done.connect(self.thread.quit)
        self.thread.finished.connect(self.cleanup)
        self.thread.start()

    def reply(self, text: str):
        self.chat.append(f"<b>ALVIS:</b> {text}")

    def cleanup(self):
        self.send.setEnabled(True)
        self.thread.deleteLater()
        self.worker.deleteLater()
        self.thread = None
        self.worker = None


def run():
    app = QApplication([])
    app.setStyle("Fusion")
    window = MainWindow()
    window.show()
    app.exec()
