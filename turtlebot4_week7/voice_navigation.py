"""Vietnamese command parser and explicitly started Nav2 voice navigation node."""
import json
import math
import re
import shutil
import subprocess
import threading
import time
import unicodedata
from pathlib import Path

import yaml


def normalize(text):
    text = unicodedata.normalize('NFD', text.lower().replace('đ', 'd'))
    text = ''.join(c for c in text if unicodedata.category(c) != 'Mn')
    return re.sub(r'[^a-z0-9]+', ' ', text).strip()


def has_navigation_intent(text):
    """Filter silence/noise recognitions before reporting command parse errors."""
    normalized = normalize(text)
    return any(re.search(r'(?<!\w)' + token + r'(?!\w)', normalized)
               for token in ('di', 'den', 'toi', 'qua', 'chuyen'))


def parse_command(text, aliases):
    """Return ordered semantic destinations or raise ValueError for unknown/ambiguous input."""
    normalized = normalize(text)
    found = []
    for alias, region_id in aliases.items():
        key = normalize(alias)
        match = re.search(r'(?<!\w)' + re.escape(key) + r'(?!\w)', normalized)
        if match:
            found.append((match.start(), match.end(), region_id))
    found.sort()
    compact = []
    for start, end, region_id in found:
        if compact and start < compact[-1][1]:
            if region_id != compact[-1][2]:
                raise ValueError('Lệnh chứa nhiều tên vùng trùng/không rõ nghĩa')
            continue
        compact.append((start, end, region_id))
    if not compact:
        raise ValueError('Không nhận diện được khu vực đích')
    ids = [entry[2] for entry in compact]
    ids = [region_id for index, region_id in enumerate(ids)
           if index == 0 or region_id != ids[index - 1]]
    if not any(token in normalized for token in (' den ', ' toi ', ' qua ', 'di ', ' den')):
        raise ValueError('Không nhận diện được ý định điều hướng')
    return ids


def load_regions(path):
    doc = yaml.safe_load(Path(path).read_text(encoding='utf-8'))
    regions = {str(r['id']): r for r in doc['regions']}
    aliases = {}
    for region in regions.values():
        for alias in [region['id'], region['name'], *region.get('aliases', [])]:
            aliases[str(alias)] = str(region['id'])
    return regions, aliases


def build_guided_prompts(regions):
    """Build a short spoken demo checklist from the configured region IDs."""
    prompts = []
    if 'A' in regions:
        prompts.append(('Đi đến khu vực A.', ['A']))
    if 'B' in regions:
        prompts.append(('Đi đến phòng thí nghiệm.', ['B']))
    if {'A', 'B'} <= regions.keys():
        prompts.append(('Đi từ khu vực A đến phòng thí nghiệm.', ['A', 'B']))
    if {'B', 'C'} <= regions.keys():
        prompts.append(('Đi qua hành lang rồi đến phòng thí nghiệm.', ['C', 'B']))
    prompts.append(('Đi đến khu vực Z để kiểm tra tên vùng không tồn tại.', None))
    return prompts


