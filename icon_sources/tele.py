import requests
import json


class tele:
    def get_images():
        print('[*] downloading icon links')
        resp = requests.get(
            "https://www.tele.ch/epg-api/channels/categorized").text
        loaded = json.loads(resp)
        return tele.parse_resp(loaded)


    def parse_resp(json_data):
        icon_links = []
        for channel in json_data['all']['channels']:
            icon = {}
            icon['name'] = channel['name']
            icon['src'] = "https://www.tele.ch/" + \
                channel['logo'] + channel['cid'] + ".png"
            icon_links.append(icon)

        return icon_links
