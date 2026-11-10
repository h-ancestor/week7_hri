# Nguồn map

`map.pgm` và `map.yaml` là bản sao không chỉnh sửa từ `bài thực hành 04/maps/`, map được lưu từ SLAM Toolbox trong mô phỏng TurtleBot 4 warehouse (560×472, 0.05 m/pixel). Map chỉ khảo sát một phần, có vùng nhiễu và không đủ cơ sở để khẳng định nhãn phòng/hành lang. `config/regions.yaml` chứa ba waypoint mẫu; các tọa độ chỉ là ứng viên free-space ban đầu, cần xác nhận bằng RViz/AMCL/Nav2 trước khi chạy robot.
