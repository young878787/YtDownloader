#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YouTube 播放清單音頻下載器
下載 YouTube 播放清單中的所有影片並轉換為高品質音頻檔案
專注於音頻下載、錯誤日誌記錄和進度顯示
"""

import os
import sys
import re
import json
import logging
import warnings
from datetime import datetime
from pathlib import Path

# 抑制所有警告
warnings.filterwarnings('ignore')
os.environ['PYTHONWARNINGS'] = 'ignore'
import yt_dlp
from urllib.parse import urlparse, parse_qs

class YouTubePlaylistDownloader:
    def __init__(self, output_dir=None):
        """
        初始化下載器
        
        Args:
            output_dir (str): 輸出資料夾路徑，預設為 audio/歌/播放清單
        """
        if output_dir is None:
            self.output_dir = Path(__file__).parent / "audio" / "歌" / "播放清單"
        else:
            self.output_dir = Path(output_dir)
          # 確保輸出資料夾存在
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # 設定日誌
        self.setup_logging()
        
        # 追蹤失敗的影片
        self.failed_downloads = []
        self.current_video_info = None
        self.download_count = 0
        self.total_count = 0
        
        # 追蹤音頻格式嘗試
        self.current_format = 'wav'
        self.format_attempts = []
        
        # 設定 yt-dlp 選項 - 優先 WAV，失敗時回退到 MP3
        self.ydl_opts = {
            'format': 'bestaudio[ext=m4a]/bestaudio[ext=webm]/bestaudio/best',  # 下載最佳音質
            'outtmpl': str(self.output_dir / '%(playlist_index)02d - %(title)s.%(ext)s'),
            'extractaudio': True,
            'audioformat': 'wav',  # 優先使用 WAV 格式 (無損)
            'audioquality': '0',   # 最高音質 
            'ignoreerrors': True,  # 忽略錯誤繼續下載
            'no_warnings': True,   # 減少警告訊息
            'quiet': True,         # 靜默模式
            'noprogress': False,   # 允許進度顯示
            'writeinfojson': False,  # 不保存影片資訊
            'writethumbnail': False,  # 不下載縮圖
            'writesubtitles': False,  # 不下載字幕
            'writeautomaticsub': False,  # 不下載自動字幕
            'extractor_args': {
                'youtube': {
                    'player_client': ['android'],  # 只使用 android 客戶端減少警告
                    'skip': ['dash', 'hls']
                }
            },
            'postprocessors': [
                {
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'wav',
                    'preferredquality': '0',  # WAV 無損品質
                },
                {
                    'key': 'FFmpegMetadata',
                    'add_metadata': True,
                },
            ],            'postprocessor_args': {
                'ffmpeg': ['-threads', '0']  # 使用所有可用 CPU 線程
            },
            'logger': self.get_logger(),
            'progress_hooks': [self.progress_hook],
        }
    
    def setup_logging(self):
        """設定日誌系統"""
        log_dir = self.output_dir / "logs"
        log_dir.mkdir(exist_ok=True)
        
        # 創建日誌檔案名稱（包含時間戳）
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = log_dir / f"download_log_{timestamp}.log"
        # 設定日誌格式
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file, encoding='utf-8'),
                logging.StreamHandler(sys.stdout)
            ],
            force=True
        )
        
        self.logger = logging.getLogger(__name__)
        # 抑制所有可能的 yt-dlp 相關警告訊息
        loggers_to_suppress = [
            'yt_dlp', 'yt_dlp.utils', 'yt_dlp.extractor', 'yt_dlp.downloader',
            'yt_dlp.postprocessor', 'yt_dlp.extractor.youtube', 'yt_dlp.extractor.common'
        ]
        for logger_name in loggers_to_suppress:
            logging.getLogger(logger_name).setLevel(logging.ERROR)
            logging.getLogger(logger_name).disabled = True
        
        self.logger.info("=" * 50)
        self.logger.info("YouTube 播放清單音頻下載器啟動")
        self.logger.info("=" * 50)
    
    def get_logger(self):
        """返回 yt-dlp 使用的日誌記錄器"""
        return self.logger
    
    def progress_hook(self, d):
        """進度回調函數"""
        if d['status'] == 'downloading':
            if 'total_bytes' in d:
                percent = d['downloaded_bytes'] / d['total_bytes'] * 100
                speed = d.get('speed', 0)
                if speed:
                    speed_mb = speed / (1024 * 1024)
                    eta = d.get('eta', 0)
                    progress_info = f"[{self.download_count}/{self.total_count}] {percent:.1f}% | {speed_mb:.1f} MB/s | ETA: {eta}s"
                else:
                    progress_info = f"[{self.download_count}/{self.total_count}] {percent:.1f}%"
                print(f"\r🔄 下載中 {progress_info}", end='', flush=True)
            else:
                print(f"\r🔄 [{self.download_count}/{self.total_count}] 下載中...", end='', flush=True)
        elif d['status'] == 'finished':
            filename = os.path.basename(d['filename'])
            print(f"\n✅ 下載完成: {filename}")
            print(f"🔄 轉換為 {self.current_format.upper()} 格式中...")
            self.logger.info(f"下載完成，開始轉換: {filename}")
        elif d['status'] == 'error':
            filename = d.get('filename', '未知檔案')
            print(f"\n❌ 失敗: {os.path.basename(filename)}")
            error_msg = f"下載失敗: {filename} - {d.get('error', '未知錯誤')}"
            self.logger.error(error_msg)
    
    def extract_playlist_id(self, url):
        """
        從 YouTube URL 中提取播放清單 ID
        
        Args:
            url (str): YouTube 播放清單 URL
            
        Returns:
            str: 播放清單 ID，如果無法提取則返回 None
        """
        try:
            parsed_url = urlparse(url)
            if 'youtube.com' in parsed_url.netloc or 'youtu.be' in parsed_url.netloc:
                query_params = parse_qs(parsed_url.query)
                if 'list' in query_params:
                    return query_params['list'][0]
            return None
        except Exception as e:
            self.logger.error(f"提取播放清單 ID 時發生錯誤: {e}")
            return None
    
    def sanitize_filename(self, filename):
        """
        清理檔名，移除不合法字元
        
        Args:
            filename (str): 原始檔名
            
        Returns:
            str: 清理後的檔名
        """
        # 移除或替換不合法字元
        illegal_chars = r'[<>:"/\\|?*]'
        filename = re.sub(illegal_chars, '_', filename)
          # 移除多餘空格
        filename = re.sub(r'\s+', ' ', filename).strip()
        
        # 限制檔名長度
        if len(filename) > 200:
            filename = filename[:200] + '...'
        
        return filename
    
    def get_playlist_info(self, url):
        """
        獲取播放清單資訊
        
        Args:
            url (str): YouTube 播放清單 URL
            
        Returns:
            dict: 播放清單資訊
        """
        try:
            self.logger.info(f"正在分析播放清單: {url}")
            
            # 使用更嚴格的設定來減少警告
            quiet_opts = {
                'quiet': True,
                'no_warnings': True,
                'extract_flat': False,
                'extractor_args': {
                    'youtube': {
                        'player_client': ['android'],  # 只使用 android 客戶端
                        'skip': ['dash', 'hls']
                    }
                }
            }
            
            with yt_dlp.YoutubeDL(quiet_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                playlist_info = {
                    'title': info.get('title', '未知播放清單'),
                    'uploader': info.get('uploader', '未知上傳者'),
                    'description': info.get('description', ''),
                    'entry_count': len(info.get('entries', [])),
                    'entries': info.get('entries', [])
                }
                self.logger.info(f"播放清單分析完成: {playlist_info['title']} ({playlist_info['entry_count']} 個影片)")
                return playlist_info
        except Exception as e:
            error_msg = f"獲取播放清單資訊時發生錯誤: {e}"
            self.logger.error(error_msg)
            print(error_msg)
            return None
    
    def download_playlist(self, url, start_index=1, end_index=None):
        """
        下載播放清單
        
        Args:
            url (str): YouTube 播放清單 URL
            start_index (int): 開始下載的影片索引（從1開始）
            end_index (int): 結束下載的影片索引（可選）
        """
        print(f"🎵 開始分析播放清單...")
        self.logger.info(f"開始下載播放清單: {url}")
        
        # 獲取播放清單資訊
        playlist_info = self.get_playlist_info(url)
        if not playlist_info:
            error_msg = "無法獲取播放清單資訊"
            self.logger.error(error_msg)
            print(error_msg)
            return False
        
        print(f"📋 播放清單: {playlist_info['title']}")
        print(f"👤 上傳者: {playlist_info['uploader']}")
        print(f"🎶 影片總數: {playlist_info['entry_count']}")
        print(f"📁 儲存位置: {self.output_dir}")
        
        # 計算實際要下載的影片數量
        entries = playlist_info['entries']
        if end_index:
            entries = entries[start_index-1:end_index]
            self.total_count = end_index - start_index + 1
        elif start_index > 1:
            entries = entries[start_index-1:]
            self.total_count = len(entries)
        else:
            self.total_count = len(entries)
        
        print(f"🔢 預計下載: {self.total_count} 個檔案")
        print("-" * 50)
        
        # 創建播放清單專用資料夾
        playlist_title = self.sanitize_filename(playlist_info['title'])
        playlist_dir = self.output_dir / playlist_title
        playlist_dir.mkdir(parents=True, exist_ok=True)
        
        # 更新輸出路徑
        self.ydl_opts['outtmpl'] = str(playlist_dir / '%(playlist_index)02d - %(title)s.%(ext)s')
        
        # 設定下載範圍
        if end_index:
            self.ydl_opts['playlist_start'] = start_index
            self.ydl_opts['playlist_end'] = end_index
            self.logger.info(f"下載範圍: {start_index} - {end_index}")
        elif start_index > 1:
            self.ydl_opts['playlist_start'] = start_index
            self.logger.info(f"從第 {start_index} 個影片開始下載")
          # 開始下載
        success_count = 0
        try:
            print("🚀 開始下載音頻檔案...")
            
            # 逐個下載影片以更好地追蹤進度和錯誤
            for i, entry in enumerate(entries, 1):
                if not entry:
                    continue
                    
                self.download_count = i
                self.current_video_info = entry
                title = entry.get('title', '未知標題')
                
                print(f"\n📥 [{i}/{self.total_count}] {title}")
                
                # 檢查檔案是否已存在
                file_exists, existing_file_path, format_used = self.check_file_exists(playlist_dir, i, title)
                
                if file_exists:
                    format_emoji = "🎵" if format_used == 'wav' else "🎶"
                    print(f"✅ 檔案已存在 ({format_used.upper()}): {existing_file_path}")
                    self.logger.info(f"檔案已存在 [{i}/{self.total_count}] ({format_used.upper()}): {title}")
                    success_count += 1
                    continue  # 跳過下載已存在的檔案
                
                # 使用格式回退機制下載
                output_path = str(playlist_dir / f'{i:02d} - %(title)s.%(ext)s')
                success, format_used, error_msg = self.download_with_format_fallback(
                    entry['webpage_url'], output_path, title, i
                )
                
                if success:
                    success_count += 1
                    format_emoji = "🎵" if format_used == 'wav' else "🎶"
                    print(f"{format_emoji} 成功 ({format_used.upper()}): {title}")
                    self.logger.info(f"成功下載 [{i}/{self.total_count}] ({format_used.upper()}): {title}")
                else:
                    self.logger.error(f"下載完全失敗: {title} - {error_msg}")
                    self.failed_downloads.append({
                        'index': i,
                        'title': title,
                        'url': entry.get('webpage_url', ''),
                        'error': error_msg,
                        'timestamp': datetime.now().isoformat()
                    })
                    print(f"❌ 跳過: {title}")
                    continue
            
            self.save_failed_downloads()
            self.show_download_summary(success_count)
            return True
        except Exception as e:
            error_msg = f"下載過程中發生嚴重錯誤: {e}"
            self.logger.error(error_msg)
            print(f"❌ {error_msg}")
            return False
    
    def save_failed_downloads(self):
        """保存失敗下載的記錄"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        if self.failed_downloads:
            failed_log_file = self.output_dir / "logs" / f"failed_downloads_{timestamp}.json"
            with open(failed_log_file, 'w', encoding='utf-8') as f:
                json.dump(self.failed_downloads, f, ensure_ascii=False, indent=2)
            self.logger.info(f"失敗下載記錄已保存至: {failed_log_file}")
        
        if self.format_attempts:
            format_log_file = self.output_dir / "logs" / f"format_attempts_{timestamp}.json"
            with open(format_log_file, 'w', encoding='utf-8') as f:
                json.dump(self.format_attempts, f, ensure_ascii=False, indent=2)
            self.logger.info(f"格式嘗試記錄已保存至: {format_log_file}")
    
    def show_download_summary(self, success_count):
        """顯示下載摘要"""
        print("\n" + "=" * 50)
        print("📊 下載摘要")
        print("=" * 50)
        
        # 計算格式統計
        wav_count = len([attempt for attempt in self.format_attempts if attempt.get('format') == 'wav' and 'error' not in attempt])
        mp3_fallback_count = len([attempt for attempt in self.format_attempts if attempt.get('format') == 'mp3'])
        
        print(f"✅ 成功: {success_count} 個檔案")
        if wav_count > 0 or mp3_fallback_count > 0:
            print(f"🎵 WAV 格式: {success_count - mp3_fallback_count} 個")
            if mp3_fallback_count > 0:
                print(f"🎶 MP3 格式 (WAV失敗回退): {mp3_fallback_count} 個")
        
        if self.failed_downloads:
            print(f"❌ 失敗: {len(self.failed_downloads)} 個檔案")
            print("\n失敗清單:")
            for failed in self.failed_downloads:
                print(f"  {failed['index']:02d}. {failed['title']}")
                print(f"      💥 {failed['error']}")
            print(f"\n📋 詳細失敗記錄已保存至 logs 資料夾")
        else:
            print("🎉 所有檔案下載成功！")
        
        success_rate = (success_count / self.total_count) * 100 if self.total_count > 0 else 0
        print(f"📈 成功率: {success_rate:.1f}%")
        
        # 顯示格式嘗試統計
        if self.format_attempts:
            wav_failures = len([a for a in self.format_attempts if a.get('format') == 'wav'])
            print(f"⚠️  WAV 轉換失敗: {wav_failures} 個 (已回退到 MP3)")
        
        self.logger.info(f"下載任務完成 - 成功: {success_count}, 失敗: {len(self.failed_downloads)}, 成功率: {success_rate:.1f}%")
    
    def download_single_video(self, url):
        """
        下載單個影片
        
        Args:
            url (str): YouTube 影片 URL
        """
        print(f"🎵 開始下載單個影片...")
        self.logger.info(f"開始下載單個影片: {url}")
        self.total_count = 1
        self.download_count = 1
        
        # 為單個影片創建專用設定
        single_opts = self.ydl_opts.copy()
        single_opts['outtmpl'] = str(self.output_dir / '%(title)s.%(ext)s')
        
        try:
            with yt_dlp.YoutubeDL(single_opts) as ydl:
                ydl.download([url])
            print("\n✅ 下載完成！")
            self.logger.info("單個影片下載完成")
            return True
        except Exception as e:            
            error_msg = f"下載過程中發生錯誤: {e}"
            self.logger.error(error_msg)
            print(f"\n❌ {error_msg}")
            return False
        
    def create_mp3_options(self):
        """創建 MP3 格式的下載選項"""
        mp3_opts = self.ydl_opts.copy()
        mp3_opts['audioformat'] = 'mp3'
        mp3_opts['quiet'] = True
        mp3_opts['no_warnings'] = True
        mp3_opts['postprocessors'] = [
            {
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '320',  # 320kbps 高品質
            },
            {
                'key': 'FFmpegMetadata',
                'add_metadata': True,
            },
        ]
        mp3_opts['postprocessor_args'] = {
            'ffmpeg': ['-threads', '0', '-preset', 'fast']  # 快速轉換
        }
        return mp3_opts
    
    def download_with_format_fallback(self, video_url, output_path, title, index):
        """
        嘗試使用不同格式下載影片，優先 WAV，失敗時回退到 MP3
        
        Args:
            video_url (str): 影片 URL
            output_path (str): 輸出路徑
            title (str): 影片標題
            index (int): 影片索引
              Returns:
            tuple: (success, format_used, error_msg)
        """
        # 首先嘗試 WAV 格式
        try:
            self.current_format = 'wav'
            wav_opts = self.ydl_opts.copy()
            wav_opts['outtmpl'] = output_path
            # 進一步抑制警告
            wav_opts['quiet'] = True
            wav_opts['no_warnings'] = True
            
            with yt_dlp.YoutubeDL(wav_opts) as ydl:
                ydl.download([video_url])
            
            self.logger.info(f"WAV 格式下載成功: {title}")
            return True, 'wav', None
            
        except Exception as wav_error:
            wav_error_msg = str(wav_error)
            self.logger.warning(f"WAV 格式失敗，嘗試 MP3: {title} - {wav_error_msg}")
            
            # 記錄 WAV 失敗
            self.format_attempts.append({
                'index': index,
                'title': title,
                'format': 'wav',
                'error': wav_error_msg,
                'timestamp': datetime.now().isoformat()
            })
            
            # 嘗試 MP3 格式
            try:
                self.current_format = 'mp3'
                mp3_opts = self.create_mp3_options()
                mp3_opts['outtmpl'] = output_path
                # 進一步抑制警告
                mp3_opts['quiet'] = True
                mp3_opts['no_warnings'] = True
                
                with yt_dlp.YoutubeDL(mp3_opts) as ydl:
                    ydl.download([video_url])
                
                self.logger.info(f"MP3 格式下載成功: {title}")
                return True, 'mp3', None
                
            except Exception as mp3_error:
                mp3_error_msg = str(mp3_error)
                self.logger.error(f"MP3 格式也失敗: {title} - {mp3_error_msg}")
                
                # 記錄 MP3 失敗
                self.format_attempts.append({
                    'index': index,
                    'title': title,
                    'format': 'mp3',
                    'error': mp3_error_msg,
                    'timestamp': datetime.now().isoformat()                })
                
                return False, None, f"WAV: {wav_error_msg}; MP3: {mp3_error_msg}"
    
    def check_file_exists(self, playlist_dir, index, title):
        """
        檢查檔案是否已經存在
        
        Args:
            playlist_dir (Path): 播放清單目錄
            index (int): 影片索引
            title (str): 影片標題
            
        Returns:
            tuple: (exists, existing_file_path, format)
        """
        # 清理標題用於檔名比較
        clean_title = self.sanitize_filename(title)
        
        # 可能的檔案格式
        possible_formats = ['.wav', '.mp3', '.m4a', '.webm', '.opus']
        
        # 精確匹配：優先檢查帶索引的檔名
        exact_patterns = [
            f"{index:02d} - {clean_title}",  # 正常格式
            f"{index:02d} - {title}",        # 原始標題
        ]
        
        # 檢查精確匹配
        for pattern in exact_patterns:
            for ext in possible_formats:
                file_path = playlist_dir / f"{pattern}{ext}"
                if file_path.exists():
                    format_name = ext[1:].upper()  # 移除點並轉大寫
                    return True, file_path, format_name
        
        # 如果精確匹配失敗，嘗試模糊匹配（但更嚴格）
        try:
            # 只檢查以當前索引開頭的檔案
            index_prefix = f"{index:02d} -"
            
            for file_path in playlist_dir.glob(f"{index_prefix}*"):
                if file_path.is_file():
                    # 檢查檔名是否包含標題的關鍵字
                    file_stem = file_path.stem.lower()
                    title_lower = clean_title.lower()
                    
                    # 提取標題的主要關鍵字（去除特殊字元）
                    title_keywords = re.sub(r'[^\w\s]', '', title_lower).split()
                    # 過濾掉太短的關鍵字
                    significant_keywords = [kw for kw in title_keywords if len(kw) > 2]
                    
                    # 如果有足夠的關鍵字，並且檔名包含大部分關鍵字
                    if significant_keywords:
                        matches = sum(1 for kw in significant_keywords if kw in file_stem)
                        if matches >= len(significant_keywords) * 0.7:  # 至少70%匹配
                            format_name = file_path.suffix[1:].upper() if file_path.suffix else "UNKNOWN"
                            return True, file_path, format_name
        except Exception:
            pass
        
        return False, None, None

