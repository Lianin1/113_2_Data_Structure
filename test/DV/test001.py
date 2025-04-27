import os
from PIL import Image as PILImage
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Image, Spacer, Table, TableStyle
from reportlab.lib import colors

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

# PDF 生成函數（僅排版圖表，2x3 網格）
def generate_pdf(groups, output_pdf):
    # 初始化 PDF
    doc = SimpleDocTemplate(output_pdf, pagesize=A4, leftMargin=20, rightMargin=20, topMargin=20, bottomMargin=20)
    elements = []

    # 頁面尺寸（A4: 595 x 842 點）
    page_width, page_height = A4
    max_image_width = (page_width - 50) / 2  # 每張圖片寬度（考慮邊距和間距）
    max_image_height = (page_height - 60) / 3  # 每張圖片高度（考慮邊距和間距）

    # 處理每組圖片
    for group_name, image_paths in groups.items():
        # 第一頁：圖表頁（2x3 網格）
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

    # 生成 PDF
    doc.build(elements)

# 主程式
def main():
    static_folder = "static"
    output_pdf = "layout_test.pdf"

    # 分組圖片
    groups = group_images(static_folder)

    # 生成 PDF
    generate_pdf(groups, output_pdf)

if __name__ == "__main__":
    main()