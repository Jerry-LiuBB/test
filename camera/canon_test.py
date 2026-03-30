import requests
import json
import time
import os

class CanonEOSR100CCAPI:
    def __init__(self, camera_ip, port=8080):
        self.base_url = f"http://{camera_ip}:{port}"
        self.shooting_api_version = "ver100"
        self.storage_api_version = "ver130"
        self.session = requests.Session()
        self.session.headers.update({
            "Accept": "application/json",
            "Content-Type": "application/json"
        })

    def _get_shooting_url(self, endpoint):
        return f"{self.base_url}/ccapi/{self.shooting_api_version}/{endpoint}"

    def _get_storage_url(self, endpoint):
        return f"{self.base_url}/ccapi/{self.storage_api_version}/{endpoint}"

    def list_supported_apis(self):
        """
        获取相机支持的所有API版本和端点
        CCAPI端点: GET /ccapi
        """
        try:
            url = f"{self.base_url}/ccapi"
            response = self.session.get(url)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"获取API列表失败: {e}")
            return None

    def detect_api_version(self):
        """
        自动检测相机支持的API版本
        """
        versions = ["ver140", "ver130", "ver120", "ver110", "ver100"]
        for ver in versions:
            try:
                url = f"{self.base_url}/ccapi/{ver}/deviceinformation"
                response = self.session.get(url)
                if response.status_code == 200:
                    print(f"发现支持的API版本: {ver}")
                    self.api_version = ver
                    return ver
            except:
                continue
        print("未检测到支持的API版本")
        return None
    
    def capture_image(self, save_path=None):
        """
        拍摄照片并保存到本地

        CCAPI端点: POST /ccapi/ver140/shooting/control/shutterbutton

        Args:
            save_path: 图像保存目录，默认为 "Users\\dell\\Downloads"

        Returns:
            dict: 拍摄结果信息，包含文件路径
        """
        if save_path is None:
            save_path = "Users\\dell\\图片"

        try:
            url = self._get_shooting_url("shooting/control/shutterbutton")

            payload = {"af": False}

            response = self.session.post(url, json=payload)
            response.raise_for_status()

            result = response.json() if response.content else {}
            print(f"拍摄成功")

            return True

        except requests.exceptions.RequestException as e:
            print(f"拍摄失败: {e}")
            return False
    
    def _download_image(self, image_url, save_filepath):
        """下载图像到本地"""
        try:
            os.makedirs(os.path.dirname(save_filepath), exist_ok=True)
            response = self.session.get(image_url, timeout=30)
            response.raise_for_status()
            with open(save_filepath, "wb") as f:
                f.write(response.content)
            print(f"图像已保存: {save_filepath}")
        except Exception as e:
            print(f"图像下载失败: {e}")

    def get_storage_list(self):
        """
        获取相机存储列表
        CCAPI端点: GET /ccapi/ver100/contents
        """
        try:
            url = self._get_storage_url("contents")
            response = self.session.get(url)
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 404:
                print("存储不可用，可能没有插入存储卡")
                return None
            else:
                response.raise_for_status()
                return None
        except requests.exceptions.RequestException as e:
            print(f"获取存储列表失败: {e}")
            return None

    def get_directory_list(self, storage="sd"):
        """
        获取存储目录列表
        CCAPI端点: GET /ccapi/ver130/contents/[storage]
        """
        try:
            url = self._get_storage_url(f"contents/{storage}")
            response = self.session.get(url)
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 404:
                print(f"存储 {storage} 不可用")
                return None
            elif response.status_code == 503:
                print(f"存储服务暂时不可用 (503)")
                return None
            else:
                response.raise_for_status()
                return None
        except requests.exceptions.RequestException as e:
            print(f"获取目录列表失败: {e}")
            return None

    def download_image(self, storage, directory, filename, save_path):
        """
        从相机下载图像

        Args:
            storage: 存储名称 (如 "sd")
            directory: 目录名称 (如 "100CANON")
            filename: 文件名 (如 "IMG_0001.JPG")
            save_path: 本地保存路径

        Returns:
            str: 保存的完整文件路径，失败返回None
        """
        try:
            url = self._get_storage_url(f"contents/{storage}/{directory}/{filename}")
            print(f"正在下载: {url}")

            os.makedirs(save_path, exist_ok=True)
            filepath = os.path.join(save_path, filename)

            response = self.session.get(url, timeout=60)
            response.raise_for_status()

            with open(filepath, "wb") as f:
                f.write(response.content)

            print(f"图像已保存: {filepath}")
            return filepath

        except requests.exceptions.RequestException as e:
            print(f"下载图像失败: {e}")
            return None

    def get_latest_photo(self, save_path, max_retries=5, retry_delay=2):
        """
        获取相机中最新拍摄的照片并下载到本地

        Args:
            save_path: 本地保存目录
            max_retries: 最大重试次数
            retry_delay: 重试间隔（秒）

        Returns:
            str: 保存的文件路径，失败返回None
        """
        import time

        for attempt in range(max_retries):
            dirs = self.get_directory_list("sd")
            if not dirs:
                print(f"尝试 {attempt+1}/{max_retries}: 无法获取目录列表")
                time.sleep(retry_delay)
                continue

            all_files = []
            for dir_path in dirs.get('path', []):
                dir_name = dir_path.split('/')[-1]
                dir_url = self._get_storage_url(f"contents/sd/{dir_name}")
                resp = self.session.get(dir_url)
                if resp.status_code == 200:
                    files_data = resp.json()
                    if 'path' in files_data and files_data['path']:
                        files = [f.split('/')[-1] for f in files_data['path']]
                        all_files.extend([(dir_name, f) for f in files])

            if not all_files:
                print(f"尝试 {attempt+1}/{max_retries}: 未找到文件，等待中...")
                time.sleep(retry_delay)
                continue

            all_files_sorted = sorted(all_files, key=lambda x: x[1])
            latest_dir, latest_file = all_files_sorted[-1]
            print(f"最新文件: {latest_dir}/{latest_file}")

            downloaded = self.download_image("sd", latest_dir, latest_file, save_path)
            if downloaded:
                return downloaded

        print("无法获取最新照片")
        return None
    
    def get_shooting_settings(self):
        """
        获取拍摄设置
        CCAPI端点: GET /ccapi/ver140/shooting/settings
        """
        try:
            url = self._get_shooting_url("shooting/settings")
            response = self.session.get(url)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"获取拍摄设置失败: {e}")
            return None

    def set_shooting_setting(self, parameter_name, value):
        """
        设置拍摄参数

        Args:
            parameter_name: 参数名称
            value: 参数值

        Returns:
            bool: 设置是否成功
        """
        try:
            url = self._get_shooting_url("shooting/settings")

            payload = {

                parameter_name: value
            }

            response = self.session.put(url, json=payload)
            response.raise_for_status()

            print(f"参数设置成功: {parameter_name} = {value}")
            return True

        except requests.exceptions.RequestException as e:
            print(f"设置拍摄参数失败: {e}")
            return False

    def get_liveview_image(self):
        """
        获取实时取景图像
        CCAPI端点: GET /ccapi/ver140/property/liveview
        """
        try:
            url = self._get_shooting_url("property/liveview")
            response = self.session.get(url, stream=True)
            response.raise_for_status()
            return response.content
        except requests.exceptions.RequestException as e:
            print(f"获取实时取景失败: {e}")
            return None

    def start_liveview(self):
        """
        启动实时取景
        CCAPI端点: POST /ccapi/ver100/shooting/liveview
        Body: {"liveviewsize": "medium", "cameradisplay": "on"}
        """
        try:
            url = self._get_shooting_url("shooting/liveview")
            payload = {"liveviewsize": "medium", "cameradisplay": "on"}
            response = self.session.post(url, json=payload)
            response.raise_for_status()
            print("实时取景已启动")
            return True
        except requests.exceptions.RequestException as e:
            print(f"启动实时取景失败: {e}")
            return False

    def stop_liveview(self):
        """
        停止实时取景
        CCAPI端点: POST /ccapi/ver100/shooting/liveview (with liveviewsize=off)
        """
        try:
            url = self._get_shooting_url("shooting/liveview")
            payload = {"liveviewsize": "off", "cameradisplay": "off"}
            response = self.session.post(url, json=payload)
            response.raise_for_status()
            print("实时取景已停止")
            return True
        except requests.exceptions.RequestException as e:
            print(f"停止实时取景失败: {e}")
            return False
    
    def continuous_capture(self, count=5, interval=2, save_path="./captures"):
        """
        连续拍摄
        
        Args:
            count: 拍摄张数
            interval: 拍摄间隔（秒）
            save_path: 保存路径
            
        Returns:
            list: 拍摄结果列表
        """
        results = []
        
        # 确保保存目录存在
        os.makedirs(save_path, exist_ok=True)
        
        print(f"开始连续拍摄，共{count}张，间隔{interval}秒...")
        
        for i in range(count):
            print(f"拍摄第 {i+1}/{count} 张...")
            
            result = self.capture_image()
            if result:
                results.append(result)
            else:
                print(f"第 {i+1} 张拍摄失败")
            
            # 等待下一次拍摄（最后一帧不等待）
            if i < count - 1:
                time.sleep(interval)
        
        print(f"连续拍摄完成，成功 {len(results)} 张")
        return results


