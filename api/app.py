from flask import Flask, render_template, request, redirect, url_for, Response
import os
from werkzeug.utils import secure_filename
import cv2
from datetime import datetime, timedelta
import qrcode
from io import BytesIO
import base64

app = Flask(__name__,
            template_folder="../templates",
            static_folder="../static"
            )

# 配置上传参数
app.config['UPLOAD_FOLDER'] = 'static/uploads'  # 上传文件保存目录
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif'}  # 允许的文件类型
app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024  # 限制文件大小（2MB）

def generate_qr_code(data, version=5, box_size=10, border=4):
    """
    生成二维码图片
    :param data: 要编码的字符串（如"checkwork|id=..."）
    :param version: 二维码复杂度 (1-40)
    :param box_size: 每个小格子的像素数
    :param border: 边框宽度（单位：格子数）
    :return: PIL Image 对象
    """
    qr = qrcode.QRCode(
        version=version,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=box_size,
        border=border,
    )
    qr.add_data(data)
    qr.make(fit=True)
    return qr.make_image(fill_color="black", back_color="white")

def adjust_create_time(original_str):
    try:
        # 拆分原始字符串为各个参数段
        parts = original_str.split('&')

        # 遍历查找并修改createTime参数
        for i in range(len(parts)):
            if parts[i].startswith('createTime='):
                # 提取时间部分
                _, time_value = parts[i].split('=', 1)

                # 解析时间（支持带毫秒的格式）
                dt = datetime.strptime(time_value, "%Y-%m-%dT%H:%M:%S.%f")

                # 时间加1小时（自动处理跨天）
                dt += timedelta(hours=1)

                # 重新格式化（保留3位毫秒）
                new_time = dt.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3]  # 截取前23位

                # 替换原时间参数
                parts[i] = f"createTime={new_time}"
                break

        # 重新组合字符串
        return '&'.join(parts)

    except Exception as e:
        print(f"处理失败: {str(e)}")
        return original_str  # 失败时返回原字符串

def allowed_file(filename):
    """验证文件类型是否合法"""
    return '.' in filename and \
        filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

# 在 upload_file 路由中修改保存后的处理逻辑
def read_qr_code(filepath):
    """读取二维码内容"""
    try:
        img = cv2.imread(filepath)
        detect_obj = cv2.wechat_qrcode_WeChatQRCode()
        res = detect_obj.detectAndDecode(img)
        if res[0]:
            return res[0]  # 返回第一个二维码内容
        return None
    except Exception as e:
        print(f"二维码解析失败: {str(e)}")
        return None


@app.route('/', methods=['GET', 'POST'])
def home():
    if request.method == 'POST':
        # 检查是否有文件被上传
        if 'file' not in request.files:
            return "No file selected"

        file = request.files['file']

        # 验证文件名和类型
        if file.filename == '':
            return "No file selected"
        if not allowed_file(file.filename):
            return "Invalid file type"

        # 安全保存文件
        if file:
            filename = secure_filename(file.filename)
            save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)  # 定义 save_path
            file.save(save_path)  # 保存文件到指定路径

            # 读取二维码内容
            qr_text = read_qr_code(save_path)
            if qr_text:
                return redirect(url_for('show_image', filename=filename, qr_text=qr_text))
            else:
                return "未检测到二维码或读取失败"

    return render_template('index.html')


@app.route('/show/<filename>')
def show_image(filename):
    qr_text = request.args.get('qr_text', '')
    # 获取要生成二维码的字符串（示例参数）
    qr_data = request.args.get('data', adjust_create_time(qr_text))

    try:
        # 生成二维码到内存
        img = generate_qr_code(qr_data)  # 使用之前定义的生成函数

        # 将图片保存到内存缓冲区
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)  # 将指针移回缓冲区开头
        image_data = base64.b64encode(buffer.getvalue()).decode('utf-8')

        # 渲染包含文字和图片的模板
        return render_template('show.html',
                               qr_text=qr_text,
                               adjusted_text=qr_data,
                               image_data=image_data,
                               filename=filename)

    except Exception as e:
        return f"二维码生成失败: {str(e)}", 500

if __name__ == '__main__':
    # 确保上传目录存在
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])
    app.run(debug=True)