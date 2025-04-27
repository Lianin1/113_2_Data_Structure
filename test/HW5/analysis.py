import os
import time
import pandas as pd
from dialog_processor import ITEMS, process_batch_dialogue
from utils import select_dialogue_column, generate_rating_plot

def generate_suggestions(df, model, socketio):
    """生成建議，根據低得分項目提供具體建議，並利用 Gemini API"""
    ratings = {item: df[item].value_counts().get("1", 0) for item in ITEMS[:-1]}
    low_score_items = [item for item, count in ratings.items() if count < len(df) * 0.3]

    if not low_score_items:
        return "對話表現良好，繼續保持！"

    # 簡單的建議模板（備用）
    suggestion_templates = {
        "明確目標設定": "多與員工共同設定具體且可衡量的目標，例如『本週完成報告的初稿』。",
        "提供具體反饋": "在反饋時提供具體的例子，例如『你在簡報中提到的數據很有說服力，但可以再補充一些圖表』。",
        "積極傾聽": "多重述員工的意見以確認理解，例如『你的意思是想調整專案進度，對嗎？』。",
        "鼓勵參與": "鼓勵員工提出想法，例如『你對這個專案有什麼建議？』。",
        "解決問題": "針對員工提出的問題，提供具體的解決方案或行動計劃。",
        "情感支持": "多表達對員工努力的認可，例如『我知道你這週很忙，感謝你的努力』。",
        "確認理解": "在對話結束時確認雙方的共識，例如『我們同意下週一提交報告，對吧？』。",
        "連結工作意義": "將員工的工作與更大的目標連結，例如『你的報告將幫助我們爭取更多資源』。",
        "開放式提問": "多使用開放式問題促進討論，例如『你覺得目前的進度如何？』。"
    }

    # 使用 Gemini API 生成更具體的建議
    prompt = (
        "你是一位管理與溝通專家，請根據以下主管與員工 1:1 對話的評分結果，提供改進建議。\n"
        "以下項目得分較低（表示主管在對話中未充分觸及該項）:\n"
        + "\n".join([f"- {item}" for item in low_score_items]) +
        "\n\n請針對每個低得分項目，提供具體且可行的建議，幫助主管改進。格式如下：\n"
        "建議加強「項目名稱」，例如具體建議。\n"
        "例如：\n"
        "建議加強「情感支持」，例如多表達對員工努力的認可，例如『我知道你這週很忙，感謝你的努力』。\n"
    )

    try:
        response = model.generate_content(prompt)
        suggestions = response.text.strip()
        if not suggestions:
            raise ValueError("Gemini API 回傳空建議")
        return suggestions
    except Exception as e:
        socketio.emit('update', {'message': f"生成建議失敗：{str(e)}，使用備用建議"})
        # 備用建議
        suggestions = []
        for item in low_score_items:
            suggestion = suggestion_templates.get(item, "請多關注此項目，與員工進行更深入的討論。")
            suggestions.append(f"建議加強「{item}」，{suggestion}")
        return "\n".join(suggestions)

def background_task(file_path, output_csv, model, socketio, app_config):
    """後台處理上傳的 CSV 檔案"""
    try:
        df = pd.read_csv(file_path)
        dialogue_col = select_dialogue_column(df, socketio)
        socketio.emit('update', {'message': f'使用欄位作為逐字稿：{dialogue_col}'})

        batch_size = 10
        total = len(df)
        batch_dfs = []
        for start_idx in range(0, total, batch_size):
            end_idx = min(start_idx + batch_size, total)
            batch = df.iloc[start_idx:end_idx].copy()
            dialogues = batch[dialogue_col].tolist()
            dialogues = [str(d).strip() for d in dialogues]
            batch_results = process_batch_dialogue(dialogues, model, socketio)
            for item in ITEMS:
                batch[item] = [res.get(item, "") for res in batch_results]
            batch_dfs.append(batch)
            socketio.emit('update', {'message': f'已處理 {end_idx} 筆 / {total}'})
            time.sleep(1)

        # 合併所有批次結果
        result_df = pd.concat(batch_dfs, ignore_index=True)
        result_df.to_csv(output_csv, index=False, encoding="utf-8-sig")

        # 生成評分分佈圖
        plot_path = os.path.join(app_config['STATIC_FOLDER'], 'rating_plot.png')
        generate_rating_plot(result_df, plot_path, ITEMS)
        socketio.emit('plot_generated', {'plot_url': '/static/rating_plot.png'})

        # 生成建議
        suggestions = generate_suggestions(result_df, model, socketio)
        socketio.emit('suggestions', {'suggestions': suggestions})

        # 通知前端結果檔案可下載
        socketio.emit('result_ready', {'result_url': f'/download/{os.path.basename(output_csv)}'})

    except Exception as e:
        socketio.emit('error', {'message': f"分析過程出現錯誤：{str(e)}"})