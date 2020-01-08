# M5Stack ZX-Spectrum GigaScreen Viewer v.0.2
# 
# The script loads gigascreen ZX-Spectrum .scr images via HTTP and displays them on the screen. 
# An excellent collection of the best screens of ZX-Spectrum is located at the Dmitry Ponomarev's website - https://zxart.ee
# 
# Tested on UIFlow V1.4.3

# 
# The MIT License (MIT)
# 
#  Copyright © 2020 Alexey Radyuk
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and 
# associated documentation files (the «Software»), to deal in the Software without restriction, including 
# without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies 
# of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED «AS IS», WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, 
# INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. 
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, 
# WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR 
# THE USE OR OTHER DEALINGS IN THE SOFTWARE.
# 

import usocket as socket
import ujson
from m5stack import lcd

# press the button A to scroll back
# press the button B to reload screen
# press the button С to scroll forward

# the number of pictures in the top from which to start the show
START_IX = 0
LOAD_LIMIT = 5
PICTURE_MIN_RATING = 0

ZX_ART_HOST = "https://zxart.ee/file/id:%s/filename:tmp"
ZX_ART_API_REQUEST = "https://zxart.ee/api/types:zxPicture/export:zxPicture/language:eng/start:%s/limit:%s/order:votes,desc/filter:zxPictureMinRating=%s;zxPictureType=gigascreen;"
GET_REQUEST = 'GET /%s HTTP/1.0\r\nHost: %s\r\n\r\n'
TEMP_FILE = 'temp_file.scr'
DATA_FILE = 'data.json'

#  Color scheme - Pulsar
PALETTE = [
    (0, 0, 0), (0, 0, 205), (205, 0, 0), (205, 0, 205), (0, 205, 0), (0, 205, 205), (205, 205, 0), (205, 205, 205),
    (0, 0, 0), (0, 0, 255), (255, 0, 0), (255, 0, 255), (0, 255, 0), (0, 255, 255), (255, 255, 0), (255, 255, 255),
]

ix = 0
isTryingLoad = True
screens = []


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
    s.send(bytes(GET_REQUEST % (path, host), 'utf8'))
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
        for column in range(32):
            palette0 = readColor(data, y, column, 0)
            bits0 = readBits(data, y, column, 0)
            ink0 = palette0[0]
            paper0 = palette0[1]
            bright0 = palette0[2]

            palette1 = readColor(data, y, column, 6912)
            bits1 = readBits(data, y, column, 6912)
            ink1 = palette1[0]
            paper1 = palette1[1]
            bright1 = palette1[2]

            for b in range(8):
                col0 = paper0
                if bits0 & (0b10000000 >> b):
                    col0 = ink0

                col1 = paper1
                if bits1 & (0b10000000 >> b):
                    col1 = ink1

                color = getResultColor(PALETTE[col0], bright0, PALETTE[col1], bright1)

                if color != 0 and color != 8:
                    lcd.pixel(32 + column * 8 + b, 24 + y, color)


def getResultColor(C0, I0, C1, I1):
    r0 = C0[0]
    g0 = C0[1]
    b0 = C0[2]
    if not I0:
        r0 *= 0.666
        g0 *= 0.666
        b0 *= 0.666

    r1 = C1[0]
    g1 = C1[1]
    b1 = C1[2]
    if not I0:
        r1 *= 0.666
        g1 *= 0.666
        b1 *= 0.666

    red = int((r0 + r1) / 2)
    green = int((g0 + g1) / 2)
    blue = int((b0 + b1) / 2)

    return (red << 16) + (green << 8) + blue


def readBits(data, y, col, shift):
    block = int(y / 64)
    line = int((y % 64) / 8)
    row = y % 8
    offset = ((((block * 8) + row) * 8) + line) * 32 + col + shift
    return data[offset] if offset < len(data) else 0


def readColor(data, y, column, shift):
    row = (int)(y / 8)
    offset = 6144 + row * 32 + column + shift
    attr = data[offset]
    ink = attr - 8 * (attr // 8)
    paper = (attr // 8) - 8 * (attr // 64)
    bright = attr // 64 == 1 or attr // 64 == 3
    # flash = attr > 127

    if (bright == False):
        return (ink, paper, bright)
    else:
        return (ink + 8, paper + 8, bright)


def loadImage():
    global ix, START_IX, LOAD_LIMIT, isTryingLoad
    isTryingLoad = True
    if ix < 0:
        ix = len(screens) - 1

    if ix > len(screens) - 1 :
        START_IX += LOAD_LIMIT
        appendScreensIds()

    lcd.clear()
    lcd.setCursor(0, 0)
    lcd.setColor(lcd.WHITE)
    lcd.print('GigaScreens: #%s %s' % (ix + 1, screens[ix][1]))

    data = open(TEMP_FILE, 'wb')
    addr = ZX_ART_HOST % screens[ix][0]
    http_getFile(addr, data)
    loadedData = open(TEMP_FILE, 'rb').read()
    convertToScreen(loadedData)
    lcd.print("        <<  A        Reload - B         C >>", 0, 224)


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
        screens.append((id, title))


def printLoadingBreak():
    lcd.clear()
    lcd.print("Loading BREAK, press any key", 24, 224)


def on_A_wasPressed():
    global ix
    ix -= 1
    loadImage()


def on_B_wasPressed():
    global isTryingLoad
    isTryingLoad = False
    printLoadingBreak()
    loadImage()


def on_C_wasPressed():
    global ix
    ix += 1
    loadImage()


btnA.wasPressed(on_A_wasPressed)
btnB.wasPressed(on_B_wasPressed)
btnC.wasPressed(on_C_wasPressed)

appendScreensIds()
loadImage()
