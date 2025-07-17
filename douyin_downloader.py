import requests
import json
import os
from urllib.parse import urlparse
import time
from DrissionPage import ChromiumPage, ChromiumOptions
import re
import tempfile
import shutil

class DouyinVideoDownloader:
    def __init__(self, download_folder="douyin_videos"):
        self.download_folder = download_folder
        self.session = requests.Session()
        self.setup_session()
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
            # co.set_argument('--disable-gpu')
            co.set_argument('--disable-web-security')
            co.set_argument('--disable-features=VizDisplayCompositor')
            co.set_argument('--disable-extensions')
            co.set_argument('--disable-plugins')
            co.set_argument('--disable-images')
            # 這兩行新增：
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
            
            # 訪問用戶頁面
            print("訪問用戶頁面...")
            page.get(user_url)
            time.sleep(5)  # 等待頁面加載
            
            # 開始監聽所有網絡請求
            print("開始監聽網絡請求...")
            page.listen.start()
            
            # 檢查新的登入介面
            login_panel = page.ele('#douyin-login-new-id')
            if login_panel:
                print("發現登入介面，關閉它...")
                # 點擊對應的關閉按鈕 (svg rect)
                close_btn = page.ele('rect[fill="url(#pattern0_3645_22461)"]')
                if close_btn:
                    close_btn.click()
                    time.sleep(2)
                else:
                    print("未找到關閉按鈕")

            # 滾動頁面以觸發視頻列表的加載
            print("滾動頁面觸發請求...")
            for i in range(5):  # 增加滾動次數
                page.scroll.to_bottom()
                time.sleep(2)
                print(f"滾動 {i+1}/5...")
            
            # 等待並獲取包含aweme的請求
            print("等待API響應...")
            timeout = 30
            start_time = time.time()
            found_responses = []
            
            while time.time() - start_time < timeout:
                # 獲取所有響應
                responses = page.listen.steps()
                
                for response in responses:
                    if response.url and 'aweme' in response.url:
                        found_responses.append(response.url)
                        print(f"找到響應: {response.url[:100]}...")
                        
                        if 'post' in response.url:
                            print(f"找到aweme API請求: {response.url[:100]}...")
                            try:
                                data = response.response.body
                                if data:
                                    # 嘗試解析為JSON
                                    if isinstance(data, str):
                                        json_data = json.loads(data)
                                    else:
                                        json_data = data
                                    
                                    if 'aweme_list' in json_data:
                                        print(f"成功獲取 {len(json_data['aweme_list'])} 個視頻")
                                        return json_data['aweme_list']
                            except Exception as e:
                                print(f"解析響應失敗: {e}")
                                continue
                
                time.sleep(1)
            
            print(f"未找到包含aweme_list的響應")
            print(f"找到的響應: {found_responses}")
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
    
    def download_video(self, video_url, filename):
        """下載視頻"""
        try:
            print(f"正在下載: {filename}")
            
            # 設置下載用的請求頭
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36',
                'Referer': 'https://www.douyin.com/',
            }
            
            response = requests.get(video_url, headers=headers, stream=True)
            
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