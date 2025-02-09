import time
import random
import pickle
import re
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, ElementClickInterceptedException
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

class ToutiaoPublisher:
    def __init__(self):
        self.driver = None
        # 日志文件用于记录程序运行情况
        self.log_file = open("publish_log.txt", "a", encoding="utf-8")
        # 草稿箱页面 URL
        self.draft_url = "https://mp.toutiao.com/profile_v4/manage/draft"
        # 单篇文章发布重试的最大次数
        self.MAX_RETRY = 3
        self.init_driver()

    def log(self, message):
        """记录日志，并在控制台输出（附带时间戳）"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_msg = f"[{timestamp}] {message}"
        print(log_msg)
        self.log_file.write(log_msg + "\n")
        self.log_file.flush()

    def init_driver(self):
        """初始化 Chrome 浏览器驱动"""
        try:
            options = webdriver.ChromeOptions()
            options.add_argument("--start-maximized")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--no-sandbox")
            options.add_argument("--ignore-certificate-errors")
            options.add_argument("--disable-blink-features=AutomationControlled")
            # 设置 User-Agent 模拟真实浏览器
            options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                                 "AppleWebKit/537.36 (KHTML, like Gecko) "
                                 "Chrome/97.0.4692.71 Safari/537.36")
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=options)
            self.driver.set_page_load_timeout(90)
            self.log("浏览器初始化成功")
        except Exception as e:
            self.log(f"驱动初始化失败: {e}")
            raise

    def check_login(self):
        """检查登录状态：登录后页面中会出现包含 'user-info' 的元素"""
        try:
            self.driver.get("https://mp.toutiao.com/profile_v4/")
            WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.CLASS_NAME, "user-info"))
            )
            self.log("登录状态验证成功")
            return True
        except Exception as e:
            self.log(f"登录状态检查失败: {e}")
            return False

    def login(self):
        """登录流程：如果无法加载 Cookies，则打开登录页面让用户手动登录，登录成功后保存 Cookies"""
        self.log("开始登录流程，请手动完成登录")
        self.driver.get("https://mp.toutiao.com/auth/page/login/")
        input("登录完成后，请按回车继续...")
        if self.check_login():
            self.save_cookies()
        else:
            self.log("登录验证失败")
            raise Exception("登录失败")

    def save_cookies(self):
        """将 Cookies 保存到本地文件 toutiao_cookies.pkl 中"""
        try:
            with open("toutiao_cookies.pkl", "wb") as f:
                pickle.dump(self.driver.get_cookies(), f)
            self.log("Cookies已保存")
        except Exception as e:
            self.log(f"保存Cookies失败: {e}")

    def load_cookies(self):
        """加载本地 Cookies 并刷新页面验证登录状态"""
        try:
            self.driver.get("https://mp.toutiao.com/")
            with open("toutiao_cookies.pkl", "rb") as f:
                cookies = pickle.load(f)
            for cookie in cookies:
                if "expiry" in cookie:
                    del cookie["expiry"]
                self.driver.add_cookie(cookie)
            self.driver.refresh()
            if self.check_login():
                self.log("Cookies加载成功")
                return True
            else:
                self.log("Cookies加载后验证失败")
                return False
        except Exception as e:
            self.log(f"加载Cookies失败: {e}")
            return False

    def check_drafts(self):
        """
        检查草稿箱文章数量：
        1. 打开草稿箱页面。
        2. 通过 XPath "//*[@id='masterRoot']/div/div[5]/section/main/div[1]/div/div[1]/div/div/div[10]/span/span"
           获取包含草稿数量的文本（例如“共 76 条内容”）。
        3. 使用正则表达式提取数字。如果提取失败，则尝试通过计数草稿项的数量（包含 draft-item 的元素）来判断数量。
        """
        try:
            self.driver.get(self.draft_url)
            WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.XPATH, '//*[@id="masterRoot"]/div/div[5]/section/main/div[1]/div/div[1]/div/div/div[10]/span/span'))
            )
            text = self.driver.find_element(By.XPATH, '//*[@id="masterRoot"]/div/div[5]/section/main/div[1]/div/div[1]/div/div/div[10]/span/span').text
            self.log(f"草稿箱文本: {text}")
            match = re.search(r'(\d+)', text)
            if match:
                count = int(match.group(1))
                self.log(f"检测到 {count} 篇草稿")
                return count
            else:
                self.log("未能解析草稿数量，从草稿项列表中计数...")
                draft_items = self.driver.find_elements(By.XPATH, "//*[contains(@class, 'draft-item')]")
                count = len(draft_items)
                self.log(f"检测到 {count} 篇草稿（草稿项计数）")
                return count
        except Exception as e:
            self.log(f"草稿检查出错: {e}")
            return 0

    def publish_draft(self):
        """
        发布草稿流程：
        1. 点击第一篇草稿的编辑按钮（XPath: //*[@id="root"]/div/div[3]/div[1]/div[2]/div[2]/a[1]）。
        2. 切换到新窗口后点击发布按钮（XPath: //*[@id="root"]/div/div/div/div/div[3]/div/button[2]/span）。
        3. 等待“发布成功”或“发布完成”的提示出现，然后关闭当前窗口返回草稿箱页面。
        """
        try:
            self.log("开始点击第一篇文章的编辑按钮")
            edit_button = WebDriverWait(self.driver, 20).until(
                EC.element_to_be_clickable((By.XPATH, "//*[@id='root']/div/div[3]/div[1]/div[2]/div[2]/a[1]"))
            )
            edit_button.click()
            self.log("已点击编辑按钮")
            # 等待新窗口打开，并切换到新窗口
            WebDriverWait(self.driver, 15).until(lambda d: len(d.window_handles) > 1)
            self.driver.switch_to.window(self.driver.window_handles[-1])
            self.log("切换到新窗口")
            WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            # 点击发布按钮
            publish_button = WebDriverWait(self.driver, 30).until(
                EC.element_to_be_clickable((By.XPATH, "//*[@id='root']/div/div/div/div/div[3]/div/button[2]/span"))
            )
            publish_button.click()
            self.log("已点击发布按钮")
            # 等待发布成功提示
            WebDriverWait(self.driver, 30).until(
                EC.visibility_of_element_located((By.XPATH, "//*[contains(text(),'发布成功') or contains(text(),'发布完成')]"))
            )
            self.log("发布成功")
            # 关闭当前窗口，并切换回草稿箱页面
            self.driver.close()
            self.driver.switch_to.window(self.driver.window_handles[0])
            return True
        except Exception as e:
            self.log(f"发布失败: {e}")
            if len(self.driver.window_handles) > 1:
                self.driver.close()
                self.driver.switch_to.window(self.driver.window_handles[0])
            return False

    def run(self):
        # 先尝试加载 Cookies，如果验证失败则要求手动登录
        if not self.load_cookies() or not self.check_login():
            self.login()

        daily_limit = 50   # 每日最大发布文章数量
        daily_count = 0    # 当前已发布文章计数

        while True:
            if daily_count >= daily_limit:
                self.log("每日最大发布文章数量已达到 50 篇，程序退出")
                break

            count = self.check_drafts()
            if count <= 0:
                self.log("没有待发布草稿，程序退出")
                break

            if self.publish_draft():
                daily_count += 1
                wait_time = random.randint(120, 300)  # 等待 2 到 5 分钟（120~300 秒）
                self.log(f"已发布 {daily_count} 篇文章，等待 {wait_time} 秒后继续")
                time.sleep(wait_time)
            else:
                self.log("发布失败，稍后重试")
                time.sleep(10)

if __name__ == "__main__":
    publisher = ToutiaoPublisher()
    publisher.run()
