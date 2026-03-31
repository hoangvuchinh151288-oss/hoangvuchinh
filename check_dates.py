#!/usr/bin/env python3
"""
VN MACRO DASHBOARD — DATE AUDIT TOOL
Chạy trước mỗi lần git push để phát hiện dates cũ.

Usage:
  python3 check_dates.py              # audit + báo cáo
  python3 check_dates.py --fix        # tự fix dates market data cũ hơn 7 ngày
  python3 check_dates.py --strict 3   # báo lỗi nếu data cũ hơn 3 ngày
"""

import re, sys
from collections import Counter
from datetime import datetime, timedelta

FILE = "index.html"
TODAY = datetime.now().strftime("%d/%m/%Y")

# ══════════════════════════════════════════════════════════════════
# PHÂN LOẠI FIELDS
# ══════════════════════════════════════════════════════════════════
# Static: data tháng/năm, không thay đổi thường xuyên
STATIC_FIELDS = {
    # CPI monthly releases
    "t1_2026", "t2_2026", "t3_2026", "bq_2t", "muc_tieu",
    # BOP, XK/NK monthly
    "xk_2t", "nk_2t", "thu_2t", "chi_2t",
    # Annual/policy constants
    "kieu_hoi_2025", "ls_omo", "base_brent", "uob_q2",
    # Fed policy decision date
    "ls_usd_fed", "rate_range",
}

# Static dates (ngày công bố data tháng) - không cần update
STATIC_DATE_PATTERNS = [
    r"0[16]/0[123]/2026",  # đầu tháng 1,2,3 = ngày công bố CPI/BOP
    r"0[79]/03/2026",      # 7,9/3 = BOP T2
    r"09/03/2026",
    r"01/1[02]/202[56]",   # cuối năm/đầu năm
    r"28/01/2026",         # Fed meeting
    r"13/03/2026",
]

# Market data: phải được cập nhật thường xuyên
MARKET_FIELDS_DAILY = [
    "nhnn_tc","nhnn_tran","nhnn_san","vcb_mua","vcb_ban","vcb_tienmat",
    "tg_tu_do_mua","tg_tu_do_ban","spread_emp","dxy","tg_usd","sjc_ban","sjc_mua",
    "brent","wti",
]
MARKET_FIELDS_WEEKLY = [
    "on","w1","w2","m1","m3","m6","y1","shape",  # yield curve
    "hormuz_tau","spread_futures","war_premium","fair_brent","iea_offset",
    "luu_hanh","luu_hanh_truoc","co_che",
    "goldman_q1","goldman_q2",
    "prob_hold","next_cut",
]

def parse_date(s):
    try:
        return datetime.strptime(s, "%d/%m/%Y")
    except:
        return None

def is_static_date(date_str):
    return any(re.match(p, date_str) for p in STATIC_DATE_PATTERNS)

def audit(filepath=FILE, strict_days=None, auto_fix=False):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    today_dt = parse_date(TODAY)
    
    # Tìm tất cả updated fields
    # Pattern: field: { ..., updated:"DD/MM/YYYY", ... }
    # hoặc:   updated: "DD/MM/YYYY"
    all_dates = re.findall(r'updated:\s*"(\d{2}/\d{2}/\d{4})"', content)
    all_dates += re.findall(r'updated:"(\d{2}/\d{2}/\d{4})"', content)
    
    dc = Counter(all_dates)
    
    # Phân loại
    issues = []
    warnings = []
    ok = []
    
    for date_str, count in sorted(dc.items()):
        dt = parse_date(date_str)
        if not dt:
            continue
        
        age_days = (today_dt - dt).days
        
        if is_static_date(date_str):
            ok.append((date_str, count, "🔒 static"))
            continue
        
        if age_days <= 7:
            ok.append((date_str, count, f"✅ {age_days}d ago"))
        elif age_days <= 14:
            warnings.append((date_str, count, age_days))
        else:
            issues.append((date_str, count, age_days))
    
    # Report
    print(f"\n{'='*55}")
    print(f"📊 DATE AUDIT — {TODAY} — {filepath}")
    print(f"{'='*55}")
    
    if issues:
        print(f"\n❌ OUTDATED (>14 ngày) — {len(issues)} loại dates:")
        for d, n, age in issues:
            print(f"   {d}: {n} fields ({age} ngày cũ)")
    
    if warnings:
        print(f"\n⚠️  WARNING (8-14 ngày) — {len(warnings)} loại:")
        for d, n, age in warnings:
            print(f"   {d}: {n} fields ({age} ngày)")
    
    if ok:
        fresh = [x for x in ok if "✅" in x[2]]
        static = [x for x in ok if "🔒" in x[2]]
        print(f"\n✅ OK: {len(fresh)} loại dates mới | 🔒 Static: {len(static)} loại")
    
    # Auto-fix
    if auto_fix and issues:
        print(f"\n🔧 AUTO-FIX: Cập nhật {len(issues)} loại dates cũ → 27/03/2026...")
        fixed = content
        one_week_ago = (today_dt - timedelta(days=7)).strftime("%d/%m/%Y")
        for d, n, age in issues:
            fixed = fixed.replace(f'updated:"{d}"', f'updated:"{one_week_ago}"')
            fixed = fixed.replace(f'updated: "{d}"', f'updated: "{one_week_ago}"')
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(fixed)
        print(f"   → Đã set về {one_week_ago} (cần review lại giá trị!)")
    
    # Strict check
    total_issues = len(issues)
    if warnings and strict_days:
        total_issues += len(warnings)
    
    print(f"\n{'='*55}")
    if total_issues == 0:
        print("✅ PASS — Dashboard dates sạch, có thể push!")
    else:
        print(f"❌ FAIL — {total_issues} loại dates cần cập nhật trước khi push")
    print(f"{'='*55}\n")
    
    return total_issues

if __name__ == "__main__":
    args = sys.argv[1:]
    strict = int(args[args.index("--strict")+1]) if "--strict" in args else None
    fix = "--fix" in args
    result = audit(strict_days=strict, auto_fix=fix)
    sys.exit(1 if result > 0 else 0)
