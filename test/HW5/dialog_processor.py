import json
from google.api_core import exceptions

# 評分項目
ITEMS = [
    "明確目標設定", "提供具體反饋", "積極傾聽", "鼓勵參與", "解決問題",
    "情感支持", "確認理解", "連結工作意義", "開放式提問", "備註"
]

def parse_response(response_text, socketio):
    """解析 Gemini API 回傳的 JSON 格式結果，增加更嚴格的清理邏輯"""
    cleaned = response_text.strip()
    # 移除 Markdown 標記（```json 和 ```）
    if cleaned.startswith("```json"):
        cleaned = cleaned[len("```json"):].strip()
    if cleaned.startswith("```"):
        cleaned = cleaned[len("```"):].strip()
    if cleaned.endswith("```"):
        cleaned = cleaned[:-len("```")].strip()

    # 移除可能的額外文字（例如 Gemini API 添加的說明）
    cleaned_lines = []
    in_json = False
    for line in cleaned.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith("{"):
            in_json = True
        if in_json:
            cleaned_lines.append(line)
        if line.endswith("}"):
            break

    cleaned = "\n".join(cleaned_lines).strip()

    try:
        result = json.loads(cleaned)
        for item in ITEMS:
            if item not in result:
                result[item] = ""
        return result
    except Exception as e:
        socketio.emit('error', {'message': f"解析 JSON 失敗：{str(e)}\n原始回應：{response_text}"})
        return {item: "" for item in ITEMS}

def process_batch_dialogue(dialogues, model, socketio, delimiter="-----"):
    """批次處理對話並返回評分結果，改進 Prompt 確保正確格式"""
    prompt = (
        "你是一位管理與溝通分析專家，請根據以下評分項目評估主管與員工 1:1 對話中的每一句話，\n"
        + "\n".join(ITEMS) +
        "\n\n請依據評估結果，對每個項目：若主管的發言觸及該項則標記為 1，否則留空。"
        " 請對每筆逐字稿產生 JSON 格式回覆，並在各筆結果間用下列分隔線隔開：\n"
        f"{delimiter}\n"
        "僅回傳 JSON 格式結果，不要包含額外的文字或 Markdown 標記，例如：\n"
        "{\n  \"明確目標設定\": \"1\",\n  \"提供具體反饋\": \"\",\n  \"積極傾聽\": \"1\",\n  ...\n}\n"
        f"{delimiter}\n"
        "{\n  \"明確目標設定\": \"\",\n  \"提供具體反饋\": \"1\",\n  ...\n}\n"
    )
    batch_text = f"\n{delimiter}\n".join(dialogues)
    content = prompt + "\n\n" + batch_text

    try:
        response = model.generate_content(content)
        socketio.emit('update', {'message': f"API 回傳內容：{response.text}"})  # 除錯用
        parts = response.text.split(delimiter)
        results = []
        for part in parts:
            part = part.strip()
            if part:
                results.append(parse_response(part, socketio))
        if len(results) > len(dialogues):
            results = results[:len(dialogues)]
        elif len(results) < len(dialogues):
            results.extend([{item: "" for item in ITEMS}] * (len(dialogues) - len(results)))
        return results
    except exceptions.GoogleAPIError as e:
        socketio.emit('error', {'message': f"API 呼叫失敗：{str(e)}"})
        return [{item: "" for item in ITEMS} for _ in dialogues]