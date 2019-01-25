#!/usr/bin/python3
import requests
import re
import datetime
import html
import json
from epg_sources.tele import tele
from epg_sources.teleboy import teleboy
from icon_sources.tele import tele as teleicon
from icon_sources.teleboy import teleboy as teleboyicon


class channel_item:
    id: str
    lang: str
    display_name: str


class programm_item:
    start: datetime
    stop: datetime
    channel: str
    icon: str
    title: str
    country: str
    desc: str
    sub_title: str
    credits: dict
    category: str
    episode_num: str
    date: int
    length: int


def __main__():
    print("[*] Getting/parsing Init7 tvchannels.m3u playlist")
    channels = get_channel_list()
    channels = prepare_channel_list(channels)

    print("[*] Getting EPG and icons data from teleboy.ch")
    teleboy_raw = teleboy.get_epg_by_duration(7*24*60)
    teleboy_icons = teleboyicon.get_images(teleboy_raw)
    teleboy_icons_matched = match_icons(
        channels, teleboy_icons, './mappings/teleboy.json')
    teleboy_epg = match_teleboy_epg(channels, teleboy_raw)
    print("[✓] Matched " +
          str(len(teleboy_icons_matched)) + " teleboy.ch icons")

    print("[*] Getting icons data from tele.ch")
    tele_icons = teleicon.get_images()
    tele_icons_matched = match_icons(
        channels, tele_icons, './mappings/tele.json')
    print("[✓] Matched " + str(len(tele_icons_matched)) + " tele.ch icons")

    print("[*] Getting EPG data from tele.ch")
    tele_raw = tele.get_epg_by_duration(7*24*60)
    tele_epg = match_tele_epg(channels, tele_raw)

    # generate the xml for the channels
    all_icons = {**tele_icons_matched, **teleboy_icons_matched}
    print("[✓] Total " + str(len(all_icons)) + " icons")
    channels_xmltv = channels_to_xmltv(channels, all_icons)

    # generate tv7_teleboy_epg.xml
    with open('tv7_teleboy_epg.xml', 'w+') as w:
        w.write("<?xml version=\"1.0\" encoding=\"UTF-8\" ?><tv>" +
                channels_xmltv + programms_to_xmltv(teleboy_epg) + "</tv>")

    # generate tv7_tele_epg.xml
    with open('tv7_tele_epg.xml', 'w+') as w:
        w.write("<?xml version=\"1.0\" encoding=\"UTF-8\" ?><tv>" +
                channels_xmltv + programms_to_xmltv(tele_epg) + "</tv>")

    # generate tv7_epg.xml
    full_epg = []
    full_epg.extend(tele_epg)
    full_epg.extend(teleboy_epg)

    programms_xmltv = programms_to_xmltv(full_epg)
    with open('tv7_epg.xml', 'w+') as w:
        w.write("<?xml version=\"1.0\" encoding=\"UTF-8\" ?><tv>" +
                channels_xmltv + programms_xmltv + "</tv>")


def get_channel_list():
    tv7channel_list = requests.get("https://api.init7.net/tvchannels.m3u").text
    tv7channel_list = re.sub(r"udp:\/\/.+", "", tv7channel_list)
    tv7channel_list = tv7channel_list.replace("\n", "")
    tv7channel_list = tv7channel_list.replace("#EXTM3U", "")
    tv7channel_list = tv7channel_list.split("#EXTINF:-1,")
    return tv7channel_list


def prepare_channel_list(channel_list):
    prepared_list = []
    for channel in channel_list:
        prepared_list.append({
            "display_name": channel,
            "id": channel.lower().replace("hd", "").replace("schweiz", "").replace("ch", "").replace("(", "").replace(")", "").replace(" ", ""),
            "lang": "de"
        })

    return prepared_list


def gen_channel_id_from_name(channel_name):
    return channel_name.lower().replace("hd", "").replace("schweiz", "").replace("ch", "").replace("(", "").replace(")", "").replace(" ", "")


def find_channel_by_id(id, channel_list):
    for channel in channel_list:
        if id == channel["id"]:
            return True

    return False


def match_tele_epg(channel_list, tele_epg):
    print("[*] Matching tele.ch EPG data (" + str(len(tele_epg)) +
          " programms to " + str(len(channel_list)) + " channels)")
    mapping = json.loads(open('./mappings/tele.json', 'r').read())
    programms = []
    matched_channels = set()
    for programm in tele_epg:
        channel_id = gen_channel_id_from_name(programm["channelLong"])

        if channel_id in mapping:
            channel_id = mapping[channel_id]

        if find_channel_by_id(channel_id, channel_list):
            matched_channels.add(channel_id)
            programm_matched = {
                "start": programm["availabilityStartTime"],
                "stop": programm["availabilityEndTime"],
                "channel": channel_id,
                "icon": programm["image"],
                "title": programm["title"],
            }

            if "subtitle" in programm:
                programm_matched["sub_title"] = programm["subtitle"]

            if "productionCountry" in programm:
                programm_matched["country"] = programm["productionCountry"]

            if "synopsis" in programm:
                programm_matched["desc"] = programm["synopsis"]

            if "persons" in programm:
                programm_matched["credits"] = programm["persons"]
                if "cast" in programm["persons"]:
                    programm_matched["credits"]["actors"] = programm["persons"]["cast"]
                    del programm_matched["credits"]["cast"]

            if "category" in programm:
                programm_matched["category"] = programm["category"]

            if "episode" in programm and "season" in programm:
                programm_matched["episode_num"] = "S" + \
                    str(programm["season"]) + " E" + str(programm["episode"])
            elif "episode" in programm:
                programm_matched["episode_num"] = programm["episode"]

            if "productionYearFirst" in programm:
                programm_matched["date"] = programm["productionYearFirst"]

            programms.append(programm_matched)

    print("[✓] Matched " + str(len(matched_channels)) + " tele.ch channels")
    return programms


