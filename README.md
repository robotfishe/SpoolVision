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

AFC doesn't expose its macros in the same way so I've opened a feature request with the Armored Turtle team for something to hook into - stay tuned.

It's also a good idea to put a command in this macro to activate your fill light and wait a few seconds for the camera's brightness to stabilise before calling SpoolVision.
