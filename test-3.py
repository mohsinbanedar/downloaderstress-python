import sys
import requests
from bs4 import BeautifulSoup
import os
import time
from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QPushButton, QLineEdit, QLabel, QFileDialog,
    QProgressBar, QTextEdit, QMessageBox, QHBoxLayout, QFormLayout, QSpacerItem, QSizePolicy
)
from PyQt5.QtGui import QIcon, QFont, QColor, QPalette
from urllib.parse import urlparse, urlunparse, quote
import datetime


class DownloadThread(QThread):
    progress_signal = pyqtSignal(int)
    overall_progress_signal = pyqtSignal(int)
    log_signal = pyqtSignal(str)
    complete_signal = pyqtSignal()
    canceled_signal = pyqtSignal()
    file_count_signal = pyqtSignal(int)
    time_remaining_signal = pyqtSignal(str)

    def __init__(self, base_url, dest_folder, username=None, password=None, is_single_file=False):
        super().__init__()
        self.base_url = base_url
        self.dest_folder = dest_folder
        self.username = username
        self.password = password
        self.total_files = 0
        self.downloaded_files = 0
        self.total_size = 0
        self.retry_delay = 60
        self.completed_files = set()
        self.pending_files = []
        self.progress_file = os.path.join(dest_folder, "download_progress.txt")
        self._is_paused = False
        self._is_canceled = False
        self.is_single_file = is_single_file

        if os.path.exists(self.progress_file):
            with open(self.progress_file, 'r') as pf:
                self.completed_files = set(line.strip() for line in pf)

        if not os.path.exists(dest_folder):
            os.makedirs(dest_folder)

    def run(self):
        try:
            if self.is_single_file:
                self.download_file(self.base_url, self.dest_folder)
            else:
                self.total_files = self.count_files(self.base_url)
                self.file_count_signal.emit(self.total_files)
                self.download_directory(self.base_url, self.dest_folder)
            if not self._is_canceled:
                self.complete_signal.emit()
        except Exception as e:
            self.log_signal.emit(f"An error occurred: {e}")

    def count_files(self, url):
        total = 0
        try:
            response = requests.get(url)
            if response.status_code != 200:
                return total

            soup = BeautifulSoup(response.text, 'html.parser')
            links = soup.find_all('a')

            for link in links:
                href = link.get('href')
                if href in ('../', './'):
                    continue

                full_url = url + href

                if href.endswith('/'):
                    total += self.count_files(full_url)
                else:
                    total += 1

        except requests.RequestException:
            pass

        return total

    def download_file(self, url, dest_folder):
        if self._is_canceled:
            self.canceled_signal.emit()
            return

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

        filename = url.split('/')[-1]
        file_path = os.path.join(dest_folder, filename)

        if file_path in self.completed_files:
            self.log_signal.emit(f"Skipping already downloaded file: {file_path}")
            return

        start_time = time.time()

        while True:
            if self._is_canceled:
                self.canceled_signal.emit()
                return

            try:
                auth = (self.username, self.password) if self.username and self.password else None
                response = requests.get(url, stream=True, headers=headers, auth=auth, allow_redirects=False)

                # Handle redirect manually if status code is 302
                if response.status_code == 302:
                    redirect_url = response.headers['Location']
                    self.log_signal.emit(f"Redirected to: {redirect_url}")
                    url = redirect_url  # Update the URL to the redirected location
                    continue  # Retry with the new URL

                if response.status_code == 200:
                    file_size = int(response.headers.get('content-length', 0))
                    with open(file_path, 'wb') as f:
                        for chunk in response.iter_content(1024):
                            if chunk:
                                f.write(chunk)
                                self.progress_signal.emit(int(f.tell() / file_size * 100))

                            while self._is_paused:
                                time.sleep(0.1)

                            if self._is_canceled:
                                self.canceled_signal.emit()
                                return

                    elapsed_time = time.time() - start_time
                    if file_size > 0:
                        time_remaining = elapsed_time * (file_size - os.path.getsize(file_path)) / os.path.getsize(file_path)
                        self.time_remaining_signal.emit(
                            f"Time remaining for current file: {str(datetime.timedelta(seconds=int(time_remaining)))}"
                        )

                    self.downloaded_files += 1
                    self.total_size += file_size

                    overall_progress = int(self.downloaded_files / self.total_files * 100) if self.total_files > 0 else 100
                    self.overall_progress_signal.emit(overall_progress)

                    self.log_signal.emit(f"Downloaded: {file_path} - {file_size / (1024 * 1024):.2f} MB")
                    with open(self.progress_file, 'a') as pf:
                        pf.write(file_path + '\n')
                    self.completed_files.add(file_path)
                    break
                else:
                    self.log_signal.emit(f"Failed to download {url}: {response.status_code}")
                    self.pending_files.append(url)
                    break
            except requests.RequestException as e:
                self.log_signal.emit(f"Network issue encountered for {url}: {e}. Retrying in {self.retry_delay} seconds...")
                time.sleep(self.retry_delay)

    def download_directory(self, url, dest_folder):
        while True:
            if self._is_canceled:
                self.canceled_signal.emit()
                return

            try:
                response = requests.get(url)
                if response.status_code != 200:
                    self.log_signal.emit(f"Failed to access {url}: {response.status_code}")
                    return

                soup = BeautifulSoup(response.text, 'html.parser')
                links = soup.find_all('a')

                for link in links:
                    href = link.get('href')
                    if href in ('../', './'):
                        continue

                    full_url = url + href
                    new_dest_folder = os.path.join(dest_folder, href)

                    if href.endswith('/'):
                        if not os.path.exists(new_dest_folder):
                            os.makedirs(new_dest_folder)
                        self.log_signal.emit(f"Entering directory: {new_dest_folder}")
                        self.download_directory(full_url, new_dest_folder)
                    else:
                        self.log_signal.emit(f"Downloading file: {href} from {new_dest_folder}")
                        self.download_file(full_url, dest_folder)
                break
            except requests.RequestException as e:
                self.log_signal.emit(f"Network issue encountered for directory {url}: {e}. Retrying in {self.retry_delay} seconds...")
                time.sleep(self.retry_delay)

    def pause(self):
        self._is_paused = True

    def resume(self):
        self._is_paused = False

    def cancel(self):
        self._is_canceled = True


