# Kết quả kiểm tra Bài thực hành 07

Ngày kiểm tra: 10/11/2026.

## Phần mềm

- `python3 -m unittest discover -s tests -v`: 14/14 kiểm thử đạt, gồm parser, waypoint nhiều chặng và hồi quy tránh nhầm từ “đề” thành vùng B.
- `colcon build --base-paths . --build-base build --install-base install --symlink-install`: thành công.
- Các module Python được kiểm tra cú pháp thành công.

## Điều hướng tích hợp Gazebo/Nav2

| Lệnh | Phân giải | Kết quả log |
|---|---|---|
| Đi đến khu vực A | A | Nav2 hoàn tất |
| Đi đến phòng thí nghiệm | B | Nav2 hoàn tất |
| Đi từ khu vực A đến phòng thí nghiệm | A → B | Hai goal gửi đúng thứ tự; Nav2 hoàn tất |
| Đi qua hành lang rồi đến phòng thí nghiệm | C → B | Goal C rồi goal B; Nav2 hoàn tất tuyến |

Bước kiểm tra vùng Z được bỏ qua theo phạm vi demo.

## Video

`tuan7_demo_phan_vung_va_dieu_huong.mp4` (video để riêng ngoài repository, tải lên Drive) đã được chốt bằng SIGINT và xác minh đọc được: H.264/AAC, 1600×600, 1623,667 giây (27 phút 03,7 giây), 101.130.126 byte. Video ghi đồng thời cửa sổ RViz và dashboard. Đây là file video cần tải lên Google Drive.
