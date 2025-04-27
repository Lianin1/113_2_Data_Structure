import os
import logging
from PIL import Image as PILImage
import google.generativeai as genai
from dotenv import load_dotenv
from tqdm import tqdm
import json
import re
import retrying
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Image, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# 設定日誌
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# 載入環境變數並設定 API 金鑰
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise ValueError("未找到 GEMINI_API_KEY，請在 .env 文件中設定。")

# 配置 Gemini API
genai.configure(api_key=api_key)
model = genai.GenerativeModel('gemini-2.0-flash-lite')

# 字型路徑（使用 TTC 格式）
font_path = os.path.join(os.path.dirname(__file__), 'msjh.ttc')
if not os.path.exists(font_path):
    raise FileNotFoundError("找不到 msjh.ttc 字型檔案，請將其放在與程式相同的資料夾內。")

# 註冊字型
pdfmetrics.registerFont(TTFont('msjh', font_path, subfontIndex=0))

# 圖片分組函數（根據前綴分組）
def group_images(static_folder):
    image_files = [f for f in os.listdir(static_folder) if f.endswith(('.png', '.jpg', '.jpeg'))]
    groups = {
        'histogram_': [],
        'boxplot_': [],
        'satisfaction_bar_': [],
        'turnover_risk_bar_chart': [],
        'turnover_risk_pie_': [],
    }
    for img in image_files:
        img_path = os.path.join(static_folder, img)
        if img.startswith('histogram_'):
            groups['histogram_'].append(img_path)
        elif img.startswith('satisfaction_bar_'):
            groups['satisfaction_bar_'].append(img_path)
        elif img.startswith('turnover_risk_bar_chart'):
            groups['turnover_risk_bar_chart'].append(img_path)
        elif img.startswith('turnover_risk_pie_'):
            groups['turnover_risk_pie_'].append(img_path)
        elif img.startswith('boxplot_'):
            groups['boxplot_'].append(img_path)
        else:
            group_key = img.split('.')[0]
            groups[group_key] = [img_path]
    # 移除空的組
    groups = {k: v for k, v in groups.items() if v}
    return groups

# Gemini API 分析函數（添加重試機制）
@retrying.retry(stop_max_attempt_number=3, wait_fixed=2000)
def analyze_image_group(image_paths):
    try:
        prompt = """
        你是一名人資數據分析師，請分析以下圖表並提供專業見解。圖表為員工滿意度調查結果，包含直方圖，箱型圖，和圓餅圖。若有多張圖表屬於同一類型（如不同層級的滿意度直方圖），請進行彙整分析。

        請提供以下內容：
        1. **描述**：概述圖表的內容，包括數據、趨勢、分佈（如平均分數、部門差異、比例等），約 100-150 字。
        2. **觀點**：從人資角度進行分析，例如滿意度低的原因、部門或層級間的差異、潛在問題、改進建議等，約 100-150 字。

        請使用繁體中文做回覆

        返回格式為 JSON：
        {
          "description": "...",
          "opinion": "..."
        }
        """
        images = []
        for path in image_paths:
            img = PILImage.open(path)
            if img.format not in ['PNG', 'JPEG']:
                raise ValueError(f"圖片 {path} 格式不支援，僅支援 PNG 和 JPEG。")
            images.append(genai.upload_file(path))
        response = model.generate_content([prompt] + images)
        if not response or not response.text:
            raise ValueError("Gemini API 回應為空。")
        json_content = re.search(r'```json\n([\s\S]*?)\n```', response.text)
        if not json_content:
            raise ValueError(f"無法從回應中提取 JSON 內容：{response.text}")
        json_str = json_content.group(1)
        result = json.loads(json_str)
        return result['description'], result['opinion']
    except Exception as e:
        logging.error(f"Gemini API 請求失敗：{str(e)}")
        raise

