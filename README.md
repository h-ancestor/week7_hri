# Bài thực hành 07 — Phân vùng bản đồ và điều hướng bằng giọng nói

Package ROS 2 Humble cho TurtleBot 4 Simulation: phân vùng occupancy map, gắn nhãn vùng semantic, phân tích câu lệnh và gửi mục tiêu tuần tự tới Nav2. Đây là thư mục source đã chuẩn bị để đưa lên GitHub; chưa được push lên tài khoản.

## Nội dung repository

- `turtlebot4_week7/`: segmentation, parser/navigation node và dashboard.
- `resource/turtlebot4_week7`, `package.xml`, `setup.py`, `setup.cfg`: metadata cần để colcon nhận diện và build package.
- `LICENSE`: Apache-2.0, khớp với khai báo trong `package.xml`.
- `config/regions.yaml`: ba vùng A/B/C, aliases, pixel seed và pose đích.
- `maps/`: map PGM/YAML, ảnh phân vùng, JSON và nguồn bản đồ.
- `scripts/download_vosk_model.py`: tải và giải nén model Vosk vào `models/` khi cần dùng microphone. Model nhị phân không được commit vì sau giải nén khoảng 53 MB.
- `tests/`: 14 kiểm thử parser, segmentation, tọa độ và trường hợp vùng không tồn tại.
- `reports/figures/`, `reports/generate_report.py`: hình nguồn và script tạo lại DOCX.
- `HUONG_DAN_CHAY.md`, `KET_QUA_KIEM_THU.md`: hướng dẫn và kết quả.

## Yêu cầu ngoài repository

Ubuntu 22.04, ROS 2 Humble, TurtleBot 4 Simulation, Nav2, colcon, OpenCV, PyYAML, `alsa-utils` và thiết bị microphone nếu dùng Vosk trực tiếp. 
`requirements.txt` cài Vosk và Pillow (Pillow chỉ cần nếu muốn tạo lại báo cáo). Các thư viện ROS/OpenCV/PyYAML nên cài bằng apt/rosdep trong ROS environment. Model tiếng Việt nhỏ được Vosk công bố khoảng 32 MB và Apache-2.0; xem [danh sách model Vosk chính thức](https://alphacephei.com/vosk/models).

## Build và kiểm thử

```bash
source /opt/ros/humble/setup.bash
rosdep install --from-paths . --ignore-src -r -y
python3 -m pip install -r requirements.txt
colcon build --symlink-install
source install/setup.bash
python3 -m unittest discover -s tests -v
```

## Tải model ASR (chỉ cần khi dùng dashboard/microphone)

Sau khi cài requirements, tải model theo yêu cầu vào đúng đường dẫn node dùng:

```bash
python3 scripts/download_vosk_model.py
```

Script tải archive trực tiếp từ nguồn Vosk và kiểm tra các file chính sau giải nén. Thư mục model và file ZIP đã được thêm vào `.gitignore`; không đưa chúng lên GitHub. Nếu chỉ chạy unit test hoặc parser không bật microphone, không cần tải model.

## Chạy simulator, Nav2 và dashboard

Trước tiên đặt `COURSE_WS` thành thư mục workspace khóa học chứa `install/` và `build/`. Các package khóa học được cài isolated, vì vậy trong từng terminal cần bổ sung prefix của package:

```bash
source /opt/ros/humble/setup.bash
source "$COURSE_WS/install/setup.bash"
COURSE_INSTALL="$COURSE_WS/install"
export AMENT_PREFIX_PATH="$COURSE_INSTALL/turtlebot4_lab:$COURSE_INSTALL/turtlebot4_week5:$AMENT_PREFIX_PATH"
export PYTHONPATH="$COURSE_WS/build/turtlebot4_lab:$COURSE_WS/build/turtlebot4_week5:$PYTHONPATH"
export ROS_LOCALHOST_ONLY=1
export ROS_HOME="$PWD/.ros"
```

Sau đó vào thư mục package tuần 7, source package, đặt ROS_HOME và chạy các lệnh trong terminal riêng:

```bash
cd /path/to/github_tuan_07
source install/setup.bash
export ROS_HOME="$PWD/.ros"
ros2 launch turtlebot4_lab simulation.launch.py world:=warehouse model:=lite rviz:=false
```

Terminal Nav2:

```bash
cd /path/to/github_tuan_07
source install/setup.bash
export ROS_HOME="$PWD/.ros"
ros2 launch turtlebot4_week5 localization_navigation.launch.py map:="$PWD/maps/map.yaml" use_sim_time:=true
```

Terminal dashboard:

```bash
cd /path/to/github_tuan_07
source install/setup.bash
export ROS_HOME="$PWD/.ros"
ros2 run turtlebot4_week7 voice_dashboard
```

Mở RViz bằng cấu hình TurtleBot 4, đặt initial pose bằng **2D Pose Estimate**, rồi đợi AMCL/Nav2 active. Dashboard hướng dẫn A, B, A→B, C→B theo thứ tự. Các waypoint là điểm demo; đối chiếu map trước khi chạy. Lệnh vùng không tồn tại bị parser từ chối. Để ghi video, quay cửa sổ RViz và dashboard, sau đó dừng recorder bằng Ctrl+C để MP4 được đóng hoàn chỉnh.

