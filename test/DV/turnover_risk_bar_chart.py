import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import os

# 取得字體檔案的相對路徑
font_path = os.path.join(os.path.dirname(__file__), 'msjh.ttc')
if not os.path.exists(font_path):
    raise FileNotFoundError(f"找不到字體檔案：{font_path}，請確保 msjh.ttc 與程式放在同一資料夾內。")

# 設定全局字型
font_prop = fm.FontProperties(fname=font_path)
plt.rcParams['font.family'] = font_prop.get_name()

# 讀取 CSV 檔案
csv_file = 'employee_satisfaction_data_quantified.csv'
if not os.path.exists(csv_file):
    raise FileNotFoundError(f"找不到檔案：{csv_file}，請確保檔案位於程式同一資料夾")
df = pd.read_csv(csv_file, encoding='utf-8')

# 部門編號映射
department_map = {0: '人力資源', 1: '財務', 2: '技術', 3: '行銷', 4: '運營'}
df['部門名稱'] = df['部門'].map(department_map)

# 計算平均離職風險分級
avg_risk_by_dept = df.groupby('部門名稱')['離職風險分級'].mean()
print("各部門平均離職風險分級：")
print(avg_risk_by_dept)

# 設置 Seaborn 主題
sns.set_theme(style="whitegrid")

# 繪製柱狀圖
plt.figure(figsize=(8, 6))
bars = sns.barplot(x='部門名稱', y='離職風險分級', data=avg_risk_by_dept.reset_index(), palette='pastel')

# 在每個柱子上顯示平均值
for bar in bars.patches:
    bars.annotate(
        f'{bar.get_height():.2f}',
        (bar.get_x() + bar.get_width() / 2, bar.get_height()),
        ha='center', va='bottom', fontsize=12, fontproperties=font_prop
    )

plt.title('各部門平均離職風險分級', fontsize=14, fontproperties=font_prop)
plt.xlabel('部門', fontsize=12, fontproperties=font_prop)
plt.ylabel('平均離職風險分級', fontsize=12, fontproperties=font_prop)
plt.xticks(rotation=45, fontproperties=font_prop)

# 創建輸出資料夾
output_dir = 'static'
os.makedirs(output_dir, exist_ok=True)

# 儲存圖表
output_path = os.path.join(output_dir, 'turnover_risk_bar_chart.png')
plt.savefig(output_path, bbox_inches='tight', dpi=100)
plt.close()

print(f"圖表已儲存至：{output_path}")
