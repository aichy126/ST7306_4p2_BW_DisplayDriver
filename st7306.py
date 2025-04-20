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
        self.LCD_DATA_WIDTH = 150  # 300/2
        self.LCD_DATA_HEIGHT = 200  # 400/2
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

        # Frame Rate Control
        self.write_command(0xB2)
        self.write_data(0x11)  # HPM=32hz

        # Update Period Gate EQ Control in HPM
        self.write_command(0xB3)
        for _ in range(10):
            self.write_data(0x77)

        # Update Period Gate EQ Control in LPM
        self.write_command(0xB4)
        self.write_data(0x05)
        for _ in range(7):
            self.write_data(0x77)

        # Gate Timing Control
        self.write_command(0x62)
        self.write_data(0x32)
        self.write_data(0x03)
        self.write_data(0x1F)

        # Source EQ Enable
        self.write_command(0xB7)
        self.write_data(0x13)

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
        self.write_data(0x48)  # MX=1 ; DO=1

        # Data Format Select
        self.write_command(0x3A)
        self.write_data(0x11)  # 3write for 24bit

        # Gamma Mode Setting
        self.write_command(0xB9)
        self.write_data(0x20)  # Mono mode

        # Panel Setting
        self.write_command(0xB8)
        self.write_data(0x29)  # 1-Dot inversion, Frame inversion, One Line Interlace

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
        self.write_data(0xFF)  # Auto power down ON

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

    def clear(self):
        self.display_buffer = bytearray(self.DISPLAY_BUFFER_LENGTH)
        self.display()

    def display(self):
        self.address()
        self.dc(1)
        self.cs(0)
        self.spi.write(self.display_buffer)
        self.cs(1)

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

    def write_point(self, x, y, data):
        """写入单个像素点
        x: 0-299 横坐标
        y: 0-399 纵坐标
        data: 0=不显示, 非0=显示
        """
        if x >= self.LCD_WIDTH or y >= self.LCD_HEIGHT or x < 0 or y < 0:
            return

        # 计算实际数据位置
        real_x = x // 2
        real_y = y // 2
        write_byte_index = real_y * self.LCD_DATA_WIDTH + real_x

        # 确保不超出缓冲区范围
        if write_byte_index >= self.DISPLAY_BUFFER_LENGTH:
            return

        # 计算位位置
        one_two = 0 if y % 2 == 0 else 1
        line_bit_1 = (x % 2) * 4
        line_bit_0 = line_bit_1 + 2
        write_bit_1 = 7 - (line_bit_1 + one_two)
        write_bit_0 = 7 - (line_bit_0 + one_two)

        # 对于单色显示，我们将任何非0值都视为显示状态
        # 并将两个位都设置为1以确保最大对比度
        if data:
            # 设置两个位都为1，确保最大显示强度
            self.display_buffer[write_byte_index] |= (1 << write_bit_1) | (1 << write_bit_0)
        else:
            # 清除两个位，确保完全不显示
            self.display_buffer[write_byte_index] &= ~((1 << write_bit_1) | (1 << write_bit_0))

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

    def draw_char(self, x, y, char, color=1):
        """在指定位置绘制一个字符
        color: 0=不显示, 1=显示
        """
        if char not in FONT_8x8:
            return

        # 检查字符是否完全在屏幕范围内
        if x < 0 or x + 8 > self.LCD_WIDTH or y < 0 or y + 8 > self.LCD_HEIGHT:
            return

        font_data = FONT_8x8[char]
        for row in range(8):
            row_data = font_data[row]
            for col in range(8):
                if row_data & (1 << (7 - col)):
                    # 对于单色显示，我们只需要设置像素为显示状态
                    self.write_point(x + col, y + row, 1)

    def draw_string(self, x, y, text, color=1):
        """在指定位置绘制字符串
        color: 0=不显示, 1=显示
        """
        current_x = x
        current_y = y
        char_spacing = 7  # 字符间距

        for char in text:
            # 检查是否需要换行
            if current_x + 8 > self.LCD_WIDTH:
                current_y += 9
                current_x = x
                if current_y + 8 > self.LCD_HEIGHT:
                    break

            if char == '\n':
                current_y += 9
                current_x = x
                continue

            # 绘制字符
            self.draw_char(current_x, current_y, char, color)
            current_x += char_spacing

    def draw_char_scale(self, x, y, char, scale=1, color=1):
        """绘制放大字符"""
        if char not in FONT_8x8:
            return

        # 检查缩放后的字符是否在屏幕范围内
        if x < 0 or x + 8 * scale > self.LCD_WIDTH or y < 0 or y + 8 * scale > self.LCD_HEIGHT:
            return

        font_data = FONT_8x8[char]
        for row in range(8):
            row_data = font_data[row]
            for col in range(8):
                if row_data & (1 << (7 - col)):
                    # 绘制缩放后的像素块
                    for sy in range(scale):
                        for sx in range(scale):
                            px = x + col * scale + sx
                            py = y + row * scale + sy
                            if 0 <= px < self.LCD_WIDTH and 0 <= py < self.LCD_HEIGHT:
                                self.write_point(px, py, color)

    def draw_string_scale(self, x, y, text, scale=1, color=1):
        """绘制放大字符串"""
        current_x = x
        for char in text:
            # 检查是否超出屏幕范围
            if current_x + 8 * scale > self.LCD_WIDTH:
                break
            if char == '\n':
                y += 9 * scale  # 换行，保持适当的行间距
                current_x = x
                continue
            self.draw_char_scale(current_x, y, char, scale, color)
            current_x += 8 * scale  # 根据缩放比例调整字符间距

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

    def draw_circle(self, x0, y0, radius, color=1, fill=False):
        """使用Wu's anti-aliasing circle algorithm绘制圆"""
        def plot(x, y, brightness):
            """绘制带亮度的像素点"""
            # 将亮度映射到0-3的范围
            intensity = min(3, max(0, int(brightness * color)))
            if 0 <= x < self.LCD_WIDTH and 0 <= y < self.LCD_HEIGHT:
                self.write_point(x, y, intensity)

        def draw_circle_points(xc, yc, x, y, alpha):
            """绘制圆的八个对称点及其抗锯齿边缘"""
            plot(xc + x, yc + y, alpha)
            plot(xc - x, yc + y, alpha)
            plot(xc + x, yc - y, alpha)
            plot(xc - x, yc - y, alpha)
            plot(xc + y, yc + x, alpha)
            plot(xc - y, yc + x, alpha)
            plot(xc + y, yc - x, alpha)
            plot(xc - y, yc - x, alpha)

        def fill_between_points(x1, x2, y):
            """填充两点之间的区域"""
            for x in range(x1, x2 + 1):
                if 0 <= x < self.LCD_WIDTH and 0 <= y < self.LCD_HEIGHT:
                    self.write_point(x, y, color)

        x = 0
        y = radius
        alpha = 1.0

        # 使用改进的Xiaolin Wu's算法
        while x <= y:
            if fill:
                # 填充内部
                fill_between_points(x0 - x, x0 + x, y0 + y)
                fill_between_points(x0 - x, x0 + x, y0 - y)
                fill_between_points(x0 - y, x0 + y, y0 + x)
                fill_between_points(x0 - y, x0 + y, y0 - x)
            else:
                # 绘制主要轮廓点
                draw_circle_points(x0, y0, x, y, alpha)

                # 计算下一个像素的位置
                dy = y - 0.5
                dx = x + 1
                d = (dx * dx + dy * dy) ** 0.5 - radius

                # 计算抗锯齿强度
                if d >= 0:
                    alpha = 1 - d
                    y -= 1

                # 绘制抗锯齿边缘点
                if 0 <= alpha < 1:
                    draw_circle_points(x0, y0, x+1, y, 1-alpha)
                    draw_circle_points(x0, y0, x, y-1, alpha)

            x += 1
            if x > y:
                break

            # 更新误差项
            if d >= 0:
                y -= 1

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

