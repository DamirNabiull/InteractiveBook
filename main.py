import cv2
import os
import json
from Driver import MyDriver, logging
from selenium.webdriver.common.by import By
import pylibdmtx.pylibdmtx as dm

CONTOUR_AREA_MIN = 1000
CONTOUR_AREA_MAX = 100000

available = []
current = 0

path = os.getcwd()
prototype = open('Site/index.html', 'r').read()
config = json.load(open('config.json', 'r'))
debug = config['debug']
k = config['ksize']
ksize = (k, k)
useBlur = config['useBlur']
xMin = config['cropXm']
yMax = config['cropYM']
xMax = config['cropXM']
yMin = config['cropYm']
height = config['height']
width = config['width']


def get_qr_value(image):
    settings = config['decoder']
    gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
    decode_arr = dm.decode(
        gray, 
        max_count=settings['maxCount'], 
        threshold=settings['threshold'], 
        shrink=settings['shrink'])

    if len(decode_arr) == 0:
        return 0

    return decode_arr[0].data.decode()


def create_page(pid, video_name):
    page = prototype[:]
    page = page.replace('!-- add video --', f'source src="../Assets/{video_name}.mp4" type="video/mp4"')
    with open(f'Site/{pid}.html', 'w') as f:
        f.write(page)
    logging.warning(f'Page: page {pid} is created')


def load_data():
    global debug, available
    pages = config['pages']
    for pid in pages:
        available.append(int(pid))
        create_page(pid, pages[pid])


def crop(image):
    global yMax, yMin, xMax, xMin, ksize
    crop_img = image[yMin:yMax, xMin:xMax]

    if useBlur:
        crop_img = cv2.blur(crop_img, ksize, cv2.BORDER_DEFAULT)

    return crop_img


def get_boxes(image) -> list:
    black_border_boxes = []
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY)
    edges = cv2.Canny(thresh, 50, 150)
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    for contour in contours:
        epsilon = 0.02 * cv2.arcLength(contour, True)
        approx = cv2.approxPolyDP(contour, epsilon, True)

        # Check if the contour is a rectangle (4 vertices)
        if len(approx) == 4 and cv2.contourArea(contour) > CONTOUR_AREA_MIN:
            black_border_boxes.append(contour)

    return black_border_boxes


def get_qr_value_for_boxes(boxes, image):
    print(f'get_qr_value_for_boxes count of boxes: {len(boxes)}')
    settings = config['decoder']

    for box in boxes:
        x, y, w, h = cv2.boundingRect(box)
        boxed_image = image[y:y+h, x:x+w]

        try:
            decode_arr = dm.decode(
                boxed_image, 
                max_count=settings['maxCount'], 
                threshold=settings['threshold'], 
                shrink=settings['shrink'])

            if len(decode_arr) != 0:
                return decode_arr[0].data.decode()
        except:
            continue

    return 0


def get_boxed_image(boxes, image):
    output_image = image.copy()
    cv2.drawContours(output_image, boxes, -1, (0, 255, 0), 3)
    return output_image


load_data()
driver = MyDriver.getInstance()
driver = driver.GetDriver()

print('Player: Start player')

cam = cv2.VideoCapture(0)
cam.set(cv2.CAP_PROP_FRAME_WIDTH, width)
cam.set(cv2.CAP_PROP_FRAME_HEIGHT, height)

img_counter = 0

print('Camera: Start capture')
print(available)

while True:
    ret, frame = cam.read()
    if not ret:
        print("Camera: Failed to grab frame")
        break

    # img = crop(frame)
    # qr_value = get_qr_value(img)

    boxes = get_boxes(frame)
    qr_value = get_qr_value_for_boxes(boxes, frame)
    boxed_image = get_boxed_image(boxes, frame)

    if debug:
        cv2.imshow("debug", boxed_image)
        k = cv2.waitKey(1)
        if k % 256 == 32:
            img_name = "opencv_frame_{}.png".format(img_counter)
            cv2.imwrite(img_name, frame)
            print("{} written!".format(img_name))
            img_counter += 1

    if qr_value != 0 and qr_value != current and str(qr_value) in config['pages']:
        logging.warning(f'QR: Value = {qr_value}')
        current = qr_value
        driver.get(os.path.join(os.getcwd(), 'Site', f'{qr_value}.html'))
        element = driver.find_element(By.ID, "myVideo")
        element.click()


cam.release()

cv2.destroyAllWindows()