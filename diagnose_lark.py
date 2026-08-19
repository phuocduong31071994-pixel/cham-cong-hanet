import os
import sys
import json
import requests

# Reconfigure stdout and stderr to support UTF-8 on Windows terminal
if sys.platform.startswith('win'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except AttributeError:
        pass


def load_env_file():
    env_vars = {}
    if os.path.exists(".env"):
        print("🔍 Tìm thấy file .env, đang đọc cấu hình...")
        with open(".env", "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                parts = line.split("=", 1)
                if len(parts) == 2:
                    key = parts[0].strip()
                    val = parts[1].strip().strip('"').strip("'")
                    env_vars[key] = val
    return env_vars

def main():
    print("====================================================")
    print("   CHƯƠNG TRÌNH CHẨN ĐOÁN KẾT NỐI LARK SUITE / FEISHU")
    print("====================================================\n")
    
    # 1. Load environment variables
    env_vars = load_env_file()
    
    lark_app_id = os.getenv("LARK_APP_ID") or env_vars.get("LARK_APP_ID")
    lark_app_secret = os.getenv("LARK_APP_SECRET") or env_vars.get("LARK_APP_SECRET")
    
    if not lark_app_id or not lark_app_secret:
        print("⚠️  Không tìm thấy LARK_APP_ID hoặc LARK_APP_SECRET trong biến môi trường hoặc file .env.")
        print("Vui lòng nhập trực tiếp để kiểm tra:")
        user_id = input("👉 Nhập LARK_APP_ID (cli_xxx): ").strip()
        user_secret = input("👉 Nhập LARK_APP_SECRET: ").strip()
        if user_id:
            lark_app_id = user_id
        if user_secret:
            lark_app_secret = user_secret
            
    if not lark_app_id or not lark_app_secret:
        print("❌ Lỗi: Thiếu App ID hoặc App Secret. Không thể tiếp tục.")
        sys.exit(1)
        
    print(f"\n⚙️  Thông tin kiểm tra:")
    print(f" - APP ID: {lark_app_id}")
    print(f" - APP SECRET: {'*' * len(lark_app_secret) if lark_app_secret else 'Trống'}")
    
    # Test domains
    domains = {
        "Lark Suite (Bản quốc tế - open.larksuite.com)": "open.larksuite.com",
        "Feishu (Bản Trung Quốc - open.feishu.cn)": "open.feishu.cn"
    }
    
    success_domain = None
    tenant_token = None
    
    for label, domain in domains.items():
        print(f"\n📡 Đang thử kết nối tới {label}...")
        token_url = f"https://{domain}/open-apis/auth/v3/tenant_access_token/internal"
        
        try:
            res = requests.post(token_url, json={
                "app_id": lark_app_id,
                "app_secret": lark_app_secret
            }, timeout=10)
            
            status_code = res.status_code
            res_data = res.json()
            
            if status_code == 200 and res_data.get("code") == 0:
                print(f"✅ Kết nối thành công!")
                tenant_token = res_data.get("tenant_access_token")
                success_domain = domain
                print(f"   - Lấy Tenant Access Token thành công.")
                break
            else:
                err_code = res_data.get("code")
                err_msg = res_data.get("msg")
                print(f"❌ Kết nối thất bại (HTTP {status_code}):")
                print(f"   - Mã lỗi Lark: {err_code}")
                print(f"   - Thông báo Lark: {err_msg}")
                if err_code == 99991663:
                    print("   💡 Gợi ý: App ID hoặc App Secret không chính xác, hoặc ứng dụng chưa được kích hoạt trên nền tảng này.")
                elif err_code == 99991668:
                    print("   💡 Gợi ý: Địa chỉ IP của bạn không nằm trong danh sách trắng (IP Whitelist) của ứng dụng.")
        except Exception as e:
            print(f"❌ Lỗi kết nối mạng: {e}")
            
    if not tenant_token:
        print("\n====================================================")
        print("❌ KẾT LUẬN: Không thể lấy Token từ cả Lark Suite và Feishu.")
        print("Vui lòng kiểm tra lại:")
        print("1. Giá trị LARK_APP_ID và LARK_APP_SECRET đã chính xác chưa.")
        print("2. Ứng dụng đã được tạo và kích hoạt trên trang Developer Console tương ứng chưa:")
        print("   - Lark Developer Console: https://open.larksuite.com/document/home/index")
        print("   - Feishu Developer Console: https://open.feishu.cn/document/home/index")
        print("3. Kiểm tra thiết lập bảo mật IP Whitelist trong Developer Console -> Security Settings.")
        print("====================================================")
        sys.exit(1)
        
    print(f"\n🔓 Sử dụng domain thành công: {success_domain}")
    print("\n🔍 Đang kiểm tra quyền truy cập API đơn duyệt (Approval API)...")
    
    headers = {
        "Authorization": f"Bearer {tenant_token}",
        "Content-Type": "application/json"
    }
    
    # Check default approval code
    app_code = "0E4F14E9-F5E3-4939-8DE8-8294872C5D4E"
    query_url = f"https://{success_domain}/open-apis/approval/v4/instances/query"
    payload = {
        "approval_code": app_code,
        "start_time": "1770000000000",  # Epoch time sample
        "end_time": "1800000000000"
    }
    
    try:
        res = requests.post(query_url, headers=headers, json=payload, timeout=10)
        res_data = res.json()
        code = res_data.get("code")
        
        if code == 0:
            print("✅ Kiểm tra quyền truy cập danh sách đơn duyệt thành công!")
            print(f"   - Mã đơn phép '{app_code}' hoạt động tốt.")
        else:
            err_msg = res_data.get("msg")
            print(f"❌ Không thể truy vấn đơn duyệt (Mã lỗi Lark: {code}): {err_msg}")
            
            # Specific check for permissions
            if "permission" in err_msg.lower() or "scope" in err_msg.lower() or code == 99991672:
                print("\n💡 Gợi ý xử lý quyền:")
                print("Ứng dụng của bạn chưa được cấp quyền đọc danh sách đơn duyệt.")
                print("Hãy làm theo các bước sau:")
                print("1. Truy cập Lark Developer Console của ứng dụng.")
                print("2. Vào mục 'Permission Administration' (Quản lý quyền).")
                print("3. Tìm kiếm và bật quyền: 'approval:approval.list:readonly' (Xem danh sách đơn duyệt).")
                print("4. Đồng thời bật quyền: 'contact:user.employee_id:readonly' và 'contact:contact:readonly' (để đọc thông tin nhân sự).")
                print("5. Tạo một phiên bản mới (Version Management -> Create a version) và Phát hành (Release).")
                print("6. Nhờ Admin của Lark của tổ chức Phê duyệt (Approval) phiên bản mới này.")
            else:
                print(f"   - Chi tiết phản hồi từ Lark: {json.dumps(res_data, ensure_ascii=False, indent=2)}")
    except Exception as e:
        print(f"❌ Lỗi khi gửi yêu cầu kiểm tra quyền: {e}")
        
    print("\n====================================================")
    print("🎉 Hoàn thành kiểm tra chẩn đoán.")
    print("====================================================")

if __name__ == "__main__":
    main()
