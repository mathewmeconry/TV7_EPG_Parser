from requests import Session
from datetime import datetime, timedelta
import pytz

import dateutil.parser


class init7:
    __api__ = "https://tv7api2.tv.init7.net/api/epg/"

    def __init__(self):
        self.sess = Session()

    def get_epg(self, max_past, max_future):
        limit = 250
        offset = 0
        start_time = datetime.now(pytz.UTC) - timedelta(seconds=max_past)
        end_time = datetime.now(pytz.UTC) + timedelta(seconds=max_future)

        epg_data = []
        while True:
            print("[*] Downloading from offset " + str(offset))
            download_resp = self.__download__(limit, offset)
            for item in download_resp["results"]:
                lower = dateutil.parser.parse(item["timeslot"]["lower"])
                upper = dateutil.parser.parse(item["timeslot"]["upper"])
                if lower < start_time:
                    continue
                if upper > end_time:
                    continue

                item_epg = {
                    "start": lower,
                    "stop": upper,
                    "title": item["title"],
                    "channel": item["channel"]["name"],
                    "categories": item["categories"],
                }

                duration = upper - lower
                if not isinstance(duration, int):
                    item_epg["duration"] = duration.total_seconds()

                if "sub_title" in item:
                    item_epg["sub_title"] = item["sub_title"]

                if "icons" in item and len(item["icons"]) > 0:
                    item_epg["icon"] = item["icons"][0]

                if "episode_num" in item:
                    item_epg["episode_num"] = item["episode_num"]

                if "episode_num_system" in item:
                    item_epg["episode_num_system"] = item["episode_num_system"]

                if "desc" in item:
                    item_epg["desc"] = item["desc"]

                if "country" in item:
                    item_epg["country"] = item["country"]

                epg_data.append(item_epg)

            if len(download_resp["results"]) == 0:
                print("[*] No more data")
                break

            if (
                dateutil.parser.parse(download_resp["results"][0]["timeslot"]["upper"])
                > end_time
            ):
                print("[*] No more data")
                break
            offset += limit

        return epg_data

    def __download__(self, limit, offset):
        resp = self.sess.get(
            self.__api__ + "?limit=" + str(limit) + "&offset=" + str(offset)
        )
        return resp.json()