# PDF 生成函數（2x3 網格，確保換頁）
def generate_pdf(groups, output_pdf):
    # 初始化 PDF
    doc = SimpleDocTemplate(output_pdf, pagesize=A4, leftMargin=20, rightMargin=20, topMargin=20, bottomMargin=20)
    elements = []

    # 定義樣式
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='TitleStyle', fontName='msjh', fontSize=14, leading=16, spaceAfter=10))
    styles.add(ParagraphStyle(name='BodyStyle', fontName='msjh', fontSize=12, leading=14, spaceAfter=10))

    # 頁面尺寸（A4: 595 x 842 點）
    page_width, page_height = A4
    max_image_width = (page_width - 50) / 2  # 每張圖片寬度（考慮邊距和間距）
    max_image_height = (page_height - 60) / 3  # 每張圖片高度（考慮邊距和間距）

    # 處理每組圖片
    for group_name, image_paths in tqdm(groups.items(), desc="處理圖片組"):
        logging.info(f"正在處理組：{group_name}")
        # 調用 Gemini API 分析
        try:
            description, opinion = analyze_image_group(image_paths)
        except Exception as e:
            logging.error(f"組 {group_name} 分析失敗，跳過此組：{e}")
            description = "無法生成描述，API 請求失敗。"
            opinion = "無法生成觀點，API 請求失敗。"

        # 圖表頁（2x3 網格）
        image_elements = []
        for img_path in image_paths:
            img = PILImage.open(img_path)
            width, height = img.size
            # 按比例調整圖片大小
            if width > max_image_width or height > max_image_height:
                ratio = min(max_image_width / width, max_image_height / height)
                width = int(width * ratio)
                height = int(height * ratio)
            image_elements.append(Image(img_path, width=width, height=height))

        # 創建 2x3 網格（根據圖片數量動態調整）
        rows = []
        for i in range(0, len(image_elements), 2):
            row = image_elements[i:i+2]
            # 如果只有一張圖片，補充空白
            if len(row) < 2:
                row.append(Spacer(max_image_width, max_image_height))
            rows.append(row)
        # 如果行數不足，補充空白行
        while len(rows) < 3:
            rows.append([Spacer(max_image_width, max_image_height), Spacer(max_image_width, max_image_height)])

        # 創建表格
        table = Table(rows, colWidths=[max_image_width, max_image_width], rowHeights=[max_image_height] * 3)
        table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 0, colors.white),
            ('LEFTPADDING', (0, 0), (-1, -1), 5),
            ('RIGHTPADDING', (0, 0), (-1, -1), 5),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ]))
        elements.append(table)

        # 換頁
        elements.append(PageBreak())

        # 文字頁
        elements.append(Spacer(1, 20))
        elements.append(Paragraph("描述", styles['TitleStyle']))
        elements.append(Paragraph(description, styles['BodyStyle']))
        elements.append(Spacer(1, 10))
        elements.append(Paragraph("觀點", styles['TitleStyle']))
        elements.append(Paragraph(opinion, styles['BodyStyle']))

        # 在文字頁後換頁
        elements.append(PageBreak())

    # 生成 PDF
    doc.build(elements)
    logging.info(f"PDF 已生成：{output_pdf}")

# 主程式
def main():
    static_folder = "static"
    output_pdf = "satisfaction_analysis_2x3_fixed.pdf"

    # 分組圖片
    logging.info("開始分組圖片...")
    groups = group_images(static_folder)
    logging.info(f"圖片分組完成，共 {len(groups)} 組。")

    # 生成 PDF
    generate_pdf(groups, output_pdf)

if __name__ == "__main__":
    main()


# import os
# import logging
# from PIL import Image as PILImage
# import google.generativeai as genai
# from dotenv import load_dotenv
# from tqdm import tqdm
# import json
# import re
# import retrying
# from reportlab.lib.pagesizes import A4
# from reportlab.platypus import SimpleDocTemplate, Image, Paragraph, Spacer, Table, TableStyle
# from reportlab.lib import colors
# from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
# from reportlab.pdfbase import pdfmetrics
# from reportlab.pdfbase.ttfonts import TTFont

