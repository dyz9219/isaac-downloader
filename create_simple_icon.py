from PIL import Image, ImageDraw
import os

# 创建一个简单的机器人图标
size = 512
img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
draw = ImageDraw.Draw(img)

# 机器人头部 (圆角矩形)
head_margin = 80
head_size = size - head_margin * 2
draw.rounded_rectangle(
    [head_margin, head_margin, size - head_margin, size - head_margin],
    radius=60,
    fill=(70, 130, 180)  # 钢蓝色
)

# 天线
center = size // 2
draw.rectangle([center - 60, 40, center - 40, head_margin], fill=(50, 205, 50))
draw.ellipse([center - 75, 10, center - 25, 60], fill=(50, 205, 50))
draw.rectangle([center + 40, 40, center + 60, head_margin], fill=(50, 205, 50))
draw.ellipse([center + 25, 10, center + 75, 60], fill=(50, 205, 50))

# 眼睛
eye_y = center - 30
eye_radius = 50
left_eye = (center - 80, eye_y)
right_eye = (center + 80, eye_y)

# 眼白
draw.ellipse(
    [left_eye[0] - eye_radius, left_eye[1] - eye_radius,
     left_eye[0] + eye_radius, left_eye[1] + eye_radius],
    fill=(255, 255, 255)
)
draw.ellipse(
    [right_eye[0] - eye_radius, right_eye[1] - eye_radius,
     right_eye[0] + eye_radius, right_eye[1] + eye_radius],
    fill=(255, 255, 255)
)

# 瞳孔
pupil_radius = 20
draw.ellipse(
    [left_eye[0] - pupil_radius, left_eye[1] - pupil_radius,
     left_eye[0] + pupil_radius, left_eye[1] + pupil_radius],
    fill=(25, 25, 112)
)
draw.ellipse(
    [right_eye[0] - pupil_radius, right_eye[1] - pupil_radius,
     right_eye[0] + pupil_radius, right_eye[1] + pupil_radius],
    fill=(25, 25, 112)
)

# 嘴巴 (微笑)
mouth_y = center + 80
draw.arc(
    [center - 100, mouth_y - 50, center + 100, mouth_y + 50],
    start=0, end=180,
    fill=(255, 255, 255),
    width=8
)

base_dir = os.path.dirname(__file__)

# 保存 PNG
png_path = os.path.join(base_dir, 'build', 'appicon.png')
img.save(png_path, 'PNG')
print(f"PNG 保存到: {png_path}")

# 生成 ICO 文件，包含多个尺寸
ico_sizes = [(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)]
ico_path = os.path.join(base_dir, 'build', 'windows', 'icon.ico')

img_icons = []
for ico_size in ico_sizes:
    img_resized = img.resize(ico_size, Image.Resampling.LANCZOS)
    img_icons.append(img_resized)

img_icons[0].save(ico_path, format='ICO', sizes=[(size[0], size[1]) for size in ico_sizes])
print(f"ICO 保存到: {ico_path}")

# 同时保存到项目根目录
root_ico_path = os.path.join(base_dir, 'icon.ico')
img_icons[0].save(root_ico_path, format='ICO', sizes=[(size[0], size[1]) for size in ico_sizes])
print(f"根目录 ICO 保存到: {root_ico_path}")
