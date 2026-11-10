"""Small desktop window for the guided voice-navigation demo."""
import os
import queue
import re
import subprocess
import threading
import tkinter as tk
from pathlib import Path
from tkinter import scrolledtext


ROOT = Path(__file__).resolve().parents[1]
ANSI_ESCAPE = re.compile(r'\x1b\[[0-?]*[ -/]*[@-~]')


class VoiceDashboard:
    def __init__(self, root):
        self.root = root
        self.root.title('Bài thực hành 07 — Điều hướng bằng giọng nói')
        self.root.geometry('760x700+40+80')
        self.root.minsize(600, 480)
        self.lines = queue.Queue()
        self.process = None

        tk.Label(root, text='ĐIỀU HƯỚNG TURTLEBOT 4 BẰNG GIỌNG NÓI',
                 font=('Sans', 16, 'bold')).pack(padx=14, pady=(14, 4))
        tk.Label(root, text='Đặt initial pose trong RViz. Sau đó nói câu được hướng dẫn bên dưới.',
                 font=('Sans', 10)).pack(padx=14, pady=(0, 10))

        self.state = tk.Label(root, text='ĐANG KHỞI ĐỘNG', fg='#155eef',
                              font=('Sans', 12, 'bold'), wraplength=720)
        self.state.pack(fill='x', padx=14, pady=6)
        self.prompt = tk.Label(root, text='Đang chờ node và AMCL…', fg='#075e35',
                               font=('Sans', 16, 'bold'), wraplength=720,
                               justify='center', height=3)
        self.prompt.pack(fill='x', padx=14, pady=6)

        tk.Label(root, text='Trạng thái và kết quả nhận dạng',
                 anchor='w', font=('Sans', 10, 'bold')).pack(fill='x', padx=14, pady=(8, 2))
        self.output = scrolledtext.ScrolledText(root, height=19, state='disabled',
                                                font=('Monospace', 9), wrap='word')
        self.output.pack(fill='both', expand=True, padx=14, pady=(0, 10))

        footer = tk.Frame(root)
        footer.pack(fill='x', padx=14, pady=(0, 14))
        tk.Label(footer, text='Đang nhận lệnh qua mic. Có thể nói lại nếu node báo nghe chưa rõ.',
                 anchor='w').pack(side='left', fill='x', expand=True)
        tk.Button(footer, text='Dừng node giọng nói', command=self.stop,
                  fg='#a40000').pack(side='right')

        self.root.protocol('WM_DELETE_WINDOW', self.close)
        self.start_node()
        self.root.after(100, self.drain_output)

    def start_node(self):
        env = os.environ.copy()
        env['ROS_LOCALHOST_ONLY'] = '1'
        env['ROS_HOME'] = str(ROOT / '.ros')
        local_python = str(ROOT / '.python')
        env['PYTHONPATH'] = local_python + os.pathsep + env.get('PYTHONPATH', '')
        executable = ROOT / 'install/turtlebot4_week7/lib/turtlebot4_week7/voice_navigation'
        command = [
            str(executable), '--ros-args',
            '-p', f'regions_yaml:={ROOT / "config/regions.yaml"}',
            '-p', 'use_microphone:=true',
            '-p', f'vosk_model_path:={ROOT / "models/vosk-model-small-vn-0.4"}',
        ]
        try:
            self.process = subprocess.Popen(
                command, cwd=ROOT, env=env, stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT, text=True, bufsize=1)
            threading.Thread(target=self.read_process, daemon=True).start()
        except Exception as exc:
            self.lines.put(f'Không khởi động được node: {exc}')

    def read_process(self):
        for line in self.process.stdout:
            self.lines.put(line.rstrip())
        self.lines.put(f'Node đã dừng (mã thoát {self.process.poll()}).')

    def drain_output(self):
        while not self.lines.empty():
            line = ANSI_ESCAPE.sub('', self.lines.get_nowait()).strip()
            if not line:
                continue
            prompt_match = re.search(r'Hãy nói:\s*[“\"](.+?)[”\"]', line)
            if prompt_match:
                self.prompt.config(text=f'BẠN HÃY NÓI:\n“{prompt_match.group(1)}”')
                self.state.config(text='ĐANG CHỜ CÂU LỆNH', fg='#155eef')
            elif 'Microphone mở' in line:
                self.state.config(text='MIC ĐÃ MỞ — ĐANG NGHE', fg='#075e35')
            elif 'Đã nhận dạng:' in line:
                self.state.config(text=line.split('Đã nhận dạng:', 1)[-1].strip(), fg='#155eef')
            elif 'Gửi goal Nav2' in line:
                self.state.config(text='ROBOT ĐANG DI CHUYỂN…', fg='#9a6700')
            elif 'Nav2 đã hoàn thành tuyến' in line:
                self.state.config(text='ĐÃ ĐẾN ĐÍCH', fg='#075e35')
            elif 'Không nhận diện được' in line or 'không tồn tại' in line.lower():
                self.state.config(text='LỆNH CHƯA HỢP LỆ — XEM CHI TIẾT BÊN DƯỚI', fg='#a40000')
            self.output.configure(state='normal')
            self.output.insert('end', line + '\n')
            self.output.see('end')
            self.output.configure(state='disabled')
        if self.root.winfo_exists():
            self.root.after(100, self.drain_output)

    def stop(self):
        if self.process and self.process.poll() is None:
            self.process.terminate()
            self.state.config(text='ĐANG DỪNG NODE GIỌNG NÓI', fg='#a40000')

    def close(self):
        self.stop()
        self.root.after(300, self.root.destroy)


def main():
    root = tk.Tk()
    VoiceDashboard(root)
    root.mainloop()


if __name__ == '__main__':
    main()
