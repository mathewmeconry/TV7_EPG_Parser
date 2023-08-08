import datetime
import dateutil
import math
from typing import Dict
from requests import Session

class epg_item:
    subtitle: str
    image: str
    begin: datetime.datetime
    end: datetime.datetime
    title: str
    station: str
    desc: str
    country: str
    year: int
    duration: int
    episode_num: int
    season_num: int


class teleboy:
    __base__ = "https://www.teleboy.ch/"
    __api__ = "https://tv.api.teleboy.ch/"

    def __init__(self):
        # Session to maintain headers across sesssion for CF.  
        self.sess = Session()
        self.sess.headers.update({"x-teleboy-apikey": "e899f715940a209148f834702fc7f340b6b0496b62120b3ed9c9b3ec4d7dca00"})
        # using generic browser header to avoid 403
        self.sess.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"})
        # short duration because of response size (max from teleboy is 323.6 KB)
        self.max_duration = 20


    def get_epg_by_time(self, start_time: datetime.datetime = None, duration: int = None) -> Dict[epg_item, epg_item]:
        if not start_time:
            start_time = datetime.datetime.now()

        if not duration:
            duration = self.max_duration

        if duration > self.max_duration:
            print(f"Duration too long max is {self.max_duration} min")
            return

        return self.__download__(start_time, start_time + datetime.timedelta(minutes=duration))

    def get_epg_by_duration(self, duration: int) -> Dict[epg_item, epg_item]:
        rounds = math.floor(duration / self.max_duration)
        now = datetime.datetime.now()
        data = []

        for i in range(0, rounds):
            data.extend(self.get_epg_by_time(
                now + datetime.timedelta(minutes=(i*self.max_duration)), self.max_duration))

        data.extend(self.get_epg_by_time(now + datetime.timedelta(minutes=(rounds *
                                                                              self.max_duration)), duration - (rounds * self.max_duration)))

        return data

    def get_epg_from_past_by_duration(self, duration: int) -> Dict[epg_item, epg_item]:
        rounds = math.floor(duration / self.max_duration)
        past = datetime.datetime.now() - datetime.timedelta(minutes=duration)
        data = []

        for i in range(0, rounds):
            data.extend(self.get_epg_by_time(
                past + datetime.timedelta(minutes=(i*self.max_duration)), self.max_duration))

        data.extend(self.get_epg_by_time(past + datetime.timedelta(minutes=(rounds *
                                                                              self.max_duration)), duration - (rounds * self.max_duration)))

        return data

    def __download__(self, start_time: datetime.datetime, end_time: datetime.datetime) -> Dict[epg_item, epg_item]:
        try:
            print(f"[*] Dowloading from {start_time.isoformat()} until {end_time.isoformat()}")
            response = self.sess.get("https://tv.api.teleboy.ch/epg/broadcasts?begin="
                                             f"{start_time.isoformat()}&end={end_time.isoformat()}&expand=station,logos,flags,primary_image&limit=0")
            raw_data = response.json()

            data = []
            if "data" in raw_data and "items" in raw_data["data"]:
                for item in raw_data["data"]["items"]:
                    item_epg = {
                        "subtitle": item["subtitle"],
                        "image": f"{item['primary_image']['base_path']}raw/{item['primary_image']['hash']}.jpg",
                        "begin": dateutil.parser.parse(item["begin"]),
                        "end": dateutil.parser.parse(item["end"]),
                        "title": item["title"],
                        "station": item["station"]["name"],
                        "stationid": item["station"]["id"]
                    }

                    if "serie_episode" in item:
                        item_epg["episode_num"] = item["serie_episode"]

                    if "serie_season" in item:
                        item_epg["season_num"] = item["serie_season"]

                    if "short_description" in item:
                        item_epg["desc"] = item["short_description"]

                    if "country" in item:
                        item_epg["country"] = item["country"]

                    if "year" in item:
                        item_epg["year"] = item["year"]

                    if "duration" in item:
                        item_epg["duration"] = item["duration"]

                    data.append(item_epg)
            if(len(data) == 0):
                print("[!] No data returned. Still continuing...")
            return data
        except Exception as e:
            print("[!] Download failed with err")
            print(e)
        return []