# 高级拍摄示例：设置参数后拍摄
def advanced_capture_example():
    """高级拍摄示例：配置参数后进行拍摄"""
    camera_ip = "192.168.1.2"
    camera = CanonEOSR100CCAPI(camera_ip)
    
    # 首先获取当前设置
    current_settings = camera.get_shooting_settings()
    if current_settings:
        print("当前拍摄设置:")
        print(json.dumps(current_settings, indent=2, ensure_ascii=False))
    
    # 设置ISO值
    # 常见的ISO值: 100, 200, 400, 800, 1600, 3200, 6400, 12800
    camera.set_shooting_setting("iso", 800)
    
    # 设置光圈值
    # 常见的Av值: 1.8, 2.8, 4.0, 5.6, 8.0, 11.0, 16.0
    camera.set_shooting_setting("av", 5.6)
    
    # 设置快门速度
    # 常见的Tv值: 1/500, 1/250, 1/125, 1/60, 1/30, 1/15, 1/8
    camera.set_shooting_setting("tv", 1/125)

    # 执行拍摄
    result = camera.capture_image()

    return result


if __name__ == "__main__":
    print("佳能 EOS R100 CCAPI 测试")
    print("-" * 40)

    camera_ip = "192.168.1.2"
    camera = CanonEOSR100CCAPI(camera_ip)

    print(f"连接到相机: {camera.base_url}")

    print("\n检测API版本...")
    camera.detect_api_version()

    print("\n获取支持的API列表...")
    apis = camera.list_supported_apis()
    if apis:
        print(f"支持的API版本: {list(apis.keys())}")

    print("\n获取拍摄设置...")
    settings = camera.get_shooting_settings()
    if settings:
        print(f"当前设置: {json.dumps(settings, ensure_ascii=False, indent=2)}")

    print("\n启动实时取景...")
    camera.start_liveview()
    time.sleep(1)

    print("\n拍摄照片...")
    success = camera.capture_image()

    if success:
        print("\n下载照片到本地...")
        save_path = r"c:\Users\dell\图片\canon_captures"
        downloaded_file = camera.get_latest_photo(save_path)
        if downloaded_file:
            print(f"照片已保存到: {downloaded_file}")
        else:
            print("照片下载失败，请检查相机存储卡是否正常")
    else:
        print("拍摄失败，请检查相机连接和IP地址")