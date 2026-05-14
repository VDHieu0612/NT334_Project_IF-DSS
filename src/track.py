#!/usr/bin/env python3

import sys
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

import base64, base58
import subprocess, json, os

# It should be added more for accurate tracking
Gateway_NodeID = ["QmQzqxhK82kAmKvARFZSkUVS6fo9sySaiogAnx5EnZ6ZmC", "Qma8ddFEQWEU8ijWvdxXm3nxU7oHsRtCykAaVz8WUYhiKn", "12D3KooWL4oguAYeRKYL6xv8S5wMwKjLgP78FoNDMECuHY6vAkYH", "QmcfJeB3Js1FG7T8YaZATEiaHqNKVdQfybYYkbT1knUswx", "12D3KooWPToGJ2YLfYRn6QKQcYT7dwNZD39w3KkMpWjDt8csr8Rf", "12D3KooWMkBZYybPgHMr7Se5P2qecu4oz34V1TMgsLPJbNeBCekz", "12D3KooWDfrUc9KWYphepLsoGvFYqmHaahjBAKj2iFmY2nFDY2Wy"]

def CIDv0_to_CIDv1(CIDv0):
    return (b"B"+base64.b32encode(b"\x01\x55"+base58.b58decode(CIDv0)).replace(b"=",b"")).decode().lower()

def URL_to_CID(fd):
    cid_list = []
    phishing_site = fd.readline()

    while phishing_site:
        if phishing_site.find("Qm") != -1:
            index = phishing_site.find("Qm")
            if len(phishing_site[index:index+46]) == 46:
                cid_list.append(f"{phishing_site[index:index+46]}")
        elif phishing_site.find("baf") != -1:
            index = phishing_site.find("baf")
            if len(phishing_site[index:index+59]) == 59:
                cid_list.append(f"{phishing_site[index:index+59]}")
        phishing_site = fd.readline()

    fd.close()

    return cid_list

def findprovs(ipfs_path, CID):
    try:    # Check collected phishing site errors
        args = [ipfs_path, 'dht', 'findprovs', CID]
        output = subprocess.check_output(args, timeout=120, stderr=subprocess.STDOUT)
        output = output.decode('utf-8').split("\n")
        output = list(dict.fromkeys(output))
        output = output[:len(output)-1]
    except subprocess.TimeoutExpired:
        print(f"  [TIMEOUT] findprovs cho {CID[:16]}... đã quá 120 giây, bỏ qua.")
        output = []
    except subprocess.CalledProcessError as e:
        err_msg = e.output.decode('utf-8', errors='replace') if e.output else ''
        if 'online mode' in err_msg:
            print(f"Error: {err_msg.strip()}")
            return 'OFFLINE'
        output = []
    except:
        output = []
    return output

def findpeer(ipfs_path, Node_ID):
    IP_LIST = []

    for NodeID in Node_ID:
        if NodeID in Gateway_NodeID:
            continue
        args = [ipfs_path, 'dht', 'findpeer', NodeID]

        try:
            output = subprocess.check_output(args, timeout=60)
            output = output.decode('utf-8').split('\n')
        except subprocess.TimeoutExpired:
            continue
        except subprocess.CalledProcessError:
            continue

        for ip_data in output: # remove Virtual IP
            if "ip4" in ip_data:
                IP = ip_data.split('/')[2]
                check = IP.split('.')[0]
                if check not in ['10', '127', '172', '192']:
                    IP_LIST.append(IP)

    IP_LIST = list(dict.fromkeys(IP_LIST)) # remove duplicate IP

    return IP_LIST  

def node_track(file_path, ipfs, output):
    # --- RESUME: Load checkpoint nếu có ---
    dup_path = os.path.join(output, "track_duplicate.json")
    track_path = os.path.join(output, "track.json")
    
    if os.path.exists(dup_path):
        try:
            with open(dup_path, "r") as f:
                duplication = json.load(f)
            print(f"  [RESUME] Loaded checkpoint: {len(duplication)} CID đã track trước đó.")
        except (json.JSONDecodeError, Exception):
            duplication = []
    else:
        duplication = []
    
    if os.path.exists(track_path) and len(duplication) > 0:
        try:
            with open(track_path, "r") as f:
                result = json.load(f)
            print(f"  [RESUME] Loaded kết quả cũ: {len(result)} CID có provider.")
        except (json.JSONDecodeError, Exception):
            result = {}
    else:
        result = {}
    
    CID_LIST = URL_to_CID(fd = open(file_path,"r"))
    CID_LIST = list(set(CID_LIST)) # CID deduplicate
    ipfs_path = ipfs
    
    # Đếm số CID cần track (trừ đã track)
    remaining = [cid for cid in CID_LIST if cid not in duplication]
    total = len(CID_LIST)
    already_done = total - len(remaining)
    
    if already_done > 0:
        print(f"  [RESUME] Tổng: {total} CID | Đã track: {already_done} | Còn lại: {len(remaining)}")

    yn = input("Is your IPFS daemon running? (y/n): ")
    if yn.lower() != "y":
        return

    tracked_count = already_done
    found_count = len(result)
    offline_streak = 0  # Đếm số lần liên tiếp daemon offline
    
    for CID in CID_LIST:
        if CID in duplication:
            continue
        
        tracked_count += 1
        print(f"  [{tracked_count}/{total}] Đang track: {CID[:20]}...", end=" ", flush=True)
        
        NodeID = findprovs(ipfs_path, CID)
        
        # Phát hiện daemon offline → dừng ngay
        if NodeID == 'OFFLINE':
            offline_streak += 1
            if offline_streak >= 3:
                print(f"\n  [!] IPFS Daemon đã tắt (3 lần liên tiếp). Dừng tracking.")
                print(f"  [!] Checkpoint đã lưu. Chạy lại pipeline để resume.")
                break
            continue
        offline_streak = 0  # Reset nếu daemon hoạt động bình thường
        
        if NodeID != []:
            result_IPs = findpeer(ipfs_path, NodeID)
            result_findpeer = {'IP' : result_IPs}
            result[CID] = result_findpeer
            found_count += 1
            print(f"[OK] Tim thay {len(result_IPs)} IP (tong found: {found_count})")
            duplication.append(CID)

            # Save checkpoint sau mỗi CID thành công
            json.dump(result, open(os.path.join(output, "track.json"),"w"))
            json.dump(duplication, open(os.path.join(output, "track_duplicate.json"),"w"))
        else:
            print(f"[--] Khong tim thay provider")
            # Vẫn đánh dấu đã xử lý để không track lại
            duplication.append(CID)
            json.dump(duplication, open(os.path.join(output, "track_duplicate.json"),"w"))
    
    print(f"\n  [DONE] Hoàn tất tracking: {found_count}/{total} CID có provider.")
