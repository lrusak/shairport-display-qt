# shairport-display-qt

A simple app to be used with [shairport-sync](https://github.com/mikebrady/shairport-sync) and the official Raspberry Pi 7" touchscreen

![Example App Photo](shairport-display.png)

Table of Contents
=================

  * [Background](#background)
  * [My Setup](#my-setup)
  * [Usage](#usage)
  * [DTB Patching](#dtb-patching)
  * [Future Plans](#future-plans)


## Background

I wanted a simple device to connect be able to connect my iPhone to that would play my music and show the metadata data on a display. I also wanted the ability to control the volume from my phone. I found [shairport-sync](https://github.com/mikebrady/shairport-sync) and saw that it had a dbus interface so I though this would be a good start.

I originally wrote [shairport-display](https://github.com/lrusak/shairport-display) which uses GTK. The problem with this was that it required a display server (x11/wayland) to be running. I didn't want to use x11 (because reasons) and weston isn't really trivial to run as a service.

I rewrote the GTK code into QT which is used here. QT allows using the drm/kms interface of the linux kernel directly so I didn't have to run a display server at all.

## My Setup

I'm currently using a Raspberry Pi 3b+ with the Official Raspberry Pi 7" touchscreen connected via DSI. I'm also using a Behringer UCA202 for the audio output. This is connected to my stereo and the RPi is running 24/7.

I have this running on drm/kms using QT but also works on wayland and x11. This allows me to do development on my workstation running wayland and run this app in a window (like the screenshot above).

@todo: add a photo of my setup

## Usage

I've provided a sample systemd service file to run the app as a service using drm/kms. This requires using the vc4 driver on the raspberry pi. You should also be running [shairport-sync](https://github.com/mikebrady/shairport-sync) as a service with dbus support enabled.

I've included a udev rule that can be used to allow the backlight to be controlled by non root services (depening how you run this app). The backlight control in the app simply looks for backlights in `/sys/class/backlight` and will simply turn off the backlight when no device is connected via airplay. This makes it so the display isn't bright all the time when nothing is playing.

To use the DSI panel with the mainline kernel you need to patch the dtb file for your RPi. I'll outline the instruction to do this and the patch that I use below. Note that I don't use the touchscreen at all. I just use the panel for display only.

## Upstream DTB

Even on Fedora you need to specify the upstream dtb file otherwise it's used as an overlay

add the following to the end of `/boot/efi/config.txt`
```
upstream_kernel=1
```

## DTB Patching

The mainline kernel requires patching in order to use the 7" DSI touchscreen display (even though the driver for it is included). These instructions are just a guideline as you may have to adjust them for your system. For the example I'm using fedora and an RPi3b+.

----

copy the default dtb
```
cp /boot/dtb-6.3.8-200.fc38.aarch64/broadcom/bcm2837-rpi-3-b-plus.dtb ./bcm2837-rpi-3-b-plus.dtb.orig
```
decompile the dtb binary to a dts file
```
dtc -I dtb -O dts -o bcm2837-rpi-3-b-plus.dts.orig bcm2837-rpi-3-b-plus.dtb.orig
```
make a copy
```
cp bcm2837-rpi-3-b-plus.dts.orig bcm2837-rpi-3-b-plus.dts
```
apply the patch:
```
patch -p0 -i patches/0001-add-dsi-panel.patch
```
compile the dts back to a dtb
```
dtc -I dts -O dtb -o bcm2837-rpi-3-b-plus.dtb bcm2837-rpi-3-b-plus.dts
```
copy the dtb back to the filesystem
```
cp bcm2837-rpi-3-b-plus.dtb /boot/dtb-6.3.8-200.fc38.aarch64/broadcom/bcm2837-rpi-3-b-plus.dtb
```
also copy the dtb to the efi directory
```
cp bcm2837-rpi-3-b-plus.dtb /boot/efi/
```
reboot
```
reboot
```

## Future Plans

1) I would like to enable autoscrolling for text that is too long to be displayed on the screen
2) Possibly add the ability to show other info (time, weather, etc).
