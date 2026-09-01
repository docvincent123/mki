from __future__ import annotations

from PySide6.QtCore import QObject, QThread, Signal
from PySide6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QLineEdit, QPushButton, QLabel

from .agent import Agent
from .voice import Voice


class Worker(QObject):
    done = Signal(str)
    def __init__(self, agent: Agent, text: str):
        super().__init__(); self.agent = agent; self.text = text
    def run(self):
        try: self.done.emit(self.agent.ask(self.text))
        except Exception as exc: self.done.emit(f"Помилка ALVIS: {exc}")


class VoiceWorker(QObject):
    done = Signal(str)
    def __init__(self, voice: Voice):
        super().__init__(); self.voice = voice
    def run(self):
        try: self.done.emit(self.voice.record_and_transcribe())
        except Exception as exc: self.done.emit(f"[VOICE_ERROR] {exc}")


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ALVIS")
        self.resize(900, 650)
        self.agent = Agent(); self.voice = Voice()
        self.thread = self.worker = None
        self.voice_thread = self.voice_worker = None
        self.pending_voice = None

        root = QWidget(); layout = QVBoxLayout(root)
        title = QLabel("ALVIS  •  Windows AI Assistant")
        title.setStyleSheet("font-size: 22px; font-weight: 700; padding: 8px;")
        self.chat = QTextEdit(); self.chat.setReadOnly(True)
        self.input = QLineEdit(); self.input.setPlaceholderText("Напиши команду українською або англійською…")
        row = QHBoxLayout()
        self.send = QPushButton("Виконати")
        self.voice_button = QPushButton("🎙 Говорити")
        self.send.clicked.connect(self.submit); self.voice_button.clicked.connect(self.record_voice)
        self.input.returnPressed.connect(self.submit)
        row.addWidget(self.input, 1); row.addWidget(self.voice_button); row.addWidget(self.send)
        layout.addWidget(title); layout.addWidget(self.chat, 1); layout.addLayout(row)
        self.setCentralWidget(root)
        self.chat.append("<b>ALVIS:</b> Онлайн. Чим допомогти?")

    def submit(self):
        text = self.input.text().strip()
        if not text or self.thread or self.voice_thread: return
        self.input.clear(); self.chat.append(f"<b>Ти:</b> {text}"); self.send.setEnabled(False)
        self.thread = QThread(); self.worker = Worker(self.agent, text); self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run); self.worker.done.connect(self.reply)
        self.worker.done.connect(self.thread.quit); self.thread.finished.connect(self.cleanup); self.thread.start()

    def record_voice(self):
        if self.thread or self.voice_thread: return
        self.voice_button.setEnabled(False); self.chat.append("<b>ALVIS:</b> Слухаю 6 секунд…")
        self.voice_thread = QThread(); self.voice_worker = VoiceWorker(self.voice); self.voice_worker.moveToThread(self.voice_thread)
        self.voice_thread.started.connect(self.voice_worker.run); self.voice_worker.done.connect(self.voice_result)
        self.voice_worker.done.connect(self.voice_thread.quit); self.voice_thread.finished.connect(self.voice_cleanup)
        self.voice_thread.start()

    def voice_result(self, text: str):
        if text.startswith("[VOICE_ERROR]"):
            self.chat.append(f"<b>ALVIS:</b> {text}"); return
        self.pending_voice = text
        self.input.setText(text)
        self.chat.append(f"<b>Ти:</b> {text}")

    def voice_cleanup(self):
        self.voice_button.setEnabled(True)
        self.voice_thread.deleteLater(); self.voice_worker.deleteLater()
        self.voice_thread = self.voice_worker = None
        if self.pending_voice:
            text = self.pending_voice; self.pending_voice = None
            self.input.setText(text); self.submit()

    def reply(self, text: str):
        self.chat.append(f"<b>ALVIS:</b> {text}")
        self.voice.speak(text)

    def cleanup(self):
        self.send.setEnabled(True)
        self.thread.deleteLater(); self.worker.deleteLater()
        self.thread = self.worker = None


def run():
    app = QApplication([]); app.setStyle("Fusion")
    window = MainWindow(); window.show(); app.exec()
