import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import os
import numpy as np  # 新增 NumPy 導入

# 設定字體為程式同目錄下的 msjh.ttc
font_path = os.path.join(os.path.dirname(__file__), 'msjh.ttc')
if not os.path.exists(font_path):
    raise FileNotFoundError("找不到 msjh.ttc 字型檔案，請將其放在與程式相同的資料夾內。")

font_prop = fm.FontProperties(fname=font_path)

# 讀取 CSV 檔案
csv_file = 'employee_satisfaction_data_quantified.csv'
if not os.path.exists(csv_file):
    raise FileNotFoundError(f"找不到檔案：{csv_file}，請確保檔案位於程式同一資料夾")
df = pd.read_csv(csv_file, encoding='utf-8')

# 部門編號映射
department_map = {0: '人力資源', 1: '財務', 2: '技術', 3: '行銷', 4: '運營'}
df['部門名稱'] = df['部門'].map(department_map)

# 創建輸出資料夾
output_dir = 'static'
os.makedirs(output_dir, exist_ok=True)

# 為每個部門生成圓餅圖
departments = df['部門名稱'].unique()
for dept in departments:
    # 篩選該部門的數據
    dept_data = df[df['部門名稱'] == dept]
    
    # 計算離職風險分級的分布，按分級排序
    risk_counts = dept_data['離職風險分級'].value_counts().sort_index()
    total_people = len(dept_data)  # 該部門總人數
    
    # 設置 Seaborn 主題
    sns.set_theme(style="whitegrid")
    
    # 繪製圓餅圖
    plt.figure(figsize=(6, 6))
    colors = sns.color_palette("pastel", len(risk_counts))
    
    # 繪製圓餅圖，不使用 autopct
    wedges, _ = plt.pie(
        risk_counts,
        startangle=90,
        colors=colors,
        shadow=True,
        explode=[0.05] * len(risk_counts)
    )
    
    # 手動添加標籤到扇區內部
    for i, wedge in enumerate(wedges):
        # 計算扇區中心角度
        theta = (wedge.theta2 + wedge.theta1) / 2
        # 計算標籤位置（扇區中心）
        r = 0.6  # 控制標籤距離中心的距離
        x = r * np.cos(np.radians(theta))
        y = r * np.sin(np.radians(theta))
        
        # 獲取對應的風險分級和人數
        level = risk_counts.index[i]
        count = risk_counts.iloc[i]
        percentage = (count / total_people) * 100
        
        # 設置標籤文字
        label = f'風險分級 {level}\n{percentage:.1f}%\n{count} 人'
        
        # 添加標籤到扇區中心
        plt.text(x, y, label, ha='center', va='center', fontsize=10,
                 fontproperties=font_prop, color='black')
    
    # 設定標題，包含總人數
    plt.title(f'{dept} 部門離職風險分級占比\n(總人數：{total_people} 人)', 
              fontsize=14, pad=20, fontproperties=font_prop)
    
    # 確保圓餅圖為正圓
    plt.axis('equal')
    
    # 儲存圖表
    output_path = os.path.join(output_dir, f'turnover_risk_pie_{dept}.png')
    plt.savefig(output_path, bbox_inches='tight', dpi=100)
    plt.close()
    
    print(f"{dept} 部門的圖表已儲存至：{output_path}")

print("所有部門的圖表生成完成！")