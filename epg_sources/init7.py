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
        data = self.__download__(limit, offset)
        start_time = datetime.now(pytz.UTC) - timedelta(seconds=max_past)
        end_time = datetime.now(pytz.UTC) + timedelta(seconds=max_future)

        # Searching for right timeframe
        offset = int(data["count"] / 2)
        while True:
            search_resp = self.__download__(limit, offset)
            first_entry = search_resp["results"][0]
            entry_start = dateutil.parser.parse(first_entry["timeslot"]["lower"])
            if entry_start < start_time or offset == 0:
                delta = entry_start - start_time
                if delta.seconds > max_past or offset == 0:
                    break
            offset = int(offset / 2)

        print("[*] Found proper offset. Start downloading from offset " + str(offset))
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
                    "end": upper,
                    "title": item["title"],
                    "station": item["channel"]["name"],
                }

                if "sub_title" in item:
                    item_epg["subtitle"] = item["sub_title"]

                if "icons" in item and len(item["icons"]) > 0:
                    item_epg["image"] = item["icons"][0]

                if "episode_num" in item:
                    item_epg["episode_num"] = item["episode_num"]

                if "episode_num_system" in item:
                    item_epg["episode_num_system"] = item["episode_num_system"]

                if "desc" in item:
                    item_epg["desc"] = item["desc"]

                if "country" in item:
                    item_epg["country"] = item["country"]

                if "duration" in item:
                    duration = upper - lower
                    item_epg["duration"] = duration.seconds()

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
