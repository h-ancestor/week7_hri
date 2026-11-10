#!/usr/bin/env python3
"""Build an illustrated, editable DOCX report with embedded figures and tables."""
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
from xml.sax.saxutils import escape
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / 'reports'
FIG = REPORTS / 'figures'
OUT = REPORTS / 'bao_cao_bai_thuc_hanh_07.docx'
PAGE_W, PAGE_H = 11906, 16838
MARGIN = 900
CONTENT_W = PAGE_W - 2*MARGIN
EMU = 914400
IMG_IDS = {}

def r(text, size=22, bold=False, color=None, italic=False, font='Times New Roman'):
    p = [f'<w:rFonts w:ascii="{font}" w:hAnsi="{font}" w:eastAsia="{font}"/>',f'<w:sz w:val="{size}"/>']
    if bold: p.append('<w:b/>')
    if italic: p.append('<w:i/>')
    if color: p.append(f'<w:color w:val="{color}"/>')
    return '<w:r><w:rPr>'+''.join(p)+'</w:rPr><w:t xml:space="preserve">'+escape(text)+'</w:t></w:r>'

def p(text='', size=22, bold=False, color=None, align=None, before=0, after=110, italic=False, indent=0):
    props=[f'<w:spacing w:before="{before}" w:after="{after}" w:line="290" w:lineRule="auto"/>']
    if align: props.append(f'<w:jc w:val="{align}"/>')
    if indent: props.append(f'<w:ind w:left="{indent}"/>')
    return '<w:p><w:pPr>'+''.join(props)+'</w:pPr>'+r(text,size,bold,color,italic)+'</w:p>'

def heading(text, level=1):
    size=30 if level==1 else 25
    return p(text,size=size,bold=True,color='174A70',before=100 if level==1 else 80,after=120)

def rich_paragraph(parts, after=100, align=None):
    props=f'<w:spacing w:after="{after}" w:line="290" w:lineRule="auto"/>'
    if align: props+=f'<w:jc w:val="{align}"/>'
    return '<w:p><w:pPr>'+props+'</w:pPr>'+''.join(r(t,size=s,bold=b,color=c,italic=i) for t,s,b,c,i in parts)+'</w:p>'

