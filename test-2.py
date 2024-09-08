import sys
import requests
import os
import time
from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QPushButton, QLineEdit, QLabel, QFileDialog,
    QProgressBar, QTextEdit, QMessageBox, QHBoxLayout, QFormLayout, QSizePolicy, QSpacerItem
)
from PyQt5.QtGui import QIcon, QFont, QColor, QPalette


class DownloadThread(QThread):
    progress_signal = pyqtSignal(int)
    log_signal = pyqtSignal(str)
    complete_signal = pyqtSignal()

    def __init__(self, url, dest_folder):
        super().__init__()
        self.url = url
        self.dest_folder = dest_folder
        self._is_canceled = False

    def run(self):
        try:
            self.download_file(self.url, self.dest_folder)
            if not self._is_canceled:
                self.complete_signal.emit()
        except Exception as e:
            self.log_signal.emit(f"An error occurred: {e}")

    def download_file(self, url, dest_folder):
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

        response = requests.get(url, stream=True, headers=headers)
        if response.status_code == 200:
            total_size = int(response.headers.get('content-length', 0))
            filename = url.split('/')[-1]
            file_path = os.path.join(dest_folder, filename)
            start_time = time.time()

            with open(file_path, 'wb') as file:
                for data in response.iter_content(1024):
                    if self._is_canceled:
                        self.log_signal.emit("Download canceled.")
                        return
                    file.write(data)
                    downloaded_size = file.tell()
                    self.progress_signal.emit(int(downloaded_size / total_size * 100))

            elapsed_time = time.time() - start_time
            self.log_signal.emit(f"Download completed: {file_path} in {elapsed_time:.2f} seconds.")
        else:
            self.log_signal.emit(f"Failed to download file: {response.status_code}")

    def cancel(self):
        self._is_canceled = True


class DownloaderApp(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.setWindowTitle('Stress-Free Downloader')
        self.setWindowIcon(QIcon('logo.png'))
        self.setGeometry(300, 200, 700, 400)

        main_layout = QVBoxLayout()

        form_layout = QFormLayout()
        self.url_input = QLineEdit(self)
        self.url_input.setPlaceholderText('Enter the URL you want to download from...')
        form_layout.addRow(QLabel('URL:'), self.url_input)

        path_layout = QHBoxLayout()
        self.path_input = QLineEdit(self)
        self.path_input.setPlaceholderText('Select destination folder...')
        self.browse_button = QPushButton('Browse...')
        self.browse_button.clicked.connect(self.browse_folder)
        path_layout.addWidget(self.path_input)
        path_layout.addWidget(self.browse_button)
        form_layout.addRow(QLabel('Destination Path:'), path_layout)

        self.download_button = QPushButton('Download')
        self.download_button.setEnabled(False)
        self.download_button.clicked.connect(self.start_download)
        self.cancel_button = QPushButton('Cancel')
        self.cancel_button.setEnabled(False)
        self.cancel_button.clicked.connect(self.cancel_download)

        self.progress = QProgressBar(self)
        self.log_output = QTextEdit(self)
        self.log_output.setReadOnly(True)

        button_layout = QHBoxLayout()
        button_layout.addWidget(self.download_button)
        button_layout.addWidget(self.cancel_button)

        main_layout.addLayout(form_layout)
        main_layout.addWidget(QLabel("Progress:"))
        main_layout.addWidget(self.progress)
        main_layout.addLayout(button_layout)
        main_layout.addWidget(self.log_output)

        footer_layout = QHBoxLayout()
        footer_layout.addSpacerItem(QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))

        created_by_label = QLabel('Created by Mohsin Banedar')
        created_by_label.setFont(QFont('Arial', 12, QFont.Bold))
        palette = created_by_label.palette()
        palette.setColor(QPalette.WindowText, QColor('black'))
        created_by_label.setPalette(palette)

        footer_layout.addWidget(created_by_label)
        main_layout.addLayout(footer_layout)

        self.setLayout(main_layout)

        self.setStyleSheet("""
        QLabel {
            color: black;
        }
        QPushButton {
            background-color: #4CAF50;
            color: white;
            border-radius: 5px;
            padding: 5px;
        }
        QPushButton:disabled {
            background-color: #d3d3d3;
            color: #808080;
        }
        QProgressBar {
            text-align: center;
            color: white;
        }
        QProgressBar::chunk {
            background-color: #76c7c0;
        }
        QTextEdit {
            background-color: #ffffff;
            color: #000000;
        }
        """)

    def browse_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Folder")
        if folder:
            self.path_input.setText(folder)
            self.download_button.setEnabled(True)

    def log(self, message):
        self.log_output.append(message)
        self.log_output.ensureCursorVisible()

    def start_download(self):
        url = self.url_input.text()
        dest_folder = self.path_input.text()

        if not url or not dest_folder:
            QMessageBox.warning(self, "Input Error", "Please enter a URL and select a destination folder.")
            return

        self.thread = DownloadThread(url, dest_folder)
        self.thread.progress_signal.connect(self.progress.setValue)
        self.thread.log_signal.connect(self.log)
        self.thread.complete_signal.connect(self.download_complete)
        self.thread.start()

        self.download_button.setEnabled(False)
        self.cancel_button.setEnabled(True)

    def cancel_download(self):
        if self.thread.isRunning():
            self.thread.cancel()
            self.cancel_button.setEnabled(False)
            self.download_button.setEnabled(True)

    def download_complete(self):
        self.log("Download complete.")
        self.cancel_button.setEnabled(False)
        self.download_button.setEnabled(True)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = DownloaderApp()
    ex.show()
    sys.exit(app.exec_())
