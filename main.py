from machine import Pin, SPI
import time
import math
from st7306 import ST7306

# 引脚定义
SPI_SCK_PIN = 12   # 时钟引脚
SPI_MOSI_PIN = 11  # 数据输出引脚
LCD_CS_PIN = 10    # 片选引脚
LCD_DC_PIN = 13    # 数据/命令选择引脚
LCD_RST_PIN = 14   # 复位引脚

# 初始化SPI
spi = SPI(1, baudrate=40000000, polarity=0, phase=0, sck=Pin(SPI_SCK_PIN), mosi=Pin(SPI_MOSI_PIN))

# 初始化屏幕
lcd = ST7306(spi, Pin(LCD_CS_PIN), Pin(LCD_DC_PIN), Pin(LCD_RST_PIN))

def draw_line(x1, y1, x2, y2, color=0x03):
    """使用Wu's line algorithm绘制抗锯齿直线"""
    def plot(x, y, c):
        if 0 <= x < 300 and 0 <= y < 400:
            lcd.write_point(x, y, color)

    dx = x2 - x1
    dy = y2 - y1
    if abs(dx) > abs(dy):
        if x2 < x1:
            x1, x2 = x2, x1
            y1, y2 = y2, y1
        gradient = dy / dx
        xend = round(x1)
        yend = y1 + gradient * (xend - x1)
        xgap = 1 - (x1 + 0.5) % 1
        xpxl1 = xend
        ypxl1 = int(yend)
        plot(xpxl1, ypxl1, 1 - (yend % 1) * xgap)
        plot(xpxl1, ypxl1 + 1, (yend % 1) * xgap)
        intery = yend + gradient
        xend = round(x2)
        yend = y2 + gradient * (xend - x2)
        xgap = (x2 + 0.5) % 1
        xpxl2 = xend
        ypxl2 = int(yend)
        plot(xpxl2, ypxl2, 1 - (yend % 1) * xgap)
        plot(xpxl2, ypxl2 + 1, (yend % 1) * xgap)
        for x in range(xpxl1 + 1, xpxl2):
            plot(x, int(intery), 1 - (intery % 1))
            plot(x, int(intery) + 1, intery % 1)
            intery = intery + gradient
    else:
        if y2 < y1:
            x1, x2 = x2, x1
            y1, y2 = y2, y1
        gradient = dx / dy
        yend = round(y1)
        xend = x1 + gradient * (yend - y1)
        ygap = 1 - (y1 + 0.5) % 1
        ypxl1 = yend
        xpxl1 = int(xend)
        plot(xpxl1, ypxl1, 1 - (xend % 1) * ygap)
        plot(xpxl1 + 1, ypxl1, (xend % 1) * ygap)
        interx = xend + gradient
        yend = round(y2)
        xend = x2 + gradient * (yend - y2)
        ygap = (y2 + 0.5) % 1
        ypxl2 = yend
        xpxl2 = int(xend)
        plot(xpxl2, ypxl2, 1 - (xend % 1) * ygap)
        plot(xpxl2 + 1, ypxl2, (xend % 1) * ygap)
        for y in range(ypxl1 + 1, ypxl2):
            plot(int(interx), y, 1 - (interx % 1))
            plot(int(interx) + 1, y, interx % 1)
            interx = interx + gradient

def draw_rect(x, y, width, height, color=0x03, fill=False):
    """画矩形"""
    if fill:
        for i in range(x, x + width):
            for j in range(y, y + height):
                lcd.write_point(i, j, color)
    else:
        # 画四条边
        for i in range(x, x + width):
            lcd.write_point(i, y, color)
            lcd.write_point(i, y + height - 1, color)
        for j in range(y, y + height):
            lcd.write_point(x, j, color)
            lcd.write_point(x + width - 1, j, color)

def draw_circle(x0, y0, radius, color=0x03, fill=False):
    """使用中点圆算法绘制抗锯齿圆"""
    def plot(x, y, c):
        if 0 <= x < 300 and 0 <= y < 400:
            lcd.write_point(x, y, color)

    def plot_circle_points(x, y, c):
        plot(x0 + x, y0 + y, c)
        plot(x0 - x, y0 + y, c)
        plot(x0 + x, y0 - y, c)
        plot(x0 - x, y0 - y, c)
        plot(x0 + y, y0 + x, c)
        plot(x0 - y, y0 + x, c)
        plot(x0 + y, y0 - x, c)
        plot(x0 - y, y0 - x, c)

    if fill:
        for y in range(-radius, radius + 1):
            for x in range(-radius, radius + 1):
                if x*x + y*y <= radius*radius:
                    plot(x0 + x, y0 + y, color)
    else:
        x = radius
        y = 0
        err = 0
        while x >= y:
            plot_circle_points(x, y, 1)
            if err <= 0:
                y += 1
                err += 2*y + 1
            if err > 0:
                x -= 1
                err -= 2*x + 1

