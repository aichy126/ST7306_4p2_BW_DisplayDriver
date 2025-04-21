from machine import Pin, SPI
import framebuf
import time
import math
from font import FONT_8x8

class ST7306(framebuf.FrameBuffer):
    """ST7306 电子墨水屏驱动类
    继承自 framebuf.FrameBuffer，提供基本的显示功能

    参数说明：
    spi: SPI对象，用于通信
    cs: 片选引脚
    dc: 数据/命令选择引脚
    rst: 复位引脚
    """
    def __init__(self, spi, cs, dc, rst):
        """初始化显示屏

        参数说明：
        spi: SPI通信对象
        cs: 片选引脚对象
        dc: 数据/命令选择引脚对象
        rst: 复位引脚对象

        使用示例：
        spi = SPI(1, baudrate=15000000, polarity=0, phase=0)
        cs = Pin(10, Pin.OUT)
        dc = Pin(13, Pin.OUT)
        rst = Pin(14, Pin.OUT)
        lcd = ST7306(spi, cs, dc, rst)
        """
        self.spi = spi
        self.cs = cs
        self.dc = dc
        self.rst = rst

        # 屏幕物理参数
        self.PHYSICAL_WIDTH = 300   # 屏幕物理宽度
        self.PHYSICAL_HEIGHT = 400  # 屏幕物理高度

        # 实际显示参数
        self.LCD_WIDTH = 300       # 显示宽度
        self.LCD_HEIGHT = 400      # 显示高度

        # 缓冲区参数（2位灰度，4个像素点共用1个字节）
        self.LCD_DATA_WIDTH = 150   # 每行字节数 = 显示宽度/2
        self.LCD_DATA_HEIGHT = 200  # 行数 = 显示高度/2
        self.BUFFER_SIZE = self.LCD_DATA_WIDTH * self.LCD_DATA_HEIGHT  # 总字节数

        # 初始化引脚
        self.cs.init(Pin.OUT, value=1)
        self.dc.init(Pin.OUT, value=0)
        self.rst.init(Pin.OUT, value=1)

        # 创建显示缓冲区
        self.buffer = bytearray(self.BUFFER_SIZE)

        # 初始化FrameBuffer
        super().__init__(self.buffer, self.LCD_WIDTH, self.LCD_HEIGHT, framebuf.GS2_HMSB)

        # 初始化屏幕
        self.initialize()

    def pixel(self, x, y, color=None):
        """设置或获取单个像素点的颜色值

        参数说明：
        x: x坐标，范围0-299
        y: y坐标，范围0-399
        color: 颜色值（0-3），None时为获取像素值

        使用示例：
        lcd.pixel(100, 100, 3)  # 设置坐标(100,100)的像素为最深色
        value = lcd.pixel(100, 100)  # 获取坐标(100,100)的像素值
        """
        if not (0 <= x < self.LCD_WIDTH and 0 <= y < self.LCD_HEIGHT):
            return

        if color is None:
            return super().pixel(x, y)

        # 计算字节索引和位位置
        real_x = x // 2
        real_y = y // 2
        write_byte_index = real_y * self.LCD_DATA_WIDTH + real_x

        # 计算位位置
        one_two = 1 if y % 2 else 0
        line_bit_1 = (x % 2) * 4
        line_bit_0 = (x % 2) * 4 + 2
        write_bit_1 = 7 - (line_bit_1 + one_two)
        write_bit_0 = 7 - (line_bit_0 + one_two)

        # 设置颜色值
        data_bit0 = (color & 0x01) > 0
        data_bit1 = (color & 0x02) > 0

        if data_bit1:
            self.buffer[write_byte_index] |= (1 << write_bit_1)
        else:
            self.buffer[write_byte_index] &= ~(1 << write_bit_1)

        if data_bit0:
            self.buffer[write_byte_index] |= (1 << write_bit_0)
        else:
            self.buffer[write_byte_index] &= ~(1 << write_bit_0)

    def show(self):
        """更新显示内容到屏幕

        将缓冲区的内容刷新到显示屏上，在修改显示内容后需要调用此函数才能看到效果

        使用示例：
        lcd.draw_line(0, 0, 100, 100, 1)
        lcd.show()  # 显示绘制的线条
        """
        # 设置列地址范围
        self.write_command(0x2A)
        self.write_data(0x05)
        self.write_data(0x36)

        # 设置行地址范围
        self.write_command(0x2B)
        self.write_data(0x00)
        self.write_data(0xC7)

        # 准备写入数据
        self.write_command(0x2C)

        # 发送显示数据
        self.dc(1)
        self.cs(0)
        self.spi.write(self.buffer)
        self.cs(1)

    def fill(self, color):
        """填充整个屏幕为指定颜色

        参数说明：
        color: 填充颜色（0-3）
            0: 白色
            1: 浅灰
            2: 深灰
            3: 黑色

        使用示例：
        lcd.fill(0)  # 清屏为白色
        lcd.fill(3)  # 填充为黑色
        """
        color = color & 0x03
        fill_value = (color << 6) | (color << 4) | (color << 2) | color
        for i in range(self.BUFFER_SIZE):
            self.buffer[i] = fill_value
        self.show()

    def clear(self):
        """清除显示内容

        将屏幕清除为白色背景，相当于调用 fill(0)

        使用示例：
        lcd.clear()  # 清屏
        """
        self.fill(0)

    def draw_line(self, x1, y1, x2, y2, color=1):
        """绘制直线

        参数说明：
        x1, y1: 起点坐标
        x2, y2: 终点坐标
        color: 线条颜色（0-3），默认为1

        使用示例：
        lcd.draw_line(0, 0, 100, 100, 1)  # 绘制对角线
        """
        value = 0x03 if color else 0x00

        # 确保坐标在有效范围内
        x1 = max(0, min(x1, self.LCD_WIDTH - 1))
        y1 = max(0, min(y1, self.LCD_HEIGHT - 1))
        x2 = max(0, min(x2, self.LCD_WIDTH - 1))
        y2 = max(0, min(y2, self.LCD_HEIGHT - 1))

        dx = abs(x2 - x1)
        dy = abs(y2 - y1)
        steep = dy > dx

        if steep:
            x1, y1 = y1, x1
            x2, y2 = y2, x2
            dx, dy = dy, dx

        if x1 > x2:
            x1, x2 = x2, x1
            y1, y2 = y2, y1

        dx = x2 - x1
        dy = abs(y2 - y1)
        error = dx // 2
        y = y1
        y_step = 1 if y1 < y2 else -1

        for x in range(x1, x2 + 1):
            if steep:
                if 0 <= y < self.LCD_WIDTH and 0 <= x < self.LCD_HEIGHT:
                    self.pixel(y, x, value)
            else:
                if 0 <= x < self.LCD_WIDTH and 0 <= y < self.LCD_HEIGHT:
                    self.pixel(x, y, value)

            error -= dy
            if error < 0:
                y += y_step
                error += dx

    def draw_rect(self, x, y, width, height, color=1):
        """绘制矩形

        参数说明：
        x, y: 左上角坐标
        width: 矩形宽度
        height: 矩形高度
        color: 线条颜色（0-3），默认为1

        使用示例：
        lcd.draw_rect(10, 10, 100, 50, 1)  # 绘制一个矩形
        """
        value = 0x03 if color else 0x00

        # 确保坐标在有效范围内
        x = max(0, min(x, self.LCD_WIDTH - 1))
        y = max(0, min(y, self.LCD_HEIGHT - 1))
        width = min(width, self.LCD_WIDTH - x)
        height = min(height, self.LCD_HEIGHT - y)

        # 绘制水平边
        for i in range(x, x + width):
            self.pixel(i, y, value)  # 上边
            if y + height - 1 < self.LCD_HEIGHT:
                self.pixel(i, y + height - 1, value)  # 下边

        # 绘制垂直边
        for i in range(y, y + height):
            self.pixel(x, i, value)  # 左边
            if x + width - 1 < self.LCD_WIDTH:
                self.pixel(x + width - 1, i, value)  # 右边

    def draw_circle(self, x0, y0, radius, color=1):
        """绘制圆形

        参数说明：
        x0, y0: 圆心坐标
        radius: 半径
        color: 线条颜色（0-3），默认为1

        使用示例：
        lcd.draw_circle(150, 200, 50, 1)  # 绘制一个圆
        """
        value = 0x03 if color else 0x00
        x = radius
        y = 0
        err = 0

        def plot_points(cx, cy):
            points = [
                (x0 + cx, y0 + cy), (x0 - cx, y0 + cy),
                (x0 + cx, y0 - cy), (x0 - cx, y0 - cy),
                (x0 + cy, y0 + cx), (x0 - cy, y0 + cx),
                (x0 + cy, y0 - cx), (x0 - cy, y0 - cx)
            ]
            for px, py in points:
                if 0 <= px < self.LCD_WIDTH and 0 <= py < self.LCD_HEIGHT:
                    self.pixel(px, py, value)

        while x >= y:
            plot_points(x, y)
            y += 1
            err += 1 + 2*y
            if 2*(err-x) + 1 > 0:
                x -= 1
                err += 1 - 2*x

    def draw_string(self, x, y, text, scale=1, color=1):
        """绘制字符串

        参数说明：
        x, y: 起始坐标
        text: 要显示的文本
        scale: 字体缩放倍数，默认为1
        color: 文字颜色（0-3），默认为1

        使用示例：
        lcd.draw_string(10, 10, "Hello", 2, 1)  # 绘制2倍大小的文本
        """
        if not text:
            return

        value = 0x03 if color else 0x00
        char_width = 8 * scale
        char_height = 8 * scale

        for char in text:
            if char not in FONT_8x8:
                continue

            if x + char_width > self.LCD_WIDTH:
                x = 0
                y += char_height
                if y + char_height > self.LCD_HEIGHT:
                    break

            font_data = FONT_8x8[char]
            for row in range(8):
                row_data = font_data[row]
                for col in range(8):
                    if row_data & (1 << col):
                        for dy in range(scale):
                            for dx in range(scale):
                                px = x + col * scale + dx
                                py = y + row * scale + dy
                                if px < self.LCD_WIDTH and py < self.LCD_HEIGHT:
                                    self.pixel(px, py, value)
            x += char_width

    def write_command(self, cmd):
        """写入命令到显示屏

        参数说明：
        cmd: 命令字节

        注意：这是底层函数，通常不需要直接调用
        """
        self.dc(0)
        self.cs(0)
        self.spi.write(bytearray([cmd]))
        self.cs(1)

    def write_data(self, data):
        """写入数据到显示屏

        参数说明：
        data: 数据字节

        注意：这是底层函数，通常不需要直接调用
        """
        self.dc(1)
        self.cs(0)
        self.spi.write(bytearray([data]))
        self.cs(1)

    def initialize(self):
        """初始化显示屏

        执行显示屏的初始化序列，包括：
        - 复位
        - 设置电压和时序参数
        - 配置显示模式
        - 清屏

        注意：此函数在创建对象时自动调用，通常不需要手动调用
        """
        # 复位
        self.rst(0)
        time.sleep_ms(10)
        self.rst(1)
        time.sleep_ms(10)

        # 初始化命令序列
        self.write_command(0xD6)  # NVM Load Control
        self.write_data(0x17)
        self.write_data(0x02)

        self.write_command(0xD1)  # Booster Enable
        self.write_data(0x01)

        self.write_command(0xC0)  # Gate Voltage Setting
        self.write_data(0x12)  # VGH 17V
        self.write_data(0x0A)  # VGL -10V

        self.write_command(0xC1)  # VSHP Setting
        self.write_data(115)   # VSHP1
        self.write_data(0x3E)  # VSHP2
        self.write_data(0x3C)  # VSHP3
        self.write_data(0x3C)  # VSHP4

        self.write_command(0xC2)  # VSLP Setting
        self.write_data(0x00)  # VSLP1
        self.write_data(0x21)  # VSLP2
        self.write_data(0x23)  # VSLP3
        self.write_data(0x23)  # VSLP4

        self.write_command(0xC4)  # VSHN Setting
        self.write_data(50)    # VSHN1
        self.write_data(0x5C)  # VSHN2
        self.write_data(0x5A)  # VSHN3
        self.write_data(0x5A)  # VSHN4

        self.write_command(0xC5)  # VSLN Setting
        self.write_data(50)    # VSLN1
        self.write_data(0x35)  # VSLN2
        self.write_data(0x37)  # VSLN3
        self.write_data(0x37)  # VSLN4

        self.write_command(0xD8)  # OSC Setting
        self.write_data(0xA6)
        self.write_data(0xE9)

        self.write_command(0xB2)  # Frame Rate Control
        self.write_data(0x12)  # HPM=32hz ; LPM=1hz

        self.write_command(0xB3)  # Update Period Gate EQ Control in HPM
        self.write_data(0xE5)
        self.write_data(0xF6)
        self.write_data(0x17)
        self.write_data(0x77)
        self.write_data(0x77)
        self.write_data(0x77)
        self.write_data(0x77)
        self.write_data(0x77)
        self.write_data(0x77)
        self.write_data(0x71)

        self.write_command(0xB4)  # Update Period Gate EQ Control in LPM
        self.write_data(0x05)
        self.write_data(0x46)
        self.write_data(0x77)
        self.write_data(0x77)
        self.write_data(0x77)
        self.write_data(0x77)
        self.write_data(0x76)
        self.write_data(0x45)

        self.write_command(0x62)  # Gate Timing Control
        self.write_data(0x32)
        self.write_data(0x03)
        self.write_data(0x1F)

        self.write_command(0xB7)  # Source EQ Enable
        self.write_data(0x13)

        self.write_command(0xB0)  # Gate Line Setting
        self.write_data(0x64)  # 400 line = 100*4

        self.write_command(0x11)  # Sleep out
        time.sleep_ms(120)

        self.write_command(0xC9)  # Source Voltage Select
        self.write_data(0x00)

        self.write_command(0x36)  # Memory Data Access Control
        self.write_data(0x48)  # MX=1 ; DO=1

        self.write_command(0x3A)  # Data Format Select
        self.write_data(0x11)  # 3write for 24bit

        self.write_command(0xB9)  # Gamma Mode Setting
        self.write_data(0x20)  # Mono mode

        self.write_command(0xB8)  # Panel Setting
        self.write_data(0x29)  # 1-Dot inversion, Frame inversion, One Line Interlace

        self.write_command(0x2A)  # Column Address Setting
        self.write_data(0x05)
        self.write_data(0x36)

        self.write_command(0x2B)  # Row Address Setting
        self.write_data(0x00)
        self.write_data(0xC7)

        self.write_command(0x35)  # TE
        self.write_data(0x00)

        self.write_command(0xD0)  # Auto power down
        self.write_data(0xFF)  # Auto power down ON

        self.write_command(0x38)  # High Power Mode
        self.write_command(0x29)  # Display ON
        self.write_command(0x20)  # Display Inversion Off

        self.write_command(0xBB)  # Enable Clear RAM
        self.write_data(0x4F)

        # 清屏
        self.fill(0)
        self.show()
        time.sleep_ms(10)