class VoiceNavigationNode:
    def __new__(cls):
        import rclpy
        from rclpy.node import Node
        from rclpy.action import ActionClient
        from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy
        from std_msgs.msg import String
        from geometry_msgs.msg import PoseStamped, PoseWithCovarianceStamped
        from nav2_msgs.action import NavigateToPose
        from action_msgs.msg import GoalStatus

        class _Node(Node):
            def __init__(self):
                super().__init__('week7_voice_navigation')
                self.declare_parameter('regions_yaml', '')
                self.declare_parameter('use_microphone', False)
                self.declare_parameter('vosk_model_path', '')
                self.declare_parameter('sample_rate', 16000)
                self.declare_parameter('action_server_timeout', 20.0)
                self.regions, self.aliases = load_regions(self.get_parameter('regions_yaml').value)
                self.guided_prompts = build_guided_prompts(self.regions)
                self.prompt_index = 0
                self.active_prompt_index = None
                self.action_client = ActionClient(self, NavigateToPose, '/navigate_to_pose')
                self.sub = self.create_subscription(String, '/voice_command', self.on_text, 10)
                amcl_qos = QoSProfile(depth=1,
                    reliability=ReliabilityPolicy.RELIABLE,
                    durability=DurabilityPolicy.TRANSIENT_LOCAL)
                self.pose_sub = self.create_subscription(
                    PoseWithCovarianceStamped, '/amcl_pose', self.on_amcl_pose, amcl_qos)
                self.localization_ready = False
                self.route = []
                self.route_index = 0
                self.goal_future = None
                self.goal_handle = None
                self.result_future = None
                self.route_started = 0.0
                self.poll_timer = self.create_timer(0.2, self.advance_route)
                self.get_logger().info(
                    'Node sẵn sàng; microphone chỉ mở khi use_microphone:=true. '
                    'BƯỚC CHUẨN BỊ: đặt initial pose bằng 2D Pose Estimate trong RViz. '
                    'Khi AMCL xác nhận, câu cần nói sẽ hiện ở đây.')
                if self.get_parameter('use_microphone').value:
                    self.start_microphone()

            def on_amcl_pose(self, _message):
                was_ready = self.localization_ready
                self.localization_ready = True
                if not was_ready:
                    self.show_next_prompt()

            def show_next_prompt(self):
                if self.prompt_index < len(self.guided_prompts):
                    phrase, _expected_route = self.guided_prompts[self.prompt_index]
                    self.get_logger().info(
                        f'===== BƯỚC {self.prompt_index + 1}/{len(self.guided_prompts)} =====\n'
                        f'Hãy nói: “{phrase}”\n'
                        'Chờ robot đến đích rồi node sẽ hiện bước kế tiếp.')
                else:
                    self.get_logger().info(
                        '===== ĐÃ HẾT CÁC BƯỚC GỢI Ý =====\n'
                        'Bạn có thể tiếp tục nói bất kỳ lệnh điều hướng hợp lệ nào.')

            def advance_prompt(self):
                self.prompt_index += 1
                self.active_prompt_index = None
                self.show_next_prompt()

            def start_microphone(self):
                import queue
                from vosk import Model, KaldiRecognizer
                model_path = self.get_parameter('vosk_model_path').value
                if not model_path or not Path(model_path).is_dir():
                    raise ValueError('Vosk model path không tồn tại')
                arecord = shutil.which('arecord')
                if not arecord:
                    raise RuntimeError('Thiếu arecord; cài gói alsa-utils để nhận âm thanh microphone')
                model = Model(model_path)
                sample_rate = int(self.get_parameter('sample_rate').value)
                self.recognizer = KaldiRecognizer(model, sample_rate)
                self.audio_queue = queue.Queue()
                self.audio_process = subprocess.Popen(
                    [arecord, '-q', '-f', 'S16_LE', '-c', '1', '-r', str(sample_rate), '-t', 'raw'],
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=0)
                time.sleep(0.2)
                if self.audio_process.poll() is not None:
                    error = self.audio_process.stderr.read().decode(errors='replace').strip()
                    raise RuntimeError(f'Không mở được microphone qua arecord: {error}')
                def collect_audio():
                    while True:
                        chunk = self.audio_process.stdout.read(4000)
                        if not chunk:
                            break
                        self.audio_queue.put(chunk)
                self.audio_thread = threading.Thread(target=collect_audio, daemon=True)
                self.audio_thread.start()
                self.timer = self.create_timer(0.1, self.read_audio)
                self.get_logger().info('Microphone mở theo use_microphone:=true.')

            def read_audio(self):
                while not self.audio_queue.empty():
                    data = self.audio_queue.get_nowait()
                    if self.recognizer.AcceptWaveform(data):
                        text = json.loads(self.recognizer.Result()).get('text', '')
                        if text:
                            self.on_text(String(data=text))

            def on_text(self, message):
                if not has_navigation_intent(message.data):
                    self.get_logger().debug(f'Bỏ qua âm thanh không giống câu lệnh: {message.data!r}')
                    return
                self.get_logger().info(f'Đã nhận dạng: “{message.data}”')
                parse_failed = False
                try:
                    try:
                        ids = parse_command(message.data, self.aliases)
                    except ValueError:
                        parse_failed = True
                        raise
                    for region_id in ids:
                        if region_id not in self.regions:
                            raise ValueError(f'Khu vực không tồn tại: {region_id}')
                    if self.route or self.goal_future or self.goal_handle:
                        raise ValueError('Robot đang xử lý tuyến trước; hãy đợi tuyến hiện tại kết thúc')
                    if not self.localization_ready:
                        raise ValueError('AMCL chưa có initial pose; đặt 2D Pose Estimate trước khi ra lệnh')
                    self.get_logger().info(f"Lệnh: {message.data!r} -> {' -> '.join(ids)}")
                    self.active_prompt_index = self.prompt_index
                    self.route = ids
                    self.route_index = 0
                    self.route_started = time.monotonic()
                    self.advance_route()
                except Exception as exc:
                    self.get_logger().error(str(exc))
                    normalized = normalize(message.data)
                    if (parse_failed and self.prompt_index < len(self.guided_prompts)
                            and self.guided_prompts[self.prompt_index][1] is None
                            and ('khu vuc z' in normalized or 'vung z' in normalized)):
                        self.get_logger().info(
                            'Đúng: vùng Z không tồn tại; không gửi goal Nav2.')
                        self.advance_prompt()
                    else:
                        self.get_logger().info('Chưa nhận được lệnh hợp lệ; hãy thử lại câu đang hiển thị.')

            def advance_route(self):
                if not self.route or self.goal_future or self.goal_handle:
                    return
                if not self.localization_ready:
                    self.finish_route(False, 'Mất trạng thái localization; dừng tuyến')
                    return
                if not self.action_client.server_is_ready():
                    timeout = float(self.get_parameter('action_server_timeout').value)
                    if time.monotonic() - self.route_started > timeout:
                        self.finish_route(False, 'Không tìm thấy action server /navigate_to_pose')
                    return
                region_id = self.route[self.route_index]
                goal = self.regions[region_id]['goal']
                pose = PoseStamped()
                pose.header.frame_id = 'map'
                pose.header.stamp = self.get_clock().now().to_msg()
                pose.pose.position.x = float(goal['x'])
                pose.pose.position.y = float(goal['y'])
                yaw = float(goal.get('yaw', 0.0))
                pose.pose.orientation.z = math.sin(yaw / 2.0)
                pose.pose.orientation.w = math.cos(yaw / 2.0)
                request = NavigateToPose.Goal()
                request.pose = pose
                self.get_logger().info(f'Gửi goal Nav2 tới vùng {region_id}')
                self.goal_future = self.action_client.send_goal_async(request)
                self.goal_future.add_done_callback(self.on_goal_response)

            def on_goal_response(self, future):
                self.goal_future = None
                try:
                    self.goal_handle = future.result()
                    if not self.goal_handle or not self.goal_handle.accepted:
                        self.finish_route(False, 'Nav2 từ chối goal')
                        return
                    self.result_future = self.goal_handle.get_result_async()
                    self.result_future.add_done_callback(self.on_goal_result)
                except Exception as exc:
                    self.finish_route(False, f'Lỗi gửi goal Nav2: {exc}')

            def on_goal_result(self, future):
                self.goal_handle = None
                self.result_future = None
                self.route_started = 0.0
                try:
                    result = future.result()
                    if result.status != GoalStatus.STATUS_SUCCEEDED:
                        self.finish_route(False, f'Nav2 thất bại tại vùng {self.route[self.route_index]}')
                        return
                    self.route_index += 1
                    if self.route_index >= len(self.route):
                        completed_prompt = self.active_prompt_index
                        self.finish_route(True, 'Nav2 đã hoàn thành tuyến')
                        if completed_prompt == self.prompt_index:
                            self.advance_prompt()
                    else:
                        self.advance_route()
                except Exception as exc:
                    self.finish_route(False, f'Lỗi kết quả Nav2: {exc}')

            def finish_route(self, success, message):
                self.get_logger().info(message) if success else self.get_logger().error(message)
                self.route = []
                self.route_index = 0
                self.goal_future = None
                self.goal_handle = None
                self.result_future = None
        return _Node()


def main():
    import rclpy
    rclpy.init()
    node = VoiceNavigationNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        if hasattr(node, 'audio_process'):
            node.audio_process.terminate()
            node.audio_process.wait(timeout=3)
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
