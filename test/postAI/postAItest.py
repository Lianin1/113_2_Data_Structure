from playwright.sync_api import sync_playwright
import os
from dotenv import load_dotenv

# 讀取 .env 檔案
load_dotenv()
SLACK_EMAIL = os.getenv("SLACK_EMAIL")

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)  # 顯示瀏覽器
    page = browser.new_page()

    print("啟動瀏覽器，前往 Slack 頁面...")
    # 前往 Slack 登入頁面
    page.goto("https://slack.com/signin#/signin")
    page.wait_for_timeout(3000)

    # 填入 email
    print("填入 Slack 電子郵件...")
    page.fill("#signup_email", SLACK_EMAIL)
    page.wait_for_timeout(1000)

    # 點擊「繼續」按鈕
    print("點擊繼續按鈕...")
    page.click("#submit_btn")
    page.wait_for_timeout(3000)  # 等待驗證碼頁面載入

    # 在終端機提示使用者輸入 6 位英文字驗證碼
    verification_code = input("請輸入 Slack 寄送的 6 位英文字驗證碼（輸入 'Exit' 退出程式），然後按 Enter: ")
    while len(verification_code) != 6:
        if verification_code.lower() == "exit":
            print("使用者選擇退出程式...")
            browser.close()
            print("程式已終止")
            exit()  # 終止程式
        print("驗證碼必須是 6 位英文字！")
        verification_code = input("請重新輸入 6 位英文字驗證碼（輸入 'Exit' 退出程式）: ")

    # 填入 6 個驗證碼欄位
    print("正在填入驗證碼...")
    for i, char in enumerate(verification_code):
        selector = f"[aria-label='數字 {i + 1}，6']"
        page.fill(selector, char)
        page.wait_for_timeout(100)  # 模擬真人輸入間隔

    # 等待 Slack 自動登入
    print("驗證碼已填入，等待 Slack 自動登入...")
    page.wait_for_timeout(5000)

    # 點擊「在瀏覽器中使用 Slack」超連結
    print("點擊『在瀏覽器中使用 Slack』超連結...")
    page.click("[data-qa='ssb_redirect_open_in_browser']")
    page.wait_for_timeout(5000)  # 等待頁面跳轉並載入

    # 點擊「首頁」
    print("點擊首頁...")
    page.click("#home")
    page.wait_for_timeout(2000)

    # # 點擊「general」頻道
    # print("點擊 general 頻道...")
    # page.click("#C07BN8A9QU9")
    # page.wait_for_timeout(2000)


    print("點擊 IDEA 頻道...")
    page.click("#C07B2VA55RU")
    page.wait_for_timeout(2000)


    # 在輸入欄輸入 "test"
    print("輸入 'test'...")
    page.fill("div[data-qa='message_input'] .ql-editor", "test")
    page.wait_for_timeout(1000)

    # 點擊送出按鈕
    print("送出訊息...")
    page.click("[data-qa='texty_send_button']")
    page.wait_for_timeout(2000)

    # # 截圖確認結果
    # page.screenshot(path="slack_post_result.png")
    # print("操作完成！截圖已保存為 slack_post_result.png")

    # 保持瀏覽器開啟，方便檢查
    input("瀏覽器保持開啟，按 Enter 關閉...")
    browser.close()
    print("瀏覽器已關閉")