def table(rows, widths=None, font_size=18, header=True):
    cols=max(len(row) for row in rows)
    if widths is None: widths=[CONTENT_W//cols]*cols
    widths=widths[:cols]
    borders='<w:tblBorders><w:top w:val="single" w:sz="5" w:color="9EB2BD"/><w:left w:val="single" w:sz="5" w:color="9EB2BD"/><w:bottom w:val="single" w:sz="5" w:color="9EB2BD"/><w:right w:val="single" w:sz="5" w:color="9EB2BD"/><w:insideH w:val="single" w:sz="4" w:color="B8C7CF"/><w:insideV w:val="single" w:sz="4" w:color="B8C7CF"/></w:tblBorders>'
    xml=['<w:tbl><w:tblPr><w:tblW w:w="0" w:type="auto"/><w:tblLayout w:type="fixed"/>',borders,'<w:tblCellMar><w:top w:w="70" w:type="dxa"/><w:left w:w="85" w:type="dxa"/><w:bottom w:w="70" w:type="dxa"/><w:right w:w="85" w:type="dxa"/></w:tblCellMar></w:tblPr><w:tblGrid>']
    for w in widths: xml.append(f'<w:gridCol w:w="{w}"/>')
    xml.append('</w:tblGrid>')
    for ri,row in enumerate(rows):
        xml.append('<w:tr>')
        for ci,cell in enumerate(row):
            val=str(cell)
            shade='<w:shd w:fill="DCEAF1"/>' if header and ri==0 else ''
            xml.append(f'<w:tc><w:tcPr><w:tcW w:w="{widths[ci]}" w:type="dxa"/>{shade}<w:vAlign w:val="center"/></w:tcPr>')
            xml.append(p(val,size=font_size,bold=header and ri==0,color='173C53' if header and ri==0 else None,after=10))
            xml.append('</w:tc>')
        xml.append('</w:tr>')
    xml.append('</w:tbl><w:p><w:pPr><w:spacing w:after="55"/></w:pPr></w:p>')
    return ''.join(xml)

def image(name, caption, max_width=CONTENT_W, max_height=int(3.2*EMU)):
    # Caller width is in twips; DrawingML extents use EMU.
    if max_width < 100000: max_width = int(max_width / 1440 * EMU)
    path=FIG/name
    with Image.open(path) as im: w,h=im.size
    scale=min(max_width/w,max_height/h)
    cx,cy=int(w*scale),int(h*scale)
    rid=IMG_IDS[name]
    drawing=(f'<w:p><w:pPr><w:jc w:val="center"/><w:spacing w:before="40" w:after="20"/></w:pPr>'
      f'<w:r><w:drawing><wp:inline distT="0" distB="0" distL="0" distR="0">'
      f'<wp:extent cx="{cx}" cy="{cy}"/><wp:effectExtent l="0" t="0" r="0" b="0"/>'
      f'<wp:docPr id="{len(IMG_IDS)}" name="{escape(name)}" descr="{escape(caption)}"/>'
      f'<wp:cNvGraphicFramePr><a:graphicFrameLocks xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" noChangeAspect="1"/></wp:cNvGraphicFramePr>'
      f'<a:graphic xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"><a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture">'
      f'<pic:pic xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture"><pic:nvPicPr><pic:cNvPr id="0" name="{escape(name)}"/><pic:cNvPicPr/></pic:nvPicPr>'
      f'<pic:blipFill><a:blip r:embed="{rid}"/><a:stretch><a:fillRect/></a:stretch></pic:blipFill>'
      f'<pic:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="{cx}" cy="{cy}"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom></pic:spPr>'
      f'</pic:pic></a:graphicData></a:graphic></wp:inline></w:drawing></w:r></w:p>')
    return drawing+p(caption,size=17,color='586C77',align='center',after=90)

def pagebreak(): return '<w:p><w:r><w:br w:type="page"/></w:r></w:p>'

# Four local, embedded figures used by the report.
image_names=['map_so_sanh.png','architecture.png','pipeline_segmentation.png','demo_tuyen_C_B.png']
for idx,name in enumerate(image_names,1): IMG_IDS[name]=f'rId{idx}'
body=[]
# PAGE 1: cover and actual map evidence.
body += [p('BÁO CÁO THỰC HÀNH TUẦN 07',size=34,bold=True,color='174A70',align='center',before=120,after=70),
 p('PHÂN VÙNG BẢN ĐỒ VÀ ĐIỀU HƯỚNG ROBOT BẰNG GIỌNG NÓI',size=25,bold=True,color='2C637F',align='center',after=60),
 p('Ubuntu 22.04 · ROS 2 Humble · TurtleBot 4 Simulation · Nav2',size=20,align='center',after=180),
 p('Sinh viên: ........................................................................................................',size=21,after=70),
 p('Lớp: ......................................................     Ngày: 10/11/2026',size=21,after=140),
 p('Mục tiêu: gắn nhãn vùng trên occupancy grid, chuyển câu lệnh tiếng Việt thành waypoint, điều hướng robot qua Nav2 và ghi lại kết quả trên dashboard/RViz.',size=23,align='center',after=130),
 image('map_so_sanh.png','Hình 1. Bản đồ occupancy gốc và kết quả phân vùng ngữ nghĩa A/B/C.',CONTENT_W,int(3.0*EMU)),
 table([['03 vùng','14/14 test','04 tuyến','Video xác minh'],['A · B · C','đạt','Nav2 hoàn tất','H.264/AAC · 1600×600']],font_size=18),
 p('Tệp video cần nộp riêng lên Drive: tuan7_demo_phan_vung_va_dieu_huong.mp4 · 27 phút 03,7 giây. Bước Z được bỏ qua theo phạm vi chạy.',size=17,color='536873',align='center',after=0)]
body.append(pagebreak())
# PAGE 2
body += [heading('TÓM TẮT VÀ PHẠM VI ĐÁNH GIÁ'),
 p('Bản đồ occupancy grid thuận tiện cho định vị và lập kế hoạch nhưng không cung cấp tên gọi gần gũi với người sử dụng. Bài làm bổ sung lớp semantic map để các tọa độ trên map có thể được gọi bằng “khu vực A”, “phòng thí nghiệm” hoặc “hành lang”. Node ROS 2 nhận transcript, chuẩn hóa tiếng Việt, tìm các vùng trong cấu hình và gửi một chuỗi goal NavigateToPose theo đúng thứ tự.',size=22),
 p('Ảnh map có 560×472 pixel, resolution 0,05 m/pixel và origin [-13,1; -11,9; 0]. OpenCV tìm connected components của pixel free, kiểm tra ba seed, rồi phân chia phần không gian tự do được seed theo khoảng cách tới waypoint. Kết quả ảnh được tô màu và gắn nhãn; file JSON lưu vùng và tọa độ để kiểm tra lại.',size=22),
 p('Kiểm thử phần mềm được ghi nhận 14/14 đạt và build colcon thành công. Log mô phỏng xác nhận bốn lệnh: tới A, tới B, A→B và C→B. Hai route nhiều chặng có log gửi goal tuần tự và hoàn tất. Video được xác minh có cả khung RViz và dashboard. Báo cáo không gán độ chính xác ASR theo phần trăm vì chưa có tập âm thanh tham chiếu được gán transcript để tính WER.',size=22),
 heading('CẤU TRÚC BÁO CÁO',2),
 table([['Phần','Nội dung'],['1–3','Yêu cầu, kiến trúc ROS và nguồn map'],['4–6','Phân vùng ảnh, waypoint và parser câu lệnh'],['7–9','Vosk/dashboard, Nav2 và ảnh tuyến C→B'],['10–13','Test, kết quả chạy, giới hạn, cách tái lập']],font_size=19),
 p('Các hình trong báo cáo được nhúng vào tệp Word nên không phụ thuộc đường dẫn ảnh bên ngoài. Tệp nguồn ảnh cũng được giữ tại reports/figures để tiện cập nhật.',size=20),
 p('Mục tiêu kỹ thuật là kiểm chứng toàn bộ chuỗi xử lý chứ không chỉ chạy riêng mô hình nhận dạng: dữ liệu map phải hợp lệ; tên vùng phải tra cứu được; câu nhiều điểm phải giữ thứ tự; action phải trả trạng thái; giao diện phải chờ action trước khi chuyển bước. Cách chia lớp giúp phân biệt lỗi cấu hình map, lỗi parser, localization và planner.',size=22),
 p('Đầu ra được chia thành hai nhóm: artefact chạy được (source, cấu hình, map, model và test) và minh chứng kết quả (log, ảnh chụp màn hình, video, báo cáo). Video được giữ riêng để nộp qua Drive; thư mục GitHub tuần 7 chỉ chứa source cùng hướng dẫn để tránh repository quá nặng.',size=22)]
body.append(pagebreak())
# PAGE 3
body += [heading('1. YÊU CẦU VÀ TIÊU CHÍ NGHIỆM THU'),
 p('Đề bài đặt ra bốn yêu cầu cốt lõi. Một là chia occupancy map thành ít nhất ba khu vực có nhãn. Hai là tạo semantic mapping và pose đích hợp lệ. Ba là nhận dạng/diễn giải câu lệnh tiếng Việt. Bốn là gửi goal qua Nav2, đi qua vùng trung gian khi câu lệnh chỉ định tuyến và xử lý vùng không tồn tại mà không phát goal sai.',size=22),
 table([['Yêu cầu','Thiết kế thực hiện','Bằng chứng kiểm tra'],['Phân vùng ≥3 vùng','OpenCV + ba seed A/B/C, overlay PNG','map_segmented.png; JSON 3 vùng'],['Semantic mapping','regions.yaml: ID, tên, alias, pixel, pose','Các seed được test trên ô free'],['Nhận lệnh','Chuẩn hóa Unicode, regex theo alias','Unit test parser và log route'],['Nav2','Action NavigateToPose, frame map','4 route kết thúc trong log'],['Vùng không tồn tại','Không tra thấy ID thì báo lỗi','Unit test Z; bỏ qua Z ở demo']],font_size=18),
 p('Điều kiện tiên quyết khi chạy là map server và AMCL hoạt động, transform đến frame map sẵn sàng, Nav2 lifecycle active, và initial pose được đặt. Nếu bỏ qua khởi tạo localization, action có thể không lập được đường hoặc dùng pose ban đầu sai. Do đó kết quả nghiệm thu được phân tầng: test logic độc lập; build package; chạy simulator; sau cùng quan sát robot và dashboard.',size=22),
 p('Bằng chứng video cần đồng thời cho thấy trạng thái hệ thống và chuyển động. Bản demo ghép cửa sổ RViz với dashboard theo chiều ngang, không lấy toàn màn hình. Bảng kết quả ở phần 11 ghi riêng từng lệnh, vùng được phân giải, thứ tự goal và trạng thái cuối.',size=22),
 p('Tiêu chí “đúng đích” trong mô phỏng là action Nav2 trả kết quả thành công với waypoint cấu hình và localization/costmap cho thấy robot đến vùng tương ứng. Unit test không xác nhận chuyển động; log action cũng không chứng minh tên gọi vật lý của phòng. Báo cáo vì vậy tách ảnh segmentation, kết quả parse và trạng thái route.',size=22),
 p('Phạm vi không gồm điều khiển robot thật, kiểm tra an toàn với người trong môi trường thật, hay đo WER. Vùng Z có unit test parser riêng nhưng không được chạy trong video theo yêu cầu demo.',size=22),
 p('Tiêu chí “đúng đích” trong mô phỏng được hiểu là action Nav2 trả kết quả thành công với waypoint cấu hình và AMCL/costmap cho thấy robot tới vùng tương ứng. Bộ test đơn vị không thể xác nhận chuyển động; log action cũng không xác nhận tên gọi vật lý của phòng. Vì thế báo cáo tách riêng ảnh segmentation, kết quả parse và trạng thái route thay vì gộp thành một nhận xét chung.',size=22),
 p('Phạm vi không bao gồm điều khiển robot thật, kiểm tra an toàn người–robot trong môi trường có người, hay đánh giá WER. Bước Z có unit test ở mức parser nhưng được bỏ qua trong video theo yêu cầu demo.',size=22)]
body.append(pagebreak())
# PAGE 4
body += [heading('2. KIẾN TRÚC ROS 2 VÀ LUỒNG DỮ LIỆU'),
 image('architecture.png','Hình 2. Kiến trúc node và các luồng dữ liệu trong hệ thống.',CONTENT_W,int(3.5*EMU)),
 p('Lớp giao tiếp gồm microphone, Vosk và dashboard. Lớp điều phối là `voice_navigation.py`: chuẩn hóa transcript, ánh xạ alias sang ID, tra cấu hình waypoint và vận hành action client. Lớp robot gồm map server, AMCL, Nav2, TurtleBot 4 và Gazebo. Tách lớp cho phép kiểm tra parser mà không cần bật robot.',size=22),
 p('Topic `/voice_command` dùng `std_msgs/String` làm đầu vào văn bản. `/amcl_pose` dùng để chờ localization. Action `/navigate_to_pose` nhận từng pose trong frame `map`. Simulator cung cấp `/clock`, scan, odometry và TF. Dashboard hiển thị câu lệnh đang chờ, transcript/log và trạng thái điều hướng.',size=22),
 p('Parser quyết định câu tương ứng với ID nào; semantic map cung cấp pose; Nav2 lập kế hoạch và điều khiển robot. Khi transcript không chứa vùng hợp lệ, node báo lỗi trước khi gọi action. Với route nhiều chặng, callback kết quả của goal hiện tại khởi tạo goal kế tiếp chỉ khi chặng hiện tại thành công. Nhờ đó, thứ tự được kiểm chứng ở cả logic lẫn log runtime.',size=22),
 p('AMCL và map server phối hợp trong frame map. AMCL dùng laser scan/odom để ước lượng transform map→odom; robot state publisher cùng odometry cung cấp chuỗi TF tới base_link. Costmap tổng hợp static map và dữ liệu cảm biến để planner/controller chọn đường an toàn. Khi RViz báo localization inactive hoặc TF thiếu, cần xử lý điều kiện này trước khi diễn giải lỗi goal.',size=22),
 p('Trong triển khai, `voice_dashboard` quản lý cửa sổ hướng dẫn; node điều hướng phụ trách ROS subscription/action. Bố trí process riêng tránh chặn GUI khi action đang chờ. Giao diện chỉ hiển thị chỉ dẫn tiếp theo sau callback kết quả, nhờ vậy người dùng không vô tình gửi lệnh mới trong khi route cũ còn chạy.',size=22)]
body.append(pagebreak())
# PAGE 5
body += [heading('3. DỮ LIỆU MAP VÀ HỆ TỌA ĐỘ'),
 image('map_so_sanh.png','Hình 3. Map gốc bên trái và lớp vùng ngữ nghĩa bên phải; các nhãn được đặt trên không gian tự do.',CONTENT_W,int(3.5*EMU)),
 p('Map đầu vào gồm `maps/map.pgm` và `maps/map.yaml`. Metadata: mode trinary; resolution 0,05 m; origin [-13,1; -11,9; 0]; negate 0; occupied threshold 0,65; free threshold 0,25. Nguồn map và quan hệ với map SLAM được ghi trong SOURCE.md của workspace.',size=22),
 p('Ảnh số có gốc ở góc trên trái nên v tăng xuống. Tọa độ map có y tăng lên. Với chiều cao H=472, pixel center (u,v) đổi sang world như sau:',size=22),
 p('x = x₀ + (u + 0,5) r     ;     y = y₀ + (H − v − 0,5) r',size=24,bold=True,color='174A70',align='center',before=30,after=130),
 p('Ví dụ A tại (140,120): x=−13,1+(140,5×0,05)=−6,075 m; y=−11,9+(351,5×0,05)=5,675 m. Hàm `pixel_to_world` còn tính phép quay theo origin yaw. Unit test xác nhận cả đổi trục y và các seed của bản đồ hiện tại.',size=22),
 p('Bản map có nhiễu và các không gian nối nhau; nhãn A/B/C là waypoint thử nghiệm chứ chưa là phân loại kiến trúc đã khảo sát. Pixel seed nằm trong ô free chỉ là điều kiện cần; trước khi dùng map khác cần xem footprint, inflation radius và khoảng trống quay trên RViz.',size=21),
 p('Mode trinary ánh xạ xác suất occupancy thành occupied, free hoặc unknown theo hai threshold. Những ô unknown không nên xem như lối đi; ảnh segmentation chỉ nhận pixel trắng gần mức 255 làm free, do đó vùng xám và đen không bị gán vào partition. Ảnh PGM là grayscale 8-bit; độ phân giải bảo đảm tọa độ đổi từ pixel sang mét nhất quán.',size=21),
 p('Khi origin yaw khác 0, hàm đổi tọa độ trước tiên tính vector cục bộ rồi quay bằng cos(yaw), sin(yaw). Hiện map dùng yaw 0 nên phép quay không làm thay đổi kết quả. Sai số chọn pixel ±1 tương ứng khoảng ±0,05 m theo mỗi trục; điểm tâm pixel có offset 0,5 cell để tránh lệch nửa ô.',size=21)]
body.append(pagebreak())
# PAGE 6
body += [heading('4. THUẬT TOÁN PHÂN VÙNG VÀ ẢNH ĐẦU RA'),
 image('pipeline_segmentation.png','Hình 4. Pipeline xử lý ảnh occupancy, tạo connected components và phân vùng theo semantic seed.',CONTENT_W,int(2.5*EMU)),
 p('Hàm `load_map` đọc YAML, giải quyết đường dẫn ảnh tương đối và tải PGM thành grayscale. Hàm `segment` tạo mask bằng điều kiện pixel xám ≥250, rồi gọi `cv2.connectedComponentsWithStats` với connectivity 8. Thành phần nhỏ hơn 40 pixel không được đưa vào danh sách mô tả. Bản đồ hiện tại có bốn thành phần free vượt ngưỡng; component lớn nhất có 111.780 pixel.',size=21),
 p('Exporter kiểm tra mỗi seed nằm trong biên ảnh và pixel tại seed có giá trị free. Các seed thuộc cùng component được so khoảng cách bình phương `(x−u)²+(y−v)²`; mỗi pixel của component được gán cho seed gần nhất. Mask được pha màu trên nền xám, sau đó vẽ marker và nhãn A/B/C.',size=21),
 p('Cách làm này giữ tường và biên của component; không cần watershed. Tuy nhiên khi hành lang/phòng nằm trong cùng một component, ranh giới Voronoi chỉ chia vùng theo hình học, không phát hiện cửa hay chức năng phòng. Nếu map có tường hở do SLAM, các vùng nhập làm một component lớn. Muốn segmentation kiến trúc chính xác cần chỉnh map hoặc vẽ polygon ranh giới có giám sát.',size=21),
 p('Đầu ra `map_segmented.png` phục vụ kiểm tra trực quan; `segmented_regions.json` ghi map, component centroid, ID, nhãn, alias, pixel, goal và diện tích pixel từng partition.',size=21),
 p('Nếu N là số pixel và K là số seed cùng component, bước gán nhãn tính khoảng cách tới K seed nên chi phí xấp xỉ O(NK); K hiện bằng tối đa ba nên phù hợp với map nhỏ 560×472. Dùng khoảng cách bình phương tránh phép căn bậc hai không cần thiết. Connected components chạy tuyến tính theo số pixel.',size=21),
 p('Ngưỡng 250 được chọn để chỉ lấy vùng gần trắng, giảm nguy cơ đưa ô xám chưa chắc chắn vào mặt nạ đi được. Đổi ngưỡng có thể làm vùng free phân mảnh hoặc nối qua nhiễu. Kiểm tra định lượng gồm số component, diện tích và kiểm tra từng seed; kiểm tra trực quan gồm so ảnh màu cạnh PGM gốc để phát hiện vùng tô đè tường.',size=21)]
body.append(pagebreak())
# PAGE 7
body += [heading('5. SEMANTIC MAP VÀ WAYPOINT'),
 p('`config/regions.yaml` là nguồn cấu hình sử dụng trong node. Mỗi bản ghi vùng có ID, tên hiển thị, alias nhận dạng, pixel seed và goal x/y/yaw. Exporter chuyển pixel seed sang frame map, đồng thời lưu kết quả trong JSON. B dùng tên “Phòng thí nghiệm” để có một alias giàu ngữ nghĩa; C được gọi là “Hành lang C”.',size=22),
 table([['ID / nhãn','Pixel seed','Goal map (m, rad)','Diện tích mask'],['A · Khu vực A','(140,120)','(−6,075; 5,675; 0)','24.729 px ≈61,82 m²'],['B · Phòng thí nghiệm','(320,200)','(2,925; 1,675; 0)','73.429 px ≈183,57 m²'],['C · Hành lang C','(260,360)','(−0,075; −6,325; 0)','13.622 px ≈34,06 m²']],font_size=19),
 p('Diện tích quy đổi dùng số pixel trong mask nhân resolution²=0,0025 m²/pixel. Nó mô tả phần mặt nạ tự do được Voronoi gán, không phải diện tích phòng đo vật lý. Tổng diện tích không bao gồm occupied, unknown và các component không có waypoint.',size=21),
 p('Điểm đích được gửi dưới dạng pose orientation yaw=0.0 rad. Một lần thay map đòi hỏi cập nhật origin/resolution hoặc tính lại pose; giữ tọa độ cũ có thể đưa robot tới vị trí khác. Kiểm tra cần bao gồm hiển thị marker, xác nhận ô free, khoảng cách đến obstacle và thử action ở tốc độ thấp trước khi chạy cả route.',size=21),
 p('Danh sách aliases phải đủ hẹp. Alias nhiều biến thể tăng khả năng chịu lỗi âm học nhưng tăng false positive. Các test hồi quy cho transcript A/B và câu “khu vực Z” bảo vệ trường hợp tên vùng lạ không vô tình khớp một alias ngắn.',size=21),
 p('Trường `pixel` hữu ích khi xem overlay; trường `goal` là giá trị node gửi đi. Hai giá trị được kiểm tra đồng bộ qua hàm chuyển đổi trong exporter. Nếu người dùng chỉnh pixel seed nhưng giữ goal cũ, hình minh họa và điều hướng sẽ không còn khớp; cần chạy lại segmentation exporter để cập nhật JSON và đối chiếu YAML.',size=21),
 p('Diện tích A/B/C lần lượt khoảng 61,82; 183,57; 34,06 m² theo số ô partition × 0,0025. Chênh lệch lớn thể hiện vùng B chiếm phần lớn component free được seed. Đây là diện tích mask tính toán, không phải số đo không gian vật lý; nên dùng để kiểm tra pipeline chứ không dùng cho thiết kế kiến trúc.',size=21)]
body.append(pagebreak())
# PAGE 8
body += [heading('6. PHÂN TÍCH VĂN BẢN VÀ LẬP TUYẾN'),
 p('Hàm `normalize` chuyển về chữ thường, Unicode NFD, đổi đ thành d, bỏ combining marks và thay dấu câu/ký tự không phải chữ-số bằng khoảng trắng. Tìm alias bằng regex có ranh giới từ. Các match được sắp theo vị trí trong câu; khớp lồng cùng vùng bị gộp, còn khớp chồng lấn giữa hai vùng khác nhau bị coi là mơ hồ.',size=22),
 table([['Câu ví dụ','ID trả về','Hành vi điều hướng'],['Đi đến khu vực A','A','Gửi một goal'],['Đi đến phòng thí nghiệm','B','Gửi một goal'],['Đi từ khu vực A đến phòng thí nghiệm','A → B','Gửi A, chờ xong rồi gửi B'],['Đi qua hành lang rồi đến phòng thí nghiệm','C → B','Gửi C, chờ xong rồi gửi B'],['Đi đến khu vực Z','Không có ID hợp lệ','Báo lỗi, không gửi action']],font_size=18),
 p('`has_navigation_intent` lọc đoạn nhận dạng không có động từ/ý định điều hướng để giảm log báo lỗi cho im lặng hoặc tiếng ồn. Parser từ chối khi không có alias đích, alias không rõ nghĩa hoặc không có ý định đi. Với lệnh từ A đến B, thứ tự vùng được giữ theo câu; robot không tự bỏ qua vùng xuất phát chỉ vì localization hiện tại đang ở vị trí khác.',size=22),
 p('14 unit test gồm các trường hợp alias, câu đơn, route, transcript biến thể, unknown region, noise, pixel conversion và segmentation. Unit test vùng Z xác nhận parser từ chối cả câu ngắn lẫn prompt dài chứa tên vùng chưa khai báo.',size=21),
 p('Một rủi ro parser là thứ tự match: alias “khu vực” chung không được phép ăn mất tên vùng cụ thể. Mã dùng boundary và sắp theo chỉ số ký tự, rồi gộp match lồng cùng ID. Nếu câu chứa hai vùng khác nhau nhưng overlap, parser chủ động báo mơ hồ thay vì chọn ngẫu nhiên. Lọc navigation intent ngăn âm thanh ngắn không mang động từ đi được báo như một lỗi vùng.',size=21),
 p('Ví dụ thực tế cho route nhiều điểm là cấu trúc [C,B]. Nếu node chỉ trả B, hành lang sẽ không được dùng làm waypoint trung gian. Log runtime xác nhận C được gửi trước B; đây là đối chiếu end-to-end quan trọng cho thuật toán parse thứ tự.',size=21)]
body.append(pagebreak())
# PAGE 9
body += [heading('7. NHẬN DẠNG ÂM THANH VÀ DASHBOARD'),
 p('Workspace kèm Vosk model tiếng Việt `vosk-model-small-vn-0.4`, dependency `vosk==0.3.45` và tham số `use_microphone`. Khi bật mic, node kiểm tra model, xác nhận `arecord`, thu PCM mono 16 kHz rồi feed audio vào recognizer. Kết quả text đi vào parser chung. Cấu trúc này cho phép thay nguồn audio hoặc test transcript mà không viết lại điều hướng.',size=22),
 p('Dashboard là GUI hướng dẫn từng bước: sau khi nhận AMCL pose, nó hiện prompt; khi có câu hợp lệ, hiển thị transcript và vùng parse; trong lúc action chạy, trạng thái “đang di chuyển” được giữ; khi route kết thúc, dashboard hiện bước kế tiếp. Người quay có thể xem hướng dẫn mà không cần quan sát terminal nền.',size=22),
 table([['Trạng thái GUI','Ý nghĩa'],['Đang chờ câu lệnh','Node đã sẵn sàng nhận command'],['Đang di chuyển','Nav2 action đang xử lý waypoint'],['Hoàn tất tuyến','Tất cả waypoint của lệnh đã xong'],['Tên vùng không hợp lệ','Parser từ chối; không gửi goal']],font_size=19),
 p('Trong log của phiên cuối, node thông báo microphone mở và xuất các dòng nhận dạng/phân giải. Tuy nhiên không có corpus audio được gán transcript để tính WER, precision hoặc tỷ lệ nhận sai theo người nói. Vì vậy báo cáo xác nhận pipeline và các kết quả route có log, nhưng không đưa ra phần trăm chính xác ASR. Đánh giá định lượng cần ghi âm nhiều câu/giọng nói và đối chiếu transcript tham chiếu.',size=22),
 p('Các hướng cải tiến là ngưỡng confidence, từ chối transcript mơ hồ, xác nhận vùng bằng tiếng nói tổng hợp, hiển thị confidence trên GUI và kiểm tra nhiều mức ồn/khoảng cách mic.',size=21),
 p('`arecord` cung cấp PCM đơn kênh 16.000 mẫu/giây; node thu theo khung để không phải lưu toàn bộ buổi ghi vào RAM. Model Vosk nhỏ chạy offline, không cần gửi âm thanh lên dịch vụ đám mây. Chất lượng phụ thuộc gain, quyền thiết bị, tiếng vọng và khoảng cách. Khi mic không mở, node cần log lỗi thiết bị/model rõ ràng để người vận hành phân biệt với “không nhận ra tên vùng”.',size=21),
 p('Một đánh giá đầy đủ sẽ phân loại lỗi thành: không có transcript, transcript sai từ, parser sai ID, parser từ chối đúng, và Nav2 không tới goal. Bảng confusion theo A/B/C/Z cùng WER cho phép xác định nên sửa model, từ điển alias hay waypoint. Không gộp các loại lỗi này thành một tỷ lệ “nhận dạng đúng” duy nhất.',size=21)]
body.append(pagebreak())
# PAGE 10
body += [heading('8. NAV2: GỬI GOAL VÀ XỬ LÝ LỖI'),
 p('Node tạo `NavigateToPose.Goal` với `PoseStamped` trong frame `map`. Action client đợi server và gửi mỗi goal bất đồng bộ. Callback goal response phát hiện server từ chối; callback result đọc trạng thái thành công/thất bại. Sau kết quả thành công, chỉ số waypoint tăng; nếu còn vùng thì node gửi pose tiếp. Nếu một chặng thất bại, route kết thúc và giao diện báo trạng thái lỗi.',size=22),
 table([['Bước','Kiểm tra / hành động','Kết quả mong đợi'],['1','Localization có pose AMCL','Robot có vị trí ban đầu'],['2','Parser trả ID vùng theo thứ tự','Ví dụ [C,B]'],['3','Tra pose trong YAML','Có x/y/yaw hợp lệ'],['4','Gửi NavigateToPose','Nav2 lập kế hoạch'],['5','Chờ action result','Thành công mới sang điểm kế'],['6','Hoàn tất hết route','Dashboard chuyển hướng dẫn']],font_size=18),
 p('Nav2 chịu trách nhiệm lập đường toàn cục, điều khiển cục bộ và phản ứng với costmap/sensor. Tránh vật cản là chức năng của cấu hình Nav2 và sensor trong simulator, không phải parser câu. Nếu goal nằm sát tường, planner có thể báo không có đường; nếu AMCL sai, robot điều khiển theo vị trí estimate lệch. Do đó quan sát RViz trong demo là bằng chứng quan trọng, song không thay thế kiểm thử an toàn trên robot thật.',size=22),
 p('Trong kết quả A→B, log gửi A trước B. Trong tuyến C→B, log gửi C rồi B. Cả hai route chỉ báo hoàn tất sau goal cuối. Đây là bằng chứng node vận hành chuỗi action thay vì chỉ parse câu xong dừng.',size=22),
 p('Action server có thể chưa sẵn sàng khi node khởi động; client cần đợi server trước khi send goal. Goal response cho biết request có được chấp nhận; result trả trạng thái cuối. Node cần phân biệt bị từ chối goal, action aborted và thành công để dashboard báo đúng. Với mỗi chặng, callback kiểm tra kết quả rồi tăng index waypoint; khi thất bại, không gửi các chặng còn lại.',size=22),
 p('Obstacle avoidance phụ thuộc scan, odometry, footprint và costmap parameters. Trong RViz có thể thấy global plan, local costmap và trạng thái Navigation 2. Nếu robot đứng yên, cần kiểm tra action server, AMCL, `/cmd_vel`, controller activation và topic scan thay vì sửa parser. Việc ghi log “gửi goal” không đồng nghĩa robot đã tới; chỉ log hoàn tất mới đóng route.',size=22)]
body.append(pagebreak())
# PAGE 11
body += [heading('9. ẢNH DEMO: ROBOT ĐANG CHẠY C → B'),
 p('Hình dưới được lấy trực tiếp từ video cuối tại thời điểm robot còn đang tiến tới waypoint B. Cửa sổ RViz bên trái hiển thị bản đồ, costmap, localization và robot; dashboard bên phải hiển thị lệnh “đi qua hành lang rồi đến phòng thí nghiệm” và log đã gửi goal C, tiếp theo goal B. Log về sau xác nhận tuyến hoàn tất.',size=21),
 image('demo_tuyen_C_B.png','Hình 5. Khung hình demo thật trong lúc tuyến C→B đang chạy; không phải ảnh minh họa dựng.',CONTENT_W,int(4.0*EMU)),
 heading('Tóm tắt log chặng cuối',2),
 table([['Dấu mốc','Dòng log / ý nghĩa'],['Nhận câu','Transcript hiển thị tuyến hành lang → phòng thí nghiệm'],['Phân giải','Lệnh: C → B'],['Goal 1','Gửi goal Nav2 tới vùng C'],['Goal 2','Gửi goal Nav2 tới vùng B sau khi chặng C xong'],['Kết quả','Nav2 đã hoàn thành tuyến; dashboard hiện prompt tiếp']],font_size=18),
 p('Video hoàn chỉnh lưu tại `tuan7_demo_phan_vung_va_dieu_huong.mp4`; ảnh trong báo cáo là một khung đại diện để người đọc nhìn thấy map và GUI mà không phải mở ngay video dài.',size=20),
 p('Trong khung hình, RViz chiếm nửa trái và dashboard nửa phải. RViz cho thấy localization/costmap active, robot tại vùng hành lang và khoảng cách ngắn còn lại tới đích; dashboard giữ đúng câu C→B. Dòng log cuối cùng xuất hiện sau khung được trích xác nhận Nav2 hoàn thành và giao diện chuyển sang prompt tiếp theo.',size=21),
 p('Video có kích thước 1600×600, phù hợp hai cửa sổ 800×600 ghép ngang. H.264 lưu hình và AAC lưu âm thanh đầu vào. Metadata kiểm tra được duration 1623,667 giây và size 101.130.126 byte. Tệp đã đóng moov atom hợp lệ; người nhận có thể mở bằng VLC/Movies hoặc upload lên Drive.',size=21)]
body.append(pagebreak())
# PAGE 12
body += [heading('10. KẾT QUẢ ĐỊNH LƯỢNG VÀ KIỂM THỬ'),
 table([['Lệnh','Parse','Goal theo thứ tự','Timestamp log đến hoàn tất*','Trạng thái'],['Tới khu vực A','A','A','≈125,6 s','Hoàn tất'],['Tới phòng thí nghiệm','B','B','≈115,8 s','Hoàn tất'],['Từ A tới phòng thí nghiệm','A→B','A rồi B','≈253,7 s','Hoàn tất'],['Qua hành lang tới phòng thí nghiệm','C→B','C rồi B','≈238,2 s','Hoàn tất']],font_size=17),
 p('*Khoảng thời gian là hiệu giữa dấu thời gian log nhận command và log hoàn tất trong phiên mô phỏng, gồm thời gian chờ giữa action; chỉ mô tả phiên này, không phải benchmark tốc độ.',size=17,italic=True),
 heading('Bằng chứng kiểm thử phần mềm',2),
 table([['Kiểm tra','Kết quả','Mục đích'],['Unit test','14/14 đạt','Parser, segmentation, pixel/world, free-space seeds'],['colcon build','Thành công','Đóng gói ament_python và entry points'],['py_compile','Thành công','Cú pháp module Python'],['Video ffprobe','H.264/AAC · 1600×600 · 1623,667 s','Đảm bảo MP4 đóng hợp lệ'],['Z trong demo','Bỏ qua','Không gửi vùng không tồn tại theo yêu cầu']],font_size=18),
 p('Kết quả điều hướng lấy từ log node và trạng thái Nav2, không chỉ từ việc parser in được ID. Tuyến A→B và C→B đều có hai goal theo đúng thứ tự rồi mới ghi “Nav2 đã hoàn thành tuyến”.',size=21),
 p('Bộ test parser có nhánh unknown-Z, nhưng demo vận hành không chạy prompt Z. Đây là hai loại minh chứng khác nhau: logic unknown được unit test; video tập trung vào bốn lệnh route hợp lệ.',size=21),
 p('Timestamps node ghi A nhận lúc 1794320001, hoàn tất 1794320127; B nhận lúc 1794320157, hoàn tất 1794320273; route A→B kết thúc 1794320564; route C→B nhận lúc 1794321338, gửi B tại 1794321461 và hoàn tất lúc 1794321576. Sai khác giữa các mốc giải thích thời lượng route; timestamp epoch được giữ trong log ROS tại `.ros/log`.',size=21),
 p('Đối chiếu 14 test giúp xác nhận sửa alias “đề” không làm hỏng các biến thể B hợp lệ. Test map kiểm tra shape 472×560 và mỗi seed >=250 grayscale; test pixel conversion xác nhận tâm pixel (0,0) chuyển thành (0,5; 9,5) khi resolution=1 và origin=(0,0).',size=21)]
body.append(pagebreak())
# PAGE 13
body += [heading('11. HẠN CHẾ, TÁI LẬP VÀ KẾT LUẬN'),
 heading('Hạn chế và cải tiến',2),
 p('Ranh giới vùng phụ thuộc connected components và seed waypoint, nên chất lượng map ảnh hưởng trực tiếp kết quả. Cần xác minh các nhãn semantic với bố cục thật; current map ghi nhận waypoint thử nghiệm. ASR chưa được đánh giá định lượng trên bộ audio có nhãn; alias nên được kiểm soát để tránh nhận nhầm. Kết quả chỉ chứng minh cấu hình mô phỏng này, không suy rộng sang robot thật.',size=21),
 p('Cải tiến phù hợp gồm vẽ polygon ranh giới có giám sát; tự kiểm tra khoảng cách goal đến obstacle; lưu rosbag; đo WER và tỷ lệ route đúng; ghi pose cuối và sai số đến goal; thêm timeout/hủy action khi localization mất.',size=21),
 heading('Các bước build và chạy',2),
 p('Cài Ubuntu 22.04, ROS 2 Humble, TurtleBot4 Simulation, Nav2, OpenCV, PyYAML, Vosk và `arecord`. Cài workspace khóa học có `turtlebot4_lab`/`turtlebot4_week5`, build package tuần 7 bằng `colcon build --symlink-install`, rồi source install. Mở simulator, localization/Nav2 với `maps/map.yaml`, đặt initial pose và chờ lifecycle active. Mở dashboard + RViz; kiểm tra robot/map trước khi chạy. Hướng dẫn từng lệnh có ở `HUONG_DAN_CHAY.md` và `github_tuan_07/README.md`.',size=21),
 heading('Kết luận',2),
 p('Bài làm nối được map occupancy với tên vùng, phân tích câu đơn/đa chặng, và gửi waypoint tới Nav2. Ba vùng A/B/C được hiển thị; build và 14 unit test đạt; bốn tuyến A, B, A→B, C→B có log hoàn tất. Video ghi đồng thời RViz và dashboard. Kết quả xác nhận pipeline điều hướng trong mô phỏng; phần đo chuẩn chất lượng ASR và xác thực semantic ngoài thực địa là công việc tiếp theo.',size=21),
 p('Tài liệu tham khảo: ROS 2 Humble documentation; Nav2 NavigateToPose/action concepts; OpenCV connectedComponentsWithStats; Vosk API/model README. Source, map, model và tests được đóng gói trong `github_tuan_07/`; Word/PDF và video nằm ở `reports/` và `videos/` trong folder tuần 7.',size=18),
 p('Các lệnh build cụ thể: source `/opt/ros/humble/setup.bash`; source install của workspace course; tại thư mục package chạy `colcon build --symlink-install`; sau đó source package `install/setup.bash`. Khởi động simulation world warehouse, chạy localization_navigation với map tuần 7 và `use_sim_time:=true`, đặt initial pose qua RViz 2D Pose Estimate, rồi mở dashboard và RViz.',size=20),
 p('Khi quay xong, dừng recorder trước simulator để MP4 hoàn tất chỉ mục. Giữ video ngoài repository source và tải riêng lên Drive. Tên báo cáo Word/PDF giống nhau để dễ đối chiếu. Bản source chưa push lên GitHub; folder `github_tuan_07` là nội dung đã chuẩn bị để người nộp rà soát rồi xuất bản.',size=20)]

# Assemble WordprocessingML document with 13 explicit page breaks.
content=''.join(body)
sect=f'<w:sectPr><w:pgSz w:w="{PAGE_W}" w:h="{PAGE_H}"/><w:pgMar w:top="{MARGIN}" w:right="{MARGIN}" w:bottom="{MARGIN}" w:left="{MARGIN}"/><w:cols w:space="425"/></w:sectPr>'
document=f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing" xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture"><w:body>{content}{sect}</w:body></w:document>'''
styles='''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:docDefaults><w:rPrDefault><w:rPr><w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman" w:eastAsia="Times New Roman"/><w:sz w:val="22"/></w:rPr></w:rPrDefault><w:pPrDefault><w:pPr><w:spacing w:after="110" w:line="290" w:lineRule="auto"/></w:pPr></w:pPrDefault></w:docDefaults></w:styles>'''
rels=['<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rIdStyles" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>']
for idx,name in enumerate(image_names,1): rels.append(f'<Relationship Id="rId{idx}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="media/image{idx}.png"/>')
rels.append('</Relationships>')
content_types='''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Default Extension="png" ContentType="image/png"/><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/><Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/></Types>'''
rootrels='''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>'''
with ZipFile(OUT,'w',ZIP_DEFLATED) as z:
    z.writestr('[Content_Types].xml',content_types)
    z.writestr('_rels/.rels',rootrels)
    z.writestr('word/document.xml',document)
    z.writestr('word/styles.xml',styles)
    z.writestr('word/_rels/document.xml.rels',''.join(rels))
    for idx,name in enumerate(image_names,1): z.write(FIG/name,f'word/media/image{idx}.png')
print(OUT)
