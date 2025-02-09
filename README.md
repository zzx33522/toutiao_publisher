# 今日头条草稿自动发布脚本

此脚本用于自动模拟登录今日头条账号，检查草稿箱并自动发布草稿文章。  
脚本主要功能包括：

- **登录与 Cookie 管理**  
  - 尝试加载本地保存的 Cookies（文件名 `toutiao_cookies.pkl`）。  
  - 如果 Cookies 不存在或验证失败，则自动打开登录页面，等待你手动登录，登录成功后保存 Cookies，便于下次自动登录。

- **草稿箱检查**  
  - 自动打开草稿箱页面： [https://mp.toutiao.com/profile_v4/manage/draft](https://mp.toutiao.com/profile_v4/manage/draft)  
  - 通过 XPath `//*[@id="masterRoot"]/div/div[5]/section/main/div[1]/div/div[1]/div/div/div[10]/span/span` 获取包含草稿数量的文本（例如“共 76 条内容”）。  
  - 如果无法从文本中提取数字，则通过查找页面上草稿项（class 包含 `draft-item` 的元素）来计数。

- **自动发布流程**  
  - 点击第一篇草稿的编辑按钮（XPath：`//*[@id="root"]/div/div[3]/div[1]/div[2]/div[2]/a[1]`）。  
  - 新窗口打开后，点击发布按钮（XPath：`//*[@id="root"]/div/div/div/div/div[3]/div/button[2]/span`）。  
  - 等待页面显示“发布成功”或“发布完成”的提示后，关闭当前窗口并返回草稿箱页面。

- **发布频率及限制**  
  - 每次发布后，程序会随机等待 2 到 5 分钟（120~300 秒）。  
  - 每日最多发布 50 篇文章，达到 50 篇后程序自动退出。

- **日志记录**  
  - 运行日志记录在 `publish_log.txt` 中，方便查看脚本运行状态及调试问题。

## 环境要求

- **Python 3.x**（推荐 Python 3.7 及以上）
- 必须安装以下 Python 库：
  - `selenium`
  - `webdriver-manager`

使用以下命令安装依赖：
```bash
pip install selenium webdriver-manager



