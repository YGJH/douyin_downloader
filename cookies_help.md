# 如何獲取和使用 Cookies

## 方法一：從瀏覽器獲取 cookies（推薦）

1. 在瀏覽器中打開 https://www.douyin.com 並登入您的帳號
2. 按 F12 打開開發者工具
3. 切換到 "Application" 或"應用程式" 標籤
4. 在左側選擇 "Storage" -> "Cookies" -> "https://www.douyin.com"
5. 複製重要的 cookies（特別是包含 session、token 等的）

## 方法二：使用瀏覽器擴展（簡單）

1. 安裝 "Get cookies.txt" 或類似的擴展
2. 訪問 https://www.douyin.com 並登入
3. 點擊擴展圖標導出 cookies

## cookies.txt 格式

### 簡單格式（推薦）：
```
sessionid=你的session值
passport_csrf_token=你的csrf_token值
tt_webid=你的webid值
ttwid=你的ttwid值
```

### Netscape 格式：
```
# Netscape HTTP Cookie File
.douyin.com	TRUE	/	FALSE	1234567890	sessionid	你的session值
.douyin.com	TRUE	/	FALSE	1234567890	passport_csrf_token	你的csrf_token值
```

## 重要的 cookies 包括：
- sessionid
- passport_csrf_token
- tt_webid
- ttwid
- odin_tt
- passport_assist_user

將這些值替換到 cookies.txt 文件中，然後重新運行程式。
