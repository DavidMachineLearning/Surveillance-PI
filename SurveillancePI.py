#!/usr/bin python3
# -*- coding: utf-8 -*-

__author__ = "David Forino AI Solutions (https://davidforino-aisolutions.com)"
__license__ = "MIT"
__version__ = "1.0.0"

import cv2
import numpy as np
from time import time, sleep
import argparse
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage


def send_notification(image):
    """
    This function sends email as a notification.
    :param image: the image you want to send.
    """
    sender_email = ""  # insert your sender email inside the quotes
    receiver_email = ""  # insert your receiver email inside the quotes
    password = ""  # insert your 16 alphanumeric characters Google password inside the quotes

    # convert image to bytes and attach it as message
    byte_image = cv2.imencode(".jpg", cv2.cvtColor(image, cv2.COLOR_BGR2RGB))[1].tobytes()
    msg = MIMEMultipart()
    msg.attach(MIMEImage(byte_image))

    # send email
    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
        server.login(sender_email, password)
        server.sendmail(sender_email, receiver_email, msg.as_string())


def preprocessing(frame_):
    """
    Preprocessing for each frame before comparison.
    It converts the frame to grayscale then applies Gaussian Blur.
    :param frame_: rgb frame coming from the camera
    :return: pre-processed frame
    """
    return cv2.GaussianBlur(cv2.cvtColor(frame_, cv2.COLOR_BGR2GRAY), (21, 21), 0)


def draw_bboxes(orig_frame, frame_, min_area):
    """
    Calculate all bounding boxes, combines them into a single big one and then draws it to the original image.
    :param orig_frame: original rgb frame coming from the camera
    :param frame_: frame after threshold
    :param min_area: (int) minimum area to consider for each contour
    """
    # Find contours
    contours, _ = cv2.findContours(frame_, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # Get all bounding boxes filtered by minimum area
    bboxes = [list(cv2.boundingRect(c)) for c in contours if cv2.contourArea(c) > min_area]

    # Combine bounding boxes
    if bboxes:
        bboxes = np.asarray(bboxes)
        x, y = bboxes[:, 0].min(), bboxes[:, 1].min()
        x1, y1 = bboxes[:, 0].max(), bboxes[:, 1].max()
        w, h = bboxes[:, 2].max(), bboxes[:, 3].max()

        cv2.rectangle(orig_frame, (x, y), (x1 + w, y1 + h), (0, 255, 0), 3)


# arguments
parser = argparse.ArgumentParser(description="SurveillancePI, program created by David Forino AI Solutions "
                                             "(https://davidforino-aisolutions.com). Make your house safer with a "
                                             "surveillance system using a Raspberry Pi! If it detects a motion above a "
                                             "specified threshold, it sends you a notification email with the picture. "
                                             "BEFORE USING THIS PROGRAM, REMEMBER TO ADD THE EMAIL DETAILS!")
parser.add_argument("-b", "--bounding_box", help="Enable bounding box drawing on original image", action="store_true")
parser.add_argument("-s", "--show", help="Show the image live on screen", action="store_true")
parser.add_argument("--threshold", help="Threshold value to detect a motion", type=int, default=80)
parser.add_argument("--max_fps", help="Maximum FPS desired value", type=int, default=5)
parser.add_argument("--pause", help="Initial pause before running the script (seconds)", type=int, default=5)
parser.add_argument("--min_area", help="Minimum area considered when creating bounding boxes", type=int, default=500)
parser.add_argument("--email_timer", type=float, default=1.5, help="Number of seconds before a notification email is "
                                                                   "sent, if value is negative no email will be sent")

args = parser.parse_args()
print(f"Wait {args.pause} seconds before starting...")
sleep(args.pause)

# define a video capture object 
camera = cv2.VideoCapture(0)

# get background frame
for i in range(120):
    _, bg_frame = camera.read()
    if bg_frame is not None:
        bg_frame = preprocessing(bg_frame)
        break
else:
    raise RuntimeError("There is a problem while capturing a frame!")

email_timer = None
# infinite loop
while True:
    start_time = time()

    # Capture 1 frame
    _, original_frame = camera.read()

    # Preprocessing
    frame = preprocessing(original_frame)

    # Compare frames
    deltaframe = cv2.absdiff(bg_frame, frame)

    # Thresholding and dilation
    thresholded = cv2.threshold(deltaframe, args.threshold, 255, cv2.THRESH_BINARY)[1]

    # draw bounding boxes
    if args.bounding_box:
        draw_bboxes(original_frame, thresholded, args.min_area)

    # send notification email
    if thresholded.any() and args.email_timer >= 0:
        if email_timer is not None and start_time > (email_timer + args.email_timer):
            send_notification(original_frame)
            email_timer = None
        elif email_timer is None:
            email_timer = start_time + args.email_timer
    else:
        email_timer = None

    # add delay if needed
    stop_time = time()
    sleep_time = max(0, 1 / args.max_fps - (stop_time - start_time))
    sleep(sleep_time)

    if args.show:
        # Display the resulting frame
        cv2.imshow("Live Stream", original_frame)

        # press 'q' to quit
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

        print(f'FPS: {round(1 / (stop_time - start_time + sleep_time), 1)}')

# After the loop release the cap object 
camera.release() 
# Destroy all windows
cv2.destroyAllWindows()
