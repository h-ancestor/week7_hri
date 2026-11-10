#!/usr/bin/env python3
"""Download and safely extract the official Vietnamese Vosk small model."""
from pathlib import Path, PurePosixPath
from tempfile import TemporaryDirectory
from urllib.request import urlopen
from zipfile import ZipFile
import shutil

MODEL_NAME = 'vosk-model-small-vn-0.4'
MODEL_URL = f'https://alphacephei.com/vosk/models/{MODEL_NAME}.zip'
ROOT = Path(__file__).resolve().parents[1]
MODELS = ROOT / 'models'
DEST = MODELS / MODEL_NAME
REQUIRED = (Path('am/final.mdl'), Path('graph/Gr.fst'), Path('graph/HCLr.fst'))


def main():
    if all((DEST / item).is_file() for item in REQUIRED):
        print(f'Model đã có sẵn: {DEST}')
        return
    if DEST.exists():
        raise SystemExit(f'{DEST} tồn tại nhưng thiếu file model. Hãy đổi tên hoặc xóa thư mục lỗi rồi chạy lại.')

    MODELS.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix='vosk-vn-download-') as temp_dir:
        temp = Path(temp_dir)
        archive = temp / f'{MODEL_NAME}.zip'
        print(f'Tải model từ {MODEL_URL}')
        with urlopen(MODEL_URL, timeout=60) as response, archive.open('wb') as output:
            shutil.copyfileobj(response, output)

        extraction = temp / 'unpacked'
        extraction.mkdir()
        with ZipFile(archive) as zf:
            for info in zf.infolist():
                member = PurePosixPath(info.filename)
                if member.is_absolute() or '..' in member.parts:
                    raise RuntimeError(f'Đường dẫn không an toàn trong archive: {info.filename}')
            zf.extractall(extraction)

        source = extraction / MODEL_NAME
        if not all((source / item).is_file() for item in REQUIRED):
            raise RuntimeError('Archive tải về không có cấu trúc model Vosk mong đợi.')
        shutil.move(str(source), str(DEST))
    print(f'Đã cài model vào: {DEST}')


if __name__ == '__main__':
    main()
