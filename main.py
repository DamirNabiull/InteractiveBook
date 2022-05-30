import cv2
import os
import json
from Driver import MyDriver, logging
import pylibdmtx.pylibdmtx as dm

available = []
path = os.getcwd()
prototype = open('Site/index.html', 'r').read()
config = json.load(open('config.json', 'r'))
debug = False
k = config['ksize']
ksize = (k, k)
xMin = config['cropXm']
yMax = config['cropYM']
xMax = config['cropXM']
yMin = config['cropYm']
height = config['height']
width = config['width']


def get_qr_valur(image):
    val = 0
    try:
        if len(dm.decode(img)) == 0:
            return 0
        val = dm.decode(img)[0].data.decode("utf-8")
    except Exception as e:
        logging.error(e)
    return val


def create_page(pid, video_name):
    page = prototype[:]
    page = page.replace('!-- add video --', f'source src="../Assets/{video_name}.mp4" type="video/mp4"')
    with open(f'Site/{pid}.html', 'w') as f:
        f.write(page)
    logging.warning(f'Page: page {pid} is created')


def load_data():
    global debug, available
    if config['debug'] == 'yes':
        debug = True
    pages = config['pages']
    for pid in pages:
        available.append(int(pid))
        create_page(pid, pages[pid])


def crop(image):
    global yMax, yMin, xMax, xMin, ksize
    crop_img = image[yMin:yMax, xMin:xMax]
    crop_img = cv2.blur(crop_img, ksize, cv2.BORDER_DEFAULT)
    return crop_img


load_data()

current = 0
det = cv2.QRCodeDetector()

driver = MyDriver.getInstance()
driver = driver.GetDriver()

logging.warning(f'Player: Start player')

element = driver.find_element_by_id("myVideo")
element.click()

cam = cv2.VideoCapture(0)
cam.set(cv2.CAP_PROP_FRAME_WIDTH, width)
cam.set(cv2.CAP_PROP_FRAME_HEIGHT, height)

img_counter = 0

logging.warning(f'Camera: Start capture')

print(available)
while True:
    ret, frame = cam.read()
    if not ret:
        logging.error(f'Camera: FAILED TO GRAB')
        print("failed to grab frame")
        break

    img = crop(frame)
    qr_value = get_qr_valur(img)

    if debug:
        cv2.imshow("debug", img)
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
        element = driver.find_element_by_id("myVideo")
        element.click()


cam.release()

cv2.destroyAllWindows()