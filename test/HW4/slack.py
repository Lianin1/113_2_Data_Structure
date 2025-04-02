from playwright.sync_api import sync_playwright
import os
from dotenv import load_dotenv

# 讀取 .env 檔案
load_dotenv()
SLACK_EMAIL = os.getenv("SLACK_EMAIL")

# HW4 設定檔案路徑與檔名，讓機器人自動傳送兩筆檔案
# 動態獲取當前腳本所在目錄，並指定多個檔案名稱
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
FILE_NAME_1 = "report_20250402_232621.pdf"  # 第一個檔案名稱
FILE_NAME_2 = "report_20250402_235230.pdf"  # 第二個檔案名稱（請替換為實際名稱）
FILE_PATHS = [
    os.path.join(SCRIPT_DIR, FILE_NAME_1),
    os.path.join(SCRIPT_DIR, FILE_NAME_2)
]

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)  # 顯示瀏覽器
    page = browser.new_page()

    print("啟動瀏覽器，前往 Slack 頁面...")
    page.goto("https://slack.com/signin#/signin")
    page.wait_for_timeout(3000)

    print("填入 Slack 電子郵件...")
    page.fill("#signup_email", SLACK_EMAIL)
    page.wait_for_timeout(1000)

    print("點擊繼續按鈕...")
    page.click("#submit_btn")
    page.wait_for_timeout(3000)

    verification_code = input("請輸入 Slack 寄送的 6 位英文字驗證碼（輸入 'Exit' 退出程式），然後按 Enter: ")
    while len(verification_code) != 6:
        if verification_code.lower() == "exit":
            print("使用者選擇退出程式...")
            browser.close()
            print("程式已終止")
            exit()
        print("驗證碼必須是 6 位英文字！")
        verification_code = input("請重新輸入 6 位英文字驗證碼（輸入 'Exit' 退出程式）: ")

    print("正在填入驗證碼...")
    for i, char in enumerate(verification_code):
        selector = f"[aria-label='數字 {i + 1}，6']"
        page.fill(selector, char)
        page.wait_for_timeout(100)

    print("驗證碼已填入，等待 Slack 自動登入...")
    page.wait_for_timeout(5000)

    print("點擊『在瀏覽器中使用 Slack』超連結...")
    page.click("[data-qa='ssb_redirect_open_in_browser']")
    page.wait_for_timeout(5000)

    print("點擊首頁...")
    page.click("#home")
    page.wait_for_timeout(2000)

    print("點擊 general 頻道...")
    page.click("#C07BN8A9QU9")
    page.wait_for_timeout(2000)

    # HW4 改為上傳檔案：設定檔案路徑、並指定代理行動
    # 上傳多個檔案
    print(f"上傳檔案: {FILE_PATHS}")
    # 點擊「+」按鈕打開選單
    page.click("[data-qa='shortcuts_menu_trigger__Channel']")
    page.wait_for_timeout(1000)  # 等待選單出現

    # 點擊「從電腦上傳」
    print("點擊『從電腦上傳』...")
    page.click("[data-qa='upload-from-your-computer']")
    page.wait_for_timeout(1000)  # 等待檔案輸入元素出現

    # 設定多個檔案到隱藏的 <input type="file">
    print("設定檔案...")
    page.locator("input[type='file']").set_input_files(FILE_PATHS)
    page.wait_for_timeout(2000)  # 等待檔案上傳完成

    # 點擊送出按鈕
    print("送出訊息...")
    page.click("[data-qa='texty_send_button']")
    page.wait_for_timeout(2000)

    # 截圖確認結果
    page.screenshot(path="slack_post_result.png")
    print("操作完成！截圖已保存為 slack_post_result.png")

    input("瀏覽器保持開啟，按 Enter 關閉...")
    browser.close()
    print("瀏覽器已關閉")