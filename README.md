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

## DTB Patching

The mainline kernel requires patching in order to use the 7" DSI touchscreen display (even though the driver for it is included). These instructions are just a guideline as you may have to adjust them for your system. For the example I'm using fedora and an RPi3b+.

----

copy the default dtb
```
cp /boot/dtb-5.9.16-200.fc33.aarch64/broadcom/bcm2837-rpi-3-b-plus.dtb ./bcm2837-rpi-3-b-plus.dtb.orig
```
decompile the dtb binary to a dts file
```
dtc -I dtb -O dts -o bcm2837-rpi-3-b-plus.dts.orig bcm2837-rpi-3-b-plus.dtb.orig
```
make a copy
```
cp bcm2837-rpi-3-b-plus.dtb.orig bcm2837-rpi-3-b-plus.dtb
```

apply the following patch:
```
patch -p0 -i dts-lcd.patch
```

`dts-lcd.patch`
```
--- bcm2837-rpi-3-b-plus.dts.orig       2021-01-01 16:24:35.621149531 -0800
+++ bcm2837-rpi-3-b-plus.dts    2021-01-01 16:26:20.740214933 -0800
@@ -89,7 +89,7 @@
                        phandle = <0x1b>;
                };

-               gpio@7e200000 {
+               gpio: gpio@7e200000 {
                        compatible = "brcm,bcm2835-gpio";
                        reg = <0x7e200000 0xb4>;
                        interrupts = <0x02 0x11 0x02 0x12 0x02 0x13 0x02 0x14>;
@@ -512,7 +512,7 @@
                        interrupts = <0x02 0x01>;
                };

-               dsi@7e700000 {
+               dsi1: dsi@7e700000 {
                        compatible = "brcm,bcm2835-dsi1";
                        reg = <0x7e700000 0x8c>;
                        interrupts = <0x02 0x0c>;
@@ -522,9 +522,37 @@
                        clocks = <0x06 0x23 0x06 0x30 0x06 0x32>;
                        clock-names = "phy\0escape\0pixel";
                        clock-output-names = "dsi1_byte\0dsi1_ddr2\0dsi1_ddr";
-                       status = "disabled";
                        power-domains = <0x0e 0x12>;
                        phandle = <0x05>;
+                       port {
+                               dsi_out_port: endpoint {
+                                       remote-endpoint = <&panel_dsi_port>;
+                               };
+                       };
+               };
+
+               i2c_dsi: i2c {
+                       compatible = "i2c-gpio";
+                       #address-cells = <1>;
+                       #size-cells = <0>;
+                       gpios = <&gpio 44 0 &gpio 45 0>;
+
+                       lcd@45 {
+                               compatible = "raspberrypi,7inch-touchscreen-panel";
+                               reg = <0x45>;
+
+                               port {
+                                       panel_dsi_port: endpoint {
+                                               remote-endpoint = <&dsi_out_port>;
+                                       };
+                               };
+                       };
+               };
+
+               rpi_backlight {
+                       compatible = "raspberrypi,rpi-backlight";
+                       firmware = <&firmware>;
+                       status = "okay";
                };

                i2c@7e804000 {
@@ -700,7 +728,7 @@
                        phandle = <0x18>;
                };

-               firmware {
+               firmware: firmware {
                        compatible = "raspberrypi,bcm2835-firmware\0simple-mfd";
                        #address-cells = <0x01>;
                        #size-cells = <0x01>;
```

compile the dts back to a dtb
```
dtc -I dts -O dtb -o bcm2837-rpi-3-b-plus.dtb bcm2837-rpi-3-b-plus.dts
```
copy the dtb back to the filesystem
```
cp bcm2837-rpi-3-b-plus.dtb /boot/dtb-5.9.16-200.fc33.aarch64/broadcom/bcm2837-rpi-3-b-plus.dtb
```
reboot
```
reboot
```

## Future Plans

1) I would like to enable autoscrolling for text that is too long to be displayed on the screen
2) Possibly add the ability to show other info (time, weather, etc).
