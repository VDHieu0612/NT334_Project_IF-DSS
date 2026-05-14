import os
import sys

# Fix UnicodeEncodeError trên Windows console (cp1252 không hỗ trợ tiếng Việt)
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

import subprocess
import time
import requests
import json
import random
import re
import signal
import platform
import threading
from datetime import datetime

# Định nghĩa các đường dẫn
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
CSV_FILE = os.path.join(BASE_DIR, "online-valid.csv")
MAIN_PATH = os.path.abspath(os.path.join(BASE_DIR, "..", "main.py"))
PHISHTANK_URL = "https://data.phishtank.com/data/online-valid.csv"

# Detect OS
IS_WINDOWS = platform.system() == "Windows"
PYTHON_CMD = sys.executable  # Tự động dùng đúng Python (python / python3)

# Biến toàn cục để xử lý gián đoạn
daemon_process = None
bitswap_thread = None
bitswap_stop_event = threading.Event()

def signal_handler(sig, frame):
    """Xử lý Ctrl+C - tắt IPFS daemon an toàn và lưu tiến trình."""
    print("\n\n[!] Nhận tín hiệu gián đoạn (Ctrl+C).")
    print("[*] Tiến trình đã được lưu tự động (track.json + track_duplicate.json).")
    print("[*] Chạy lại pipeline.py để RESUME từ vị trí đã dừng.\n")
    cleanup_daemon()
    sys.exit(0)

