from PIL import Image, ImageDraw
import os

# 创建 1024x1024 的图标
size = 1024
img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
draw = ImageDraw.Draw(img)

# 颜色定义
robot_color = (66, 133, 244)  # 蓝色
eye_color = (255, 255, 255)  # 白色
pupil_color = (33, 66, 133)   # 深蓝色
antenna_color = (52, 168, 83) # 绿色

# 机器人头部 (圆角矩形)
head_x1, head_y1 = 200, 200
head_x2, head_y2 = 824, 700
corner_radius = 80

# 绘制圆角矩形头部
draw.rounded_rectangle(
    [(head_x1, head_y1), (head_x2, head_y2)],
    radius=corner_radius,
    fill=robot_color
)

# 天线
antenna_x = size // 2
antenna_width = 20
# 左天线
draw.rectangle([antenna_x - 100, 140, antenna_x - 80, 200], fill=antenna_color)
draw.ellipse([antenna_x - 115, 110, antenna_x - 65, 160], fill=antenna_color)
# 右天线
draw.rectangle([antenna_x + 80, 140, antenna_x + 100, 200], fill=antenna_color)
draw.ellipse([antenna_x + 65, 110, antenna_x + 115, 160], fill=antenna_color)
# 中间天线
draw.rectangle([antenna_x - 10, 150, antenna_x + 10, 200], fill=antenna_color)
draw.ellipse([antenna_x - 25, 115, antenna_x + 25, 165], fill=antenna_color)

# 眼睛 (大的圆形眼睛)
eye_radius = 70
eye_y = 350
left_eye_center = (350, eye_y)
right_eye_center = (674, eye_y)

# 眼白
draw.ellipse(
    [left_eye_center[0] - eye_radius, left_eye_center[1] - eye_radius,
     left_eye_center[0] + eye_radius, left_eye_center[1] + eye_radius],
    fill=eye_color
)
draw.ellipse(
    [right_eye_center[0] - eye_radius, right_eye_center[1] - eye_radius,
     right_eye_center[0] + eye_radius, right_eye_center[1] + eye_radius],
    fill=eye_color
)

# 瞳孔
pupil_radius = 30
draw.ellipse(
    [left_eye_center[0] - pupil_radius, left_eye_center[1] - pupil_radius,
     left_eye_center[0] + pupil_radius, left_eye_center[1] + pupil_radius],
    fill=pupil_color
)
draw.ellipse(
    [right_eye_center[0] - pupil_radius, right_eye_center[1] - pupil_radius,
     right_eye_center[0] + pupil_radius, right_eye_center[1] + pupil_radius],
    fill=pupil_color
)

# 嘴巴 (微笑)
mouth_y = 500
mouth_x1, mouth_x2 = 350, 674
mouth_width = 10
draw.arc(
    [mouth_x1, mouth_y - 40, mouth_x2, mouth_y + 60],
    start=0, end=180,
    fill=eye_color,
    width=mouth_width
)

base_dir = os.path.dirname(__file__)

# 保存 PNG 图标
png_path = os.path.join(base_dir, 'build', 'appicon.png')
img.save(png_path, 'PNG')
print(f"机器人图标 PNG 已保存到: {png_path}")

# 生成 ICO 文件，包含多种尺寸
ico_sizes = [(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)]
ico_path = os.path.join(base_dir, 'build', 'windows', 'icon.ico')

# 为每个尺寸调整图片大小
img_icons = []
for ico_size in ico_sizes:
    img_resized = img.resize(ico_size, Image.Resampling.LANCZOS)
    img_icons.append(img_resized)

# 保存为 ICO 文件
img_icons[0].save(ico_path, format='ICO', sizes=[(size[0], size[1]) for size in ico_sizes])
print(f"机器人图标 ICO 已保存到: {ico_path}")
