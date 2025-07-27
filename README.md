# 知乎盐选小说批量下载与还原工具

## 功能
- 自动处理字体反爬，识别并还原乱码文本。
- 批量下载知乎盐选小说，自动识别章节链接。
- 支持还原原文标点（可选“o”→“。”、“I”→“！”）。

## 实现原理
知乎盐选内容采用自定义字体混淆反爬。  
工具会自动解析网页中的字体文件，利用 OCR 技术识别每个字体字形对应的真实汉字，生成映射关系，从而将乱码文本还原为正常可读内容。

## 使用方法
### 1. 安装依赖
```bash
pip install -r requirements.txt
```

### 2. 准备 cookies
将浏览器登录知乎后获取的 cookies 字符串完整粘贴到 `cookies.txt` 文件中。

### 3. 运行脚本
```bash
python yanxuan.py <第一节链接> [--auto] [--punct]
```
- `<第一节链接>`：小说第一节的网页链接（必填）。
- `--auto`：自动下载全部章节。
- `--punct`：自动恢复标点（将“o”替换为“。”、“I”替换为“！”）。

下载结果会保存在 `download/` 文件夹下。

### 4. 示例
-   ```bash
    python yanxuan.py "https://www.zhihu.com/question/114514/answer/1919810"
    ```
-   ```bash
    python yanxuan.py "https://www.zhihu.com/xen/market/remix/paid_column/1145141919810" --auto --punct
    ```

## 致谢
本项目基于 [moran69/yanxuan](https://github.com/moran69/yanxuan) 仓库的原始实现，感谢原作者的开源贡献。

## 免责声明
- 本工具仅供学习与技术交流，请勿用于任何商业或非法用途。
- 使用本工具下载的内容仅限个人保存和阅读，严禁传播、公开或用于其他用途。
- 如因使用本工具造成的任何法律责任，均由使用者自行承担，作者不负任何责任。

---
如有问题或建议，欢迎 issue 反馈。
