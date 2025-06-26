# YouTube 播放清單音頻下載器

一個專業的 Python 工具，用於下載 YouTube 播放清單中的所有影片並轉換為高品質音頻檔案。支援 WAV 無損格式和 MP3 高品質格式，具備完整的錯誤處理和進度顯示功能。

## ✨ 主要功能

- 🎵 **高品質音頻下載**：優先使用 WAV 無損格式，失敗時自動回退到 320kbps MP3
- 📋 **播放清單支援**：完整下載 YouTube 播放清單或指定範圍
- 🎬 **單影片下載**：支援下載單個 YouTube 影片
- 📊 **智慧檔案管理**：自動檢測已存在檔案，避免重複下載
- 📝 **詳細日誌記錄**：完整的下載日誌和錯誤追蹤
- 🔄 **進度顯示**：即時顯示下載進度和速度
- 🛡️ **錯誤處理**：優雅處理下載失敗，記錄詳細錯誤資訊
- 📁 **自動分類**：按播放清單自動創建資料夾結構

## 🔧 安裝需求

### 必要套件

```bash
pip install yt-dlp
```

### 系統需求

- Python 3.7 或更高版本
- FFmpeg（用於音頻轉換）

#### 安裝 FFmpeg

**Windows：**
1. 從 [FFmpeg 官網](https://ffmpeg.org/download.html) 下載 Windows 版本
2. 解壓縮並將 `bin` 資料夾加入系統 PATH

**macOS：**
```bash
brew install ffmpeg
```

**Ubuntu/Debian：**
```bash
sudo apt update
sudo apt install ffmpeg
```

## 🚀 使用方法

### 基本使用

```bash
python youtube_downloader.py
```

執行後程式會提示您輸入 YouTube 播放清單 URL。

### 命令列參數

```bash
python youtube_downloader.py "https://www.youtube.com/playlist?list=YOUR_PLAYLIST_ID"
```

### 互動式使用

1. **輸入播放清單 URL**：程式會自動識別播放清單
2. **選擇下載範圍**：
   - 開始編號（預設為 1）
   - 結束編號（留空下載全部）

### 使用示例

```
請輸入 YouTube 播放清單 URL: https://www.youtube.com/playlist?list=PLxxxxx
開始下載的影片編號 (預設為 1): 5
結束下載的影片編號 (按 Enter 下載全部): 10
```

這將下載播放清單中第 5 到第 10 個影片。

## 📁 檔案結構

```
audio/歌/播放清單/
├── [播放清單名稱]/
│   ├── 01 - 第一首歌.wav
│   ├── 02 - 第二首歌.wav
│   └── ...
└── logs/
    ├── download_log_20231225_120000.log
    ├── failed_downloads_20231225_120000.json
    └── format_attempts_20231225_120000.json
```

## 🎵 音頻格式說明

### WAV 格式（優先）
- **品質**：無損音質
- **檔案大小**：較大
- **相容性**：優秀
- **適用場景**：音樂製作、高品質收藏

### MP3 格式（回退）
- **品質**：320kbps 高品質
- **檔案大小**：較小
- **相容性**：優秀
- **適用場景**：日常聆聽、儲存空間有限

## 📊 功能特色

### 智慧檔案檢測
- 自動檢測已下載的檔案
- 支援多種音頻格式檢測
- 避免重複下載節省時間

### 格式回退機制
```
WAV 下載嘗試 → 失敗 → 自動嘗試 MP3 → 成功/失敗記錄
```

### 詳細進度顯示
```
🔄 下載中 [3/10] 45.2% | 2.1 MB/s | ETA: 15s
✅ 下載完成: 03 - 歌曲名稱.wav
🔄 轉換為 WAV 格式中...
```

## 🔧 自訂設定

### 修改輸出路徑
```python
# 在 main() 函數中修改
output_dir = r"C:\your\custom\path"
downloader = YouTubePlaylistDownloader(output_dir)
```

### 調整音質設定
```python
# 在 ydl_opts 中修改
'audioquality': '0',  # 0 = 最高品質, 9 = 最低品質
'preferredquality': '320',  # MP3 位元率
```

## 📝 日誌系統

### 日誌檔案類型

1. **下載日誌** (`download_log_*.log`)
   - 完整的下載過程記錄
   - 成功/失敗狀態
   - 時間戳記和詳細資訊

2. **失敗記錄** (`failed_downloads_*.json`)
   ```json
   [
     {
       "index": 5,
       "title": "影片標題",
       "url": "https://youtube.com/watch?v=...",
       "error": "錯誤訊息",
       "timestamp": "2023-12-25T12:00:00"
     }
   ]
   ```

3. **格式嘗試記錄** (`format_attempts_*.json`)
   - WAV/MP3 格式嘗試結果
   - 失敗原因分析

## ⚠️ 常見問題

### Q: 下載速度很慢？
A: 這通常是由於：
- 網路連線品質
- YouTube 伺服器限制
- 音頻轉換時間

### Q: 部分影片下載失敗？
A: 可能原因：
- 影片被設為私人或刪除
- 地區限制
- 版權保護

檢查 `logs` 資料夾中的失敗記錄以獲得詳細資訊。

### Q: FFmpeg 相關錯誤？
A: 確保：
- FFmpeg 已正確安裝
- FFmpeg 在系統 PATH 中
- 有足夠的磁碟空間

### Q: 檔名包含特殊字元？
A: 程式會自動：
- 替換不合法字元為底線
- 限制檔名長度
- 保持可讀性

## 🛠️ 技術細節

### 相依套件
- `yt-dlp`：YouTube 下載核心
- `pathlib`：路徑處理
- `logging`：日誌系統
- `json`：資料存儲
- `urllib.parse`：URL 解析

### 系統需求
- **記憶體**：建議 2GB 以上
- **儲存空間**：根據播放清單大小而定
- **網路**：穩定的網際網路連線

## 📄 授權

此專案採用 MIT 授權條款。

## 🤝 貢獻

歡迎提交 Issue 和 Pull Request！

## ⚡ 效能優化

- 使用多線程進行 FFmpeg 轉換
- 智慧檔案檢測避免重複下載
- 優化的 yt-dlp 設定減少網路請求

## 🔄 版本更新

### v1.0.0
- 初始版本發布
- 支援 WAV/MP3 雙格式
- 完整的錯誤處理機制
- 智慧檔案管理系統

---

💡 **提示**：首次使用建議先測試少量影片，確認所有依賴項目都正確安裝。
