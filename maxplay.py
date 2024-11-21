from pyplayready.cdm import Cdm
from pyplayready.device import Device
from pyplayready.pssh import PSSH


import requests, re, xmltodict, os, subprocess, shutil

device = Device.load("./device.prd")
cdm = Cdm.from_device(device)
session_id = cdm.open()

inputmpd = input("mpd : ")


uri = re.search(r"https://[^?]+",inputmpd)[0]
manifest = re.search(r"r\.manifest=([^&]+)",inputmpd)[0]
origin = re.search(r"r\.origin=([^&]+)",inputmpd)[0]

mpd = f"{uri}?{manifest}&{origin}&f.audioCodec=heaac&f.videoCodec=hevc"

responseMPD = requests.get(
    url= mpd,
    headers={
        'Content-Type': 'text/xml; charset=UTF-8',
    }
)


dictfromXML = xmltodict.parse(responseMPD.text)["MPD"]["Period"]

dictfromXML = dictfromXML[-1]["AdaptationSet"]

resVideo = ""

resAudio = ""

height = 0

bandwidth = 0

for i in dictfromXML :
    if(i["@contentType"] == "video" and int(i["@maxHeight"]) > height):
        resVideo = i
        height = int(i["@maxHeight"])

    elif(i["@contentType"] == "audio" and int(i["Representation"]["@bandwidth"]) > bandwidth):
        resAudio = i
        bandwidth = int(i["Representation"]["@bandwidth"])

psshVideo = resVideo["ContentProtection"][1]["cenc:pssh"]

psshAudio = resAudio["ContentProtection"][1]["cenc:pssh"]


psshVideo = PSSH(psshVideo)

wrm_headers = psshVideo.get_wrm_headers(downgrade_to_v4=False)
request = cdm.get_license_challenge(session_id, wrm_headers[0])


inputLicense = input("widevine?keygen : ")

token = re.search(r"auth=([^&]+)",inputLicense)[0]


reqLicense = inputLicense.replace('widevine?keygen=playready', f'play-ready?token={token}')

responseVideo = requests.post(
    url=reqLicense,
    headers={
        'Content-Type': 'text/xml; charset=UTF-8',
    },
    data=request,
)

cdm.parse_license(session_id, responseVideo.text)

videoKey = ""

for key in cdm.get_keys(session_id):
    videoKey = f"{key.key_id.hex}:{key.key.hex()}"


psshAudio = PSSH(psshAudio)

wrm_headers = psshAudio.get_wrm_headers(downgrade_to_v4=False)
request = cdm.get_license_challenge(session_id, wrm_headers[0])

responseAudio = requests.post(
    url=reqLicense,
    headers={
        'Content-Type': 'text/xml; charset=UTF-8',
    },
    data=request,
)

cdm.parse_license(session_id, responseAudio.text)

audioKey = ""

for key in cdm.get_keys(session_id):
    audioKey = f"{key.key_id.hex}:{key.key.hex()}"

cdm.close(session_id)

print()
name = input("name (without .mkv) : ")

print()
command = f'N_m3u8DL-RE -sa all -sv best -M format=mkv:muxer=mkvmerge --key {videoKey} --key {audioKey} --use-shaka-packager --save-name "{name}" "{mpd}"'
print(command)

with os.popen(command) as stream:
    for line in stream:
        print(line, end="")

with open("tag.txt", "r", encoding="utf-8") as f:
            tag = f.read()

mkvName = name + ".mkv"
nfoName = name + ".nfo"

process = subprocess.run(
    ['MediaInfo', mkvName],
    capture_output=True,
    text=True,
    encoding='utf-8'
)

with open(nfoName, "w", encoding="utf-8") as f:
                f.write(tag)
                
                f.write(f"{process.stdout}".replace(".\\", "").replace("./", ""))

os.makedirs(name, exist_ok=True)

try:
    shutil.move(mkvName, name)
    shutil.move(nfoName, name)
except Exception as e:
    print("filing failed!")
