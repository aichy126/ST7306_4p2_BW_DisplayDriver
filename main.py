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

# 初始化SPI，降低通信速率
spi = SPI(1, baudrate=15000000, polarity=0, phase=0, sck=Pin(SPI_SCK_PIN), mosi=Pin(SPI_MOSI_PIN))

# 初始化屏幕
lcd = ST7306(spi, Pin(LCD_CS_PIN), Pin(LCD_DC_PIN), Pin(LCD_RST_PIN))

def test_basic_shapes():
    """基本图形测试"""
    print("测试基本图形...")
    lcd.clear()
    lcd.draw_line(0, 0, 299, 399, 1)  # 对角线
    lcd.draw_rect(50, 50, 200, 300, 1)  # 矩形
    lcd.draw_circle(150, 200, 50, 1)  # 圆形
    lcd.draw_string(10, 10, "Basic Shapes Test", 2)  # 文字
    lcd.show()
    time.sleep(3)

def test_rotating_line():
    """旋转线条测试"""
    print("测试旋转线条...")
    center_x, center_y = 150, 200
    radius = 100
    for angle in range(0, 360, 5):
        lcd.clear()
        rad = math.radians(angle)
        end_x = int(center_x + radius * math.cos(rad))
        end_y = int(center_y + radius * math.sin(rad))
        lcd.draw_line(center_x, center_y, end_x, end_y, 1)
        lcd.show()
        time.sleep(0.05)

def test_expanding_circles():
    """扩展圆形测试"""
    print("测试扩展圆形...")
    center_x, center_y = 150, 200
    for radius in range(10, 100, 5):
        lcd.clear()
        lcd.draw_circle(center_x, center_y, radius, 1)
        lcd.show()
        time.sleep(0.1)

def test_moving_text():
    """移动文字测试"""
    print("测试移动文字...")
    text = "Moving Text Test"
    for pos in range(0, 400, 10):
        lcd.clear()
        lcd.draw_string(10, pos, text, 2)
        lcd.show()
        time.sleep(0.1)

def test_rectangle_pattern():
    """矩形图案测试"""
    print("测试矩形图案...")
    lcd.clear()
    for i in range(0, 150, 20):
        lcd.draw_rect(i, i, 300-2*i, 400-2*i, 1)
    lcd.show()
    time.sleep(3)

def test_diagonal_pattern():
    """对角线图案测试"""
    print("测试对角线图案...")
    lcd.clear()
    for i in range(0, 300, 20):
        lcd.draw_line(0, 0, i, 399, 1)
        lcd.draw_line(299, 0, i, 399, 1)
    lcd.show()
    time.sleep(3)

def test_circle_pattern():
    """圆形图案测试"""
    print("测试圆形图案...")
    lcd.clear()
    for i in range(10, 150, 20):
        lcd.draw_circle(150, 200, i, 1)
    lcd.show()
    time.sleep(3)

def test_bouncing_ball():
    """弹跳球动画测试"""
    print("测试弹跳球动画...")
    x, y = 150, 50
    dx, dy = 5, 5
    radius = 10

    for _ in range(100):
        lcd.clear()
        # 更新球的位置
        x += dx
        y += dy

        # 碰撞检测
        if x - radius <= 0 or x + radius >= 299:
            dx = -dx
        if y - radius <= 0 or y + radius >= 399:
            dy = -dy

        # 绘制球
        lcd.draw_circle(int(x), int(y), radius, 1)
        lcd.show()
        time.sleep(0.05)

def main():
    """主测试程序"""
    print("开始显示测试...")

    while True:
        try:
            # 基本测试
            test_basic_shapes()

            # 动画测试
            test_rotating_line()
            test_expanding_circles()
            test_moving_text()
            test_bouncing_ball()

            # 图案测试
            test_rectangle_pattern()
            test_diagonal_pattern()
            test_circle_pattern()

            # 显示完成信息
            lcd.clear()
            lcd.draw_string(10, 150, "Test Complete", 2)
            lcd.draw_string(10, 200, "Press Reset", 2)
            lcd.show()
            time.sleep(3)

        except KeyboardInterrupt:
            print("\n测试被中断")
            break
        except Exception as e:
            print(f"发生错误: {e}")
            continue

if __name__ == '__main__':
    main()

