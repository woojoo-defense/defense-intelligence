# -*- coding: utf-8 -*-
"""아티클별 오픈그래프 이미지(1200×630 PNG) 생성.

연한 블루그레이 배경(카톡 흰색 설명 영역과 구분), 상단 오렌지 라인,
영문 아이브로, 큰 날짜, 워드마크, 호수 메타, 하단 디펜스엑스포 로고.
"""

import os

from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONT_DIR = os.path.join(ROOT, "data", "fonts")
LOGO_PATH = os.path.join(FONT_DIR, "dx_logo.png")

W, H = 1200, 630
BG = (233, 238, 245)          # 연한 블루그레이 — 흰 카드 영역과 구분
INK = (26, 30, 41)
META = (90, 101, 119)
MUTED = (122, 132, 148)
LINE = (201, 210, 222)
ACCENT = (255, 85, 0)
TYPE_KO = {"daily": "일일뉴스", "weekly": "주간뉴스", "monthly": "월간뉴스"}


def _font(weight, size):
    path = os.path.join(FONT_DIR, f"Pretendard-{weight}.otf")
    if os.path.exists(path):
        return ImageFont.truetype(path, size)
    return ImageFont.truetype("C:/Windows/Fonts/malgunbd.ttf", size)


def _spaced(draw, xy, text, font, fill, tracking=0, anchor=None):
    """자간(tracking px) 적용해 그린다. anchor='mm'면 중앙 정렬."""
    widths = [draw.textlength(ch, font=font) for ch in text]
    total = sum(widths) + tracking * (len(text) - 1)
    x, y = xy
    if anchor == "mm":
        x -= total / 2
    for ch, w in zip(text, widths):
        draw.text((x, y), ch, font=font, fill=fill)
        x += w + tracking


def _paste_logo(img, cy, height=30):
    """디펜스엑스포 로고를 하단 중앙에 (없으면 건너뜀)."""
    if not os.path.exists(LOGO_PATH):
        return
    logo = Image.open(LOGO_PATH).convert("RGBA")
    w = int(logo.width * height / logo.height)
    logo = logo.resize((w, height), Image.LANCZOS)
    img.paste(logo, (W // 2 - w // 2, cy - height // 2), logo)


def og_image(date_str, weekday, type_key, issue_no, out_path):
    """date_str='2026-08-27', weekday='목', type_key='daily', issue_no=27"""
    yy, mm, dd = date_str[2:4], date_str[5:7], date_str[8:10]
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)

    d.rectangle([0, 0, W, 10], fill=ACCENT)
    _spaced(d, (W / 2, 108), "K-DEFENSE GLOBAL MARKET INTELLIGENCE",
            _font("Medium", 22), MUTED, tracking=7, anchor="mm")
    d.text((W / 2, 258), f"{yy}.{mm}.{dd} ({weekday})",
           font=_font("ExtraBold", 120), fill=INK, anchor="mm")
    d.text((W / 2, 390), "방산MICE 글로벌 마켓 인텔리전스",
           font=_font("Bold", 46), fill=INK, anchor="mm")
    d.line([440, 462, 760, 462], fill=LINE, width=2)
    meta = f"{TYPE_KO.get(type_key, '뉴스레터')}  제{issue_no}호"
    d.text((W / 2, 506), meta, font=_font("Medium", 27), fill=META, anchor="mm")
    _paste_logo(img, 572)

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    img.save(out_path, "PNG", optimize=True)
    return out_path


def og_default(out_path):
    """사이트 루트·아카이브 목록용 기본 이미지(날짜 없음)."""
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W, 10], fill=ACCENT)
    _spaced(d, (W / 2, 150), "K-DEFENSE GLOBAL MARKET INTELLIGENCE",
            _font("Medium", 22), MUTED, tracking=7, anchor="mm")
    d.text((W / 2, 288), "방산MICE 글로벌 마켓 인텔리전스",
           font=_font("ExtraBold", 64), fill=INK, anchor="mm")
    d.line([440, 372, 760, 372], fill=LINE, width=2)
    d.text((W / 2, 428), "뉴스에서 수출기회까지 — 일일 · 주간 · 월간 뉴스레터",
           font=_font("Medium", 28), fill=META, anchor="mm")
    _paste_logo(img, 520)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    img.save(out_path, "PNG", optimize=True)
    return out_path


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8")
    p = og_image("2026-08-27", "목", "daily", 27,
                 os.path.join(ROOT, "data", "og_sample.png"))
    print("샘플 생성:", p, os.path.getsize(p) // 1024, "KB")
