import usocket as socket
import ujson
from m5stack import lcd

# press the button A if the picture is not loaded
# press the button B to scroll back
# press the button С to scroll forward

# the number of pictures in the top from which to start the show
START_IX = 5

LOAD_LIMIT = 5
PICTURE_MIN_RATING = 0

WIDTH = 256
HEIGHT = 192
ZX_ART_HOST = "https://zxart.ee/file/id:%s/filename:tmp"
ZX_ART_API_REQUEST = "https://zxart.ee/api/types:zxPicture/export:zxPicture/language:eng/start:%s/limit:%s/order:votes,desc/filter:zxPictureMinRating=%s;zxPictureType=standard;"
TOP_ZX_ART_SCREENS = []
TEMP_FILE = 'temp_file.scr'
DATA_FILE = 'data.json'

#  Color scheme - Pulsar
PALETTE = [
    0, 205, 13434880, 13435085, 52480, 52685, 13487360, 13487565, 0, 255, 16711680, 16711935, 65280, 65535, 16776960,
    16777215
]

ix = 0
isTryingLoad = True


def split_list(l, s):
    count = 0
    ni = []
    for i in range(0, len(l) - len(s)):
        if l[i] == s[count]:
            count = count + 1
            if count == len(s):
                ni.append(i + 1)
                count = 0
        else:
            count = 0
    if len(ni) == 0:
        return l
    else:
        r = []
        pi = 0
        for j in range(0, len(ni)):
            r.append(l[pi:(ni[j] - len(s))])
            pi = ni[j]
        r.append(l[pi:len(l)])
        return r


def http_getFile(url, file):
    global isTryingLoad
    counter = 0
    maxCount = 50
    _, _, host, path = url.split('/', 3)
    addr = socket.getaddrinfo(host, 80)[0][-1]
    s = socket.socket()
    s.connect(addr)
    s.send(bytes('GET /%s HTTP/1.0\r\nHost: %s\r\n\r\n' % (path, host), 'utf8'))
    while isTryingLoad:
        data = s.recv(200)
        if data:
            l = split_list(data, [13, 10, 13, 10])
            if len(l) == 2:
                file.write(l[1])
                break
        if counter > maxCount:
            isTryingLoad = False
            printLoadingBreak()
            break
        counter += 1

    while isTryingLoad:
        data = s.recv(100)
        if data:
            file.write(data)
        else:
            break

    s.close()
    file.close()


def convertToScreen(data):
    for y in range(192):
        pixrow = []
        for column in range(32):
            palette = readColor(data, y, column)
            bits = readBits(data, y, column)
            for b in range(8):
                if bits & (0b10000000 >> b):
                    pixrow.append(palette[0])
                else:
                    pixrow.append(palette[1])
        # draw screen
        for x in range(256):
            if pixrow[x] == 0 or pixrow[x] == 8:
                continue
            lcd.pixel(32 + x, 24 + y, PALETTE[pixrow[x]])

    lcd.print("<< >>", 270, 0)


def readBits(data, y, col):
    block = int(y / 64)
    line = int((y % 64) / 8)
    row = y % 8
    offset = ((((block * 8) + row) * 8) + line) * 32 + col
    return data[offset] if offset < len(data) else 0


def readColor(data, y, column):
    row = (int)(y / 8)
    offset = 6144 + row * 32 + column
    attr = data[offset]
    ink = attr - 8 * (attr // 8)
    paper = (attr // 8) - 8 * (attr // 64)
    bright = attr // 64 == 1 or attr // 64 == 3
    # flash = attr > 127

    if (bright == False):
        return (ink, paper)
    else:
        return (ink + 8, paper + 8)


def loadImage():
    global ix, START_IX, LOAD_LIMIT, isTryingLoad
    isTryingLoad = True
    if ix < 0:
        ix = len(TOP_ZX_ART_SCREENS) - 1

    if ix > len(TOP_ZX_ART_SCREENS) - 1:
        START_IX += LOAD_LIMIT
        appendScreensIds()

    lcd.clear()
    lcd.setCursor(0, 0)
    lcd.setColor(lcd.WHITE)
    lcd.print('Load #%s: %s' % (START_IX + ix + 1, TOP_ZX_ART_SCREENS[ix][1]))

    data = open(TEMP_FILE, 'wb')
    addr = ZX_ART_HOST % TOP_ZX_ART_SCREENS[ix][0]
    http_getFile(addr, data)
    loadedData = open(TEMP_FILE, 'rb').read()
    convertToScreen(loadedData)
    lcd.print("SCR-file got from the top of ZXART.EE", 24, 224)


def appendScreensIds():
    data = open(DATA_FILE, 'wb')
    addr = ZX_ART_API_REQUEST % (START_IX, LOAD_LIMIT, PICTURE_MIN_RATING)
    http_getFile(addr, data)
    loadedData = open(DATA_FILE, 'rb')
    jsonObj = ujson.load(loadedData)

    scrData = jsonObj['responseData']['zxPicture']
    for data in scrData:
        id = data['id']
        title = data['title'][0:30]
        TOP_ZX_ART_SCREENS.append((id, title))


def printLoadingBreak():
    lcd.clear()
    lcd.print("Loading BREAK, press B or C", 24, 224)


def on_A_wasPressed():
    global isTryingLoad
    isTryingLoad = False
    printLoadingBreak()


def on_B_wasPressed():
    global ix
    ix -= 1
    loadImage()


def on_C_wasPressed():
    global ix
    ix += 1
    loadImage()


buttonA.wasPressed(on_A_wasPressed)
buttonB.wasPressed(on_B_wasPressed)
buttonC.wasPressed(on_C_wasPressed)

appendScreensIds()
loadImage()