def match_icons(channel_list, icons, mapping):
    print("[*] Matching channel icons (" + str(len(icons)) +
          " icons to " + str(len(channel_list)) + " channels)")
    mapping = json.loads(open(mapping, 'r').read())
    icons_matched = {}
    for icon in icons:
        channel_id = gen_channel_id_from_name(icon['name'])

        if channel_id in mapping:
            channel_id = mapping[channel_id]

        if find_channel_by_id(channel_id, channel_list):
            icons_matched[channel_id] = icon['src']

    return icons_matched


def match_teleboy_epg(channel_list, teleboy_epg):
    print("[*] Matching teleboy.ch EPG data (" + str(len(teleboy_epg)) +
          " programms to " + str(len(channel_list)) + " channels)")
    mapping = json.loads(open('./mappings/teleboy.json', 'r').read())
    programms = []
    matched_channels = set()
    for programm in teleboy_epg:
        channel_id = gen_channel_id_from_name(programm["station"])

        if channel_id in mapping:
            channel_id = mapping[channel_id]

        if find_channel_by_id(channel_id, channel_list):
            matched_channels.add(channel_id)

            programm_matched = {
                "start": programm["begin"],
                "stop": programm["end"],
                "channel": channel_id,
                "icon": programm["image"],
                "title": programm["title"],
            }

            if "subtitle" in programm:
                programm_matched["sub_title"] = programm["subtitle"]

            if "country" in programm:
                programm_matched["country"] = programm["country"]

            if "desc" in programm:
                programm_matched["desc"] = programm["desc"]

            if "episode_num" in programm and "season_num" in programm:
                programm_matched["episode_num"] = "S" + \
                    str(programm["season_num"]) + " E" + \
                    str(programm["episode_num"])
            elif "episode_num" in programm:
                programm_matched["episode_num"] = programm["episode_num"]

            if "year" in programm:
                programm_matched["date"] = programm["year"]

            programms.append(programm_matched)

    print("[✓] Matched " + str(len(matched_channels)) + " teleboy.ch channels")
    return programms


def programms_to_xmltv(programms):
    print("[*] Generating XML for " + str(len(programms)) + " programms")
    programms_xml = ""
    for programm in programms:
        programm_xml = ""
        programm_xml = programm_xml + "<programme start=\""+programm["start"].strftime(
            "%Y%m%d%H%M%S %z")+"\" stop=\""+programm["stop"].strftime("%Y%m%d%H%M%S %z")+"\" channel=\""+programm["channel"]+"\">"

        programm_xml = programm_xml + "<icon src=\""+programm["icon"]+"\" />"
        programm_xml = programm_xml + "<title>" + \
            html.escape(programm["title"])+"</title>"

        if "sub_title" in programm:
            programm_xml = programm_xml + "<sub-title>" + \
                html.escape(programm["sub_title"])+"</sub-title>"

        if "country" in programm:
            programm_xml = programm_xml + "<country>" + \
                html.escape(programm["country"])+"</country>"

        if "category" in programm:
            programm_xml = programm_xml + "<category lang=\"de\">" + \
                html.escape(programm["category"])+"</category>"

        if "desc" in programm:
            programm_xml = programm_xml + "<desc lang=\"de\">" + \
                html.escape(programm["desc"])+"</desc>"

        if "persons" in programm:
            programm_xml = programm_xml + "<credits>"
            for attrib in programm["persons"]:
                if attrib == "actors":
                    for actor in programm["persons"]["actors"]:
                        programm_xml = programm_xml + "<actor>" + actor + "</actor>"
                else:
                    programm_xml = programm_xml + "<"+attrib+">" + \
                        programm["persons"][attrib] + "</"+attrib+">"
            programm_xml = programm_xml + "</credits>"

        if "episode-num" in programm:
            programm_xml = programm_xml + "<episode-num>" + \
                programm["episode_num"]+"</episode-num>"

        if "date" in programm:
            programm_xml = programm_xml + "<date>" + \
                str(programm["date"])+"</date>"

        if "durationSeconds" in programm:
            programm_xml = programm_xml + "<length>" + \
                str(programm["duration"])+"</length>"

        programm_xml = programm_xml + "</programme>"
        programms_xml = programms_xml + programm_xml

    return programms_xml


def channels_to_xmltv(channel_list, icons):
    print("[*] Generating XML for " + str(len(channel_list)) + " channels")
    channels_xml = ""
    for channel in channel_list:
        channel_xml = "<channel id=\"" + channel["id"] + "\">"
        channel_xml = channel_xml + "<display-name lang=\"de\">" + \
            channel["display_name"] + "</display-name>"
        channel_xml = channel_xml + "<display-name lang=\"fr\">" + \
            channel["display_name"] + "</display-name>"
        channel_xml = channel_xml + "<display-name lang=\"it\">" + \
            channel["display_name"] + "</display-name>"

        if channel['id'] in icons:
            channel_xml = channel_xml + "<icon src=\"" + \
                icons[channel['id']] + "\" />"

        channel_xml = channel_xml + "</channel>"
        channels_xml = channels_xml + channel_xml

    return channels_xml


__main__()
# programm.availabilityStartTime.strftime("%Y%m%d%H%M%S %z"),
