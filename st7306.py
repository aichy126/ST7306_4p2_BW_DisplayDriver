from machine import Pin, SPI
import time
import math
from font import FONT_8x8

class ST7306:
    def __init__(self, spi, cs, dc, rst):
        self.spi = spi
        self.cs = cs
        self.dc = dc
        self.rst = rst

        # 屏幕参数
        self.LCD_WIDTH = 300
        self.LCD_HEIGHT = 400
        self.LCD_DATA_WIDTH = 150  # 300/2 每行150个字节
        self.LCD_DATA_HEIGHT = 200  # 400/2 共200行
        self.DISPLAY_BUFFER_LENGTH = 30000  # 150 * 200

        # 模式标志
        self.HPM_MODE = False
        self.LPM_MODE = False

        # 初始化引脚
        self.cs.init(Pin.OUT, value=1)
        self.dc.init(Pin.OUT, value=0)
        self.rst.init(Pin.OUT, value=1)

        # 初始化显示缓冲区
        self.display_buffer = bytearray(self.DISPLAY_BUFFER_LENGTH)

        # 初始化屏幕
        self.initialize()

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

        # NVM Load Control
        self.write_command(0xD6)
        self.write_data(0x17)
        self.write_data(0x02)

        # Booster Enable
        self.write_command(0xD1)
        self.write_data(0x01)

        # Gate Voltage Setting
        self.write_command(0xC0)
        self.write_data(0x12)  # VGH 17V
        self.write_data(0x0A)  # VGL -10V

        # VSHP Setting
        self.write_command(0xC1)
        self.write_data(115)   # VSHP1
        self.write_data(0x3E)  # VSHP2
        self.write_data(0x3C)  # VSHP3
        self.write_data(0x3C)  # VSHP4

        # VSLP Setting
        self.write_command(0xC2)
        self.write_data(0x00)  # VSLP1
        self.write_data(0x21)  # VSLP2
        self.write_data(0x23)  # VSLP3
        self.write_data(0x23)  # VSLP4

        # VSHN Setting
        self.write_command(0xC4)
        self.write_data(50)    # VSHN1
        self.write_data(0x5C)  # VSHN2
        self.write_data(0x5A)  # VSHN3
        self.write_data(0x5A)  # VSHN4

        # VSLN Setting
        self.write_command(0xC5)
        self.write_data(50)    # VSLN1
        self.write_data(0x35)  # VSLN2
        self.write_data(0x37)  # VSLN3
        self.write_data(0x37)  # VSLN4

        # OSC Setting
        self.write_command(0xD8)
        self.write_data(0xA6)
        self.write_data(0xE9)

        # Frame Rate Control - 提高刷新率
        self.write_command(0xB2)
        self.write_data(0x01)  # 提高刷新率到最大

        # Update Period Gate EQ Control in HPM - 优化更新周期
        self.write_command(0xB3)
        for _ in range(10):
            self.write_data(0x33)  # 减小更新周期

        # Update Period Gate EQ Control in LPM
        self.write_command(0xB4)
        self.write_data(0x00)  # 禁用低功耗模式的更新
        for _ in range(7):
            self.write_data(0x33)

        # Gate Timing Control - 优化门控时序
        self.write_command(0x62)
        self.write_data(0x32)
        self.write_data(0x01)  # 减小门控延迟
        self.write_data(0x1F)

        # Source EQ Enable
        self.write_command(0xB7)
        self.write_data(0x11)  # 优化源极均衡

        # Gate Line Setting
        self.write_command(0xB0)
        self.write_data(0x64)  # 400 line = 100*4

        # Sleep out
        self.write_command(0x11)
        time.sleep_ms(120)

        # Source Voltage Select
        self.write_command(0xC9)
        self.write_data(0x00)  # VSHP1; VSLP1 ; VSHN1 ; VSLN1

        # Memory Data Access Control
        self.write_command(0x36)
        self.write_data(0x48)  # 恢复原始设置 MX=1 ; DO=1

        # Data Format Select
        self.write_command(0x3A)
        self.write_data(0x11)  # 3write for 24bit

        # Gamma Mode Setting
        self.write_command(0xB9)
        self.write_data(0x20)  # Mono mode

        # Panel Setting - 优化面板设置
        self.write_command(0xB8)
        self.write_data(0x21)  # 1-Dot inversion, Frame inversion, No Line Interlace

        # Column Address Setting
        self.write_command(0x2A)
        self.write_data(0x05)
        self.write_data(0x36)

        # Row Address Setting
        self.write_command(0x2B)
        self.write_data(0x00)
        self.write_data(0xC7)

        # TE
        self.write_command(0x35)
        self.write_data(0x00)

        # Auto power down
        self.write_command(0xD0)
        self.write_data(0x00)  # 禁用自动掉电以提高性能

        # High Power Mode
        self.write_command(0x38)
        self.HPM_MODE = True
        self.LPM_MODE = False

        # Display ON
        self.write_command(0x29)

        # Display Inversion Off
        self.write_command(0x20)

        # Enable Clear RAM
        self.write_command(0xBB)
        self.write_data(0x4F)

        # 清屏
        self.clear()

    def write_point(self, x, y, data):
        """写入单个像素点到缓冲区
        x: 0-299 横坐标
        y: 0-399 纵坐标
        data: 像素值 (0-3)

        硬件像素排列（每个字节控制4个像素点）：
        字节内像素排列：
        P0(7,6) P1(5,4) P2(3,2) P3(1,0)

        屏幕上的实际排列（2x2矩阵）：
        P0 P1
        P2 P3
        """
        if x >= self.LCD_WIDTH or y >= self.LCD_HEIGHT or x < 0 or y < 0:
            return

        # 确保写入完整的2x2像素块
        x = (x // 2) * 2
        y = (y // 2) * 2

        # 计算字节位置
        byte_x = x // 2
        byte_y = y // 2
        byte_index = byte_y * self.LCD_DATA_WIDTH + byte_x

        if byte_index >= self.DISPLAY_BUFFER_LENGTH:
            return

        # 写入完整的2x2像素块
        value = data & 0x03
        self.display_buffer[byte_index] = (value << 6) | (value << 4) | (value << 2) | value

    def display(self):
        """显示缓冲区内容"""
        # 设置显示区域
        self.write_command(0x2A)  # Column Address Setting
        self.write_data(0x05)
        self.write_data(0x36)

        self.write_command(0x2B)  # Row Address Setting
        self.write_data(0x00)
        self.write_data(0xC7)

        # 准备写入数据
        self.write_command(0x2C)  # Write image data

        # 一次性发送所有数据
        self.dc(1)  # 数据模式
        self.cs(0)  # 片选有效
        self.spi.write(self.display_buffer)
        self.cs(1)  # 片选无效

    def clear(self):
        """清除显示缓冲区"""
        for i in range(self.DISPLAY_BUFFER_LENGTH):
            self.display_buffer[i] = 0x00
        self.display()

    def address(self):
        # Column Address Setting
        self.write_command(0x2A)
        self.write_data(0x05)
        self.write_data(0x36)

        # Row Address Setting
        self.write_command(0x2B)
        self.write_data(0x00)
        self.write_data(0xC7)

        # Write image data
        self.write_command(0x2C)

    def draw_char(self, x, y, char, color=1):
        """绘制单个字符
        使用增强的像素填充方式提高清晰度
        """
        if char not in FONT_8x8:
            return

        font_data = FONT_8x8[char]
        value = 0x03 if color else 0x00

        # 清除字符区域
        for row in range(8):
            for col in range(8):
                self.write_point(x + col, y + row, 0)

        # 绘制字符（增强边缘）
        for row in range(8):
            row_data = font_data[row]
            for col in range(8):
                if row_data & (1 << (7 - col)):
                    # 主像素点
                    self.write_point(x + col, y + row, value)

                    # 增强水平连接
                    if col > 0 and row_data & (1 << (7 - (col - 1))):
                        self.write_point(x + col - 1, y + row, value)
                        self.write_point(x + col, y + row, value)

                    # 增强垂直连接
                    if row > 0 and font_data[row - 1] & (1 << (7 - col)):
                        self.write_point(x + col, y + row - 1, value)
                        self.write_point(x + col, y + row, value)

                    # 增强对角连接
                    if (row > 0 and col > 0 and
                        font_data[row - 1] & (1 << (7 - (col - 1)))):
                        self.write_point(x + col - 1, y + row - 1, value)
                        self.write_point(x + col, y + row - 1, value)
                        self.write_point(x + col - 1, y + row, value)

    def draw_string(self, x, y, text, color=1):
        """绘制字符串
        确保字符间距合适并保持清晰度
        """
        text_width = len(text) * 8
        current_x = x
        current_y = y

        # 如果x是负值，从右边开始计算
        if x < 0:
            current_x = max(0, self.LCD_WIDTH + x - text_width)

        # 清除整个文本区域
        for clear_y in range(y, y + 8):
            for clear_x in range(current_x, current_x + text_width):
                self.write_point(clear_x, clear_y, 0)

        # 绘制字符
        for char in text:
            if char == '\n':
                current_y += 8
                current_x = x if x >= 0 else max(0, self.LCD_WIDTH + x - text_width)
                continue

            if current_x + 8 > self.LCD_WIDTH:
                current_y += 8
                current_x = x if x >= 0 else max(0, self.LCD_WIDTH + x - text_width)

            # 绘制当前字符
            self.draw_char(current_x, current_y, char, color)

            # 确保字符间距合适
            if current_x > x:  # 不是第一个字符
                # 检查是否需要连接相邻字符
                prev_char = text[text.index(char) - 1]
                if prev_char in FONT_8x8:
                    prev_data = FONT_8x8[prev_char]
                    curr_data = FONT_8x8[char]
                    # 检查并连接相邻字符的边缘
                    for row in range(8):
                        if (prev_data[row] & 0x01) and (curr_data[row] & 0x80):
                            self.write_point(current_x - 1, current_y + row, color)

            current_x += 8

    def draw_line(self, x1, y1, x2, y2, color=1):
        """使用改进的Bresenham算法绘制直线"""
        value = 0x03 if color else 0x00

        # 确保坐标与2x2像素块对齐
        x1 = (x1 // 2) * 2
        y1 = (y1 // 2) * 2
        x2 = (x2 // 2) * 2
        y2 = (y2 // 2) * 2

        dx = abs(x2 - x1)
        dy = abs(y2 - y1)
        steep = dy > dx

        if steep:
            x1, y1 = y1, x1
            x2, y2 = y2, x2

        if x1 > x2:
            x1, x2 = x2, x1
            y1, y2 = y2, y1

        dx = x2 - x1
        dy = abs(y2 - y1)
        error = dx // 2
        y = y1
        y_step = 2 if y1 < y2 else -2

        # 按2x2像素块绘制
        for x in range(x1, x2 + 1, 2):
            if steep:
                self.write_point(y, x, value)
                self.write_point(y + 1, x, value)
                self.write_point(y, x + 1, value)
                self.write_point(y + 1, x + 1, value)
            else:
                self.write_point(x, y, value)
                self.write_point(x + 1, y, value)
                self.write_point(x, y + 1, value)
                self.write_point(x + 1, y + 1, value)

            error -= dy
            if error < 0:
                y += y_step
                error += dx

    def draw_rect(self, x, y, width, height, color=1, fill=False):
        """绘制矩形
        使用连续的像素点绘制，确保边缘完整
        """
        if width <= 0 or height <= 0:
            return

        value = 0x03 if color else 0x00

        # 确保坐标和尺寸与2x2像素块对齐
        x = (x // 2) * 2
        y = (y // 2) * 2
        width = ((width + 1) // 2) * 2
        height = ((height + 1) // 2) * 2

        if fill:
            # 填充矩形（按2x2像素块）
            for cy in range(y, y + height, 2):
                for cx in range(x, x + width, 2):
                    self.write_point(cx, cy, value)
                    self.write_point(cx + 1, cy, value)
                    self.write_point(cx, cy + 1, value)
                    self.write_point(cx + 1, cy + 1, value)
        else:
            # 绘制水平边
            for cx in range(x, x + width):
                # 上边
                self.write_point(cx, y, value)
                self.write_point(cx, y + 1, value)
                # 下边
                self.write_point(cx, y + height - 2, value)
                self.write_point(cx, y + height - 1, value)

            # 绘制垂直边
            for cy in range(y, y + height):
                # 左边
                self.write_point(x, cy, value)
                self.write_point(x + 1, cy, value)
                # 右边
                self.write_point(x + width - 2, cy, value)
                self.write_point(x + width - 1, cy, value)

    def draw_circle(self, x0, y0, radius, color=1, fill=False):
        """使用改进的Bresenham算法绘制圆"""
        # 确保坐标与2x2像素块对齐
        x0 = (x0 // 2) * 2
        y0 = (y0 // 2) * 2
        radius = (radius // 2) * 2

        value = 0x03 if color else 0x00
        x = radius
        y = 0
        err = 0

        def draw_circle_points(cx, cy):
            points = [
                (x0 + cx, y0 + cy), (x0 - cx, y0 + cy),
                (x0 + cx, y0 - cy), (x0 - cx, y0 - cy),
                (x0 + cy, y0 + cx), (x0 - cy, y0 + cx),
                (x0 + cy, y0 - cx), (x0 - cy, y0 - cx)
            ]
            for px, py in points:
                if 0 <= px < self.LCD_WIDTH and 0 <= py < self.LCD_HEIGHT:
                    # 绘制2x2像素块
                    self.write_point(px, py, value)
                    self.write_point(px + 1, py, value)
                    self.write_point(px, py + 1, value)
                    self.write_point(px + 1, py + 1, value)

        while x >= y:
            if fill:
                # 填充对应的扇形区域（按2x2像素块）
                for i in range(-x, x + 1, 2):
                    for j in range(-1, 2, 2):
                        py = y0 + y * j
                        if 0 <= py < self.LCD_HEIGHT:
                            px = x0 + i
                            if 0 <= px < self.LCD_WIDTH:
                                self.write_point(px, py, value)
                                self.write_point(px + 1, py, value)
                                self.write_point(px, py + 1, value)
                                self.write_point(px + 1, py + 1, value)
            else:
                draw_circle_points(x, y)

            y += 2
            err += 1 + 2*y
            if 2*(err-x) + 1 > 0:
                x -= 2
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
                self.write_point(clear_x, clear_y, 0)

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

                            self.write_point(base_x, base_y, value)

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
                continue

            # 检查水平方向是否需要换行
            if current_x + char_width > self.LCD_WIDTH:
                current_y += char_height + char_spacing
                current_x = x if x >= 0 else max(0, self.LCD_WIDTH - text_width)

                # 检查换行后是否还有足够空间
                if current_y + char_height > self.LCD_HEIGHT:
                    break

            # 绘制当前字符
            self.draw_char_scale(current_x, current_y, char, scale, color)
            current_x += char_width + char_spacing

        # 最后一次性更新显示
        self.display()

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
                        self.write_point(new_x, new_y, color)

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
                        self.write_point(px, py, color)
                    elif dist <= radius:
                        # 边缘渐变
                        alpha = radius - dist
                        intensity = min(3, max(0, int(alpha * color)))
                        self.write_point(px, py, intensity)

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



