This Klipper plugin pulls an image from a webcam attached to your MMU and sets filament colours in either AFC or Happy Hare.

# Hardware

You will need a camera with a good view of all your spools and decent lighting conditions. I recommend [this camera](https://www.aliexpress.com/item/1005004587961991.html) from GXIVISION on AliExpress. It has two sensors which are merged into one image, giving you a wide field view with low distortion that only takes up one USB device's bandwidth.

<img src="/gxivision_camera.avif" height=300 />

I also recommend a dedicated fill light LED of some sort. I use 20 neopixels mounted under the cameras.

# Setup

## 1. Install dependencies.
If `klippy-env` is in your home folder (standard for kiauh installations), you'll need to run:
```
source ~/klippy-env/bin/activate
pip install opencv-python-headless numpy requests
```

## 2. Download the spool_vision.py file and put it in `klipper/klippy/extras/`

## 3. Make sure your camera is set up in crowsnest.conf.
For example:
```
[cam 2]
mode: ustreamer
port: 8081
device: /dev/v4l/by-id/usb-VNV_USB_Camera-video-index0
resolution: 1280x360
max_fps: 5
v4l2ctl: white_balance_temperature_auto=0,white_balance_temperature=5500,gamma=175
```
Tune white balance, hue, gamma, etc in your v4l2ctl parameters until the webcam image is as close as possible to a true representation of the filament colours.
Do not leave these on auto; _repeatable_ colour accuracy is important!

## 4. Load a snapshot from the camera into your image editor of choice and measure out a box for the filament on each spool.

For example, in the screenshot below, the crop area for the spool on the right starts at x=1100, y=20, and has a width of 80 and height of 70 pixels.
Avoid any areas with harsh reflections, and remember that as filament is used up some areas of the image will show the spool instead of the filament.

<img src="/example_crop.png" height=200 />

## 5. Add spool_vision sections to your printer config, one for each lane.

Because my camera is mounted on the back of my MMU, the lane order is reversed, so the crop area shown in the image above is lane 1. Therefore I would configure as follows:
```
[spool_vision lane1]
mmu_type: afc   # defaults to "afc"; you can also use "happy_hare"
camera_url: http://localhost:8081/?action=snapshot
area: 1100, 20, 80, 70     # top left point, top right point, width, and height of the crop area for this lane
```
Lane names should follow the format of your MMU plugin of choice: "lane1", "lane2", etc for AFC; "1", "2", etc for Happy Hare.

## 6. Add "GET_SPOOL_COLOR LANE={}" to your lane load macro.

In Happy Hare there are several ways to do this, the simplest is probably to add it to your mmu_software.cfg:
```
[gcode_macro MMU__PRELOAD]
gcode:
    MMU_PRELOAD {rawparams}
    {% set gate = params.GATE|default(-1)|int %}
    GET_SPOOL_COLOR LANE={gate}
```
AFC doesn't expose its macros in the same way but I have recently opened a pull request to create an optional AFC_POST_PREP macro that is called after a spool is loaded, so hopefully you will be able to do this soon. For AFC, the simplest version is something like:
```
[gcode_macro AFC_POST_PREP]
gcode:
    {% set lane = params.LANE|default(-1)|int %}
    GET_SPOOL_COLOR LANE={lane}
```
## 7. Further tweaks and advanced macro commands

You will probably want to activate your fill light automatically before GET_SPOOL_COLOR is called, and wait a few seconds for the camera's brightness to stabilise before calling SpoolVision. Since you don't want to lock up all your other Klipper processes, you will need to use a delayed_gcode command to do any waiting.

You may also want to use a gcode shell command to pass manual exposure parameters to the camera, which will help with repeatability and reduce the delay you need between the lights going on and the colour vision script being run.

For reference, here is my AFC_POST_PREP macro and the other commands it calls:

```
[gcode_macro AFC_POST_PREP]
gcode:
  {% set lane_name = params.LANE|default("lane1")|string %}
  { action_respond_info("Setting SPOOL_VISION_VARS" ~ lane_name) }
  SET_GCODE_VARIABLE MACRO=__SPOOL_VISION_VARS VARIABLE=current_lane VALUE="'{lane_name}'"
  RUN_SHELL_COMMAND CMD=manual_exposure
  SET_LED LED=spool_vision RED=1 GREEN=1 BLUE=1
  RESET_LANE_MATERIAL LANE={lane_name}
  UPDATE_DELAYED_GCODE ID=__RUN_SPOOL_VISION DURATION=1

[delayed_gcode __RUN_SPOOL_VISION]
gcode:
  {% set parameters = printer['gcode_macro __SPOOL_VISION_VARS'] %}
  GET_SPOOL_COLOR LANE={parameters['current_lane']}
  UPDATE_DELAYED_GCODE ID=__SPOOL_VISION_LIGHTS_OFF DURATION=10

[delayed_gcode __SPOOL_VISION_LIGHTS_OFF]
gcode:
  SET_LED LED=spool_vision RED=0 GREEN=0 BLUE=0
  RUN_SHELL_COMMAND CMD=auto_exposure

[gcode_macro __SPOOL_VISION_VARS]
variable_current_lane: "lane1"
gcode:

[gcode_shell_command auto_exposure]
command: v4l2-ctl --device /dev/v4l/by-id/usb-VNV_USB_Camera-video-index0 --set-ctrl=exposure_auto=3

[gcode_shell_command manual_exposure]
command: v4l2-ctl --device /dev/v4l/by-id/usb-VNV_USB_Camera-video-index0 --set-ctrl=exposure_auto=1,exposure_absolute=500,gain=0
```
