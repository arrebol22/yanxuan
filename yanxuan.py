import os
import time
import requests
from bs4 import BeautifulSoup
import re
import base64
from fontTools.ttLib import TTFont
import ddddocr
from PIL import ImageFont, Image, ImageDraw
import argparse

class FontDecoder:
    def __init__(self, headers, cookies_raw):
        self.headers = headers
        self.cookies_dict = self._parse_cookies(cookies_raw)
        self.ocr_engine = ddddocr.DdddOcr()
        self.session = requests.Session()
        self.session.headers.update(headers)
        self.session.cookies.update(self.cookies_dict)

    @staticmethod
    def _parse_cookies(cookies_raw):
        # 解析原始Cookie字符串为字典
        return {cookie.split('=')[0]: '='.join(cookie.split('=')[1:]) for cookie in cookies_raw.split('; ')}

    def fetch_content(self, url):
        # 获取网页内容并解析
        response = self.session.get(url)
        response.raise_for_status()
        time.sleep(2)
        soup = BeautifulSoup(response.text, 'html.parser')
        return soup, response.text

    def save_content(self, soup, title, folder_path, file_type='txt'):
        # 保存网页内容到本地文件
        filename = f"{title}.{file_type}"
        full_path = os.path.join(folder_path, filename)
        if file_type == 'html':
            content = str(soup)
        else:
            content = '\n'.join(tag.get_text() for tag in soup.find_all('p'))
        with open(full_path, 'w', encoding='utf-8') as file:
            file.write(content)

    def recognize_font(self, font_path):
        # 识别字体文件，生成字符映射字典
        with open(font_path, 'rb') as f:
            font = TTFont(f)
            cmap = font.getBestCmap()
            unicode_list = list(cmap.keys())

        recognition_dict = {}
        failed_recognitions = []

        for unicode_code in unicode_list:
            char = chr(unicode_code)
            img_size = 128
            img = Image.new('RGB', (img_size, img_size), 'white')
            draw = ImageDraw.Draw(img)
            font_size = int(img_size * 0.7)
            font = ImageFont.truetype(font_path, font_size)
            text_width, text_height = draw.textsize(char, font=font)
            draw.text(((img_size - text_width) / 2, (img_size - text_height) / 2), char, fill='black', font=font)
            try:
                recognized_text = self.ocr_engine.classification(img)
                if recognized_text:
                    recognition_dict[char] = recognized_text[0]
                else:
                    failed_recognitions.append(char)
            except Exception:
                failed_recognitions.append(char)

        # 输出识别结果统计
        if failed_recognitions:
            print(f"[字体识别] 未识别字符数: {len(failed_recognitions)}")
        else:
            print("[字体识别] 所有字符识别成功")
        print(f"[字体识别] 映射字典长度: {len(recognition_dict)}")
        return recognition_dict

    def convert_dialogue(self, text, use_punct_replace=False):
        # 对话格式转换及特殊符号替换
        pattern = r'广(.*?)上'
        def replace(match):
            content = match.group(1)
            return f'「{content}」'
        converted_text = re.sub(pattern, replace, text)
        if use_punct_replace:
            # 替换 "o" 为 "。"
            converted_text = converted_text.replace('o', '。')
            # 替换 "I" 为 "！"
            converted_text = converted_text.replace('I', '！')
        return converted_text

    def replace_string_matches(self, input_str, mapping_dict):
        # 用映射字典还原乱码文本
        pattern = re.compile("|".join(re.escape(key) for key in mapping_dict.keys()))
        def replace_callback(match):
            key = match.group(0)
            return mapping_dict[key]
        output_str = pattern.sub(replace_callback, input_str)
        return output_str

    def my_replace_text(self, input_file, output_file, replace_dict, folder_path, use_punct_replace=False):
        # 还原文本并保存，删除原文件
        input_path = os.path.join(folder_path, input_file)
        output_path = os.path.join(folder_path, output_file)
        with open(input_path, 'r', encoding='utf-8') as f:
            content = f.read()
            content = self.replace_string_matches(content, replace_dict)
            content = self.convert_dialogue(content, use_punct_replace=use_punct_replace)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"[文本处理] 已保存还原结果: {output_path}")
        os.remove(input_path)
        print(f"[清理] 已删除原文件: {input_path}")


