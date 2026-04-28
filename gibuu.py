from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
import re

app = FastAPI()
connected_clients = []

@app.get("/")
async def get_webpage():
    html_content = """
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8">
        <title>재혁이에게 기부하기</title>
        <style>
            body { font-family: 'Malgun Gothic', sans-serif; text-align: center; margin-top: 150px; background-color: #f0f2f5; }
            #alert-box { 
                font-size: 25px; font-weight: bold; color: #333; padding: 40px; 
                border-radius: 20px; background-color: white; 
                box-shadow: 0 10px 20px rgba(0,0,0,0.1); display: inline-block;
                transition: all 0.3s ease-in-out;
            }
            .highlight { color: #e91e63; font-size: 50px; }
        </style>
    </head>
    <body>
        <div id="alert-box">💸 신한은행 110-504-443616으로 원하는 금액을 입금해보세요!
        신기한 일이 생깁니다~</div>
        <script>
            var wsProtocol = window.location.protocol === "https:" ? "wss://" : "ws://";
            var ws = new WebSocket(wsProtocol + window.location.host + "/ws");
            
            ws.onmessage = function(event) {
                var data = JSON.parse(event.data);
                var box = document.getElementById("alert-box");
                
                // 천 단위 콤마를 다시 찍어주는 기능 추가 (예: 22000 -> 22,000)
                var formattedAmount = Number(data.amount).toLocaleString();
                
                box.innerHTML = "🎉 <b>" + data.senderName + "</b>님이 <br><span class='highlight'>" + formattedAmount + "원</span>을 입금하셨습니다!! 바보~";
                
                box.style.transform = "scale(1.1)";
                setTimeout(() => box.style.transform = "scale(1)", 300);
            };
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    connected_clients.append(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        connected_clients.remove(websocket)

# 여기가 핵심입니다! 문자를 받아서 분석하는 곳
@app.post("/webhook/deposit")
async def receive_deposit(request: Request):
    data = await request.json()
    
    # 아이폰에서 보낸 전체 문자 내용을 가져옵니다.
    sms_text = data.get("sms_text", "")
    
    print("-----------------------------------------")
    print("📱 [수신된 원본 문자]\n", sms_text)
    
    try:
        # 1. 금액 추출 (입금 글자 뒤의 숫자와 쉼표 찾기)
        amount_match = re.search(r'입금\s+([0-9,]+)', sms_text)
        if amount_match:
            amount = amount_match.group(1).replace(',', '') # 계산을 위해 쉼표 제거 (예: 22,000 -> 22000)
        else:
            amount = "0"
        
        # 2. 이름 추출 (문자를 줄바꿈으로 나누고, '입금'이 있는 다음 줄을 가져오기)
        lines = sms_text.strip().split('\n')
        sender_name = "이름 모름"
        for i, line in enumerate(lines):
            if '입금' in line:
                if i + 1 < len(lines):
                    sender_name = lines[i+1].strip()
                break
                
    except Exception as e:
        print("문자 분석 중 에러 발생:", e)
        sender_name = "분석오류"
        amount = "0"
    
    print(f"🎯 [분석 완료] 이름: {sender_name}, 금액: {amount}원")
    print("-----------------------------------------")
    
    # 웹페이지로 데이터 전송
    for client in connected_clients:
        await client.send_json({"senderName": sender_name, "amount": amount})
        
    return {"status": "success", "message": "분석 성공"}