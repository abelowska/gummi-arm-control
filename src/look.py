"""
captures video
detects glyphs and their position
based on
rdmilligan.wordpress.com/2015/07/19/glyph-recognition-using-opencv-and-python/
"""


import os
# print(cv2.getBuildInformation())

import cv2
import threading
import time
import glob

from src.look_helpers import *

# tweak these
EDGE_LOWER_THRESHOLD = 30
EDGE_UPPER_THRESHOLD = 90

GLYPH_PATTERNS = {
    "ALPHA": [[0, 1, 0],
              [1, 0, 0],
              [0, 1, 1]],
    "BETA": [[1, 1, 0],
             [0, 0, 0],
             [0, 1, 0]],
    "GAMMA": [[1, 0, 1],
              [0, 1, 0],
              [1, 0, 0]],
    "DELTA": [[1, 0, 1],
              [0, 0, 0],
              [1, 0, 0]]
}


class TimingOut:
    """
    When value is set
    Save the time, reading will fail
    If you read too late
    """
    def __init__(self, timeout):
        self._timeout = timeout
        self._last_assignment_timestamp = 0
        self._value = None

    def set(self, value):
        self._value = value
        self._last_assignment_timestamp = time.time()

    def get(self):
        expiration = self._last_assignment_timestamp + self._timeout
        if time.time() > expiration:
            raise TimeoutError('Variable timed out')
        return self._value


class PositionDetector(threading.Thread):
    """
    Connect camera
    Detect marker positions
    Find out their angle
    """
    def __init__(self, timeout):
        threading.Thread.__init__(self)
        # current glyphs coordinates
        self.glyphs = {
            'ALPHA': TimingOut(timeout),
            'BETA': TimingOut(timeout),
            'GAMMA': TimingOut(timeout),
            'DELTA': TimingOut(timeout)
        }
        self._die = False

    @staticmethod
    def connect_camera():
        cameras = glob.glob('dev/video*')
        if not cameras:
            raise IOError('No camera found')

        # on default choose camera with biggest number (should be most recent)
        camera = sorted(cameras)[-1]
        device_number = camera[-1]
        return cv2.VideoCapture(device_number)

    @staticmethod
    def find_contours(imgray):
        edges = cv2.Canny(imgray, EDGE_LOWER_THRESHOLD, EDGE_UPPER_THRESHOLD)
        im2, contours, hierarchy = cv2.findContours(edges,
                                                    cv2.RETR_TREE,
                                                    cv2.CHAIN_APPROX_SIMPLE)
        return sorted(contours, key=cv2.contourArea, reverse=True)[:100]

    def get_angle(self):
        while True:
            try:
                return calculate_angle_4_glyphs(self.glyphs['ALPHA'].get(),
                                                self.glyphs['BETA'].get(),
                                                self.glyphs['GAMMA'].get(),
                                                self.glyphs['DELTA'].get())
            except TimeoutError:
                print('getting angle timed out')
                continue

    def record_glyph_coordinates(self, contours, imgray):
        for contour in contours:
            # approximate the contour
            peri = cv2.arcLength(curve=contour, closed=True)
            approx = cv2.approxPolyDP(curve=contour, epsilon=0.01 * peri, closed=True)
            if len(approx) != 4:
                continue
            topdown_quad = get_topdown_quad(imgray, approx.reshape(4, 2))
            bitmap = cv2.resize(topdown_quad, (5, 5))
            self.recognize_glyph(bitmap, approx)

    def recognize_glyph(self, bitmap, approx):
        for glyph_pattern in GLYPH_PATTERNS:
            for rotation_num in range(4):
                if bitmap_matches_glyph(bitmap, GLYPH_PATTERNS[glyph_pattern]):
                    flattened = flatten(approx)
                    ordered = order_points(flattened)
                    self.glyphs[glyph_pattern].set(ordered)
                    break
                bitmap = rotate_image(bitmap, 90)

    def run(self):
        camera = self.connect_camera()
        while self._die is False:
            is_open, frame = camera.read()
            if not is_open:
                break
            imgray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            imgray = cv2.GaussianBlur(imgray, (3, 3), 0)
            contours = self.find_contours(imgray)
            self.record_glyph_coordinates(contours, imgray)

    def kill(self):
        """tell the thread to die gracefully"""
        self._die = True
