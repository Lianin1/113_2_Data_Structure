import os
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv
from fpdf import FPDF
import time
# 导入需要执行的模块
import employee_satisfaction_test
import t318
import postAItest

# 载入环境变量
load_dotenv()

def run_module(module):
    """
    执行导入的模块
    """
    try:
        # 调用模块的 main 函数（如果存在）
        if hasattr(module, 'main'):
            output = module.main()
            return str(output) if output else f"⚠️ {module.__name__} 没有产生输出"
        return f"⚠️ {module.__name__} 没有 main 函数"
    except Exception as e:
        return f"❌ 执行 {module.__name__} 时发生错误：{e}"

def save_terminal_output_to_csv(outputs, output_file):
    """
    將終端輸出保存為 CSV 格式。
    """
    data = []
    for output in outputs:
        data.append({"output": output.strip()})
    
    df = pd.DataFrame(data)
    df.to_csv(output_file, index=False, encoding="utf-8-sig")
    print(f"已將終端輸出保存為 {output_file}")

def get_chinese_font_file() -> str:
    """
    只檢查 Windows 系統字型資料夾中是否存在候選中文字型（TTF 格式）。
    若找到則回傳完整路徑；否則回傳 None。
    """
    fonts_path = r"C:\USERS\A0934\APPDATA\LOCAL\MICROSOFT\WINDOWS\FONTS"
    candidates = ["NotoSansTC-VariableFont_wght_1.ttf"]  # 這裡以楷體為例，可依需要修改
    for font in candidates:
        font_path = os.path.join(fonts_path, font)
        if os.path.exists(font_path):
            print("找到系統中文字型：", font_path)
            return os.path.abspath(font_path)
    print("未在系統中找到候選中文字型檔案。")
    return None

def create_pdf_from_csv(csv_file):
    """
    從 CSV 檔案生成 PDF。
    """
    pdf = FPDF(format="A4")
    pdf.add_page()
    
    chinese_font_path = get_chinese_font_file()
    if not chinese_font_path:
        print("錯誤：無法取得中文字型檔，請先安裝合適的中文字型！")
        return
    
    pdf.add_font("ChineseFont", "", chinese_font_path, uni=True)
    pdf.set_font("ChineseFont", "", 10)

    df = pd.read_csv(csv_file)
    for index, row in df.iterrows():
        # 將 row['output'] 轉換為字串
        pdf.multi_cell(0, 10, str(row['output']))  # 修改這一行
    
    pdf_filename = f"terminal_output_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    pdf.output(pdf_filename)
    print(f"已生成 PDF 檔案：{pdf_filename}")

def main():
    # 定义 CSV 路径
    csv_file = "t318.csv"

    # 执行模块并收集输出
    modules = [
        employee_satisfaction_test,
        t318,
        postAItest
    ]

    outputs = []
    for module in modules:
        print(f"执行 {module.__name__}...")
        output = run_module(module)
        outputs.append(output)
        time.sleep(10)

    # 储存输出
    save_terminal_output_to_csv(outputs, "terminal_output.csv")

    # 生成 PDF
    create_pdf_from_csv("terminal_output.csv")

if __name__ == "__main__":
    main()
