import os
import subprocess
import time
import requests
import json
import random
import re
import shlex
from datetime import datetime

# Định nghĩa các đường dẫn
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
CSV_FILE = os.path.join(BASE_DIR, "online-valid.csv")
MAIN_PATH = os.path.abspath(os.path.join(BASE_DIR, "..", "main.py"))
PHISHTANK_URL = "https://data.phishtank.com/data/online-valid.csv"

def setup_environment():
    """Tạo thư mục output nếu chưa tồn tại."""
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
    print("[*] Môi trường đã sẵn sàng.")

def step_1_data_ingestion():
    """Bước 1: Thu thập và Tiền xử lý Dữ liệu"""
    print("\n--- BƯỚC 1: THU THẬP VÀ TIỀN XỬ LÝ DỮ LIỆU ---")
    
    # 1. Tải dữ liệu mới nhất từ Phishtank trực tiếp từ web
    print(f"[*] Đang kéo dữ liệu lừa đảo mới nhất từ {PHISHTANK_URL}...")
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36'
        }
        response = requests.get(PHISHTANK_URL, headers=headers, timeout=30)
        response.raise_for_status() 
        
        with open(CSV_FILE, 'wb') as f:
            f.write(response.content)
        print("[+] Đã tải xong tập dữ liệu CSV mới nhất.")
        
    except Exception as e:
        print(f"[-] Lỗi khi tải dữ liệu từ web: {e}")
        return False

    # 2. Gọi parse.py (thông qua main.py) để lấy CIDv0 và CIDv1
    print("[*] Đang bóc tách CID từ URL...")
    subprocess.run(["python3", MAIN_PATH, "parse", CSV_FILE, "-o", OUTPUT_DIR])
    
    # 3. Gọi dnslink.py (thông qua main.py) để lấy CID ẩn dưới DNS
    print("[*] Đang truy vấn DNSLink để tìm CID ẩn...")
    # [FIX CẬP NHẬT] Đọc file dns_result.txt đã được parse thay vì file CSV thô
    dns_result_path = os.path.join(OUTPUT_DIR, "dns_result.txt")
    if os.path.exists(dns_result_path):
        subprocess.run(["python3", MAIN_PATH, "trackdns", dns_result_path, "-o", OUTPUT_DIR])
    else:
        print("[-] Không tìm thấy file dns_result.txt, bỏ qua truy vấn DNS.")
    
    return True

def step_2_node_tracking(sample_percent=100): 
    """Bước 2: Xây dựng Module Truy vết Mạng (Có tính năng lấy mẫu %)"""
    print("\n--- BƯỚC 2: TRUY VẾT MẠNG P2P (NODE TRACKING) ---")
    
    # 1. Khởi chạy IPFS daemon ngầm và grep log Bitswap ra file
    print("[*] Đang khởi chạy IPFS Daemon trong background và monitor Bitswap...")
    bitswap_log_path = os.path.join(OUTPUT_DIR, "bitswap_monitor.log")
    bitswap_cmd = (
        'ipfs daemon 2>&1 | grep "Bitswap engine" '
        '| grep -E \'"from"\\s*:\\s*"(.*?)".*?"cid"\\s*:\\s*"(.*?)"\' '
        f"> {shlex.quote(bitswap_log_path)}"
    )
    daemon_process = subprocess.Popen(bitswap_cmd, shell=True)
    
    # Đợi 15 giây để IPFS daemon khởi động ổn định trước khi làm bước tiếp theo
    print("[*] Đợi 15 giây để IPFS Daemon ổn định kết nối...")
    time.sleep(15)

    # [FIX CẬP NHẬT] 2. Set log level cho IPFS sau khi daemon CHẮC CHẮN đã chạy
    print("[*] Thiết lập tính năng thu thập log Bitswap (Daemon đã kích hoạt)...")
    subprocess.run(["ipfs", "log", "level", "engine", "debug"])
    
    # --- LẤY MẪU (SAMPLING) % CID ---
    cid_result_path = os.path.join(OUTPUT_DIR, "cid_result.txt")
    cid_sampled_path = os.path.join(OUTPUT_DIR, "cid_sampled_result.txt")
    
    if os.path.exists(cid_result_path):
        with open(cid_result_path, "r") as f:
            cids = list(set([line.strip() for line in f if line.strip()]))
            
        total_cids = len(cids)
        sample_size = int(total_cids * (sample_percent / 100.0))
        
        if sample_size == 0 and total_cids > 0:
            sample_size = 1 
            
        print(f"[*] Tìm thấy tổng cộng {total_cids} CID duy nhất.")
        
        sampled_cids = random.sample(cids, sample_size)
        
        with open(cid_sampled_path, "w") as f:
            for cid in sampled_cids:
                f.write(cid + "\n")
                
        # [FIX HIỂN THỊ] Thông báo số lượng RÕ RÀNG trước khi chạy track.py
        print("\n" + "="*60)
        print(f"[>>>] BẮT ĐẦU TRUY VẾT: Phân tích {sample_size} CID ngẫu nhiên ({sample_percent}%) [<<<]")
        print("="*60 + "\n")

        # 3. Gọi track.py với file ĐÃ ĐƯỢC LẤY MẪU
        subprocess.run(
            ["python3", MAIN_PATH, "track", "--ipfs", "ipfs", cid_sampled_path, "-o", OUTPUT_DIR],
            input="y\n",
            text=True
        )
    else:
        print("[-] Không tìm thấy file cid_result.txt.")
        
    return daemon_process