def draw_sine_wave(amplitude=50, frequency=0.1, phase=0, color=0x03):
    """画正弦波"""
    for x in range(300):
        y = int(200 + amplitude * math.sin(frequency * x + phase))
        if 0 <= y < 400:
            lcd.write_point(x, y, color)

def test_lines():
    """测试画线"""
    print("测试画线...")
    lcd.clear()

    # 画不同角度的直线
    draw_line(0, 0, 299, 399, 0x03)  # 对角线
    draw_line(0, 399, 299, 0, 0x03)  # 对角线
    draw_line(0, 200, 299, 200, 0x03)  # 水平线
    draw_line(150, 0, 150, 399, 0x03)  # 垂直线

    lcd.display()
    time.sleep(2)

def test_rectangles():
    """测试画矩形"""
    print("测试画矩形...")
    lcd.clear()

    # 画不同大小的矩形
    draw_rect(50, 50, 100, 100, 0x03)  # 空心矩形
    draw_rect(200, 200, 50, 50, 0x03, True)  # 实心矩形
    draw_rect(100, 150, 100, 50, 0x03)  # 长方形

    lcd.display()
    time.sleep(2)

def test_circles():
    """测试画圆"""
    print("测试画圆...")
    lcd.clear()

    # 测试不同大小的空心圆
    lcd.draw_circle(150, 200, 50, 0x03)  # 大圆
    lcd.draw_circle(150, 200, 40, 0x03)  # 中圆
    lcd.draw_circle(150, 200, 30, 0x03)  # 小圆
    lcd.display()
    time.sleep(2)

    # 测试实心圆
    lcd.clear()
    lcd.draw_filled_circle(150, 200, 50, 0x03)  # 大实心圆
    lcd.display()
    time.sleep(2)

    # 测试圆形组合
    lcd.clear()
    for i in range(3):
        x = 100 + i * 100
        y = 200
        lcd.draw_circle(x, y, 30, 0x03)  # 外圈
        lcd.draw_filled_circle(x, y, 20, 0x02)  # 内部填充
    lcd.display()
    time.sleep(2)

def test_animation():
    """测试动画效果"""
    print("测试动画...")

    # 圆形动画
    for r in range(10, 100, 5):
        lcd.clear()
        draw_circle(150, 200, r, 0x03)
        lcd.display()
        time.sleep(0.1)

    # 正弦波动画
    for phase in range(0, 628, 10):  # 0到2π
        lcd.clear()
        draw_sine_wave(50, 0.1, phase/100, 0x03)
        lcd.display()
        time.sleep(0.1)

def test_patterns():
    """测试各种图案"""
    print("测试图案...")
    lcd.clear()

    # 画网格
    for x in range(0, 300, 30):
        draw_line(x, 0, x, 399, 0x03)
    for y in range(0, 400, 40):
        draw_line(0, y, 299, y, 0x03)

    # 画星形
    center_x, center_y = 150, 200
    for angle in range(0, 360, 72):
        rad = math.radians(angle)
        x = int(center_x + 50 * math.cos(rad))
        y = int(center_y + 50 * math.sin(rad))
        draw_line(center_x, center_y, x, y, 0x03)

    lcd.display()
    time.sleep(2)

def test_text():
    """测试文字显示功能"""
    lcd.clear()

    # 测试基本文字显示
    lcd.draw_string(10, 10, "Hello World!")
    lcd.display()
    time.sleep(2)

    # 测试放大文字
    lcd.clear()
    lcd.draw_string_scale(10, 10, "BIG TEXT", scale=2)
    lcd.display()
    time.sleep(2)

    # 测试旋转文字
    lcd.clear()
    for angle in range(0, 360, 45):
        lcd.clear()
        lcd.draw_string_rotate(150, 200, "ROTATE", angle=angle)
        lcd.display()
        time.sleep(0.5)

    # 测试多行文字
    lcd.clear()
    lcd.draw_string(10, 10, "Line 1")
    lcd.draw_string(10, 30, "Line 2")
    lcd.draw_string(10, 50, "Line 3")
    lcd.display()
    time.sleep(2)

# 运行所有测试
print("开始测试...")
test_lines()
test_rectangles()
test_circles()
test_animation()
test_patterns()
test_text()
print("测试完成！")
