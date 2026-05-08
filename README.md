# Hướng dẫn Cài đặt Môi trường cho Case Study 1

## Yêu cầu hệ thống

- Hệ điều hành: Linux (Ubuntu/Debian/CentOS...)
- Python: 3.x trở lên
- Có quyền `sudo` để cài đặt phần mềm.

---

## Bước 1: Cài đặt và Cấu hình Kubo (IPFS) v0.19.0

Dự án yêu cầu cài đặt Kubo (IPFS Client) để truy vết các node. Dưới đây là hướng dẫn cài đặt phiên bản `v0.19.0` cho kiến trúc `linux-amd64`.

### 1. Tải file nén Kubo

Mở terminal và chạy lệnh sau để tải về:

```bash
wget https://dist.ipfs.tech/kubo/v0.19.0/kubo_v0.19.0_linux-amd64.tar.gz
```

### 2. Giải nén và cài đặt

```bash
tar -xvzf kubo_v0.19.0_linux-amd64.tar.gz
cd kubo
sudo bash install.sh
```

### 3. Kiểm tra cài đặt

```bash
ipfs --version
# Kết quả mong đợi: ipfs version 0.19.0
```

### 4. Khởi tạo IPFS Node

Cần khởi tạo cấu hình cục bộ cho IPFS (chỉ chạy lệnh này 1 lần duy nhất):

```bash
ipfs init
```

### 5. Cấu hình Connection Manager (Bắt buộc)

Để theo dõi được lượng lớn kết nối P2P phục vụ cho việc điều tra, cần tinh chỉnh lại giới hạn kết nối (ConnMgr) của IPFS. Chạy 2 lệnh sau:

```bash
ipfs config --json Swarm.ConnMgr.LowWater 10000
ipfs config --json Swarm.ConnMgr.HighWater 15000
```

## Bước 2: Thiết lập môi trường Python

### 1. Tạo môi trường ảo (Virtual Environment)

Di chuyển vào thư mục gốc của dự án và tạo môi trường ảo để tránh xung đột thư viện:

```bash
python3 -m venv venv
```

### 2. Kích hoạt môi trường ảo

```bash
source venv/bin/activate
```

### 3. Cài đặt các thư viện phụ thuộc

Cài đặt các gói Python được liệt kê trong file requirements.txt:

```bash
pip install -r requirements.txt
```

## Bước 3: Chạy Pipeline Phân tích

Sau khi môi trường đã sẵn sàng, không cần phải tự chạy IPFS Daemon thủ công vì mã nguồn pipeline.py đã tự động hóa việc này.

Chỉ cần chạy lệnh duy nhất sau đây:

```bash
python3 pipeline.py
```

Quá trình này sẽ tự động:

- Kéo tập dữ liệu từ Phishtank.
- Bóc tách CID.
- Kích hoạt IPFS Daemon ngầm và thu thập log Bitswap.
- Truy vết IP của các node chứa file lừa đảo.
- Xuất các file báo cáo, IOC và biểu đồ Timeline vào thư mục output/.

Lưu ý: Quá trình truy vết mạng P2P có thể mất khá nhiều thời gian tùy thuộc vào số lượng mẫu cấu hình.