class DownloaderApp(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.setWindowTitle('Stress Free Downloader')
        self.setWindowIcon(QIcon('logo.png'))
        self.setGeometry(300, 200, 700, 700)

        main_layout = QVBoxLayout()

        form_layout = QFormLayout()
        self.url_input = QLineEdit(self)
        self.url_input.setPlaceholderText('Enter the URL you want to download from...')
        form_layout.addRow(QLabel('URL:'), self.url_input)

        self.username_input = QLineEdit(self)
        self.username_input.setPlaceholderText('Enter username (if required)')
        form_layout.addRow(QLabel('Username:'), self.username_input)

        self.password_input = QLineEdit(self)
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setPlaceholderText('Enter password (if required)')
        form_layout.addRow(QLabel('Password:'), self.password_input)

        self.final_url_input = QLineEdit(self)
        self.final_url_input.setPlaceholderText('Final URL (editable after check)...')
        self.final_url_input.setReadOnly(True)
        form_layout.addRow(QLabel('Final URL:'), self.final_url_input)

        path_layout = QHBoxLayout()
        self.path_input = QLineEdit(self)
        self.path_input.setPlaceholderText('Select destination folder...')
        self.browse_button = QPushButton('Browse...')
        self.browse_button.clicked.connect(self.browse_folder)
        path_layout.addWidget(self.path_input)
        path_layout.addWidget(self.browse_button)
        form_layout.addRow(QLabel('Destination Path:'), path_layout)

        self.check_button = QPushButton('Check URL')
        self.check_button.clicked.connect(self.check_url)
        self.download_button = QPushButton('Download')
        self.download_button.setEnabled(False)
        self.download_button.clicked.connect(self.start_download)
        self.pause_button = QPushButton('Pause')
        self.pause_button.setEnabled(False)
        self.pause_button.clicked.connect(self.pause_download)
        self.resume_button = QPushButton('Resume')
        self.resume_button.setEnabled(False)
        self.resume_button.clicked.connect(self.resume_download)
        self.cancel_button = QPushButton('Cancel')
        self.cancel_button.setEnabled(False)
        self.cancel_button.clicked.connect(self.cancel_download)

        self.progress = QProgressBar(self)
        self.overall_progress = QProgressBar(self)

        self.time_remaining_label = QLabel(self)
        self.time_remaining_label.setText("Time remaining: Calculating...")

        self.log_output = QTextEdit(self)
        self.log_output.setReadOnly(True)

        button_layout = QHBoxLayout()
        button_layout.addWidget(self.check_button)
        button_layout.addWidget(self.download_button)
        button_layout.addWidget(self.pause_button)
        button_layout.addWidget(self.resume_button)
        button_layout.addWidget(self.cancel_button)

        main_layout.addLayout(form_layout)
        main_layout.addWidget(QLabel("File Progress:"))
        main_layout.addWidget(self.progress)
        main_layout.addWidget(QLabel("Overall Progress:"))
        main_layout.addWidget(self.overall_progress)
        main_layout.addWidget(self.time_remaining_label)
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

    def log(self, message):
        self.log_output.append(message)
        self.log_output.ensureCursorVisible()

    def check_url(self):
        url = self.url_input.text()

        if not url:
            QMessageBox.warning(self, "Input Error", "Please enter a URL.")
            return

        try:
            response = requests.head(url, allow_redirects=False)
            if response.status_code == 200:
                self.log("URL is reachable.")
                self.download_button.setEnabled(True)
            elif response.status_code == 302:
                redirect_url = response.headers['Location']
                self.final_url_input.setText(redirect_url)
                self.log(f"URL redirected to {redirect_url}")
                self.download_button.setEnabled(True)
            elif response.status_code == 401:
                self.log("Authentication required. Please enter username and password.")
            else:
                self.log(f"Error: Received status code {response.status_code}")
        except requests.RequestException as e:
            self.log(f"Error: {e}")

    def start_download(self):
        url = self.final_url_input.text() or self.url_input.text()  # Use the final URL if redirected
        dest_folder = self.path_input.text()

        if not dest_folder:
            QMessageBox.warning(self, "Input Error", "Please select a destination folder.")
            return

        username = self.username_input.text()
        password = self.password_input.text()

        is_single_file = not url.endswith('/')

        self.thread = DownloadThread(url, dest_folder, username, password, is_single_file=is_single_file)
        self.thread.progress_signal.connect(self.progress.setValue)
        self.thread.overall_progress_signal.connect(self.overall_progress.setValue)
        self.thread.log_signal.connect(self.log)
        self.thread.file_count_signal.connect(self.update_file_count)
        self.thread.time_remaining_signal.connect(self.update_time_remaining)
        self.thread.complete_signal.connect(self.download_complete)
        self.thread.canceled_signal.connect(self.download_canceled)
        self.thread.start()

        self.download_button.setEnabled(False)
        self.pause_button.setEnabled(True)
        self.cancel_button.setEnabled(True)

    def update_file_count(self, count):
        self.log(f"Total files to download: {count}")

    def update_time_remaining(self, time_remaining):
        self.time_remaining_label.setText(time_remaining)

    def pause_download(self):
        if self.thread.isRunning():
            self.thread.pause()
            self.pause_button.setEnabled(False)
            self.resume_button.setEnabled(True)

    def resume_download(self):
        if self.thread.isRunning():
            self.thread.resume()
            self.resume_button.setEnabled(False)
            self.pause_button.setEnabled(True)

    def cancel_download(self):
        if self.thread.isRunning():
            self.thread.cancel()
            self.cancel_button.setEnabled(False)
            self.pause_button.setEnabled(False)
            self.resume_button.setEnabled(False)

    def download_complete(self):
        self.log("Download complete.")
        self.cancel_button.setEnabled(False)
        self.pause_button.setEnabled(False)
        self.resume_button.setEnabled(False)
        self.download_button.setEnabled(True)

    def download_canceled(self):
        self.log("Download canceled.")
        self.cancel_button.setEnabled(False)
        self.pause_button.setEnabled(False)
        self.resume_button.setEnabled(False)
        self.download_button.setEnabled(True)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = DownloaderApp()
    ex.show()
    sys.exit(app.exec_())
