import json
import time
import random
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# API Configuration
API_BASE_URL = "https://342a4fd57213.ngrok-free.app"
API_GET_BATCH = f"{API_BASE_URL}/api/get-product-batch/"
API_UPDATE_PRODUCT = f"{API_BASE_URL}/api/update-product/"
API_RESET_STUCK = f"{API_BASE_URL}/api/reset-stuck-products/"

def setup_driver():
    """Bot tespitini zorlaştırmak için ChromeDriver'ı yapılandır"""
    options = Options()
    
    # Bot tespitini zorlaştıran ayarlar
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    
    # User agent ayarla
    options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36')
    
    # Pencere boyutu
    options.add_argument('--window-size=1920,1080')
    options.add_argument('--start-maximized')
    
    # Diğer ayarlar
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-gpu')
    
    driver = webdriver.Chrome(options=options)
    
    # WebDriver özelliğini gizle
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    
    return driver

def human_like_delay(min_sec=1, max_sec=3):
    """İnsan benzeri rastgele bekleme"""
    time.sleep(random.uniform(min_sec, max_sec))

def accept_cookies(driver, first_product=True):
    """Çerez popup'ını kabul et (sadece ilk üründe)"""
    if not first_product:
        return
    
    try:
        # Çerez butonunu bekle ve tıkla
        cookie_button = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.ID, "cmpbntyestxt"))
        )
        human_like_delay(0.5, 1.5)
        cookie_button.click()
        print("✓ Çerezler kabul edildi")
        human_like_delay(1, 2)
    except TimeoutException:
        print("ℹ Çerez popup'ı bulunamadı")
    except Exception as e:
        print(f"⚠ Çerez kabul edilirken hata: {e}")

def get_category_hierarchy(driver):
    """Breadcrumb'dan kategori hiyerarşisini al"""
    try:
        # Breadcrumb container'ı bul
        breadcrumb = driver.find_element(By.CSS_SELECTOR, "nav[aria-label='breadcrumb'] ol.breadcrumb")
        
        # Tüm breadcrumb item'larını al
        items = breadcrumb.find_elements(By.CSS_SELECTOR, "li.breadcrumb-item")
        
        # "Ürünler"den sonraki tüm kategorileri topla
        categories = []
        found_products = False
        
        for item in items:
            try:
                text = item.text.strip()
                
                # "Ürünler" veya "Products" bulundu mu?
                if text in ["Ürünler", "Products"]:
                    found_products = True
                    continue
                
                # Ürünler'den sonraki kategorileri ekle
                if found_products and text:
                    categories.append(text)
            except:
                continue
        
        return ", ".join(categories) if categories else ""
    except Exception as e:
        print(f"⚠ Kategori hiyerarşisi alınırken hata: {e}")
        return ""

def get_product_batch(limit=500):
    """API'den işlenecek ürün batch'ini çek"""
    try:
        response = requests.get(API_GET_BATCH, params={"limit": limit}, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        if data.get("status") == "empty":
            return None
        
        return data
    except Exception as e:
        print(f"✗ Batch alınırken hata: {e}")
        return None

def update_product_api(product_data):
    """Ürün verilerini API'ye gönder"""
    try:
        response = requests.post(
            API_UPDATE_PRODUCT,
            json=product_data,
            timeout=30
        )
        response.raise_for_status()
        return True
    except Exception as e:
        print(f"✗ Ürün güncellenirken hata: {e}")
        return False

def reset_stuck_products():
    """Takılı kalmış ürünleri sıfırla"""
    try:
        response = requests.get(API_RESET_STUCK, timeout=30)
        response.raise_for_status()
        data = response.json()
        print(f"✓ {data.get('reset_count', 0)} takılı ürün sıfırlandı")
        return True
    except Exception as e:
        print(f"✗ Reset işlemi başarısız: {e}")
        return False

def scrape_product(driver, product_id, url, first_product=True):
    """Tek bir ürün sayfasından veri çek"""
    try:
        print(f"\n{'='*60}")
        print(f"Product ID: {product_id}")
        print(f"URL: {url}")
        
        # Sayfayı yükle
        driver.get(url)
        human_like_delay(2, 4)
        
        # İlk üründe çerezleri kabul et
        accept_cookies(driver, first_product)
        
        # Sayfanın yüklenmesini bekle
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "h1.title.d-print-none"))
        )
        
        # Code ve Name çek
        h1_element = driver.find_element(By.CSS_SELECTOR, "h1.title.d-print-none")
        code = h1_element.text.split('\n')[0].strip()
        
        name_element = h1_element.find_element(By.CSS_SELECTOR, "span.category")
        name = name_element.text.strip()
        
        # Image URL çek
        image_url = ""
        try:
            img_element = driver.find_element(By.CSS_SELECTOR, 
                "div.gallery swiper .swiper-wrapper .swiper-slide.swiper-slide-active img")
            image_url = img_element.get_attribute("src")
        except NoSuchElementException:
            try:
                # Alternatif selector
                img_element = driver.find_element(By.CSS_SELECTOR, 
                    ".image-area .gallery img")
                image_url = img_element.get_attribute("src")
            except:
                pass
        
        # Description çek
        desc_parts = []
        
        # Long description
        try:
            long_desc = driver.find_element(By.CSS_SELECTOR, "span.long-description")
            desc_parts.append(long_desc.text.strip())
        except NoSuchElementException:
            pass
        
        # Benefits listesi
        try:
            benefits_ul = driver.find_element(By.CSS_SELECTOR, "ul.benefits")
            benefits_items = benefits_ul.find_elements(By.TAG_NAME, "li")
            for item in benefits_items:
                text = item.text.strip()
                if text:
                    desc_parts.append(f"• {text}")
        except NoSuchElementException:
            pass
        
        desc = "\n".join(desc_parts)
        
        # Kategori hiyerarşisini al
        category_hierarchy = get_category_hierarchy(driver)
        
        # Sonuç
        result = {
            "id": product_id,
            "code": code,
            "name": name,
            "desc": desc,
            "image_url": image_url,
            "category_hierarchy": category_hierarchy,
            "status": "done"
        }
        
        print(f"✓ Başarılı:")
        print(f"  Code: {code}")
        print(f"  Name: {name}")
        print(f"  Category: {category_hierarchy}")
        print(f"  Image: {image_url[:50]}..." if image_url else "  Image: -")
        
        return result
        
    except Exception as e:
        print(f"✗ Hata oluştu: {e}")
        return {
            "id": product_id,
            "status": "error",
            "error": str(e)
        }

