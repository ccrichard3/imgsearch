#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成 imgsearch 应用图标：渐变圆角底 + 照片卡片 + 放大镜。
输出 icon_1024.png，随后由 shell 用 sips/iconutil 转成 .icns。"""
from __future__ import annotations

import math
from PIL import Image, ImageDraw

S = 1024


def rounded_mask(size: int, radius: int) -> Image.Image:
    m = Image.new("L", (size, size), 0)
    d = ImageDraw.Draw(m)
    d.rounded_rectangle([0, 0, size - 1, size - 1], radius=radius, fill=255)
    return m


def vgrad(size: int, top: tuple, bot: tuple) -> Image.Image:
    base = Image.new("RGB", (size, size), top)
    px = base.load()
    for y in range(size):
        t = y / (size - 1)
        r = int(top[0] + (bot[0] - top[0]) * t)
        g = int(top[1] + (bot[1] - top[1]) * t)
        b = int(top[2] + (bot[2] - top[2]) * t)
        for x in range(size):
            px[x, y] = (r, g, b)
    return base


def main():
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))

    # 背景：靛蓝 -> 亮蓝 的对角渐变（macOS 风格圆角）
    bg = vgrad(S, (99, 102, 241), (37, 99, 235)).convert("RGBA")
    mask = rounded_mask(S, radius=int(S * 0.225))
    img.paste(bg, (0, 0), mask)

    d = ImageDraw.Draw(img)

    # 顶部高光，增加质感
    hi = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    hd = ImageDraw.Draw(hi)
    hd.ellipse([-S * 0.3, -S * 0.75, S * 1.3, S * 0.35],
               fill=(255, 255, 255, 40))
    img = Image.alpha_composite(img, Image.composite(
        hi, Image.new("RGBA", (S, S), (0, 0, 0, 0)), mask))
    d = ImageDraw.Draw(img)

    # 一张“照片”卡片：白框 + 山峦 + 太阳，象征图库
    cx, cy = int(S * 0.40), int(S * 0.44)
    cw, ch = int(S * 0.40), int(S * 0.34)
    x0, y0 = cx - cw // 2, cy - ch // 2
    x1, y1 = cx + cw // 2, cy + ch // 2
    rad = int(S * 0.035)
    # 卡片阴影
    sh = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle(
        [x0 + 14, y0 + 20, x1 + 14, y1 + 20], radius=rad, fill=(0, 0, 0, 70))
    from PIL import ImageFilter
    sh = sh.filter(ImageFilter.GaussianBlur(12))
    img = Image.alpha_composite(img, sh)
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([x0, y0, x1, y1], radius=rad, fill=(255, 255, 255, 255))
    inset = int(S * 0.022)
    ix0, iy0, ix1, iy1 = x0 + inset, y0 + inset, x1 - inset, y1 - inset
    # 照片内容底色（天空）
    d.rounded_rectangle([ix0, iy0, ix1, iy1], radius=int(rad * 0.6),
                        fill=(191, 219, 254, 255))
    # 太阳
    sun_r = int(cw * 0.10)
    d.ellipse([ix1 - sun_r * 3, iy0 + sun_r, ix1 - sun_r, iy0 + sun_r * 3],
              fill=(250, 204, 21, 255))
    # 山峦（三角）
    d.polygon([(ix0, iy1), (ix0 + cw * 0.30, iy0 + ch * 0.42),
               (ix0 + cw * 0.58, iy1)], fill=(34, 197, 94, 255))
    d.polygon([(ix0 + cw * 0.34, iy1), (ix0 + cw * 0.66, iy0 + ch * 0.30),
               (ix1, iy1)], fill=(22, 163, 74, 255))
    # 裁掉溢出照片内框的部分
    photo_mask = Image.new("L", (S, S), 0)
    ImageDraw.Draw(photo_mask).rounded_rectangle(
        [ix0, iy0, ix1, iy1], radius=int(rad * 0.6), fill=255)

    # 放大镜：镜圈 + 手柄，右下叠在照片上
    gx, gy = int(S * 0.62), int(S * 0.63)
    gr_out = int(S * 0.175)
    ring = int(S * 0.05)
    # 镜圈外白描边
    d.ellipse([gx - gr_out, gy - gr_out, gx + gr_out, gy + gr_out],
              outline=(255, 255, 255, 255), width=ring)
    # 镜片（半透明浅色）
    gin = gr_out - ring // 2
    lens = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    ImageDraw.Draw(lens).ellipse([gx - gin, gy - gin, gx + gin, gy + gin],
                                 fill=(224, 242, 254, 90))
    img = Image.alpha_composite(img, lens)
    d = ImageDraw.Draw(img)
    # 手柄
    ang = math.radians(45)
    hx0 = gx + int(math.cos(ang) * gr_out)
    hy0 = gy + int(math.sin(ang) * gr_out)
    hx1 = gx + int(math.cos(ang) * (gr_out + S * 0.16))
    hy1 = gy + int(math.sin(ang) * (gr_out + S * 0.16))
    d.line([hx0, hy0, hx1, hy1], fill=(255, 255, 255, 255),
           width=int(S * 0.058))
    d.line([hx0, hy0, hx1, hy1], fill=(255, 255, 255, 255),
           width=int(S * 0.058), joint="curve")
    # 手柄端点圆头
    hw = int(S * 0.029)
    d.ellipse([hx1 - hw, hy1 - hw, hx1 + hw, hy1 + hw],
              fill=(255, 255, 255, 255))

    img.save("/Users/cc/程序/imgsearch/icon_1024.png")
    print("wrote icon_1024.png")


if __name__ == "__main__":
    main()
