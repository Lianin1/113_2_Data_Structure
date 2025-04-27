import os
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm

def select_dialogue_column(df, socketio):
    """自動選取逐字稿欄位"""
    preferred = ["text", "utterance", "content", "dialogue", "Dialogue"]
    for col in preferred:
        if col in df.columns:
            return col
    socketio.emit('update', {'message': f"未找到預期欄位，使用第一欄：{df.columns[0]}"})
    return df.columns[0]

def generate_rating_plot(df, output_path, items):
    """生成評分分佈圖，使用 msjh.ttc 字型，並在長條圖上標註數值"""
    # 設定字型路徑（與程式同目錄下的 msjh.ttc）
    font_path = os.path.join(os.path.dirname(__file__), 'msjh.ttc')
    if not os.path.exists(font_path):
        raise FileNotFoundError("找不到 msjh.ttc 字型檔案，請將其放在與程式相同的資料夾內。")

    # 設定 Matplotlib 的字型屬性
    font_prop = fm.FontProperties(fname=font_path)
    plt.rcParams['font.family'] = 'sans-serif'
    plt.rcParams['font.sans-serif'] = [font_prop.get_name()]

    # 生成評分數據
    ratings = {item: df[item].value_counts().get("1", 0) for item in items[:-1]}  # 排除「備註」

    # 繪製長條圖
    plt.figure(figsize=(10, 6))
    bars = plt.bar(ratings.keys(), ratings.values(), color='skyblue')
    plt.xticks(rotation=45, ha='right', fontproperties=font_prop)
    plt.ylabel('次數', fontproperties=font_prop)
    plt.title('評分項目分佈', fontproperties=font_prop)

    # 在每個長條圖上方標註數值
    for bar in bars:
        height = bar.get_height()
        plt.text(
            bar.get_x() + bar.get_width() / 2,  # X 軸位置（柱子中央）
            height,  # Y 軸位置（柱子頂部）
            f'{int(height)}',  # 數值（轉為整數）
            ha='center', va='bottom',  # 水平居中，垂直底部
            fontproperties=font_prop,  # 使用指定字型
            fontsize=10
        )

    plt.tight_layout()
    plt.savefig(output_path)
    plt.close()