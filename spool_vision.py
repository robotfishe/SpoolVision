# SpoolVision for Klipper
# by Julian Burton (robotfishe) 2026
# GNU GPL v3 licence

import cv2
import numpy as np
import requests

class SpoolVision:
    def __init__(self, config):
        self.printer = config.get_printer()
        self.name = config.get_name().split()[-1]

        self.camera_url = config.get('camera_url')
        self.mmu_type = config.get('mmu_type', 'afc').lower()
        raw_area = config.getlist('area')
        self.area = [int(point.strip()) for point in raw_area]

        self.gcode = self.printer.lookup_object('gcode')
        self.gcode.register_mux_command("GET_SPOOL_COLOR", "LANE", self.name,
                                        self.scan_filament,
                                        desc="Detect filament color via webcam")

    def scan_filament(self, gcmd):
        # block if printer is busy
        print_stats = self.printer.lookup_object('print_stats', None)
        if print_stats is not None and print_stats.state == "printing":
            gcmd.respond_info("SpoolVision: Command blocked. Cannot run while printing.")
            return

        try:
            # get image
            res = requests.get(self.camera_url, timeout=2)
            res.raise_for_status()

            raw_image_data = np.frombuffer(res.content, np.uint8)
            img = cv2.imdecode(raw_image_data, cv2.IMREAD_COLOR)

            if img is None:
                gcmd.respond_info(f"SpoolVision image decode failed on lane [{self.name}].")
                return

            # crop image
            img_h, img_w = img.shape[:2]
            x, y, w, h = self.area
            x1, y1 = max(0, x), max(0, y)
            x2, y2 = min(img_w, x + w), min(img_h, y + h)

            crop = img[y1:y2, x1:x2]
            #cv2.imwrite(f"/tmp/lane_{self.name}_debug.jpg", crop) - save image for debug (comment out except for debugging)

            # get colour
            hsv_array = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
            avg_hsv = cv2.mean(hsv_array)[:3]

            hue, sat, val = avg_hsv

            # conditional saturation boost
            if sat < 40:
                new_sat = sat
            else:
                new_sat = max(0, min(255, (sat / 255.0 * 195.0) + 60.0))

            # convert to hex and send
            adjusted_hsv = np.uint8([[[hue, new_sat, val]]])
            adjusted_rgb = cv2.cvtColor(adjusted_hsv, cv2.COLOR_HSV2RGB)[0][0]

            hex_code = "{:02x}{:02x}{:02x}".format(*adjusted_rgb)
            gcmd.respond_info(f"Spool {self.name} color: #{hex_code}")

            if self.mmu_type == 'happy_hare':
                mmu_cmd = f"MMU_GATE_MAP GATE={self.name} COLOR={hex_code}"
            elif self.mmu_type == 'afc':
                mmu_cmd = f"SET_COLOR LANE={self.name} COLOR={hex_code}"

            self.gcode.run_script_from_command(mmu_cmd)

        except Exception as e:
            gcmd.respond_info(f"SpoolVision Error on lane {self.name}: {str(e)}")

def load_config_prefix(config):
    return SpoolVision(config)
