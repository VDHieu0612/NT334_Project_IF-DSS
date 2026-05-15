import json
import os
from datetime import datetime
import matplotlib.pyplot as plt

def plot_timeline_hourly():
    log_path = os.path.join('CaseStudy1', 'output', 'bitswap_monitor.log')
    if not os.path.exists(log_path):
        print(f"[-] Không tìm thấy log để vẽ biểu đồ: {log_path}")
        return

    print("[*] Đang phân tích log để vẽ biểu đồ theo giờ (vui lòng đợi vì file log rất lớn)...")
    hourly_counts = {}

    with open(log_path, 'r', encoding='utf-8') as f:
        for line in f:
            try:
                # Log format: 2026-05-08T11:14:08.685+0700 ...
                timestamp_str = line.split('\t')[0].split('+')[0]
                # Chuyển về datetime object và làm tròn xuống giờ
                dt = datetime.strptime(timestamp_str, "%Y-%m-%dT%H:%M:%S.%f")
                hour_key = dt.strftime("%Y-%m-%d %H:00")
                
                hourly_counts[hour_key] = hourly_counts.get(hour_key, 0) + 1
            except:
                continue

    if not hourly_counts:
        print("[-] Không có dữ liệu hợp lệ để vẽ biểu đồ.")
        return

    # Sắp xếp theo thời gian
    sorted_keys = sorted(hourly_counts.keys())
    values = [hourly_counts[k] for k in sorted_keys]

    # Vẽ biểu đồ
    plt.figure(figsize=(12, 6))
    plt.plot(sorted_keys, values, marker='o', linestyle='-', color='red')
    plt.title('Tần suất sự kiện Bitswap theo GIỜ (Hourly Forensic Timeline)')
    plt.xlabel('Thời gian (Giờ)')
    plt.ylabel('Số lượng sự kiện')
    plt.xticks(rotation=45)
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.tight_layout()

    output_plot = os.path.join('CaseStudy1', 'output', 'forensic_timeline_hourly.png')
    plt.savefig(output_plot)
    print(f"[+] Đã xuất biểu đồ theo giờ tại: {output_plot}")

def check_forensic_stats():
    # ... (giữ nguyên code cũ) ...
    csv_path = os.path.join('CaseStudy1', 'online-valid.csv')
    cid_path = os.path.join('CaseStudy1', 'output', 'cid_result.txt')
    track_path = os.path.join('CaseStudy1', 'output', 'track.json')

    print("="*40)
    print("   THỐNG KÊ KẾT QUẢ PHÂN TÍCH IF-DSS")
    print("="*40)

    if os.path.exists(csv_path):
        with open(csv_path, 'r', encoding='utf-8') as f:
            total_urls = len(f.readlines()) - 1
        print(f"[+] Tổng URL từ PhishTank: {total_urls:,}")

    if os.path.exists(cid_path):
        with open(cid_path, 'r') as f:
            total_cids = len(f.readlines())
        print(f"[+] Số URL bóc tách được CID: {total_cids:,}")

    if os.path.exists(track_path):
        with open(track_path, 'r') as f:
            try:
                data = json.load(f)
                all_ips = []
                for cid in data:
                    all_ips.extend(data[cid].get('IP', []))
                unique_ips = set(all_ips)
                print(f"[+] Tổng số lượt IP xuất hiện: {len(all_ips)}")
                print(f"[+] Số lượng IP duy nhất (Unique): {len(unique_ips)}")
            except: pass

    print("="*40)
    
    # Gọi hàm vẽ biểu đồ
    plot_timeline_hourly()

if __name__ == "__main__":
    check_forensic_stats()
