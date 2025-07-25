import requests
import json
import os
from urllib.parse import urlparse
import time
from DrissionPage import ChromiumPage, ChromiumOptions
import re
import tempfile
import shutil
from http.cookiejar import MozillaCookieJar

class DouyinVideoDownloader:
    def __init__(self, download_folder="douyin_videos", cookies_file="cookies.json"):
        self.download_folder = download_folder
        self.cookies_file = cookies_file
        self.session = requests.Session()
        self.setup_session()
        self.load_cookies()
        self.create_download_folder()
        
    def setup_session(self):
        """設置請求頭"""
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'zh-TW,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Referer': 'https://www.douyin.com/',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin',
        })
    
    def load_cookies(self):
        """從 cookies.json 文件載入 cookies"""
        if not os.path.exists(self.cookies_file):
            print(f"未找到 cookies 文件: {self.cookies_file}")
            return
        
        try:
            # 讀取 JSON 格式的 cookies 文件
            with open(self.cookies_file, 'r', encoding='utf-8') as f:
                cookies_list = json.load(f)
            
            cookies_count = 0
            for cookie in cookies_list:
                try:
                    name = cookie.get('name')
                    value = cookie.get('value')
                    domain = cookie.get('domain', '.douyin.com')
                    
                    if name and value:
                        self.session.cookies.set(name, value, domain=domain)
                        cookies_count += 1
                        
                except Exception as cookie_error:
                    print(f"設置單個 cookie 失敗: {cookie.get('name', 'unknown')}, 錯誤: {cookie_error}")
                    continue
            
            print(f"成功載入 {cookies_count} 個 cookies")
            
        except Exception as e:
            print(f"載入 cookies 失敗: {e}")
            import traceback
            traceback.print_exc()
    
    def load_cookies_to_browser(self, page):
        """將 cookies 載入到瀏覽器"""
        if not os.path.exists(self.cookies_file):
            return
        
        try:
            # 先訪問抖音主頁以設置域名
            page.get('https://www.douyin.com')
            time.sleep(2)
            
            # 讀取 JSON 格式的 cookies 文件
            with open(self.cookies_file, 'r', encoding='utf-8') as f:
                cookies_list = json.load(f)
            
            cookies_count = 0
            for cookie in cookies_list:
                try:
                    # 構建 cookie 字典，只使用必要的字段
                    cookie_dict = {
                        'name': cookie.get('name'),
                        'value': cookie.get('value'),
                        'domain': cookie.get('domain', '.douyin.com'),
                        'path': cookie.get('path', '/'),
                        'secure': cookie.get('secure', False),
                        'httpOnly': cookie.get('httpOnly', False)
                    }
                    
                    # 過濾掉無效的 cookies
                    if cookie_dict['name'] and cookie_dict['value']:
                        page.set.cookies(cookie_dict)
                        cookies_count += 1
                        
                except Exception as cookie_error:
                    print(f"設置單個 cookie 失敗: {cookie.get('name', 'unknown')}, 錯誤: {cookie_error}")
                    continue
            
            print(f"成功載入 {cookies_count} 個 cookies 到瀏覽器")
            
        except Exception as e:
            print(f"載入 cookies 到瀏覽器失敗: {e}")
            import traceback
            traceback.print_exc()
    
    def close_popups(self, page):
        """關閉各種彈窗"""
        try:
            # 關閉登入彈窗
            login_panel = page.ele('#douyin-login-new-id')
            if login_panel:
                print("發現登入介面，關閉它...")
                close_btn = page.ele('rect[fill="url(#pattern0_3645_22461)"]') or page.ele('.close') or page.ele('[aria-label="Close"]')
                if close_btn:
                    close_btn.click()
                    time.sleep(1)
                else:
                    print("未找到關閉按鈕")
            
            # 關閉其他可能的彈窗或 alert
            try:
                alert = page.handle_alert(accept=False, timeout=1)
                if alert:
                    print("關閉 alert 彈窗")
            except:
                pass
            
            # 關閉通用的彈窗
            close_buttons = page.eles('.close-btn') + page.eles('.modal-close') + page.eles('[data-testid="close"]')
            for btn in close_buttons:
                try:
                    if btn.is_displayed():
                        btn.click()
                        time.sleep(0.5)
                        print("關閉彈窗")
                except:
                    continue
                    
        except Exception as e:
            print(f"關閉彈窗時出錯: {e}")
    
    def create_download_folder(self):
        """創建下載資料夾"""
        if not os.path.exists(self.download_folder):
            os.makedirs(self.download_folder)
            print(f"已創建下載資料夾: {self.download_folder}")
    
    def extract_sec_user_id(self, user_url):
        """從用戶頁面URL提取sec_user_id"""
        try:
            # 使用正則表達式提取sec_user_id
            match = re.search(r'/user/([^?]+)', user_url)
            if match:
                return match.group(1)
            return None
        except Exception as e:
            print(f"提取sec_user_id失敗: {e}")
            return None
    
    def get_video_list_with_browser(self, user_url):
        """使用瀏覽器獲取視頻列表"""
        user_data_dir = None
        try:
            print("啟動瀏覽器...")
            co = ChromiumOptions()

            # 改為 WSL2 上安裝的 Linux chromium
            chrome_path = '/usr/bin/google-chrome'
            co.set_browser_path(chrome_path)

            # 必要參數
            co.set_argument('--no-sandbox')
            co.set_argument('--disable-dev-shm-usage')
            co.set_argument('--disable-web-security')
            co.set_argument('--disable-features=VizDisplayCompositor')
            co.set_argument('--disable-extensions')
            co.set_argument('--disable-plugins')
            # 移除 --disable-images 以便能看到圖片
            co.set_argument('--disable-setuid-sandbox')
            co.set_argument('--remote-debugging-address=0.0.0.0')
            co.set_argument('--headless=new')

            # 設置用戶數據目錄避免衝突
            user_data_dir = tempfile.mkdtemp()
            co.set_user_data_path(user_data_dir)

            # 自動選擇一個空閒端口並啟用 remote debugging
            co.auto_port(9222)
            co.set_argument(f'--remote-debugging-port={9222}')

            print("正在啟動Chrome瀏覽器...")
            page = ChromiumPage(addr_or_opts=co)
            
            # 載入 cookies 到瀏覽器
            self.load_cookies_to_browser(page)
            
            # 訪問用戶頁面
            print("訪問用戶頁面...")
            page.get(user_url)
            time.sleep(5)  # 等待頁面加載
            
            # 開始監聽所有網絡請求
            print("開始監聽網絡請求...")
            page.listen.start()
            
            # 檢查並關閉各種彈窗
            self.close_popups(page)

            # 滾動頁面載入更多視頻
            print("滾動頁面載入視頻...")
            for i in range(3):
                page.scroll.to_bottom()
                time.sleep(2)
                print(f"滾動 {i+1}/3...")

            # 尋找視頻容器
            video_container_xpath = "/html/body/div[2]/div[1]/div[4]/div[2]/div/div/div/div[3]/div/div/div[2]/div/div[2]"
            video_container = page.ele(f'xpath:{video_container_xpath}')
            
            if not video_container:
                print("未找到視頻容器")
                return None

            # 查找所有 li 元素（每個視頻項目）
            li_elements = video_container.eles('tag:li')
            print(f"找到 {len(li_elements)} 個視頻項目")

            video_urls = []
            video_info_list = []

            # 遍歷每個 li 元素，在其子元素上鼠標懸停觸發視頻加載
            for i, li in enumerate(li_elements):
                try:
                    print(f"處理第 {i+1}/{len(li_elements)} 個視頻項目...")
                    
                    # 滾動到元素可見
                    li.scroll.to_see()
                    time.sleep(1)
                    
                    # 關閉可能出現的彈窗
                    self.close_popups(page)
                    
                    # 清除之前的監聽記錄
                    page.listen.clear()
                    
                    # 查找 li 內的所有子元素
                    child_elements = li.eles('*')  # 所有子元素
                    print(f"在第 {i+1} 個項目中找到 {len(child_elements)} 個子元素")
                    
                    # 遍歷每個子元素進行懸停
                    for j, child in enumerate(child_elements[:5]):  # 限制前5個子元素避免太多
                        try:
                            print(f"鼠標懸停在第 {i+1} 個項目的第 {j+1} 個子元素上...")
                            child.hover()
                            time.sleep(1)  # 縮短等待時間
                            
                        except Exception as child_error:
                            print(f"懸停子元素失敗: {child_error}")
                            continue
                    
                    # 等待一下讓請求觸發
                    time.sleep(2)

                    # 檢查最近的網絡請求（設置超時避免卡住）
                    print(f"檢查第 {i+1} 個項目的網絡請求...")
                    responses = []
                    try:
                        # 使用超時機制獲取響應
                        start_time = time.time()
                        timeout = 5  # 5秒超時
                        
                        while time.time() - start_time < timeout:
                            current_responses = page.listen.steps()
                            if current_responses:
                                responses.extend(current_responses)
                                break
                            time.sleep(0.1)
                        
                    except Exception as listen_error:
                        print(f"監聽請求時出錯: {listen_error}")
                        responses = []
                    
                    # 處理找到的響應
                    found_video = False
                    for response in responses:
                        try:
                            if response.url and any(domain in response.url for domain in ['zjcdn.com', 'bytedance.com', 'douyin.com']):
                                if ('video' in response.url and response.url.endswith(('.mp4', '.mov'))) or 'mime_type=video_mp4' in response.url:
                                    if response.url not in video_urls:
                                        video_urls.append(response.url)
                                        print(f"✓ 找到視頻 URL: {response.url[:100]}...")
                                        
                                        # 嘗試獲取視頻標題
                                        try:
                                            # 查找 li 元素中的標題
                                            title_elements = li.eles('tag:p') + li.eles('tag:span') + li.eles('[class*="title"]')
                                            title = None
                                            for title_elem in title_elements:
                                                if title_elem.text and len(title_elem.text.strip()) > 0:
                                                    title = title_elem.text.strip()
                                                    break
                                            
                                            if not title:
                                                title = f"video_{i+1}"
                                            
                                            # 清理文件名
                                            safe_title = re.sub(r'[<>:"/\\|?*]', '_', title)[:50]
                                            
                                            video_info_list.append({
                                                'url': response.url,
                                                'title': safe_title,
                                                'index': i+1
                                            })
                                            found_video = True
                                            break
                                            
                                        except Exception as e:
                                            print(f"獲取標題失敗: {e}")
                                            video_info_list.append({
                                                'url': response.url,
                                                'title': f"video_{i+1}",
                                                'index': i+1
                                            })
                                            found_video = True
                                            break
                        except Exception as response_error:
                            print(f"處理響應時出錯: {response_error}")
                            continue
                    
                    if not found_video:
                        print(f"第 {i+1} 個項目未找到視頻 URL")

                    # 移動鼠標離開，避免干擾下一個
                    try:
                        page.actions.move_to((100, 100)).perform()
                    except:
                        pass
                    time.sleep(1)

                except Exception as e:
                    print(f"處理第 {i+1} 個項目時出錯: {e}")
                    continue

            print(f"總共找到 {len(video_urls)} 個視頻 URL")
            
            if video_info_list:
                # 直接下載視頻
                self.download_videos_from_urls(video_info_list)
                return True
            else:
                print("未找到任何視頻 URL")
                return None
                    
        except Exception as e:
            print(f"瀏覽器獲取數據失敗: {e}")
            import traceback
            traceback.print_exc()
            return None
        finally:
            try:
                page.quit()
            except:
                pass
            # 清理臨時目錄
            if user_data_dir:
                try:
                    shutil.rmtree(user_data_dir, ignore_errors=True)
                except:
                    pass
    
    def fetch_video_list(self, api_url):
        """使用API獲取視頻列表"""
        try:
            print("正在獲取視頻列表...")
            
            # 添加必要的cookies和headers
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36',
                'Accept': 'application/json, text/plain, */*',
                'Accept-Language': 'zh-TW,zh;q=0.9,en;q=0.8',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Referer': 'https://www.douyin.com/',
                'Sec-Fetch-Dest': 'empty',
                'Sec-Fetch-Mode': 'cors',
                'Sec-Fetch-Site': 'same-origin',
                'sec-ch-ua': '"Not_A Brand";v="8", "Chromium";v="138", "Google Chrome";v="138"',
                'sec-ch-ua-mobile': '?0',
                'sec-ch-ua-platform': '"Windows"',
            }
            
            response = self.session.get(api_url, headers=headers)
            
            print(f"HTTP狀態碼: {response.status_code}")
            print(f"響應頭: {dict(response.headers)}")
            print(f"響應內容前500字符: {response.text[:500]}")
            
            if response.status_code == 200:
                if response.text.strip():
                    try:
                        data = response.json()
                        if 'aweme_list' in data:
                            print(f"成功獲取 {len(data['aweme_list'])} 個視頻")
                            return data['aweme_list']
                        else:
                            print("響應中未找到aweme_list")
                            print(f"可用的鍵: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}")
                            return None
                    except json.JSONDecodeError as e:
                        print(f"JSON解析失敗: {e}")
                        print(f"響應內容: {response.text}")
                        return None
                else:
                    print("響應為空")
                    return None
            else:
                print(f"請求失敗，狀態碼: {response.status_code}")
                print(f"響應內容: {response.text}")
                return None
                
        except Exception as e:
            print(f"獲取視頻列表失敗: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def download_videos_from_urls(self, video_info_list):
        """從視頻 URL 列表下載視頻"""
        print(f"開始下載 {len(video_info_list)} 個視頻...")
        
        success_count = 0
        for i, video_info in enumerate(video_info_list):
            try:
                video_url = video_info['url']
                title = video_info['title']
                index = video_info['index']
                
                # 構建文件名
                filename = f"{index:03d}_{title}.mp4"
                
                print(f"正在下載第 {i+1}/{len(video_info_list)} 個視頻: {filename}")
                
                # 設置下載用的請求頭
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36',
                    'Referer': 'https://www.douyin.com/',
                    'Accept': '*/*',
                    'Accept-Language': 'zh-TW,zh;q=0.9,en;q=0.8',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'Connection': 'keep-alive',
                }
                
                # 使用 session 下載視頻
                response = self.session.get(video_url, headers=headers, stream=True)
                
                if response.status_code == 200:
                    filepath = os.path.join(self.download_folder, filename)
                    
                    # 獲取文件大小
                    total_size = int(response.headers.get('content-length', 0))
                    downloaded_size = 0
                    
                    with open(filepath, 'wb') as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            if chunk:
                                f.write(chunk)
                                downloaded_size += len(chunk)
                                
                                # 顯示下載進度
                                if total_size > 0:
                                    progress = (downloaded_size / total_size) * 100
                                    print(f"\r下載進度: {progress:.1f}%", end='', flush=True)
                    
                    print(f"\n✓ 下載完成: {filename}")
                    success_count += 1
                else:
                    print(f"✗ 下載失敗: {filename}, 狀態碼: {response.status_code}")
                    
            except Exception as e:
                print(f"✗ 下載失敗: {filename}, 錯誤: {e}")
                continue
                
            # 添加延遲避免請求過快
            time.sleep(2)
        
        print(f"\n下載完成！成功: {success_count}/{len(video_info_list)}")
    
    def download_video(self, video_url, filename):
        """下載單個視頻"""
        try:
            print(f"正在下載: {filename}")
            
            # 設置下載用的請求頭
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36',
                'Referer': 'https://www.douyin.com/',
            }
            
            response = self.session.get(video_url, headers=headers, stream=True)
            
            if response.status_code == 200:
                filepath = os.path.join(self.download_folder, filename)
                
                with open(filepath, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                
                print(f"✓ 下載完成: {filename}")
                return True
            else:
                print(f"✗ 下載失敗: {filename}, 狀態碼: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"✗ 下載失敗: {filename}, 錯誤: {e}")
            return False    
    
    def extract_video_info(self, aweme_item):
        """提取視頻信息"""
        try:
            # 獲取視頻描述
            desc = aweme_item.get('desc', '無標題')
            
            # 清理文件名
            safe_desc = re.sub(r'[<>:"/\\|?*]', '_', desc)[:50]
            
            # 獲取視頻ID
            aweme_id = aweme_item.get('aweme_id', 'unknown')
            
            # 獲取視頻URL
            video_urls = []
            video_info = aweme_item.get('video', {})
            
            # 嘗試獲取play_addr中的url_list
            play_addr = video_info.get('play_addr', {})
            if 'url_list' in play_addr:
                video_urls.extend(play_addr['url_list'])
            
            # 如果沒有找到，嘗試其他位置
            if not video_urls:
                bit_rate = video_info.get('bit_rate', [])
                if bit_rate:
                    play_addr = bit_rate[0].get('play_addr', {})
                    if 'url_list' in play_addr:
                        video_urls.extend(play_addr['url_list'])
            
            return {
                'id': aweme_id,
                'desc': safe_desc,
                'urls': video_urls
            }
            
        except Exception as e:
            print(f"提取視頻信息失敗: {e}")
            return None
    
    def process_video_list(self, aweme_list):
        """處理視頻列表並下載"""
        if not aweme_list:
            print("沒有找到視頻列表")
            return
        
        print(f"開始處理 {len(aweme_list)} 個視頻...")
        
        success_count = 0
        for i, aweme_item in enumerate(aweme_list):
            video_info = self.extract_video_info(aweme_item)
            
            if video_info and video_info['urls']:
                # 使用第一個可用的URL
                video_url = video_info['urls'][0]
                filename = f"{video_info['id']}_{video_info['desc']}.mp4"
                
                if self.download_video(video_url, filename):
                    success_count += 1
                
                # 添加延遲避免請求過快
                time.sleep(1)
            else:
                print(f"✗ 無法提取視頻信息: {i+1}")
        
        print(f"\n下載完成！成功: {success_count}/{len(aweme_list)}")
    
    def run(self, user_url, api_url=None):
        """主要運行函數"""
        print("=== 抖音視頻下載器 ===")
        print(f"用戶頁面: {user_url}")
        
        # 由於API URL可能已過期，直接使用瀏覽器獲取數據
        print("使用瀏覽器獲取數據...")
        aweme_list = self.get_video_list_with_browser(user_url)
        
        if aweme_list:
            self.process_video_list(aweme_list)
        else:
            print("無法獲取視頻數據")

def main():
    # 用戶URL
    user_url = "https://www.douyin.com/user/MS4wLjABAAAAhGTvofJSpb_dRb51A_xGF5siEeiHB2ryBSRZ9V0NtM7C-UgZ9ACJLTO7HwEGnFSE?from_tab_name=main"
    
    # 創建下載器實例
    downloader = DouyinVideoDownloader()
    
    # 運行下載器
    downloader.run(user_url)

if __name__ == "__main__":
    main()