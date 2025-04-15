from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
import time
import csv

# 初始化 Chrome options
options = webdriver.ChromeOptions()
options.add_argument('--headless')  # 無介面模式
options.add_argument('--disable-gpu')
options.add_argument('--no-sandbox')
options.add_argument('--enable-unsafe-swiftshader')  # 解決 WebGL 警告

# 啟動 WebDriver
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

# 目標網址（跳轉到特定留言）
url = "https://www.youtube.com/watch?v=qAA3lzzANrg&lc=UgwHa8qZjPIz05Wta_Z4AaABAg&ab_channel=Lian"
driver.get(url)

# 停一下讓留言區載入
time.sleep(5)

# 多次捲動觸發留言載入
SCROLL_PAUSE_TIME = 2
for _ in range(10):  # 捲動 10 次以載入更多留言
    driver.execute_script("window.scrollBy(0, 1000);")
    time.sleep(SCROLL_PAUSE_TIME)

# 抓取留言內容
comments = []
elements = driver.find_elements(By.ID, "content-text")

for idx, el in enumerate(elements):
    try:
        span = el.find_element(By.CLASS_NAME, "yt-core-attributed-string--white-space-pre-wrap")
        text = span.text.strip()
        if text:
            comments.append([idx + 1, text])
    except:
        continue

# 關閉瀏覽器
driver.quit()

# 寫入 CSV 檔案
with open('comments.csv', 'w', encoding='utf-8-sig', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(['編號', '留言內容'])
    writer.writerows(comments)

print(f"✅ 共寫入 {len(comments)} 筆留言到 comments.csv")