def process_products():
    """API'den ürünleri çek ve işle"""
    
    print(f"\n{'='*60}")
    print(f"SKF Ürün Scraper - API Entegrasyonu")
    print(f"{'='*60}")
    
    # Driver'ı başlat
    driver = setup_driver()
    
    total_processed = 0
    total_success = 0
    total_error = 0
    
    try:
        while True:
            # Batch al
            print(f"\n{'='*60}")
            print("📦 Yeni batch isteniyor...")
            batch_data = get_product_batch(limit=500)
            
            if not batch_data:
                print("ℹ Daha fazla ürün yok veya API'ye ulaşılamadı")
                break
            
            products = batch_data.get("products", [])
            count = batch_data.get("count", 0)
            
            print(f"✓ {count} ürün alındı")
            
            if count == 0:
                break
            
            # Her ürünü işle
            for idx, product in enumerate(products, 1):
                product_id = product.get("id")
                url = product.get("url")
                
                if not url or not product_id:
                    continue
                
                print(f"\n[{idx}/{count}] İşleniyor...")
                
                # İlk ürün mü kontrol et
                is_first = (total_processed == 0)
                
                # Ürünü scrape et
                result = scrape_product(driver, product_id, url, first_product=is_first)
                
                # API'ye güncelleme gönder
                if update_product_api(result):
                    print(f"✓ API'ye gönderildi (ID: {product_id})")
                    if result.get("status") == "done":
                        total_success += 1
                    else:
                        total_error += 1
                else:
                    print(f"✗ API'ye gönderilemedi (ID: {product_id})")
                    total_error += 1
                
                total_processed += 1
                
                # Bot gibi görünmemek için rastgele bekleme
                if idx < count:
                    wait_time = random.uniform(2, 5)
                    print(f"⏳ {wait_time:.1f} saniye bekleniyor...")
                    time.sleep(wait_time)
            
            # Batch tamamlandı, istatistikler
            print(f"\n{'='*60}")
            print(f"📊 Batch İstatistikleri:")
            print(f"  Toplam işlenen: {total_processed}")
            print(f"  Başarılı: {total_success}")
            print(f"  Hatalı: {total_error}")
            print(f"{'='*60}")
            
            # Kısa bir mola ver
            time.sleep(2)
        
        print(f"\n{'='*60}")
        print(f"✓ Tüm ürünler işlendi!")
        print(f"📊 Final İstatistikleri:")
        print(f"  Toplam işlenen: {total_processed}")
        print(f"  Başarılı: {total_success}")
        print(f"  Hatalı: {total_error}")
        print(f"{'='*60}")
        
    except KeyboardInterrupt:
        print(f"\n\n⚠ Kullanıcı tarafından durduruldu")
        print(f"📊 Mevcut İstatistikler:")
        print(f"  Toplam işlenen: {total_processed}")
        print(f"  Başarılı: {total_success}")
        print(f"  Hatalı: {total_error}")
    
    except Exception as e:
        print(f"\n✗ Beklenmeyen hata: {e}")
    
    finally:
        print("\n🔄 Takılı ürünler sıfırlanıyor...")
        reset_stuck_products()
        
        print("\n🚪 Tarayıcı kapatılıyor...")
        driver.quit()
        
        print("\n✓ İşlem tamamlandı!")

if __name__ == "__main__":
    process_products()