def cleanup_daemon():
    """Tắt IPFS daemon an toàn - hỗ trợ cả Windows và Linux."""
    global daemon_process, bitswap_stop_event
    bitswap_stop_event.set()  # Dừng thread Bitswap monitor
    
    if daemon_process and daemon_process.poll() is None:
        print("[*] Đang tắt IPFS Daemon...")
        daemon_process.terminate()
        try:
            daemon_process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            daemon_process.kill()
    
    # Dọn dẹp tiến trình ipfs daemon còn sót
    try:
        if IS_WINDOWS:
            subprocess.run(["taskkill", "/F", "/IM", "ipfs.exe"],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            subprocess.run(["pkill", "-f", "ipfs daemon"], 
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass

def bitswap_monitor_thread(daemon_proc, log_path):
    """Thread đọc stdout của IPFS daemon và lọc Bitswap log (cross-platform)."""
    bitswap_pattern = re.compile(r'Bitswap engine')
    try:
        with open(log_path, "a", encoding="utf-8") as log_file:
            for line in iter(daemon_proc.stdout.readline, b''):
                if bitswap_stop_event.is_set():
                    break
                try:
                    decoded = line.decode("utf-8", errors="replace")
                    if bitswap_pattern.search(decoded):
                        if '"from"' in decoded and '"cid"' in decoded:
                            log_file.write(decoded)
                            log_file.flush()
                except Exception:
                    continue
    except Exception:
        pass

def setup_environment():
    """Tạo thư mục output nếu chưa tồn tại."""
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
    print(f"[*] Môi trường đã sẵn sàng. (OS: {platform.system()})")

def step_1_data_ingestion():
    """Bước 1: Thu thập và Tiền xử lý Dữ liệu"""
    print("\n--- BƯỚC 1: THU THẬP VÀ TIỀN XỬ LÝ DỮ LIỆU ---")
    
    # Kiểm tra nếu đã có dữ liệu (cho phép skip khi resume)
    cid_result_path = os.path.join(OUTPUT_DIR, "cid_result.txt")
    if os.path.exists(cid_result_path) and os.path.getsize(cid_result_path) > 0:
        print("[*] Đã tìm thấy cid_result.txt từ lần chạy trước.")
        user_input = input("    Bạn có muốn tải lại dữ liệu mới từ PhishTank? (y/n) [n]: ").strip().lower()
        if user_input != 'y':
            print("[*] Sử dụng dữ liệu có sẵn. Bỏ qua bước tải.")
            return True
    
    # 1. Tải dữ liệu mới nhất từ Phishtank trực tiếp từ web
    print(f"[*] Đang kéo dữ liệu lừa đảo mới nhất từ {PHISHTANK_URL}...")
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36'
        }
        response = requests.get(PHISHTANK_URL, headers=headers, timeout=60)
        response.raise_for_status() 
        
        with open(CSV_FILE, 'wb') as f:
            f.write(response.content)
        print("[+] Đã tải xong tập dữ liệu CSV mới nhất.")
        
    except Exception as e:
        print(f"[-] Lỗi khi tải dữ liệu từ web: {e}")
        if os.path.exists(CSV_FILE):
            print("[*] Sử dụng file CSV cũ có sẵn.")
        else:
            return False

    # 2. Gọi parse.py (thông qua main.py) để lấy CIDv0 và CIDv1
    print("[*] Đang bóc tách CID từ URL...")
    subprocess.run([PYTHON_CMD, MAIN_PATH, "parse", CSV_FILE, "-o", OUTPUT_DIR])
    
    # 3. Gọi dnslink.py (thông qua main.py) để lấy CID ẩn dưới DNS
    print("[*] Đang truy vấn DNSLink để tìm CID ẩn...")
    dns_result_path = os.path.join(OUTPUT_DIR, "dns_result.txt")
    if os.path.exists(dns_result_path) and os.path.getsize(dns_result_path) > 0:
        # DNSLink cần lệnh `dig` — trên Windows có thể không có
        # Thử chạy, nếu lỗi thì bỏ qua (không ảnh hưởng kết quả chính)
        try:
            result = subprocess.run(
                [PYTHON_CMD, MAIN_PATH, "trackdns", dns_result_path, "-o", OUTPUT_DIR],
                timeout=60, capture_output=True
            )
            if result.returncode != 0:
                print("[-] DNSLink query lỗi (có thể thiếu lệnh 'dig'). Bỏ qua — không ảnh hưởng kết quả chính.")
        except Exception:
            print("[-] DNSLink query không khả dụng trên hệ thống này. Bỏ qua.")
    else:
        print("[-] Không tìm thấy file dns_result.txt, bỏ qua truy vấn DNS.")
    
    return True

def step_2_node_tracking(sample_percent=100): 
    """Bước 2: Xây dựng Module Truy vết Mạng (Có tính năng lấy mẫu % + RESUME)
    Cross-platform: Dùng Python thread thay vì grep/pipe để capture Bitswap log."""
    global daemon_process, bitswap_thread, bitswap_stop_event
    print("\n--- BƯỚC 2: TRUY VẾT MẠNG P2P (NODE TRACKING) ---")
    
    # --- KIỂM TRA RESUME ---
    track_dup_path = os.path.join(OUTPUT_DIR, "track_duplicate.json")
    track_json_path = os.path.join(OUTPUT_DIR, "track.json")
    is_resuming = False
    
    if os.path.exists(track_dup_path):
        try:
            with open(track_dup_path, "r") as f:
                existing_tracked = json.load(f)
            if len(existing_tracked) > 0:
                print(f"\n[RESUME] Phát hiện checkpoint từ lần chạy trước!")
                print(f"[RESUME] Đã track: {len(existing_tracked)} CID")
                user_input = input("[RESUME] Tiếp tục từ checkpoint? (y/n) [y]: ").strip().lower()
                if user_input != 'n':
                    is_resuming = True
                    print(f"[RESUME] Sẽ bỏ qua {len(existing_tracked)} CID đã track.\n")
                else:
                    print("[*] Bắt đầu lại từ đầu (xóa checkpoint cũ)...")
                    os.remove(track_dup_path)
                    if os.path.exists(track_json_path):
                        os.remove(track_json_path)
        except (json.JSONDecodeError, Exception):
            pass
    
    # 1. Khởi chạy IPFS daemon — Cross-platform (không dùng grep/pipe)
    print("[*] Đang khởi chạy IPFS Daemon trong background...")
    bitswap_log_path = os.path.join(OUTPUT_DIR, "bitswap_monitor.log")
    bitswap_stop_event.clear()
    
    # Chạy daemon trực tiếp, capture stdout bằng Python
    daemon_process = subprocess.Popen(
        ["ipfs", "daemon"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT
    )
    
    # Thread riêng để đọc và lọc Bitswap log
    bitswap_thread = threading.Thread(
        target=bitswap_monitor_thread,
        args=(daemon_process, bitswap_log_path),
        daemon=True
    )
    bitswap_thread.start()
    
    # Đợi 15 giây để IPFS daemon khởi động ổn định
    print("[*] Đợi 15 giây để IPFS Daemon ổn định kết nối...")
    time.sleep(15)

    # 2. Set log level cho IPFS
    print("[*] Thiết lập tính năng thu thập log Bitswap...")
    subprocess.run(["ipfs", "log", "level", "engine", "debug"],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    # --- LẤY MẪU (SAMPLING) % CID ---
    cid_result_path = os.path.join(OUTPUT_DIR, "cid_result.txt")
    cid_sampled_path = os.path.join(OUTPUT_DIR, "cid_sampled_result.txt")
    
    if os.path.exists(cid_result_path):
        with open(cid_result_path, "r") as f:
            raw_lines = [line.strip() for line in f if line.strip()]
        
        # Lọc CID theo cùng logic với track.py (URL_to_CID)
        valid_cids = []
        for line in raw_lines:
            if "Qm" in line:
                idx = line.find("Qm")
                if len(line[idx:idx+46]) == 46:
                    valid_cids.append(line[idx:idx+46])
            elif "baf" in line:
                idx = line.find("baf")
                if len(line[idx:idx+59]) == 59:
                    valid_cids.append(line[idx:idx+59])
        
        cids = list(set(valid_cids))
        total_cids = len(cids)
        sample_size = int(total_cids * (sample_percent / 100.0))
        
        if sample_size == 0 and total_cids > 0:
            sample_size = 1 
            
        print(f"[*] Tìm thấy tổng cộng {total_cids} CID hợp lệ (từ {len(raw_lines)} dòng).")
        
        # Nếu 100%, dùng tất cả
        if sample_percent >= 100:
            sampled_cids = cids
        else:
            sampled_cids = random.sample(cids, sample_size)
        
        with open(cid_sampled_path, "w") as f:
            for cid in sampled_cids:
                f.write(cid + "\n")
                
        print("\n" + "="*60)
        print(f"[>>>] BẮT ĐẦU TRUY VẾT: Phân tích {sample_size} CID ({sample_percent}%) [<<<]")
        if is_resuming:
            print(f"[>>>] CHẾ ĐỘ RESUME: Bỏ qua CID đã track từ checkpoint [<<<]")
        print("="*60 + "\n")

        # 3. Gọi track.py với file ĐÃ ĐƯỢC LẤY MẪU
        subprocess.run(
            [PYTHON_CMD, MAIN_PATH, "track", "--ipfs", "ipfs", cid_sampled_path, "-o", OUTPUT_DIR],
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
        subprocess.run([PYTHON_CMD, MAIN_PATH, "ipmap", track_json_path, "-o", OUTPUT_DIR])
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
    
    if not os.path.exists(log_path) or os.path.getsize(log_path) == 0:
        print("[-] Không tìm thấy file bitswap_monitor.log hoặc file trống. Bỏ qua phân tích Timeline.")
        return

    try:
        import matplotlib
        matplotlib.use('Agg')  # Non-interactive backend
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
    
    with open(log_path, 'r', encoding='utf-8', errors='replace') as f:
        for line in f:
            match = pattern.search(line)
            if match:
                time_str = match.group(1)
                dt = datetime.strptime(time_str, "%Y-%m-%dT%H:%M:%S.%f")
                times.append(dt)
                cids.append(match.group(3))

    if not times:
        print("[-] File log trống hoặc chưa bắt được gói tin 'want-have' nào.")
        return
        
    print(f"[*] Đã bắt được {len(times)} sự kiện truy vấn block. Đang xử lý dữ liệu...")

    # 1. Gom nhóm thời gian theo từng PHÚT
    times_per_minute = [dt.replace(second=0, microsecond=0) for dt in times]
    time_counts = Counter(times_per_minute)
    sorted_times = sorted(time_counts.keys())
    counts = [time_counts[t] for t in sorted_times]

    # 2. Top 10 CID
    cid_counts = Counter(cids)
    top_10_cids = cid_counts.most_common(10)
    top_cids_labels = [f"{x[0][:8]}...{x[0][-6:]}" for x in top_10_cids]
    top_cids_values = [x[1] for x in top_10_cids]

    # --- BIỂU ĐỒ 1: TẦN SUẤT ---
    print("[*] Đang vẽ Biểu đồ 1 (Tần suất)...")
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
    plt.close()

    # --- BIỂU ĐỒ 2: TOP 10 CID ---
    print("[*] Đang vẽ Biểu đồ 2 (Top 10 CID)...")
    plt.figure(figsize=(12, 6))
    plt.barh(top_cids_labels[::-1], top_cids_values[::-1], color='steelblue', edgecolor='black')
    plt.title('Top 10 Content ID (CID) Lừa đảo bị truy vấn nhiều nhất', fontsize=14, fontweight='bold')
    plt.xlabel('Tổng số lần truy vấn (Requests)', fontsize=12)
    plt.grid(True, axis='x', linestyle='--', alpha=0.6)

    for index, value in enumerate(top_cids_values[::-1]):
        plt.text(value, index, f' {value}', va='center', fontsize=11)

    plt.tight_layout()
    
    output_img2 = os.path.join(OUTPUT_DIR, "forensic_timeline_top_cids.png")
    plt.savefig(output_img2, dpi=300, bbox_inches='tight')
    plt.close()

    print(f"[+] Hoàn tất! Đã xuất 2 biểu đồ:")
    print(f"    1. {output_img1}")
    print(f"    2. {output_img2}")

if __name__ == "__main__":
    # Đăng ký signal handler
    signal.signal(signal.SIGINT, signal_handler)
    if not IS_WINDOWS:
        signal.signal(signal.SIGTERM, signal_handler)
    
    # Parse tham số dòng lệnh
    sample_percent = 100
    for i, arg in enumerate(sys.argv):
        if arg in ('--sample', '-s') and i + 1 < len(sys.argv):
            try:
                sample_percent = int(sys.argv[i + 1])
            except ValueError:
                print(f"[-] Giá trị sample không hợp lệ: {sys.argv[i + 1]}")
                sys.exit(1)
        elif arg in ('--help', '-h'):
            print("Sử dụng: python pipeline.py [--sample PERCENT]")
            print("  --sample, -s  Phần trăm CID để truy vết (1-100, mặc định: 100)")
            print("\nVí dụ:")
            print("  python pipeline.py              # Chạy 100%")
            print("  python pipeline.py --sample 5   # Chạy 5%")
            print("  python pipeline.py -s 10        # Chạy 10%")
            print("\nResume: Nếu bị gián đoạn (Ctrl+C), chạy lại lệnh sẽ tự động resume.")
            sys.exit(0)
    
    print("="*60)
    print("  IF-DSS Case Study 1: IPFS Phishing Investigation Pipeline")
    print(f"  OS: {platform.system()} | Sample: {sample_percent}% | Resume: Tự động")
    print("="*60)
    
    setup_environment()
    
    if step_1_data_ingestion():
        daemon_proc = step_2_node_tracking(sample_percent=sample_percent)
        step_3_data_enrichment()
        step_4_timeline_analysis()
        
        print("\n[*] Quá trình phân tích hoàn tất.")
        cleanup_daemon()
        
        # Thống kê cuối cùng
        print("\n" + "="*60)
        print("  KẾT QUẢ PHÂN TÍCH")
        print("="*60)
        track_path = os.path.join(OUTPUT_DIR, "track.json")
        if os.path.exists(track_path):
            with open(track_path, "r") as f:
                try:
                    data = json.load(f)
                    total_ips = set()
                    for cid_data in data.values():
                        total_ips.update(cid_data.get("IP", []))
                    print(f"  CID có provider : {len(data)}")
                    print(f"  IP duy nhất     : {len(total_ips)}")
                except Exception:
                    pass
        ioc_path = os.path.join(OUTPUT_DIR, "blacklist_ioc.json")
        if os.path.exists(ioc_path):
            print(f"  Blacklist IOC   : {ioc_path}")
        map_path = os.path.join(OUTPUT_DIR, "IPMAP_result.html")
        if os.path.exists(map_path):
            print(f"  Bản đồ IP       : {map_path}")
        print("="*60)