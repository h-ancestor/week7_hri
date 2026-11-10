# Hướng dẫn chạy package tuần 7

## 1. Chuẩn bị dependency

Cần Ubuntu 22.04, ROS 2 Humble, TurtleBot 4 Simulation/Nav2 và workspace khóa học chứa `turtlebot4_lab` cùng `turtlebot4_week5`. Đặt biến `COURSE_WS` tới workspace khóa học, ví dụ:

```bash
export COURSE_WS=/path/to/course_workspace
```

Trong mỗi terminal:

```bash
source /opt/ros/humble/setup.bash
source "$COURSE_WS/install/setup.bash"
COURSE_INSTALL="$COURSE_WS/install"
export AMENT_PREFIX_PATH="$COURSE_INSTALL/turtlebot4_lab:$COURSE_INSTALL/turtlebot4_week5:$AMENT_PREFIX_PATH"
export PYTHONPATH="$COURSE_WS/build/turtlebot4_lab:$COURSE_WS/build/turtlebot4_week5:$PYTHONPATH"
export ROS_LOCALHOST_ONLY=1
cd /path/to/github_tuan_07
export ROS_HOME="$PWD/.ros"
```

## 2. Build và test

```bash
python3 -m pip install -r requirements.txt
rosdep install --from-paths . --ignore-src -r -y
colcon build --symlink-install
source install/setup.bash
python3 -m unittest discover -s tests -v
```

## 3. Tải model Vosk cho dashboard microphone

Trước khi mở dashboard lần đầu, tải model vào workspace (khoảng 53 MB sau giải nén):

```bash
python3 scripts/download_vosk_model.py
```

Nếu chỉ chạy test hoặc không bật microphone, có thể bỏ qua bước này. Model bị `.gitignore` để tránh đưa dữ liệu nhị phân lớn lên GitHub.

## 4. Khởi chạy

Mở terminal riêng cho từng tiến trình. Trong từng terminal, source ROS và course workspace như mục 1, sau đó chạy:

Simulator:

```bash
ros2 launch turtlebot4_lab simulation.launch.py world:=warehouse model:=lite rviz:=false
```

Localization/Nav2:

```bash
ros2 launch turtlebot4_week5 localization_navigation.launch.py map:="$(pwd)/maps/map.yaml" use_sim_time:=true
```

Dashboard:

```bash
source install/setup.bash
export ROS_HOME="$(pwd)/.ros"
ros2 run turtlebot4_week7 voice_dashboard
```

RViz:

```bash
rviz2 -d "$(ros2 pkg prefix turtlebot4_viz)/share/turtlebot4_viz/rviz/robot.rviz"
```

Đặt initial pose trong RViz bằng **2D Pose Estimate**, đợi localization/Nav2 active, kiểm tra vị trí robot và waypoint trên map. Dashboard hướng dẫn các câu A, B, A→B và C→B. Dừng ghi hình bằng Ctrl+C trước khi đóng các tiến trình để MP4 được finalize.

## Video và báo cáo

Video cần tải riêng lên Drive là `tuan7_demo_phan_vung_va_dieu_huong.mp4`; video không được thêm vào repository source. Word/PDF 13 trang ở thư mục gốc của repository. Kết quả test/route được ghi trong `KET_QUA_KIEM_THU.md`.
