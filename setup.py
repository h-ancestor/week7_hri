from glob import glob
from setuptools import setup

package_name = 'turtlebot4_week7'
setup(name=package_name, version='0.1.0', packages=[package_name],
      data_files=[('share/ament_index/resource_index/packages', ['resource/' + package_name]),
                  ('share/' + package_name, ['package.xml']),
                  ('share/' + package_name + '/config', glob('config/*.yaml')),
                  ('share/' + package_name + '/maps', glob('maps/*.pgm') + glob('maps/*.yaml'))],
      install_requires=['setuptools'], zip_safe=True,
      entry_points={'console_scripts': [
          'segment_map = turtlebot4_week7.segmentation:main',
          'voice_navigation = turtlebot4_week7.voice_navigation:main',
          'voice_dashboard = turtlebot4_week7.voice_dashboard:main']})
