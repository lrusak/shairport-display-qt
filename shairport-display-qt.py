#!/usr/bin/env /usr/bin/python3

from PyQt5.QtWidgets import QApplication, QLabel, QWidget, QProgressBar, QDesktopWidget
from PyQt5 import uic

from PyQt5.QtCore import QTimer, Qt, QPropertyAnimation
from PyQt5.QtGui import QPixmap, QFont

import dbus
import dbus.mainloop.glib
import datetime
import signal
import sys
import os
import time
import logging

class ShairportSyncClient(QApplication):

  def __init__(self, argv):

    self.ArtPath = None
    self.Title = None
    self.Artist = None
    self.Album = None

    super().__init__(argv)

    self.log = logging.getLogger("shairport-display")

    self.format = logging.Formatter('%(asctime)s - [%(levelname)s] - %(message)s', "%Y-%m-%d %H:%M:%S")

    self.handler = logging.StreamHandler(stream=sys.stdout)
    self.handler.setFormatter(self.format)
    self.handler.setLevel(logging.DEBUG)

    self.log.addHandler(self.handler)
    self.log.setLevel(logging.DEBUG)

    self.log.info("Starting application")

    self.backlight = ""

    for (topdir, backlights, _) in os.walk("/sys/class/backlight/"):
      for backlight in backlights:
        with open(topdir + backlight + "/max_brightness", "r") as f:
          self.backlight = topdir + backlight
          self.max_brightness = f.read()

    if self.backlight:
      self.log.debug("using backlight: '" + self.backlight + "'")
    else:
      self.log.debug("no backlight found, backlight control disabled")

    self.properties_changed = None

    self._setup_loop()
    self._setup_bus()
    self._setup_signals()

    self.length = 0
    self.progress = 0
    self.duration = 500 # miliseconds
    self.timer = None

    self.window = uic.loadUi(os.path.dirname(argv[0]) + "/shairport-display.ui")
    # self.window.resize(QDesktopWidget().availableGeometry().size());
    self.window.setStyleSheet("background-color : white; color : black;");
    self.window.setAutoFillBackground(True);
    self.window.resizeEvent = self.onResize
    self.window.keyPressEvent = self.keyPressEvent
    self.window.resize(800, 480)
    self.window.show()

    self.Art = self.window.findChild(QLabel, 'CoverArt')

    self.Title = self.window.findChild(QLabel, 'Title')
    self.Title.setFont(QFont("Montserrat", 20, QFont.Bold))

    self.Artist = self.window.findChild(QLabel, 'Artist')
    self.Artist.setFont(QFont("Montserrat", 16, QFont.Normal))
    self.Album = self.window.findChild(QLabel, 'Album')
    self.Album.setFont(QFont("Montserrat", 16, QFont.Normal))

    self.ProgressBar = self.window.findChild(QProgressBar, 'ProgressBar')
    # self.ProgressBar.setStyleSheet("QProgressBar {border: 0px solid gray; height: 2px; max-height:2px;}")
    # self.ProgressBar.setStyleSheet("QProgressBar::chunk {background: light blue;}")

    # self.animation = QPropertyAnimation(self.ProgressBar, b"value")

    self.ProgressBar.setRange(0, 100)

    self.Remaining = self.window.findChild(QLabel, 'Remaining')
    self.Remaining.setFont(QFont("Montserrat", 10, QFont.Normal))
    self.Elapsed = self.window.findChild(QLabel, 'Elapsed')
    self.Elapsed.setFont(QFont("Montserrat", 10, QFont.Normal))

    self._clear_display()
    self._initialize_display()

    self.window.destroyed.connect(self.quit)

  def onResize(self, event):

    size = self.window.size();
    self.log.info("width: %d", size.width())
    self.log.info("height: %d", size.height())

    if self.Title is not None:
      self.Title.setMaximumWidth(int(size.width() / 2))

    if self.Artist is not None:
      self.Artist.setMaximumWidth(int(size.width() / 2))

    if self.Album is not None:
      self.Album.setMaximumWidth(int(size.width() / 2))

    if self.ArtPath is not None:
      pixmap = QPixmap(self.ArtPath)
      if pixmap.width() >= pixmap.height():
        self.Art.setPixmap(pixmap.scaledToWidth(int((size.width() / 2) - 40)))
      else:
        self.Art.setPixmap(pixmap.scaledToHeight(int((size.width() / 2) - 40)))

  def event(self, e):
    return QApplication.event(self, e)

  def _tickEvent(self):

    if self.length != 0:
      # self.animation.setStartValue(self.progress / self.length * 100.0)

      self.progress += self.duration / 1000.0

      # self.animation.setEndValue(self.progress / self.length * 100.0)

      # self.log.debug("progress: %f", self.progress / self.length * 100.0)

      # self.log.debug("elapsed: %s", str(datetime.timedelta(seconds=self.progress)))

      self.ProgressBar.setValue(int(self.progress / self.length * 100))

      # self.animation.setDuration(self.duration)
      # self.animation.start()

      elapsed = round(self.progress)

      elapsed_time = datetime.timedelta(seconds=elapsed)
      remaining_time = datetime.timedelta(seconds=self.length - elapsed)

      elapsed_formated = ':'.join(str(elapsed_time).split(':')[1:])
      remaining_formated = ':'.join(str(remaining_time).split(':')[1:])

      self.Elapsed.setText(elapsed_formated)
      self.Remaining.setText("-" + remaining_formated)

    return True

  def quit(self, *args):

    self.log.info("Stopping application")

    self.properties_changed.remove()

    self._set_backlight(False)

    QApplication.quit()

  def _setup_loop(self):

    self._loop = dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)

  def _setup_bus(self):

    dbus.set_default_main_loop(self._loop)

    if dbus.SystemBus().name_has_owner("org.gnome.ShairportSync"):
      self.log.debug("shairport-sync dbus service is running on the system bus")
      self._bus = dbus.SystemBus()
      return

    if dbus.SessionBus().name_has_owner("org.gnome.ShairportSync"):
      self.log.debug("shairport-sync dbus service is running on the session bus")
      self._bus = dbus.SessionBus()
      return

    self.log.error("shairport-sync dbus service is not running")
    exit(1)

  def _fullscreen_mode(self):

    if self.window.windowState() & Qt.WindowState.WindowFullScreen:
      self.log.debug("normal")
      self.window.showNormal()
    else:
      self.log.debug("fullscreen")
      self.window.showFullScreen()

  def keyPressEvent(self, event):

    if event.key() == Qt.Key_Q:
      self.quit()
    if event.key() == Qt.Key_F:
      self._fullscreen_mode()

  def _set_backlight(self, power):

    if self.backlight:
      try:
        with open(self.backlight + "/brightness", "w") as f:
          if power:
            f.write(self.max_brightness)
          else:
            f.write("0")

      except FileNotFoundError:
        self.log.warning("path: '" + self.backlight + "' does not exist")
      except PermissionError:
        self.log.warning("incorrect permissions for '" + self.backlight + "'")

  def _initialize_display(self):

    self._set_backlight(True)

    try:
      result = self._bus.call_blocking("org.gnome.ShairportSync", "/org/gnome/ShairportSync", "org.freedesktop.DBus.Properties", "Get", "ss", ["org.gnome.ShairportSync.RemoteControl", "Metadata"])
    except dbus.exceptions.DBusException:
      self.log.warning("shairport-sync is not running on the bus")
      return

    try:
      metadata = { "art" : result['mpris:artUrl'].split("://")[-1],
                   "title" : result['xesam:title'],
                   "artist" : ", ".join(result['xesam:artist']),
                   "album" : result['xesam:album'],
                   "length" : result['mpris:length'],
                 }

    except KeyError:
      self.log.warning("no metadata available to initialize the display")
      return

    self._set_metadata(metadata)

  def _setup_signals(self):

    self.properties_changed = self._bus.add_signal_receiver(handler_function=self._display_metadata,
                                                            signal_name='PropertiesChanged',
                                                            dbus_interface='org.freedesktop.DBus.Properties',
                                                            bus_name='org.gnome.ShairportSync',
                                                            member_keyword='signal')

  def _set_metadata(self, metadata):

    self.log.debug("Metadata available")

    for key in metadata:
      self.log.info("%s: %s", key, metadata[key])

    self.Title.setText(metadata["title"])
    self.Artist.setText(metadata["artist"])
    self.Album.setText(metadata["album"])
    self.ProgressBar.setVisible(True)
    self.Elapsed.setVisible(True)
    self.Remaining.setVisible(True)

    size = self.window.size();

    self.Title.setMaximumWidth(int(size.width() / 2))
    self.Artist.setMaximumWidth(int(size.width() / 2))
    self.Album.setMaximumWidth(int(size.width() / 2))

    self.ArtPath = metadata["art"]
    pixmap = QPixmap(self.ArtPath)

    if pixmap.width() >= pixmap.height():
      self.Art.setPixmap(pixmap.scaledToWidth(int((size.width() / 2) - 40)))
    else:
      self.Art.setPixmap(pixmap.scaledToHeight(int((size.width() / 2) - 40)))

    self.log.info("length: %s", str(datetime.timedelta(microseconds=metadata["length"])))

  def _stop_timer(self):

    if self.timer is not None:
      self.log.debug("stopping timer")
      self.timer.stop()

  def _start_timer(self):

    self.log.debug("starting timer")
    self.timer = QTimer()
    self.timer.setTimerType(Qt.PreciseTimer)
    self.timer.timeout.connect(self._tickEvent)
    self.timer.start(self.duration)

  def _clear_display(self):

    self._set_backlight(False)

    self.Art.clear()

    self.Title.clear()
    self.Artist.clear()
    self.Album.clear()

    self.Elapsed.clear();
    self.Remaining.clear();
    self.ProgressBar.setVisible(False);

  def _display_metadata(self, *args, **kwargs):

    interface = args[0]
    data = args[1]

    self.log.debug("Recieved signal for %s", interface)

    if interface == "org.gnome.ShairportSync.RemoteControl":

      if 'Metadata' in data:

        try:
          metadata = { "art" : data['Metadata']['mpris:artUrl'].split("://")[-1],
                       "title" : data['Metadata']['xesam:title'],
                       "artist" : ', '.join(data['Metadata']['xesam:artist']),
                       "album" : data['Metadata']['xesam:album'],
                       "length" : data['Metadata']['mpris:length'],
                     }

        except KeyError:
          self.log.warning("no metadata available to initialize the display")
          return

        self._set_metadata(metadata)

      if 'ProgressString' in data:
        start, current, end = [int(x) for x in data['ProgressString'].split('/')]

        self.log.debug("start: %d", start)
        self.log.debug("current: %d", current)
        self.log.debug("end: %d", end)

        self.length = round((end - start) / 44100)
        elapsed = round((current - start) / 44100)

        self.log.debug("length: %s", str(datetime.timedelta(seconds=self.length)))
        self.log.debug("elapsed: %s", str(datetime.timedelta(seconds=elapsed)))

        self.progress = elapsed

        self._start_timer()

      if 'PlayerState' in data:
        state = data['PlayerState']
        self.log.info("PlayerState: %s", state)

        if state == "Stopped":
          self._stop_timer()
        elif state == "Playing":
          self._start_timer()
        elif state == "Paused":
          pass

    if interface == "org.gnome.ShairportSync":

      if "Active" in data:
        if data["Active"]:
          self.log.info("device connected")
          self._initialize_display()
        else:
          self.log.info("device disconnected")
          self._clear_display()


if (__name__ == "__main__"):

  client = ShairportSyncClient(sys.argv)
  signal.signal(signal.SIGINT, lambda *args: client.quit())

  client.startTimer(500)

  client.exec_()
