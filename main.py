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

# 测试显示
print("开始测试...")

# 画一些基本图形
lcd.clear()
lcd.draw_line(0, 0, 299, 399, 1)  # 对角线
lcd.draw_rect(50, 50, 200, 300, 1)  # 矩形
lcd.draw_circle(150, 200, 50, 1)  # 圆形
lcd.draw_string_scale(0, 0, "Hello World!", 2,1)  # 文字

lcd.display()
print("测试完成！")

