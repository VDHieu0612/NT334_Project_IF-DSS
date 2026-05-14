#!/usr/bin/env python3

import json, subprocess, os, platform

def URL_to_dnslink(fd):
    return_list = []
    _dnslink_site = fd.readline()

    while _dnslink_site:
        parts = _dnslink_site.strip().split('/')
        if len(parts) >= 3:
            return_list.append(f"_dnslink.{parts[2]}")
        _dnslink_site = fd.readline()
    
    return_list = list(dict.fromkeys(return_list))

    return return_list

def dnslink_query(file_path, dig, output_path):
    result = {}
    _dnslink_site_list = URL_to_dnslink(fd = open(file_path,"r"))

    # Thử dùng dnspython (cross-platform) trước, fallback sang dig
    use_python_dns = False
    try:
        import dns.resolver
        use_python_dns = True
        print("[*] Sử dụng dnspython để truy vấn DNSLink (cross-platform).")
    except ImportError:
        if platform.system() == "Windows":
            print("[-] Không tìm thấy dnspython. Cài bằng: pip install dnspython")
            print("[-] Thử dùng lệnh dig thay thế...")
        use_python_dns = False

    for _dnslink in _dnslink_site_list:
        try:
            if use_python_dns:
                # Dùng dnspython (chạy trên mọi OS)
                import dns.resolver
                answers = dns.resolver.resolve(_dnslink, 'TXT')
                for rdata in answers:
                    txt = rdata.to_text().strip('"')
                    if 'dnslink=/ipfs/' in txt:
                        cid = txt.split('dnslink=/ipfs/')[1]
                        if cid[:2] == "Qm":
                            result[_dnslink] = cid
                            json.dump(result, open(os.path.join(output_path, "dnslink_result.json"),"w"))
                            print(f"  [+] {_dnslink} -> {cid[:20]}...")
            else:
                # Dùng dig (Linux/macOS)
                args = [dig, '+noall', '+answer', 'TXT', _dnslink]
                output = subprocess.check_output(args)
                output = output.decode('utf-8').split('\n')[0].split('dnslink=/ipfs/')
                if output != [''] and output[1][:2] == "Qm":
                    result[_dnslink] = output[1][:-1]
                    json.dump(result, open(os.path.join(output_path, "dnslink_result.json"),"w"))
        except Exception as e:
            # DNS query failed — domain không tồn tại hoặc không có TXT record
            continue
    
    print(f"[*] DNSLink: Tìm thấy {len(result)} CID ẩn dưới DNS.")
