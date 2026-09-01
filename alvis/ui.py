from __future__ import annotations

from PySide6.QtCore import QObject, QThread, Signal, Qt
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QTextEdit,
    QLineEdit, QPushButton, QLabel, QDialog, QFormLayout, QDialogButtonBox,
    QMessageBox, QTabWidget, QPlainTextEdit
)

from .agent import Agent
from .config import get_openai_key, get_github_token, save_secret, MODEL
from .voice import Voice


class ApiDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("ALVIS — API Keys")
        self.resize(620, 330)
        layout = QVBoxLayout(self)
        tabs = QTabWidget()

        api = QWidget(); form = QFormLayout(api)
        self.openai = QLineEdit(); self.openai.setEchoMode(QLineEdit.Password)
        self.openai.setText(get_openai_key())
        self.openai.setPlaceholderText("sk-…")
        self.github = QLineEdit(); self.github.setEchoMode(QLineEdit.Password)
        self.github.setText(get_github_token())
        self.github.setPlaceholderText("ghp_… / github_pat_…")
        form.addRow("OpenAI API key:", self.openai)
        form.addRow("GitHub token:", self.github)
        note = QLabel("Ключі зберігаються локально; на Windows використовується DPAPI.\nВони не показуються в чаті та не записуються в Git.")
        note.setWordWrap(True); form.addRow(note)
        tabs.addTab(api, "🔐 API Keys")

        info = QWidget(); info_layout = QVBoxLayout(info)
        info_layout.addWidget(QLabel("ALVIS V2 + V3"))
        info_layout.addWidget(QLabel(
            "V2: web research, screenshot, UI Automation, mouse/keyboard, apps.\n"
            "V3: GitHub repository/file/issue inspection, development commands, iterative debugging.\n"
            f"Модель: {MODEL}"
        ))
        info_layout.addStretch(); tabs.addTab(info, "ℹ About")
        layout.addWidget(tabs)
        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.save); buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def save(self):
        save_secret("OPENAI_API_KEY", self.openai.text())
        save_secret("GITHUB_TOKEN", self.github.text())
        QMessageBox.information(self, "ALVIS", "Ключі збережено. ALVIS готовий до роботи.")
        self.accept()


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
        self.setWindowTitle("ALVIS V3")
        self.resize(1050, 720)
        self.setMinimumSize(820, 560)
        self.agent = Agent(); self.voice = Voice()
        self.thread = self.worker = None
        self.voice_thread = self.voice_worker = None
        self.pending_voice = None

        root = QWidget(); layout = QVBoxLayout(root)
        top = QHBoxLayout()
        title = QLabel("ALVIS  •  Windows AI Agent")
        title.setStyleSheet("font-size: 22px; font-weight: 700; padding: 8px;")
        self.status = QLabel(); self.refresh_status()
        self.settings = QPushButton("⚙ API Keys")
        self.settings.clicked.connect(self.open_settings)
        self.clear = QPushButton("New Chat")
        self.clear.clicked.connect(self.new_chat)
        top.addWidget(title); top.addStretch(); top.addWidget(self.status); top.addWidget(self.clear); top.addWidget(self.settings)

        self.chat = QTextEdit(); self.chat.setReadOnly(True)
        self.chat.setStyleSheet("QTextEdit { font-size: 14px; padding: 10px; }")
        self.input = QLineEdit(); self.input.setPlaceholderText("Команда українською або англійською… Напр.: 'проаналізуй цей проект і знайди помилку в build'")
        row = QHBoxLayout()
        self.send = QPushButton("▶ Виконати")
        self.voice_button = QPushButton("🎙 Говорити")
        self.send.clicked.connect(self.submit); self.voice_button.clicked.connect(self.record_voice)
        self.input.returnPressed.connect(self.submit)
        row.addWidget(self.input, 1); row.addWidget(self.voice_button); row.addWidget(self.send)
        layout.addLayout(top); layout.addWidget(self.chat, 1); layout.addLayout(row)
        self.setCentralWidget(root)
        self.chat.append("<b>ALVIS:</b> Онлайн. Я готовий шукати інформацію, керувати Windows, працювати з GitHub і допомагати з build/debug.")
        if not get_openai_key():
            self.chat.append("<b>ALVIS:</b> <span style='color:#d97706'>[OPENAI_ERROR] OPENAI_API_KEY is not configured.</span> Натисни <b>⚙ API Keys</b>, встав ключ і збережи.")

    def refresh_status(self):
        self.status.setText("● API OK" if get_openai_key() else "● API не налаштований")

    def open_settings(self):
        if ApiDialog(self).exec():
            self.agent.refresh_credentials(); self.refresh_status()
            self.chat.append("<b>ALVIS:</b> Налаштування API оновлено.")

    def new_chat(self):
        self.agent.clear_context(); self.chat.clear(); self.chat.append("<b>ALVIS:</b> Новий діалог. Контекст очищено.")

    def submit(self):
        text = self.input.text().strip()
        if not text or self.thread or self.voice_thread: return
        if not get_openai_key():
            self.chat.append("<b>ALVIS:</b> [OPENAI_ERROR] API key не налаштований. Натисни ⚙ API Keys.")
            self.open_settings(); return
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
            self.chat.append(f"<b>ALVIS:</b> <span style='color:#b91c1c'>{text}</span>")
            if "API_KEY" in text: self.open_settings()
            return
        self.pending_voice = text; self.input.setText(text); self.chat.append(f"<b>Ти:</b> {text}")

    def voice_cleanup(self):
        self.voice_button.setEnabled(True)
        self.voice_thread.deleteLater(); self.voice_worker.deleteLater()
        self.voice_thread = self.voice_worker = None
        if self.pending_voice:
            text = self.pending_voice; self.pending_voice = None; self.input.setText(text); self.submit()

    def reply(self, text: str):
        safe = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br>")
        self.chat.append(f"<b>ALVIS:</b> {safe}")
        if text.startswith("[OPENAI_ERROR]") and "API" in text: self.open_settings()
        self.voice.speak(text)

    def cleanup(self):
        self.send.setEnabled(True)
        self.thread.deleteLater(); self.worker.deleteLater(); self.thread = self.worker = None


def run():
    app = QApplication([]); app.setStyle("Fusion")
    window = MainWindow(); window.show(); app.exec()
