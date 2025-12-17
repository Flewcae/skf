import sys
import threading
import time
import random
import requests
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QTableWidget, QTableWidgetItem, QLabel, QSpinBox,
    QHeaderView, QMessageBox
)
from PyQt5.QtCore import Qt, pyqtSignal, QObject
from PyQt5.QtGui import QColor
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# API Configuration
API_BASE_URL = "https://5cebc809bf1e.ngrok-free.app"
API_GET_BATCH = f"{API_BASE_URL}/api/get-product-batch/"
API_UPDATE_PRODUCT = f"{API_BASE_URL}/api/update-product/"
API_RESET_STUCK = f"{API_BASE_URL}/api/reset-stuck-products/"


class SessionSignals(QObject):
    """Oturum sinyalleri"""
    update_stats = pyqtSignal(int, str, int, int, int, int)  # session_id, status, processed, success, error, remaining
    finished = pyqtSignal(int)  # session_id


class ScraperSession:
    """Tek bir scraper oturumu"""
    
    def __init__(self, session_id, batch_limit, signals):
        self.session_id = session_id
        self.batch_limit = batch_limit
        self.signals = signals
        self.driver = None
        self.is_running = False
        self.thread = None
        
        # İstatistikler
        self.total_processed = 0
        self.total_success = 0
        self.total_error = 0
        self.remaining = 0
        
    def setup_driver(self):
        """ChromeDriver'ı yapılandır"""
        options = Options()
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36')
        options.add_argument('--window-size=1920,1080')
        options.add_argument('--start-maximized')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-gpu')
        
        self.driver = webdriver.Chrome(options=options)
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    
    def human_like_delay(self, min_sec=1, max_sec=3):
        """İnsan benzeri rastgele bekleme"""
        time.sleep(random.uniform(min_sec, max_sec))
    
    def accept_cookies(self, first_product=True):
        """Çerez popup'ını kabul et"""
        if not first_product or not self.driver:
            return
        
        try:
            cookie_button = WebDriverWait(self.driver, 5).until(
                EC.element_to_be_clickable((By.ID, "cmpbntyestxt"))
            )
            self.human_like_delay(0.5, 1.5)
            cookie_button.click()
            self.human_like_delay(1, 2)
        except:
            pass
    
    def get_category_hierarchy(self):
        """Breadcrumb'dan kategori hiyerarşisini al"""
        try:
            breadcrumb = self.driver.find_element(By.CSS_SELECTOR, "nav[aria-label='breadcrumb'] ol.breadcrumb")
            items = breadcrumb.find_elements(By.CSS_SELECTOR, "li.breadcrumb-item")
            
            categories = []
            found_products = False
            
            for item in items:
                try:
                    text = item.text.strip()
                    if text in ["Ürünler", "Products"]:
                        found_products = True
                        continue
                    if found_products and text:
                        categories.append(text)
                except:
                    continue
            
            return ", ".join(categories) if categories else ""
        except:
            return ""
    
    def get_product_batch(self):
        """API'den batch al"""
        try:
            response = requests.get(API_GET_BATCH, params={"limit": self.batch_limit}, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            if data.get("status") == "empty":
                return None
            
            return data
        except:
            return None
    
    def update_product_api(self, product_data):
        """Ürün verilerini API'ye gönder"""
        try:
            response = requests.post(API_UPDATE_PRODUCT, json=product_data, timeout=30)
            response.raise_for_status()
            return True
        except:
            return False
    
    def scrape_product(self, product_id, url, first_product=True):
        """Tek bir ürünü scrape et"""
        try:
            self.driver.get(url)
            self.human_like_delay(2, 4)
            
            self.accept_cookies(first_product)
            
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "h1.title.d-print-none"))
            )
            
            h1_element = self.driver.find_element(By.CSS_SELECTOR, "h1.title.d-print-none")
            code = h1_element.text.split('\n')[0].strip()
            
            name_element = h1_element.find_element(By.CSS_SELECTOR, "span.category")
            name = name_element.text.strip()
            
            image_url = ""
            try:
                img_element = self.driver.find_element(By.CSS_SELECTOR, 
                    "div.gallery swiper .swiper-wrapper .swiper-slide.swiper-slide-active img")
                image_url = img_element.get_attribute("src")
            except:
                try:
                    img_element = self.driver.find_element(By.CSS_SELECTOR, ".image-area .gallery img")
                    image_url = img_element.get_attribute("src")
                except:
                    pass
            
            desc_parts = []
            
            try:
                long_desc = self.driver.find_element(By.CSS_SELECTOR, "span.long-description")
                desc_parts.append(long_desc.text.strip())
            except:
                pass
            
            try:
                benefits_ul = self.driver.find_element(By.CSS_SELECTOR, "ul.benefits")
                benefits_items = benefits_ul.find_elements(By.TAG_NAME, "li")
                for item in benefits_items:
                    text = item.text.strip()
                    if text:
                        desc_parts.append(f"• {text}")
            except:
                pass
            
            desc = "\n".join(desc_parts)
            category_hierarchy = self.get_category_hierarchy()
            
            return {
                "id": product_id,
                "code": code,
                "name": name,
                "desc": desc,
                "image_url": image_url,
                "category_hierarchy": category_hierarchy,
                "status": "done"
            }
            
        except Exception as e:
            return {
                "id": product_id,
                "status": "error",
                "error": str(e)
            }
    
    def run(self):
        """Oturumu çalıştır"""
        self.is_running = True
        self.signals.update_stats.emit(
            self.session_id, "Başlatılıyor...", 
            self.total_processed, self.total_success, self.total_error, self.remaining
        )
        
        try:
            self.setup_driver()
            
            # Batch al
            self.signals.update_stats.emit(
                self.session_id, "Batch alınıyor...", 
                self.total_processed, self.total_success, self.total_error, self.remaining
            )
            
            batch_data = self.get_product_batch()
            
            if not batch_data:
                self.signals.update_stats.emit(
                    self.session_id, "Ürün yok", 
                    self.total_processed, self.total_success, self.total_error, 0
                )
                return
            
            products = batch_data.get("products", [])
            count = batch_data.get("count", 0)
            self.remaining = count
            
            self.signals.update_stats.emit(
                self.session_id, "Çalışıyor", 
                self.total_processed, self.total_success, self.total_error, self.remaining
            )
            
            # Her ürünü işle
            for idx, product in enumerate(products):
                if not self.is_running:
                    self.signals.update_stats.emit(
                        self.session_id, "Durduruldu", 
                        self.total_processed, self.total_success, self.total_error, self.remaining
                    )
                    return
                
                product_id = product.get("id")
                url = product.get("url")
                
                if not url or not product_id:
                    continue
                
                is_first = (self.total_processed == 0)
                
                result = self.scrape_product(product_id, url, first_product=is_first)
                
                if self.update_product_api(result):
                    if result.get("status") == "done":
                        self.total_success += 1
                    else:
                        self.total_error += 1
                else:
                    self.total_error += 1
                
                self.total_processed += 1
                self.remaining = count - (idx + 1)
                
                self.signals.update_stats.emit(
                    self.session_id, "Çalışıyor", 
                    self.total_processed, self.total_success, self.total_error, self.remaining
                )
                
                if idx < count - 1 and self.is_running:
                    time.sleep(random.uniform(2, 5))
            
            self.signals.update_stats.emit(
                self.session_id, "Tamamlandı", 
                self.total_processed, self.total_success, self.total_error, 0
            )
            
        except Exception as e:
            self.signals.update_stats.emit(
                self.session_id, f"Hata: {str(e)[:30]}", 
                self.total_processed, self.total_success, self.total_error, self.remaining
            )
        
        finally:
            if self.driver:
                try:
                    self.driver.quit()
                except:
                    pass
            self.is_running = False
            self.signals.finished.emit(self.session_id)
    
    def start(self):
        """Oturumu thread'de başlat"""
        self.thread = threading.Thread(target=self.run, daemon=True)
        self.thread.start()
    
    def stop(self):
        """Oturumu durdur"""
        self.is_running = False
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.sessions = {}
        self.next_session_id = 1
        self.init_ui()
    
    def init_ui(self):
        self.setWindowTitle("SKF Ürün Scraper - Multi Session")
        self.setGeometry(100, 100, 1000, 600)
        
        # Ana widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout()
        central_widget.setLayout(layout)
        
        # Üst kontrol paneli
        control_layout = QHBoxLayout()
        
        # Batch limit girişi
        control_layout.addWidget(QLabel("Ürün Limiti:"))
        self.batch_limit_spin = QSpinBox()
        self.batch_limit_spin.setMinimum(1)
        self.batch_limit_spin.setMaximum(1000)
        self.batch_limit_spin.setValue(500)
        self.batch_limit_spin.setFixedWidth(100)
        control_layout.addWidget(self.batch_limit_spin)
        
        control_layout.addStretch()
        
        # Yeni oturum butonu
        self.new_session_btn = QPushButton("➕ Yeni Oturum Başlat")
        self.new_session_btn.clicked.connect(self.start_new_session)
        self.new_session_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                padding: 10px 20px;
                font-size: 14px;
                font-weight: bold;
                border: none;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        control_layout.addWidget(self.new_session_btn)
        
        # Tümünü durdur butonu
        self.stop_all_btn = QPushButton("⏹ Tümünü Durdur")
        self.stop_all_btn.clicked.connect(self.stop_all_sessions)
        self.stop_all_btn.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                padding: 10px 20px;
                font-size: 14px;
                font-weight: bold;
                border: none;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #da190b;
            }
        """)
        control_layout.addWidget(self.stop_all_btn)
        
        # Reset stuck butonu
        self.reset_btn = QPushButton("🔄 Reset Stuck")
        self.reset_btn.clicked.connect(self.reset_stuck_products)
        self.reset_btn.setStyleSheet("""
            QPushButton {
                background-color: #ff9800;
                color: white;
                padding: 10px 20px;
                font-size: 14px;
                font-weight: bold;
                border: none;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #e68900;
            }
        """)
        control_layout.addWidget(self.reset_btn)
        
        layout.addLayout(control_layout)
        
        # Oturum tablosu
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "Oturum ID", "Durum", "İşlenen", "Başarılı", "Hatalı", "Kalan", "İşlemler"
        ])
        
        # Tablo ayarları
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.ResizeToContents)
        
        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet("""
            QTableWidget {
                background-color: white;
                alternate-background-color: #f5f5f5;
                gridline-color: #d0d0d0;
            }
            QHeaderView::section {
                background-color: #2196F3;
                color: white;
                padding: 8px;
                font-weight: bold;
                border: none;
            }
        """)
        
        layout.addWidget(self.table)
        
        # Alt bilgi paneli
        info_layout = QHBoxLayout()
        self.info_label = QLabel("Toplam Oturum: 0 | Aktif: 0")
        self.info_label.setStyleSheet("font-size: 12px; padding: 5px;")
        info_layout.addWidget(self.info_label)
        info_layout.addStretch()
        
        layout.addLayout(info_layout)
    
    def start_new_session(self):
        """Yeni oturum başlat"""
        session_id = self.next_session_id
        self.next_session_id += 1
        
        batch_limit = self.batch_limit_spin.value()
        
        # Sinyal nesnesi
        signals = SessionSignals()
        signals.update_stats.connect(self.update_session_stats)
        signals.finished.connect(self.session_finished)
        
        # Oturum oluştur
        session = ScraperSession(session_id, batch_limit, signals)
        self.sessions[session_id] = session
        
        # Tabloya ekle
        row = self.table.rowCount()
        self.table.insertRow(row)
        
        self.table.setItem(row, 0, QTableWidgetItem(f"#{session_id}"))
        self.table.setItem(row, 1, QTableWidgetItem("Başlatılıyor..."))
        self.table.setItem(row, 2, QTableWidgetItem("0"))
        self.table.setItem(row, 3, QTableWidgetItem("0"))
        self.table.setItem(row, 4, QTableWidgetItem("0"))
        self.table.setItem(row, 5, QTableWidgetItem("0"))
        
        # Durdur butonu
        stop_btn = QPushButton("⏹ Durdur")
        stop_btn.clicked.connect(lambda: self.stop_session(session_id))
        stop_btn.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                padding: 5px 10px;
                border: none;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #da190b;
            }
        """)
        self.table.setCellWidget(row, 6, stop_btn)
        
        # Oturumu başlat
        session.start()
        
        self.update_info_label()
    
    def update_session_stats(self, session_id, status, processed, success, error, remaining):
        """Oturum istatistiklerini güncelle"""
        # Tablodan satırı bul
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            if item and item.text() == f"#{session_id}":
                self.table.item(row, 1).setText(status)
                self.table.item(row, 2).setText(str(processed))
                self.table.item(row, 3).setText(str(success))
                self.table.item(row, 4).setText(str(error))
                self.table.item(row, 5).setText(str(remaining))
                
                # Durum rengini ayarla
                status_item = self.table.item(row, 1)
                if "Çalışıyor" in status:
                    status_item.setBackground(QColor(76, 175, 80, 50))  # Yeşil
                elif "Tamamlandı" in status:
                    status_item.setBackground(QColor(33, 150, 243, 50))  # Mavi
                elif "Hata" in status or "Durduruldu" in status:
                    status_item.setBackground(QColor(244, 67, 54, 50))  # Kırmızı
                
                break
    
    def session_finished(self, session_id):
        """Oturum tamamlandı"""
        # İlgili satırı bul
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            if item and item.text() == f"#{session_id}":
                # Durdur butonunu kaldır
                self.table.removeCellWidget(row, 6)
                break

        self.update_info_label()
    
    def stop_session(self, session_id):
        """Belirli bir oturumu durdur"""
        if session_id in self.sessions:
            self.sessions[session_id].stop()
            self.update_info_label()
    
    def stop_all_sessions(self):
        """Tüm oturumları durdur"""
        reply = QMessageBox.question(
            self, 'Onayla', 
            'Tüm oturumları durdurmak istediğinizden emin misiniz?',
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            for session in self.sessions.values():
                session.stop()
            self.update_info_label()
    
    def reset_stuck_products(self):
        """Takılı ürünleri sıfırla"""
        try:
            response = requests.get(API_RESET_STUCK, timeout=30)
            response.raise_for_status()
            data = response.json()
            count = data.get('reset_count', 0)
            QMessageBox.information(self, "Başarılı", f"{count} takılı ürün sıfırlandı!")
        except Exception as e:
            QMessageBox.warning(self, "Hata", f"Reset işlemi başarısız: {str(e)}")
    
    def update_info_label(self):
        """Alt bilgi etiketini güncelle"""
        total = len(self.sessions)
        active = sum(1 for s in self.sessions.values() if s.is_running)
        self.info_label.setText(f"Toplam Oturum: {total} | Aktif: {active}")


def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()