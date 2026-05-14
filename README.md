# IF-DSS: Khung Điều tra Pháp y cho Hệ thống Lưu trữ Phi tập trung

> **IF-DSS** (Forensic Investigation Framework for Decentralized Storage Systems) — Bộ công cụ mã nguồn mở hỗ trợ điều tra pháp y trên hệ thống lưu trữ phi tập trung IPFS, dựa trên bài báo khoa học:
>
> *"IF-DSS: An investigation framework for decentralized storage systems"* — Forensic Science International: Digital Investigation, 2023.

---

## Mục lục

- [Tổng quan](#tổng-quan)
- [Cấu trúc thư mục](#cấu-trúc-thư-mục)
- [Yêu cầu hệ thống](#yêu-cầu-hệ-thống)
- [Cài đặt](#cài-đặt)
  - [Bước 1: Cài đặt Kubo (IPFS)](#bước-1-cài-đặt-kubo-ipfs)
  - [Bước 2: Thiết lập Python](#bước-2-thiết-lập-python)
- [Cách sử dụng](#cách-sử-dụng)
  - [CLI chính (main.py)](#cli-chính-mainpy)
  - [Case Study 1: Pipeline tự động](#case-study-1-pipeline-tự-động)
- [Kết quả đầu ra](#kết-quả-đầu-ra)
- [Giấy phép](#giấy-phép)

---

## Tổng quan

Project triển khai thực nghiệm các module chính từ framework IF-DSS:

| Module | Mô tả | File |
|--------|--------|------|
| **Parse** | Bóc tách CID (Content ID) từ URL phishing | `src/parse.py` |
| **Track** | Truy vết node IPFS đang lưu trữ nội dung phishing (findprovs + findpeer) | `src/track.py` |
| **DNSLink** | Truy vấn DNS TXT record để tìm CID ẩn dưới tên miền | `src/dnslink.py` |
| **IP Map** | Tạo bản đồ HTML hiển thị vị trí địa lý các IP node | `src/ipmap.py` |
| **Reassemble** | Tái tạo file gốc từ các block IPFS | `src/reassemble.py` |

**Case Study 1** kết hợp tất cả module trên thành một pipeline điều tra tự động end-to-end, từ thu thập dữ liệu PhishTank đến xuất báo cáo IOC.

---

## Cấu trúc thư mục

```
NT334_Project_IF-DSS/
├── main.py                  # CLI chính (click-based)
├── requirements.txt         # Thư viện Python cần thiết
├── LICENSE                  # MIT License
│
├── src/                     # Module chính
│   ├── parse.py             #   Bóc tách CID từ URL
│   ├── track.py             #   Truy vết node IPFS
│   ├── dnslink.py           #   Truy vấn DNSLink
│   ├── ipmap.py             #   Bản đồ IP
│   ├── reassemble.py        #   Tái tạo file từ block IPFS
│   ├── proto/               #   Protobuf schema cho IPFS
│   └── developerAPI/        #   Script tương tác API (Fleek, Web3.Storage)
│
├── CaseStudy1/              # Case Study 1: IPFS Phishing Investigation
│   ├── pipeline.py          #   Pipeline tự động end-to-end
│   └── output/              #   Kết quả (tự sinh khi chạy)
│
└── kubo/                    # Script cài đặt Kubo (IPFS client)
```

---

## Yêu cầu hệ thống

| Yêu cầu | Chi tiết |
|----------|----------|
| **Hệ điều hành** | Windows 10/11 hoặc Linux (Ubuntu/Debian/CentOS...) |
| **Python** | 3.8 trở lên |
| **Kubo (IPFS)** | v0.19.0 (hoặc tương thích) |
| **Kết nối mạng** | Cần thiết cho truy vết P2P và tải dữ liệu |

---

## Cài đặt

### Bước 1: Cài đặt Kubo (IPFS)

<details>
<summary><b>🐧 Linux</b></summary>

```bash
# Tải Kubo v0.19.0
wget https://dist.ipfs.tech/kubo/v0.19.0/kubo_v0.19.0_linux-amd64.tar.gz

# Giải nén và cài đặt
tar -xvzf kubo_v0.19.0_linux-amd64.tar.gz
cd kubo
sudo bash install.sh

# Kiểm tra
ipfs --version
# Kết quả: ipfs version 0.19.0
```

</details>

<details>
<summary><b>🪟 Windows</b></summary>

1. Tải Kubo v0.19.0 cho Windows tại:
   ```
   https://dist.ipfs.tech/kubo/v0.19.0/kubo_v0.19.0_windows-amd64.zip
   ```

2. Giải nén file `.zip` vào thư mục bất kỳ (ví dụ: `C:\kubo`).

3. Thêm đường dẫn thư mục chứa `ipfs.exe` vào biến môi trường `PATH`:
   - Mở **Settings** → **System** → **About** → **Advanced system settings** → **Environment Variables**
   - Chỉnh sửa biến `Path` → Thêm đường dẫn (ví dụ: `C:\kubo`)

4. Kiểm tra:
   ```powershell
   ipfs --version
   # Kết quả: ipfs version 0.19.0
   ```

</details>

#### Khởi tạo IPFS Node (chạy 1 lần duy nhất)

```bash
ipfs init
```

#### Cấu hình Connection Manager (bắt buộc)

Tăng giới hạn kết nối để theo dõi được nhiều node hơn:

```bash
ipfs config --json Swarm.ConnMgr.LowWater 10000
ipfs config --json Swarm.ConnMgr.HighWater 15000
```

---

### Bước 2: Thiết lập Python

```bash
# Clone repository
git clone https://github.com/<your-username>/<your-repo>.git
cd <your-repo>

# Tạo môi trường ảo
python -m venv venv

# Kích hoạt môi trường ảo
# Linux/macOS:
source venv/bin/activate
# Windows (PowerShell):
.\venv\Scripts\Activate.ps1

# Cài đặt thư viện
pip install -r requirements.txt
```

---

## Cách sử dụng

### CLI chính (main.py)

```bash
# Xem danh sách lệnh
python main.py --help

# Bóc tách CID từ file CSV
python main.py parse <file_csv> -o <output_dir>

# Truy vết node IPFS (cần IPFS daemon đang chạy)
python main.py track <file_cid> --ipfs ipfs -o <output_dir>

# Truy vấn DNSLink
python main.py trackdns <file_dns> -o <output_dir>

# Tạo bản đồ IP
python main.py ipmap <file_track_json> -o <output_dir>

# Tái tạo file từ IPFS block
python main.py reassemble <block_dir> -o <output_dir>
```

### Case Study 1: Pipeline tự động

Pipeline tự động hóa toàn bộ quy trình điều tra phishing trên IPFS:

```bash
cd CaseStudy1

# Chạy đầy đủ 100% CID
python pipeline.py

# Chạy với 5% CID (để test nhanh)
python pipeline.py --sample 5

# Xem hướng dẫn
python pipeline.py --help
```

**Tính năng nổi bật:**
- Tự động tải dữ liệu mới nhất từ PhishTank
- Tự khởi động/tắt IPFS Daemon
- Thu thập log Bitswap để phân tích timeline
- Hỗ trợ **Resume** — nếu bị gián đoạn (Ctrl+C), chạy lại sẽ tự động tiếp tục từ vị trí đã dừng
- Xuất bản đồ IP, biểu đồ timeline, và báo cáo IOC

---

## Kết quả đầu ra

Sau khi chạy pipeline, thư mục `CaseStudy1/output/` sẽ chứa:

| File | Mô tả |
|------|--------|
| `cid_result.txt` | Danh sách CID phishing bóc tách được |
| `track.json` | Kết quả truy vết (CID → IP node) |
| `IPMAP_result.html` | Bản đồ HTML vị trí các node |
| `blacklist_ioc.json` | Báo cáo IOC (Indicators of Compromise) |
| `forensic_timeline_frequency.png` | Biểu đồ tần suất truy vấn theo thời gian |
| `forensic_timeline_top_cids.png` | Top 10 CID bị truy vấn nhiều nhất |
| `bitswap_monitor.log` | Log raw từ Bitswap engine |

---

## Giấy phép

Dự án được phân phối theo [MIT License](LICENSE).

Dựa trên mã nguồn gốc của [hunjison/IF-DSS](https://github.com/hunjison/IF-DSS).