def get_firstsession(url, i, folder_path, decoder, use_punct_replace=False):
    # 抓取单节内容，自动识别字体并还原文本
    try:
        soup, text_response = decoder.fetch_content(url)
    except requests.exceptions.HTTPError as err:
        print(f"[网络] HTTP错误: {err}")
        return None
    except requests.exceptions.RequestException as err:
        print(f"[网络] 请求错误: {err}")
        return None

    title_tag = soup.find('h1')
    title = title_tag.text if title_tag else "未找到标题"
    decoder.save_content(soup, title, folder_path, file_type='txt')

    pattern = r"@font-face\s*\{[^\}]*?src:\s*url\(data:font/ttf;charset=utf-8;base64,([A-Za-z0-9+/=]+)\)"
    matches = re.findall(pattern, text_response)
    font_found = False
    for idx, base64_font_data in enumerate(matches):
        try:
            decoded_font_data = base64.b64decode(base64_font_data)
            font_file_path = f"/tmp/font_file_{idx}.ttf"
            with open(font_file_path, "wb") as font_file:
                font_file.write(decoded_font_data)
            mapping_dict = decoder.recognize_font(font_file_path)
            if mapping_dict and len(set(mapping_dict.values())) >= 10:
                input_file = f'{title}.txt'
                output_file = f'第{i}节{title}.txt'
                decoder.my_replace_text(input_file, output_file, mapping_dict, folder_path, use_punct_replace=use_punct_replace)
                font_found = True
                os.remove(font_file_path)
                break
            os.remove(font_file_path)
        except Exception as e:
            print(f"[字体识别] 失败: {e}")
    if not font_found:
        print("[字体识别] 未能识别有效字体，未进行文本还原。")
    url_pattern = re.compile(r'"next_section":{[^}]*"url":"(https?://[^"]+)"')
    match = url_pattern.search(text_response)
    if match:
        url = match.group(1)
        print(f"[章节] 下一节链接: {url}")
        return url
    else:
        print("[章节] 未找到下一节URL。")
        return None

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='知乎盐选批量下载脚本')
    parser.add_argument('--auto', action='store_true', help='自动下载所有章节')
    parser.add_argument('--punct', action='store_true', help='是否进行 o/I 标点替换')
    parser.add_argument('url', type=str, help='第一节链接')
    args = parser.parse_args()

    folder_path = os.path.join(os.getcwd(), 'download')
    firstsession_url = args.url
    auto_download = args.auto
    use_punct_replace = args.punct

    cookies_file = os.path.join(os.getcwd(), 'cookies.txt')
    if not os.path.exists(cookies_file):
        with open(cookies_file, 'w', encoding='utf-8') as f:
            f.write('')
        print('[配置] 未检测到 cookies.txt 文件，已自动创建。请将你的 cookies 字符串写入 cookies.txt 后重新运行程序。')
        exit(1)
    with open(cookies_file, 'r', encoding='utf-8') as f:
        cookies = f.read().strip()
        if not cookies:
            print('[配置] cookies.txt 文件为空，请将你的 cookies 字符串写入 cookies.txt 后重新运行程序。')
            exit(1)

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
        'Accept-Language': 'zh-CN,zh;q=0.9',
    }

    decoder = FontDecoder(headers, cookies)

    try:
        os.makedirs(folder_path, exist_ok=True)
        print(f"[配置] 下载目录已准备: {folder_path}")
    except Exception as e:
        print(f"[配置] 创建下载目录失败: {e}")

    i = 1
    next_url = get_firstsession(firstsession_url, i, folder_path, decoder, use_punct_replace=use_punct_replace)
    if auto_download:
        while next_url:
            i += 1
            time.sleep(5)
            next_url = get_firstsession(next_url, i, folder_path, decoder, use_punct_replace=use_punct_replace)