def main():
    """主函數"""
    print("=" * 60)
    print("🎵 YouTube 播放清單音頻下載器")
    print("=" * 60)
    
    # 預設播放清單 URL
    default_url = "https://www.youtube.com/watch?v=mP8Igecq1dA&list=PLhri3WAC3dSDoHb7D_GvnuMaMqlKatSam&index=1"
    
    # 獲取用戶輸入
    if len(sys.argv) > 1:
        url = sys.argv[1]
    else:
        url = input(f"請輸入 YouTube 播放清單 URL (按 Enter 使用預設): ").strip()
        if not url:
            url = default_url
    
    # 創建下載器 - 指定正確的輸出目錄
    output_dir = r"C:\Users\陳洋\Desktop\RushiaMode\audio\歌\播放清單"
    downloader = YouTubePlaylistDownloader(output_dir)
    
    # 檢查是否為播放清單
    playlist_id = downloader.extract_playlist_id(url)
    
    if playlist_id:
        print(f"🆔 偵測到播放清單 ID: {playlist_id}")
        
        # 詢問下載範圍
        try:
            start_input = input("開始下載的影片編號 (預設為 1): ").strip()
            start_index = int(start_input) if start_input else 1
            
            end_input = input("結束下載的影片編號 (按 Enter 下載全部): ").strip()
            end_index = int(end_input) if end_input else None
            
            # 下載播放清單
            success = downloader.download_playlist(url, start_index, end_index)
            
        except ValueError:
            print("⚠️ 輸入的編號格式不正確，使用預設設定下載全部影片")
            success = downloader.download_playlist(url)
    else:
        print("🎬 偵測到單個影片，開始下載...")
        success = downloader.download_single_video(url)
    
    if success:
        print("\n🎉 下載任務完成！")
        print(f"📁 檔案保存在: {downloader.output_dir}")
        print(f"📋 日誌保存在: {downloader.output_dir / 'logs'}")
    else:
        print("\n💥 下載任務失敗，請檢查 URL 是否正確或網路連線")
    
    input("\n按 Enter 鍵退出...")

if __name__ == "__main__":
    main()
