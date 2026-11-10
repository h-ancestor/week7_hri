"""Free-space connected-component segmentation and semantic overlay exporter."""
import argparse
import json
import unicodedata
from pathlib import Path

import cv2
import numpy as np
import yaml


def pixel_to_world(px, py, width, height, resolution, origin):
    """Convert image coordinates (top-left origin) to occupancy-grid map coordinates."""
    ox, oy, yaw = origin
    local_x = (px + 0.5) * resolution
    local_y = (height - py - 0.5) * resolution
    c, s = np.cos(yaw), np.sin(yaw)
    return [float(ox + c * local_x - s * local_y),
            float(oy + s * local_x + c * local_y)]


def segment(gray, min_area=40):
    """Return labels and component centroids; occupancy conventions: white is free."""
    free = (gray >= 250).astype(np.uint8)
    count, labels, stats, centroids = cv2.connectedComponentsWithStats(free, 8)
    components = []
    for label in range(1, count):
        area = int(stats[label, cv2.CC_STAT_AREA])
        if area >= min_area:
            cx, cy = centroids[label]
            components.append({'label': int(label), 'area': area,
                               'pixel': [float(cx), float(cy)]})
    return labels, components


def _display_name(text):
    text = unicodedata.normalize('NFD', text.replace('đ', 'd').replace('Đ', 'D'))
    return ''.join(char for char in text if unicodedata.category(char) != 'Mn')


def load_map(yaml_path):
    config = yaml.safe_load(Path(yaml_path).read_text(encoding='utf-8'))
    image_path = Path(config['image'])
    if not image_path.is_absolute():
        image_path = Path(yaml_path).resolve().parent / image_path
    image = cv2.imread(str(image_path), cv2.IMREAD_GRAYSCALE)
    if image is None:
        raise ValueError(f'Cannot read map image: {image_path}')
    return config, image


def export(map_yaml, regions_yaml, output_image):
    map_config, gray = load_map(map_yaml)
    regions_doc = yaml.safe_load(Path(regions_yaml).read_text(encoding='utf-8'))
    labels, components = segment(gray)
    height, width = gray.shape
    overlay = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
    colors = [(40, 80, 245), (30, 190, 50), (230, 120, 20), (190, 40, 190)]
    region_results = []
    prepared = []
    for index, region in enumerate(regions_doc['regions']):
        px, py = map(int, region['pixel'])
        if not (0 <= px < width and 0 <= py < height) or gray[py, px] < 250:
            raise ValueError(f"Region {region['id']} pixel is not in known free space")
        color = colors[index % len(colors)]
        goal = pixel_to_world(px, py, width, height, float(map_config['resolution']),
                              map_config['origin'])
        prepared.append((region, px, py, color, goal, int(labels[py, px])))
    # Seeded Voronoi partitions split each connected free-space component among its
    # semantic waypoints, while retaining the component map's obstacle boundaries.
    yy, xx = np.indices((height, width))
    for component_id in np.unique(labels):
        if component_id == 0:
            continue
        seeds = [item for item in prepared if item[5] == int(component_id)]
        if not seeds:
            continue
        component_mask = labels == component_id
        distances = np.stack([(xx - item[1]) ** 2 + (yy - item[2]) ** 2 for item in seeds])
        ownership = np.argmin(distances, axis=0)
        for seed_index, (region, px, py, color, goal, _) in enumerate(seeds):
            mask = component_mask & (ownership == seed_index)
            overlay[mask] = (0.62 * overlay[mask] + 0.38 * np.array(color)).astype(np.uint8)
            area = int(np.count_nonzero(mask))
            cv2.circle(overlay, (px, py), 7, color, -1)
            cv2.putText(overlay, f"{region['id']} - {_display_name(region['name'])}", (px + 8, py - 8),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, color, 1, cv2.LINE_AA)
            region_results.append({**region, 'component': int(component_id),
                                   'partition_area_pixels': area,
                                   'goal': {'x': goal[0], 'y': goal[1], 'yaw': 0.0}})
    out = Path(output_image)
    out.parent.mkdir(parents=True, exist_ok=True)
    if not cv2.imwrite(str(out), overlay):
        raise OSError(f'Could not write {out}')
    result_path = out.with_name('segmented_regions.json')
    result_path.write_text(json.dumps({'map': str(Path(map_yaml).name),
                                       'components': components,
                                       'regions': region_results},
                                      ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return result_path


def main():
    try:
        import rclpy
        from rclpy.node import Node
    except ImportError:
        parser = argparse.ArgumentParser()
        parser.add_argument('--map-yaml', required=True)
        parser.add_argument('--regions-yaml', required=True)
        parser.add_argument('--output-image', required=True)
        args = parser.parse_args()
        print(export(args.map_yaml, args.regions_yaml, args.output_image))
        return

    rclpy.init()
    node = Node('week7_map_segmentation')
    node.declare_parameter('map_yaml', '')
    node.declare_parameter('regions_yaml', '')
    node.declare_parameter('output_image', 'maps/map_segmented.png')
    try:
        result = export(node.get_parameter('map_yaml').value,
                        node.get_parameter('regions_yaml').value,
                        node.get_parameter('output_image').value)
        node.get_logger().info(f'Segmentation written to {result}')
    except Exception as exc:
        node.get_logger().error(str(exc))
        raise
    finally:
        node.destroy_node()
        rclpy.shutdown()
