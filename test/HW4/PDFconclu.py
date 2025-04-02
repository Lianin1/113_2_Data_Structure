import os
from datetime import datetime
import requests
import gradio as gr
import pandas as pd
from dotenv import load_dotenv
from fpdf import FPDF
import google.generativeai as genai
import re

# 載入環境變數並設定 API 金鑰
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

# 配置 Gemini API
genai.configure(api_key=api_key)
model = genai.GenerativeModel('gemini-2.5-pro-exp-03-25')  # 初始化模型

def get_chinese_font_file() -> str:
    # HW4 設定自訂義字體
    fonts_path = r"C:\USERS\A0934\APPDATA\LOCAL\MICROSOFT\WINDOWS\FONTS"
    candidates = ["NotoSansTC-VariableFont_wght_1.ttf"] 
    for font in candidates:
        font_path = os.path.join(fonts_path, font)
        if os.path.exists(font_path):
            print("找到系統中文字型：", font_path)
            return os.path.abspath(font_path)
    print("未在系統中找到候選中文字型檔案。")
    return None


# HW4 依需求改為分段純文字 pdf 內容
def create_text_content(pdf: FPDF, df: pd.DataFrame):
    available_width = pdf.w - 2 * pdf.l_margin
    base_cell_height = 10  # 基礎行高

    # 設置字體
    pdf.set_font("ChineseFont", "", 10)

    # 逐行處理 DataFrame
    for index, row in df.iterrows():
        # 構建該行的文字內容
        row_text = " | ".join(f"{col}: {str(item)}" for col, item in zip(df.columns, row))
        
        # 計算該段文字需要的行數
        text_width = pdf.get_string_width(row_text)
        num_lines = max(1, int((text_width / available_width) + 1))  # 計算需要的行數
        row_height = base_cell_height * num_lines

        # 檢查是否需要換頁
        if pdf.get_y() + row_height + base_cell_height > pdf.h - pdf.b_margin:
            pdf.add_page()

        # 繪製文字內容
        pdf.multi_cell(available_width, base_cell_height, row_text, border=0, align="L")
        
        # 增加空行分隔
        pdf.ln(base_cell_height)


def parse_markdown_table(markdown_text: str) -> pd.DataFrame:

    lines = markdown_text.strip().splitlines()
    # 過濾掉空行
    lines = [line.strip() for line in lines if line.strip()]
    # 找到包含 '|' 的行，假設這就是表格
    table_lines = [line for line in lines if line.startswith("|")]
    if not table_lines:
        return None
    # 忽略第二行（分隔線）
    header_line = table_lines[0]
    headers = [h.strip() for h in header_line.strip("|").split("|")]
    data = []
    for line in table_lines[2:]:
        row = [cell.strip() for cell in line.strip("|").split("|")]
        if len(row) == len(headers):
            data.append(row)
    df = pd.DataFrame(data, columns=headers)
    return df

def generate_pdf(text: str = None, df: pd.DataFrame = None) -> str:
    print("開始生成 PDF")
    pdf = FPDF(format="A4")
    pdf.add_page()
    
    # 取得中文字型
    chinese_font_path = get_chinese_font_file()
    if not chinese_font_path:
        error_msg = "錯誤：無法取得中文字型檔，請先安裝合適的中文字型！"
        print(error_msg)
        return error_msg
    
    pdf.add_font("ChineseFont", "", chinese_font_path, uni=True)
    pdf.set_font("ChineseFont", "", 10)
    
    if df is not None:
        create_table(pdf, df)
    elif text is not None:
        # 嘗試檢查 text 是否包含 Markdown 表格格式
        if "|" in text:
            # 找出可能的表格部分（假設從第一個 '|' 開始到最後一個 '|'）
            table_part = "\n".join([line for line in text.splitlines() if line.strip().startswith("|")])
            parsed_df = parse_markdown_table(table_part)
            if parsed_df is not None:
                create_table(pdf, parsed_df)
            else:
                pdf.multi_cell(0, 10, text)
        else:
            pdf.multi_cell(0, 10, text)
    else:
        pdf.cell(0, 10, "沒有可呈現的內容")
    
    pdf_filename = f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    print("輸出 PDF 至檔案：", pdf_filename)
    pdf.output(pdf_filename)
    print("PDF 生成完成")
    return pdf_filename

def gradio_handler(csv_file, user_prompt):
    print("進入 gradio_handler")
    if csv_file is not None:
        print("讀取 CSV 檔案")
        df = pd.read_csv(csv_file.name)
        total_rows = df.shape[0]
        block_size = 30
        cumulative_response = ""
        block_responses = []
        # 依區塊處理 CSV 並依每區塊呼叫 LLM 產生報表分析結果
        for i in range(0, total_rows, block_size):
            block = df.iloc[i:i+block_size]
            block_csv = block.to_csv(index=False)
            prompt = (f"以下是CSV資料第 {i+1} 到 {min(i+block_size, total_rows)} 筆：\n"
                      f"{block_csv}\n\n請根據以下規則進行分析並產出報表：\n{user_prompt}")
            print("完整 prompt for block:")
            print(prompt)
            response = model.generate_content(prompt)  # 直接使用 model
            block_response = response.text.strip()
            cumulative_response += f"區塊 {i//block_size+1}:\n{block_response}\n\n"
            block_responses.append(cumulative_response)

        pdf_path = generate_pdf(text=cumulative_response)
        return cumulative_response, pdf_path
    else:
        context = "未上傳 CSV 檔案。"
        full_prompt = f"{context}\n\n{user_prompt}"
        print("完整 prompt：")
        print(full_prompt)
    
        response = model.generate_content(full_prompt)  # 直接使用 model
        response_text = response.text.strip()
        print("AI 回應：")
        print(response_text)
    
        pdf_path = generate_pdf(text=response_text)
        return response_text, pdf_path

# HW4 更改 prompt 為自己所需之功能
default_prompt = """將整個檔案進行分析，發表你的看法"""

with gr.Blocks() as demo:
    gr.Markdown("# CSV 報表生成器")
    with gr.Row():
        csv_input = gr.File(label="上傳 CSV 檔案")
        user_input = gr.Textbox(label="請輸入分析指令", lines=10, value=default_prompt)
    output_text = gr.Textbox(label="回應內容", interactive=False)
    output_pdf = gr.File(label="下載 PDF 報表")
    submit_button = gr.Button("生成報表")
    submit_button.click(fn=gradio_handler, inputs=[csv_input, user_input],
                        outputs=[output_text, output_pdf])

demo.launch()