def step_3_data_enrichment():
    """Bước 3: Làm giàu Dữ liệu và Tổng hợp IOC"""
    print("\n--- BƯỚC 3: LÀM GIÀU DỮ LIỆU VÀ TỔNG HỢP IOC ---")
    track_json_path = os.path.join(OUTPUT_DIR, "track.json")
    
    if os.path.exists(track_json_path):
        print("[*] Đang khởi tạo bản đồ HTML...")
        subprocess.run(["python3", MAIN_PATH, "ipmap", track_json_path, "-o", OUTPUT_DIR])
    else:
        print("[-] Không tìm thấy file track.json để tạo bản đồ.")

    print("[*] Đang tổng hợp dữ liệu thành Blacklist Database (JSON)...")
    blacklist = {
        "description": "IPFS Phishing Threat Intelligence IOCs",
        "timestamp": time.time(),
        "cids": [],
        "malicious_ips": []
    }
    
    cid_result_path = os.path.join(OUTPUT_DIR, "cid_result.txt")
    if os.path.exists(cid_result_path):
        with open(cid_result_path, "r") as f:
            cids = [line.strip() for line in f if line.strip()]
            blacklist["cids"] = list(set(cids))
            
    if os.path.exists(track_json_path):
        with open(track_json_path, "r") as f:
            try:
                track_data = json.load(f)
                ip_list = []
                for cid, data in track_data.items():
                    ip_list.extend(data.get("IP", []))
                blacklist["malicious_ips"] = list(set(ip_list))
            except json.JSONDecodeError:
                print("[-] Lỗi đọc file track.json")

    ioc_output_path = os.path.join(OUTPUT_DIR, "blacklist_ioc.json")
    with open(ioc_output_path, "w") as f:
        json.dump(blacklist, f, indent=4)
        
    print(f"[+] Hoàn tất! Blacklist đã được lưu tại: {ioc_output_path}")