# # 設定日誌
# logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# # 載入環境變數並設定 API 金鑰
# load_dotenv()
# api_key = os.getenv("GEMINI_API_KEY")
# if not api_key:
#     raise ValueError("未找到 GEMINI_API_KEY，請在 .env 文件中設定。")

# # 配置 Gemini API
# genai.configure(api_key=api_key)
# model = genai.GenerativeModel('gemini-2.0-flash-lite')

# # 字型路徑（使用 TTC 格式）
# font_path = os.path.join(os.path.dirname(__file__), 'msjh.ttc')
# if not os.path.exists(font_path):
#     raise FileNotFoundError("找不到 msjh.ttc 字型檔案，請將其放在與程式相同的資料夾內。")

# # 註冊字型
# pdfmetrics.registerFont(TTFont('msjh', font_path, subfontIndex=0))

# # 圖片分組函數（根據前綴分組）
# def group_images(static_folder):
#     image_files = [f for f in os.listdir(static_folder) if f.endswith(('.png', '.jpg', '.jpeg'))]
#     groups = {
        # 'histogram_': [],
        # 'boxplot_': [],
        # 'satisfaction_bar_': [],
        # 'turnover_risk_bar_chart': [],
        # 'turnover_risk_pie_': [],
#     }
#     for img in image_files:
#         img_path = os.path.join(static_folder, img)
#         if img.startswith('histogram_'):
#             groups['histogram_'].append(img_path)
#         elif img.startswith('satisfaction_bar_'):
#             groups['satisfaction_bar_'].append(img_path)
#         elif img.startswith('turnover_risk_bar_chart'):
#             groups['turnover_risk_bar_chart'].append(img_path)
#         elif img.startswith('turnover_risk_pie_'):
#             groups['turnover_risk_pie_'].append(img_path)
#         elif img.startswith('boxplot_'):
#             groups['boxplot_'].append(img_path)
#         else:
#             group_key = img.split('.')[0]
#             groups[group_key] = [img_path]
#     # 移除空的組
#     groups = {k: v for k, v in groups.items() if v}
#     return groups

# # Gemini API 分析函數（添加重試機制）
# @retrying.retry(stop_max_attempt_number=3, wait_fixed=2000)
# def analyze_image_group(image_paths):
#     try:
#         prompt = """
#         你是一名人資數據分析師，請分析以下圖表並提供專業見解。圖表為員工滿意度調查結果，包含直方圖，箱型圖，和圓餅圖。若有多張圖表屬於同一類型（如不同層級的滿意度直方圖），請進行彙整分析。

#         請提供以下內容：
#         1. **描述**：概述圖表的內容，包括數據、趨勢、分佈（如平均分數、部門差異、比例等），約 100-150 字。
#         2. **觀點**：從人資角度進行分析，例如滿意度低的原因、部門或層級間的差異、潛在問題、改進建議等，約 100-150 字。

#         請使用繁體中文做回覆

#         返回格式為 JSON：
#         {
#           "description": "...",
#           "opinion": "..."
#         }
#         """
#         images = []
#         for path in image_paths:
#             img = PILImage.open(path)
#             if img.format not in ['PNG', 'JPEG']:
#                 raise ValueError(f"圖片 {path} 格式不支援，僅支援 PNG 和 JPEG。")
#             images.append(genai.upload_file(path))
#         response = model.generate_content([prompt] + images)
#         if not response or not response.text:
#             raise ValueError("Gemini API 回應為空。")
#         json_content = re.search(r'```json\n([\s\S]*?)\n```', response.text)
#         if not json_content:
#             raise ValueError(f"無法從回應中提取 JSON 內容：{response.text}")
#         json_str = json_content.group(1)
#         result = json.loads(json_str)
#         return result['description'], result['opinion']
#     except Exception as e:
#         logging.error(f"Gemini API 請求失敗：{str(e)}")
#         raise

