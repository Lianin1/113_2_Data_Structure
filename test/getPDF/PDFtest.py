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

def create_table(pdf: FPDF, df: pd.DataFrame):
    """
    使用 FPDF 將 DataFrame 以表格形式繪製至 PDF。
    - 'start' 和 'end' 欄位寬度根據內容自適應。
    - 其餘欄位平均分配剩餘寬度。
    - 內容超出欄位寬度時自動換行。
    - 每一列的高度統一為該列中最高的格子高度。
    - 邊框與背景色對齊。
    """
    available_width = pdf.w - 2 * pdf.l_margin
    base_cell_height = 10  # 基礎單元格高度（每行的基準高度）

    # 計算各欄寬度
    col_widths = {}
    pdf.set_font("ChineseFont", "", 10)  # 用於測量文字寬度

    # 計算 'start' 和 'end' 欄的最小寬度
    for col in ['start', 'end']:
        if col in df.columns:
            max_width = max(
                pdf.get_string_width(str(col)),  # 表頭寬度
                max(pdf.get_string_width(str(x)) for x in df[col].fillna(''))  # 內容最大寬度
            ) + 4  # 增加一點內邊距
            col_widths[col] = min(max_width, 30)  # 限制最大寬度為 30，避免過寬

    # 剩餘寬度平均分配給其他欄位
    remaining_cols = [col for col in df.columns if col not in ['start', 'end']]
    remaining_width = available_width - sum(col_widths.values())
    other_col_width = remaining_width / len(remaining_cols) if remaining_cols else 0
    for col in remaining_cols:
        col_widths[col] = other_col_width

    # 表頭
    pdf.set_fill_color(200, 200, 200)
    pdf.set_font("ChineseFont", "", 12)
    x_start = pdf.get_x()
    y_start = pdf.get_y()
    for col in df.columns:
        pdf.rect(x_start, y_start, col_widths[col], base_cell_height, style="DF")  # 繪製表頭邊框和背景
        pdf.set_xy(x_start, y_start)
        pdf.cell(col_widths[col], base_cell_height, str(col), border=0, align="C")
        x_start += col_widths[col]
    pdf.ln(base_cell_height)

    # 資料行：交替背景色並支援自動換行
    pdf.set_font("ChineseFont", "", 10)
    fill = False
    for index, row in df.iterrows():
        # 計算該列的最大高度
        max_lines = 1  # 至少一行
        for col, item in zip(df.columns, row):
            text = str(item)
            # 計算需要的行數（考慮換行）
            num_lines = max(1, (pdf.get_string_width(text) / col_widths[col]) + 1)
            max_lines = max(max_lines, int(num_lines))

        # 根據行數計算該列的總高度
        row_height = base_cell_height * max_lines

        # 檢查是否需要換頁
        if pdf.get_y() + row_height > pdf.h - pdf.b_margin:
            pdf.add_page()
            pdf.set_fill_color(200, 200, 200)
            pdf.set_font("ChineseFont", "", 12)
            x_start = pdf.get_x()
            y_start = pdf.get_y()
            for col in df.columns:
                pdf.rect(x_start, y_start, col_widths[col], base_cell_height, style="DF")
                pdf.set_xy(x_start, y_start)
                pdf.cell(col_widths[col], base_cell_height, str(col), border=0, align="C")
                x_start += col_widths[col]
            pdf.ln(base_cell_height)
            pdf.set_font("ChineseFont", "", 10)

        # 設定背景色
        if fill:
            pdf.set_fill_color(230, 240, 255)
        else:
            pdf.set_fill_color(255, 255, 255)

        # 記錄當前 x, y 位置
        x_start = pdf.get_x()
        y_start = pdf.get_y()

        # 繪製背景矩形和邊框（確保邊框與背景色對齊）
        for col in df.columns:
            pdf.rect(x_start, y_start, col_widths[col], row_height, style="DF")  # 繪製邊框和背景
            x_start += col_widths[col]

        # 繪製每一列的內容
        x_start = pdf.get_x()  # 重置 x 位置
        for col, item in zip(df.columns, row):
            pdf.set_xy(x_start, y_start)
            # 使用 multi_cell 繪製內容，但不繪製邊框（border=0）
            pdf.multi_cell(col_widths[col], base_cell_height, str(item), border=0, align="L")
            x_start += col_widths[col]  # 移動到下一欄

        # 移動到下一行
        pdf.set_xy(pdf.l_margin, y_start + row_height)
        fill = not fill

def parse_markdown_table(markdown_text: str) -> pd.DataFrame:
    """
    從 Markdown 格式的表格文字提取資料，返回一個 pandas DataFrame。
    例如，輸入：
      | start | end | text | 分類 | 註解 |
      |-------|-----|------|------|------|
      | 00:00 | 00:01 | 開始拍攝喔 | 準備開始拍攝行為 |
    會返回包含該資料的 DataFrame。
    """
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
        # 將所有區塊回應合併，並生成漂亮表格 PDF
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

default_prompt = """請根據以下的規則將每句對話進行分類，並為每個分類提供註解，說明分類的理由：

"明確目標設定",
"提供具體反饋",
"積極傾聽"
"鼓勵參與",
"解決問題",
"情感支持",
"確認理解",
"連結工作意義",
"開放式提問",

並將所有類別進行統計後產出報表。"""

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