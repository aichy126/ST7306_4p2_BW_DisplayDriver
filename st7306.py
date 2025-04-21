from machine import Pin, SPI
import framebuf
import time
import math
from font import FONT_8x8

class ST7306(framebuf.FrameBuffer):
    def __init__(self, spi, cs, dc, rst):
        self.spi = spi
        self.cs = cs
        self.dc = dc
        self.rst = rst

        # 屏幕物理参数
        self.PHYSICAL_WIDTH = 300
        self.PHYSICAL_HEIGHT = 400

        # 实际显示参数（2个像素组成1个像素，所以一行为600像素，600/4=150）
        self.LCD_WIDTH = 300
        self.LCD_HEIGHT = 400

        # 缓冲区参数
        # 2个像素组成1个像素，所以一行为600像素，600/4=150 一行共150个byte的数据
        # 上下两行共用一行的数据，所以总行数需要除2
        # 400/2=200 所以共200行，一行150个byte数据，共200*150=30000byte
        self.LCD_DATA_WIDTH = 150  # 每行150字节
        self.LCD_DATA_HEIGHT = 200  # 200行
        self.BUFFER_SIZE = self.LCD_DATA_WIDTH * self.LCD_DATA_HEIGHT  # 30000字节

        # 模式标志
        self.HPM_MODE = False
        self.LPM_MODE = False

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

    def _convert_coordinates(self, x, y):
        """转换坐标到实际显示位置"""
        return x, y

    def pixel(self, x, y, color=None):
        """重写像素绘制函数，匹配C++驱动的实现
        像素数据结构为：
        P0P2 P4P6
        P1P3 P5P7

        对应一个byte数据的：
        BIT7 BIT5 BIT3 BIT1
        BIT6 BIT4 BIT2 BIT0
        """
        if not (0 <= x < self.LCD_WIDTH and 0 <= y < self.LCD_HEIGHT):
            return

        if color is None:
            return super().pixel(x, y)

        # 找到是哪一行的数据
        real_x = x // 2  # 0->0, 3->1, 4->2, 7->3
        real_y = y // 2  # 0->0, 1->0, 2->1, 3->1
        write_byte_index = real_y * self.LCD_DATA_WIDTH + real_x

        # 计算位位置
        one_two = 1 if y % 2 else 0  # 0 1
        line_bit_1 = (x % 2) * 4  # 0 4
        line_bit_0 = (x % 2) * 4 + 2  # 2 6
        write_bit_1 = 7 - (line_bit_1 + one_two)
        write_bit_0 = 7 - (line_bit_0 + one_two)

        # 提取颜色的两个位
        data_bit0 = (color & 0x01) > 0
        data_bit1 = (color & 0x02) > 0

        # 设置或清除相应的位
        if data_bit1:
            self.buffer[write_byte_index] |= (1 << write_bit_1)
        else:
            self.buffer[write_byte_index] &= ~(1 << write_bit_1)

        if data_bit0:
            self.buffer[write_byte_index] |= (1 << write_bit_0)
        else:
            self.buffer[write_byte_index] &= ~(1 << write_bit_0)

    def show(self):
        """更新显示内容"""
        # 设置列地址范围
        self.write_command(0x2A)
        self.write_data(0x05)  # 起始列地址
        self.write_data(0x36)  # 结束列地址

        # 设置行地址范围
        self.write_command(0x2B)
        self.write_data(0x00)  # 起始行地址
        self.write_data(0xC7)  # 结束行地址

        # 准备写入数据
        self.write_command(0x2C)

        # 发送显示数据
        self.dc(1)  # 数据模式
        self.cs(0)  # 片选有效

        # 一次性发送所有数据
        self.spi.write(self.buffer)

        self.cs(1)  # 片选无效

    def fill(self, color):
        """填充整个屏幕"""
        color = color & 0x03  # 确保颜色值在0-3范围内
        # 计算填充值（每个字节包含4个2位像素）
        fill_value = (color << 6) | (color << 4) | (color << 2) | color
        for i in range(self.BUFFER_SIZE):
            self.buffer[i] = fill_value
        self.show()

    def clear(self):
        """清除显示"""
        self.fill(0)
        self.show()

    def fill_rect(self, x, y, w, h, color):
        """填充矩形，确保2x2像素对齐"""
        x = (x // 2) * 2
        y = (y // 2) * 2
        w = ((w + 1) // 2) * 2
        h = ((h + 1) // 2) * 2

        for row in range(y, y + h, 2):
            for col in range(x, x + w, 2):
                self.pixel(col, row, color)

    def rect(self, x, y, width, height, color=1, fill=False, single_pixel=True):
        """绘制矩形，支持单像素模式
        single_pixel: True为单像素模式，False为2x2像素模式
        """
        if width <= 0 or height <= 0:
            return

        value = 0x03 if color else 0x00

        if not single_pixel:
            x = (x // 2) * 2
            y = (y // 2) * 2
            width = ((width + 1) // 2) * 2
            height = ((height + 1) // 2) * 2

        if fill:
            for cy in range(y, y + height):
                for cx in range(x, x + width):
                    self.pixel(cx, cy, value)
        else:
            # 绘制水平边
            for cx in range(x, x + width):
                self.pixel(cx, y, value)  # 上边
                self.pixel(cx, y + height - 1, value)  # 下边

            # 绘制垂直边
            for cy in range(y, y + height):
                self.pixel(x, cy, value)  # 左边
                self.pixel(x + width - 1, cy, value)  # 右边

    def line(self, x1, y1, x2, y2, color=1):
        """使用Bresenham算法绘制单像素直线"""
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

    def draw_text(self, x, y, text, scale=2, color=1):
        """draw_string的别名，保持向后兼容"""
        self.draw_string(x, y, text, scale, color)

    def reverse_byte(self, b):
        """翻转一个字节的位序"""
        b = ((b & 0xF0) >> 4) | ((b & 0x0F) << 4)
        b = ((b & 0xCC) >> 2) | ((b & 0x33) << 2)
        b = ((b & 0xAA) >> 1) | ((b & 0x55) << 1)
        return b

    def draw_char(self, x, y, char, scale=2, color=1):
        """绘制单个字符，支持放大显示"""
        if char not in FONT_8x8:
            return

        # 获取字符点阵数据
        font_data = FONT_8x8[char]

        # 使用最大灰度值以确保清晰度
        value = 0x03 if color else 0x00

        # 计算字符实际大小
        char_width = 8 * scale
        char_height = 8 * scale

        # 检查边界
        if x + char_width > self.LCD_WIDTH or y + char_height > self.LCD_HEIGHT:
            return

        # 清除字符区域
        for cy in range(y, y + char_height):
            for cx in range(x, x + char_width):
                self.pixel(cx, cy, 0)

        # 逐像素绘制放大后的字符
        for row in range(8):
            row_data = font_data[row]
            for col in range(8):
                if row_data & (1 << col):  # 从右到左读取位
                    # 绘制放大后的像素块
                    for dy in range(scale):
                        for dx in range(scale):
                            px = x + col * scale + dx
                            py = y + row * scale + dy
                            if px < self.LCD_WIDTH and py < self.LCD_HEIGHT:
                                self.pixel(px, py, value)

    def draw_string(self, x, y, text, scale=2, color=1):
        """绘制字符串，支持放大显示
        x: 起始x坐标
        y: 起始y坐标
        text: 要显示的文本
        scale: 放大倍数，默认2倍
        color: 显示颜色，0=不显示，1=显示
        """
        cursor_x = x
        cursor_y = y
        char_spacing = 8 * scale  # 字符间距随放大倍数调整
        line_spacing = 10 * scale  # 行间距随放大倍数调整

        for char in text:
            if char == '\n':
                cursor_y += line_spacing
                cursor_x = x
                continue

            # 检查是否需要换行
            if cursor_x + char_spacing > self.LCD_WIDTH:
                cursor_y += line_spacing
                cursor_x = x

            # 检查是否超出屏幕底部
            if cursor_y + 8 * scale > self.LCD_HEIGHT:
                break

            # 绘制字符
            self.draw_char(cursor_x, cursor_y, char, scale, color)
            cursor_x += char_spacing

        # 更新显示
        self.show()

    def write_command(self, cmd):
        self.dc(0)
        self.cs(0)
        self.spi.write(bytearray([cmd]))
        self.cs(1)

    def write_data(self, data):
        self.dc(1)
        self.cs(0)
        self.spi.write(bytearray([data]))
        self.cs(1)

    def initialize(self):
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
        self.HPM_MODE = True
        self.LPM_MODE = False

        self.write_command(0x29)  # Display ON
        self.write_command(0x20)  # Display Inversion Off

        self.write_command(0xBB)  # Enable Clear RAM
        self.write_data(0x4F)

        # 清屏
        self.fill(0)
        self.show()
        time.sleep_ms(10)

    def draw_rect(self, x, y, width, height, color=1):
        """绘制单像素矩形"""
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

        # 更新显示
        self.show()

    def draw_circle(self, x0, y0, radius, color=1, fill=False, single_pixel=True):
        """绘制圆形，支持单像素模式
        single_pixel: True为单像素模式，False为2x2像素模式
        """
        if not single_pixel:
            x0 = (x0 // 2) * 2
            y0 = (y0 // 2) * 2
            radius = (radius // 2) * 2

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
                    if not single_pixel:
                        self.pixel(px + 1, py, value)
                        self.pixel(px, py + 1, value)
                        self.pixel(px + 1, py + 1, value)

        while x >= y:
            if fill:
                for i in range(-x, x + 1):
                    if y0 + y < self.LCD_HEIGHT and y0 - y >= 0:
                        if 0 <= x0 + i < self.LCD_WIDTH:
                            self.pixel(x0 + i, y0 + y, value)
                            self.pixel(x0 + i, y0 - y, value)
                    if y0 + x < self.LCD_HEIGHT and y0 - x >= 0:
                        if 0 <= x0 + i < self.LCD_WIDTH:
                            self.pixel(x0 + i, y0 + x, value)
                            self.pixel(x0 + i, y0 - x, value)
            else:
                plot_points(x, y)

            y += 1
            err += 1 + 2*y
            if 2*(err-x) + 1 > 0:
                x -= 1
                err += 1 - 2*x

    def draw_char_scale(self, x, y, char, scale=1, color=1):
        """绘制放大字符
        x: 起始x坐标
        y: 起始y坐标
        char: 要显示的字符
        scale: 放大倍数
        color: 显示颜色，0=不显示，1=显示
        """
        if char not in FONT_8x8:
            return

        # 确保坐标和缩放比例都为偶数
        x = (x // 2) * 2
        y = (y // 2) * 2
        scale = (scale // 2) * 2
        if scale < 2:
            scale = 2

        # 计算字符尺寸
        char_width = 8 * scale
        char_height = 8 * scale

        # 严格的边界检查
        if (x < 0 or x + char_width > self.LCD_WIDTH or
            y < 0 or y + char_height > self.LCD_HEIGHT):
            return

        font_data = FONT_8x8[char]
        value = 0x03 if color else 0x00

        # 计算实际的显示区域（确保在LCD范围内）
        end_x = min(x + char_width, self.LCD_WIDTH)
        end_y = min(y + char_height, self.LCD_HEIGHT)

        # 按2x2像素块清除字符区域
        for clear_y in range(y, end_y, 2):
            for clear_x in range(x, end_x, 2):
                self.pixel(clear_x, clear_y, 0)

        # 绘制字符（确保2x2像素块对齐）
        for row in range(8):
            row_data = font_data[row]
            for col in range(8):
                if row_data & (1 << col):
                    # 计算缩放后的位置
                    for sy in range(0, scale, 2):
                        base_y = y + row * scale + sy
                        if base_y >= end_y:
                            break

                        for sx in range(0, scale, 2):
                            base_x = x + col * scale + sx
                            if base_x >= end_x:
                                break

                            self.pixel(base_x, base_y, value)

    def draw_string_scale(self, x, y, text, scale=1, color=1):
        """绘制放大字符串
        x: 起始x坐标
        y: 起始y坐标
        text: 要显示的文本
        scale: 放大倍数
        color: 显示颜色，0=不显示，1=显示
        """
        if not text:
            return

        # 确保坐标和缩放比例都为偶数
        x = (x // 2) * 2
        y = (y // 2) * 2
        scale = (scale // 2) * 2
        if scale < 2:
            scale = 2

        # 计算字符尺寸和间距（确保为偶数）
        char_width = 8 * scale
        char_height = 8 * scale
        char_spacing = 2  # 固定使用2像素间距，确保2x2对齐

        # 计算文本总宽度（用于右对齐）
        text_width = len(text) * (char_width + char_spacing) - char_spacing

        current_x = x
        current_y = y

        # 如果x是负值，从右边开始计算
        if x < 0:
            current_x = max(0, self.LCD_WIDTH - text_width)

        # 预先检查垂直方向是否有足够空间
        if current_y + char_height > self.LCD_HEIGHT:
            return

        # 绘制所有字符
        for char in text:
            if char == '\n':
                current_y += char_height + char_spacing
                current_x = x if x >= 0 else max(0, self.LCD_WIDTH - text_width)

                # 检查换行后是否还有足够空间
                if current_y + char_height > self.LCD_HEIGHT:
                    break

            # 检查水平方向是否需要换行
            if current_x + char_width > self.LCD_WIDTH:
                current_y += char_height + char_spacing
                current_x = x if x >= 0 else max(0, self.LCD_WIDTH - text_width)

                # 检查换行后是否还有足够空间
                if current_y + char_height > self.LCD_HEIGHT:
                    break

            # 绘制当前字符
            self.draw_char(current_x, current_y, char, scale, color)
            current_x += char_width + char_spacing

        # 最后一次性更新显示
        self.show()

    def draw_char_rotate(self, x, y, char, angle=0, color=1):
        """绘制旋转字符"""
        if char not in FONT_8x8:
            return

        font_data = FONT_8x8[char]
        # 计算旋转中心
        center_x = x + 4
        center_y = y + 4
        rad = math.radians(angle)
        cos_a = math.cos(rad)
        sin_a = math.sin(rad)

        # 预计算旋转后的边界
        corners = [
            (x, y), (x + 8, y),
            (x, y + 8), (x + 8, y + 8)
        ]
        rotated_corners = []
        for cx, cy in corners:
            dx = cx - center_x
            dy = cy - center_y
            rx = center_x + dx * cos_a - dy * sin_a
            ry = center_y + dx * sin_a + dy * cos_a
            rotated_corners.append((rx, ry))

        # 检查旋转后是否在屏幕范围内
        min_x = min(x for x, _ in rotated_corners)
        max_x = max(x for x, _ in rotated_corners)
        min_y = min(y for _, y in rotated_corners)
        max_y = max(y for _, y in rotated_corners)

        if min_x < 0 or max_x >= self.LCD_WIDTH or min_y < 0 or max_y >= self.LCD_HEIGHT:
            return

        # 绘制字符
        for row in range(8):
            row_data = font_data[row]
            for col in range(8):
                if row_data & (1 << (7 - col)):
                    dx = col - 4
                    dy = row - 4
                    # 计算旋转后的坐标
                    new_x = int(center_x + dx * cos_a - dy * sin_a)
                    new_y = int(center_y + dx * sin_a + dy * cos_a)

                    if 0 <= new_x < self.LCD_WIDTH and 0 <= new_y < self.LCD_HEIGHT:
                        self.pixel(new_x, new_y, color)

    def draw_string_rotate(self, x, y, text, angle=0, color=1):
        """绘制旋转字符串"""
        rad = math.radians(angle)
        cos_a = math.cos(rad)
        sin_a = math.sin(rad)
        current_x = x

        for char in text:
            if char == '\n':
                # 计算旋转后的换行位置
                dx = 0
                dy = 9  # 行间距
                new_x = x + dx * cos_a - dy * sin_a
                new_y = y + dx * sin_a + dy * cos_a
                current_x = new_x
                y = new_y
                continue

            self.draw_char_rotate(int(current_x), int(y), char, angle, color)
            # 计算下一个字符的位置
            dx = 8  # 字符宽度
            dy = 0
            current_x += dx * cos_a
            y += dx * sin_a

    def draw_filled_circle(self, x0, y0, radius, color=1):
        """使用改进的扫描线算法绘制实心圆"""
        radius_sq = radius * radius
        for y in range(-radius, radius + 1):
            y_sq = y * y
            x_max = int((radius_sq - y_sq) ** 0.5)

            # 计算扫描线起点和终点
            for x in range(-x_max, x_max + 1):
                px = x0 + x
                py = y0 + y

                if 0 <= px < self.LCD_WIDTH and 0 <= py < self.LCD_HEIGHT:
                    # 计算到圆心的精确距离
                    dist = (x * x + y * y) ** 0.5

                    # 边缘抗锯齿处理
                    if dist <= radius - 1:
                        # 内部完全填充
                        self.pixel(px, py, color)
                    elif dist <= radius:
                        # 边缘渐变
                        alpha = radius - dist
                        intensity = min(3, max(0, int(alpha * color)))
                        self.pixel(px, py, intensity)

    def reverse_text(self, text):
        """反转字符串的辅助函数"""
        chars = list(text)
        length = len(chars)
        for i in range(length // 2):
            chars[i], chars[length - 1 - i] = chars[length - 1 - i], chars[i]
        return ''.join(chars)

    def low_power_mode(self):
        if not self.LPM_MODE:
            self.HPM_MODE = False
            self.LPM_MODE = True

            # 设置电压参数
            self.write_command(0xC1)
            self.write_data(115)
            self.write_data(0x3E)
            self.write_data(0x3C)
            self.write_data(0x3C)

            self.write_command(0xC2)
            self.write_data(0x00)
            self.write_data(0x21)
            self.write_data(0x23)
            self.write_data(0x23)

            self.write_command(0xC4)
            self.write_data(50)
            self.write_data(0x5C)
            self.write_data(0x5A)
            self.write_data(0x5A)

            self.write_command(0xC5)
            self.write_data(50)
            self.write_data(0x35)
            self.write_data(0x37)
            self.write_data(0x37)

            self.write_command(0xC9)
            self.write_data(0x00)

            time.sleep_ms(20)

            self.write_command(0x39)  # LPM ON
            time.sleep_ms(100)

    def high_power_mode(self):
        if not self.HPM_MODE:
            self.HPM_MODE = True
            self.LPM_MODE = False

            self.write_command(0x38)  # HPM ON
            time.sleep_ms(300)

            # 设置电压参数
            self.write_command(0xC1)
            self.write_data(115)
            self.write_data(0x3E)
            self.write_data(0x3C)
            self.write_data(0x3C)

            self.write_command(0xC2)
            self.write_data(0x00)
            self.write_data(0x21)
            self.write_data(0x23)
            self.write_data(0x23)

            self.write_command(0xC4)
            self.write_data(50)
            self.write_data(0x5C)
            self.write_data(0x5A)
            self.write_data(0x5A)

            self.write_command(0xC5)
            self.write_data(50)
            self.write_data(0x35)
            self.write_data(0x37)
            self.write_data(0x37)

            self.write_command(0xC9)
            self.write_data(0x00)

            time.sleep_ms(20)

    def display_on(self, enabled=True):
        self.write_command(0x29 if enabled else 0x28)

    def display_sleep(self, enabled=True):
        if enabled:
            if self.LPM_MODE:
                self.write_command(0x38)  # HPM ON
                time.sleep_ms(300)
            self.write_command(0x10)  # Sleep ON
            time.sleep_ms(100)
        else:
            self.write_command(0x11)  # Sleep OFF
            time.sleep_ms(100)

    def display_inversion(self, enabled=True):
        self.write_command(0x21 if enabled else 0x20)



