# -*- encoding: utf-8 -*-
"""
create_test_images.py - Module for toolbox
"""

#!/usr/bin/env python3
from PIL import Image
import os

# 创建测试图片目录
test_dir = "test_images"
os.makedirs(test_dir, exist_ok=True)

print("创建测试图片...")

# 创建几张测试图片
images = [
    ("test1.png", 800, 600, "red"),
    ("test2.jpg", 1024, 768, "blue"),
    ("test3.png", 640, 480, "green")
]

for filename, width, height, color in images:
    img = Image.new('RGB', (width, height), color=color)
    img.save(os.path.join(test_dir, filename))
    print(f"  创建 {filename}: {width}x{height}")

print(f"\n测试图片已保存在: {os.path.abspath(test_dir)}")