def step_4_timeline_analysis():
    """Bước 4: Trực quan hóa Dòng thời gian (Timeline Analysis) bằng Log Bitswap"""
    print("\n--- BƯỚC 4: PHÂN TÍCH TIMELINE ĐIỀU TRA ---")
    log_path = os.path.join(OUTPUT_DIR, "bitswap_monitor.log")
    
    if not os.path.exists(log_path):
        print("[-] Không tìm thấy file bitswap_monitor.log. Bỏ qua phân tích Timeline.")
        return

    try:
        import matplotlib.pyplot as plt
        import matplotlib.dates as mdates
        from collections import Counter
    except ImportError:
        print("[-] Lỗi: Cần cài đặt matplotlib để vẽ biểu đồ.")
        print("    Gõ lệnh: pip install matplotlib")
        return

    print(f"[*] Đang đọc và bóc tách dữ liệu từ {log_path}...")
    
    pattern = re.compile(r'^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d+)[+-]\d{4}.*?"from"\s*:\s*"([^"]+)".*?"cid"\s*:\s*"([^"]+)"')
    
    times = []
    cids = []
    
    with open(log_path, 'r') as f:
        for line in f:
            match = pattern.search(line)
            if match:
                time_str = match.group(1)
                dt = datetime.strptime(time_str, "%Y-%m-%dT%H:%M:%S.%f")
                times.append(dt)
                cids.append(match.group(3)) # Lấy toàn bộ CID để đếm cho chuẩn

    if not times:
        print("[-] File log trống hoặc chưa bắt được gói tin 'want-have' nào.")
        return
        
    print(f"[*] Đã bắt được {len(times)} sự kiện truy vấn block. Đang xử lý dữ liệu...")

    # --- TIỀN XỬ LÝ DỮ LIỆU ---
    # 1. Gom nhóm thời gian theo từng PHÚT để vẽ xu hướng
    times_per_minute = [dt.replace(second=0, microsecond=0) for dt in times]
    time_counts = Counter(times_per_minute)
    sorted_times = sorted(time_counts.keys())
    counts = [time_counts[t] for t in sorted_times]

    # 2. Tìm Top 10 CID được request nhiều nhất
    cid_counts = Counter(cids)
    top_10_cids = cid_counts.most_common(10)
    top_cids_labels = [f"{x[0][:8]}...{x[0][-6:]}" for x in top_10_cids]
    top_cids_values = [x[1] for x in top_10_cids]

    # --- VẼ BIỂU ĐỒ 1: TẦN SUẤT TRUY VẤN ---
    print("[*] Đang tiến hành vẽ Biểu đồ 1 (Tần suất)...")
    plt.figure(figsize=(12, 5))
    plt.plot(sorted_times, counts, color='crimson', marker='o', linestyle='-', linewidth=2, markersize=5)
    plt.title('Dòng thời gian Điều tra: Tần suất truy vấn mạng IPFS (Events per Minute)', fontsize=14, fontweight='bold')
    plt.ylabel('Số lượng truy vấn (Blocks)', fontsize=12)
    plt.xlabel('Thời gian ghi nhận', fontsize=12)
    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
    plt.grid(True, linestyle='--', alpha=0.6)
    plt.tight_layout()
    
    output_img1 = os.path.join(OUTPUT_DIR, "forensic_timeline_frequency.png")
    plt.savefig(output_img1, dpi=300, bbox_inches='tight')
    plt.close() # Đóng biểu đồ 1 để giải phóng bộ nhớ

    # --- VẼ BIỂU ĐỒ 2: TOP 10 CID ---
    print("[*] Đang tiến hành vẽ Biểu đồ 2 (Top 10 CID)...")
    plt.figure(figsize=(12, 6))
    plt.barh(top_cids_labels[::-1], top_cids_values[::-1], color='steelblue', edgecolor='black')
    plt.title('Top 10 Content ID (CID) Lừa đảo bị truy vấn nhiều nhất', fontsize=14, fontweight='bold')
    plt.xlabel('Tổng số lần truy vấn (Requests)', fontsize=12)
    plt.grid(True, axis='x', linestyle='--', alpha=0.6)

    # Hiển thị số lượng cụ thể ở đuôi mỗi cột
    for index, value in enumerate(top_cids_values[::-1]):
        plt.text(value, index, f' {value}', va='center', fontsize=11)

    plt.tight_layout()
    
    output_img2 = os.path.join(OUTPUT_DIR, "forensic_timeline_top_cids.png")
    plt.savefig(output_img2, dpi=300, bbox_inches='tight')
    plt.close() # Đóng biểu đồ 2

    print(f"[+] Hoàn tất! Đã xuất thành công 2 ảnh riêng biệt tại:")
    print(f"    1. {output_img1}")
    print(f"    2. {output_img2}")

if __name__ == "__main__":
    setup_environment()
    
    if step_1_data_ingestion():
        daemon_proc = step_2_node_tracking(sample_percent=5)
        step_3_data_enrichment()
        step_4_timeline_analysis()
        
        print("\n[*] Quá trình phân tích hoàn tất. Tắt IPFS Daemon...")
        daemon_proc.terminate()
        subprocess.run(["pkill", "-f", "ipfs daemon"])