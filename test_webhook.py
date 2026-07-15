import requests
import json
import time

url = "http://127.0.0.1:5000/webhook/hanet"

# Payload giả lập sự kiện quét khuôn mặt từ Hanet gửi về Web App
payload = {
    "action": "checkin",
    "deviceID": "CAM_GATE_01",
    "deviceName": "Camera Cổng Chính",
    "placeID": "997723",
    "placeName": "Văn phòng KimQ",
    "time": int(time.time() * 1000), # Mili-giây hiện tại
    "personID": "HANET_USER_888",
    "aliasID": "CC_0928", # Mã số nhân viên
    "personName": "Nguyễn Hoàng Nam",
    "faceImageURL": "https://images.unsplash.com/photo-1500648767791-00dcc994a43e?auto=format&fit=crop&w=150&h=150&q=80"
}

headers = {
    "Content-Type": "application/json"
}

print(f"Gửi dữ liệu check-in giả lập đến Web App: {url}...")
print(json.dumps(payload, indent=2, ensure_ascii=False))

try:
    response = requests.post(url, headers=headers, json=payload, timeout=5)
    print("\n--- PHẢN HỒI TỪ WEB APP BRIDGE ---")
    print(f"HTTP Status: {response.status_code}")
    print(f"Nội dung phản hồi: {response.text}")
except Exception as e:
    print(f"\n[LỖI]: Không thể kết nối đến Web App.")
    print("Vui lòng chạy `python app.py` trước khi chạy script test này.")
    print(f"Chi tiết: {e}")