# # PDF 生成函數（2x3 網格）
# def generate_pdf(groups, output_pdf):
#     # 初始化 PDF
#     doc = SimpleDocTemplate(output_pdf, pagesize=A4, leftMargin=20, rightMargin=20, topMargin=20, bottomMargin=20)
#     elements = []

#     # 定義樣式
#     styles = getSampleStyleSheet()
#     styles.add(ParagraphStyle(name='TitleStyle', fontName='msjh', fontSize=14, leading=16, spaceAfter=10))
#     styles.add(ParagraphStyle(name='BodyStyle', fontName='msjh', fontSize=12, leading=14, spaceAfter=10))

#     # 頁面尺寸（A4: 595 x 842 點）
#     page_width, page_height = A4
#     max_image_width = (page_width - 50) / 2  # 每張圖片寬度（考慮邊距和間距）
#     max_image_height = (page_height - 60) / 3  # 每張圖片高度（考慮邊距和間距）

#     # 處理每組圖片
#     for group_name, image_paths in tqdm(groups.items(), desc="處理圖片組"):
#         logging.info(f"正在處理組：{group_name}")
#         # 調用 Gemini API 分析
#         try:
#             description, opinion = analyze_image_group(image_paths)
#         except Exception as e:
#             logging.error(f"組 {group_name} 分析失敗，跳過此組：{e}")
#             description = "無法生成描述，API 請求失敗。"
#             opinion = "無法生成觀點，API 請求失敗。"

#         # 第一頁：圖表頁（2x3 網格）
#         image_elements = []
#         for img_path in image_paths:
#             img = PILImage.open(img_path)
#             width, height = img.size
#             # 按比例調整圖片大小
#             if width > max_image_width or height > max_image_height:
#                 ratio = min(max_image_width / width, max_image_height / height)
#                 width = int(width * ratio)
#                 height = int(height * ratio)
#             image_elements.append(Image(img_path, width=width, height=height))

#         # 創建 2x3 網格（根據圖片數量動態調整）
#         rows = []
#         for i in range(0, len(image_elements), 2):
#             row = image_elements[i:i+2]
#             # 如果只有一張圖片，補充空白
#             if len(row) < 2:
#                 row.append(Spacer(max_image_width, max_image_height))
#             rows.append(row)
#         # 如果行數不足，補充空白行
#         while len(rows) < 3:
#             rows.append([Spacer(max_image_width, max_image_height), Spacer(max_image_width, max_image_height)])

#         # 創建表格
#         table = Table(rows, colWidths=[max_image_width, max_image_width], rowHeights=[max_image_height] * 3)
#         table.setStyle(TableStyle([
#             ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
#             ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
#             ('GRID', (0, 0), (-1, -1), 0, colors.white),
#             ('LEFTPADDING', (0, 0), (-1, -1), 5),
#             ('RIGHTPADDING', (0, 0), (-1, -1), 5),
#             ('TOPPADDING', (0, 0), (-1, -1), 5),
#             ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
#         ]))
#         elements.append(table)

#         # 第二頁：文字頁
#         elements.append(Spacer(1, 20))
#         elements.append(Paragraph("描述", styles['TitleStyle']))
#         elements.append(Paragraph(description, styles['BodyStyle']))
#         elements.append(Spacer(1, 10))
#         elements.append(Paragraph("觀點", styles['TitleStyle']))
#         elements.append(Paragraph(opinion, styles['BodyStyle']))

#     # 生成 PDF
#     doc.build(elements)
#     logging.info(f"PDF 已生成：{output_pdf}")

# # 主程式
# def main():
#     static_folder = "static"
#     output_pdf = "satisfaction_analysis_2x3.pdf"

#     # 分組圖片
#     logging.info("開始分組圖片...")
#     groups = group_images(static_folder)
#     logging.info(f"圖片分組完成，共 {len(groups)} 組。")

#     # 生成 PDF
#     generate_pdf(groups, output_pdf)

# if __name__ == "__main__":
#     main()