import datetime
import dateutil.parser
import math
import os
import pytz
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
        # the API only returns a maximum of 300 items per request
        self.page_limit = 300
        # the API interprets the wall-clock part of begin/end in the
        # server's timezone and ignores any provided offset, so requests
        # are converted to the server timezone before being sent; the
        # server timezone is configurable via TELEBOY_SERVER_TZ (IANA
        # name, e.g. "America/New_York") in case the API moves
        self.tz = pytz.timezone(os.environ.get("TELEBOY_SERVER_TZ", "Europe/Zurich"))


    def get_epg_by_time(self, start_time: datetime.datetime = None, duration: int = None,
                        rangetype: str = "begin") -> Dict[epg_item, epg_item]:
        if not start_time:
            start_time = datetime.datetime.now(self.tz)

        if start_time.tzinfo is None:
            # treat naive start times as UTC so the machine's local
            # timezone cannot leak in via astimezone()
            start_time = pytz.UTC.localize(start_time)
        if not duration:
            duration = self.max_duration

        if duration > self.max_duration:
            print(f"Duration too long max is {self.max_duration} min")
            return

        return self.__download__(start_time, start_time + datetime.timedelta(minutes=duration), rangetype)

    def get_epg_by_duration(self, duration: int) -> Dict[epg_item, epg_item]:
        rounds = math.floor(duration / self.max_duration)
        now = datetime.datetime.now(self.tz)
        data = []

        for i in range(0, rounds):
            # the first window intersects the current time so broadcasts that
            # are already airing are included as well
            rangetype = "intersect" if i == 0 else "begin"
            data.extend(self.get_epg_by_time(
                now + datetime.timedelta(minutes=(i*self.max_duration)), self.max_duration, rangetype))

        remainder = duration - (rounds * self.max_duration)
        if remainder > 0:
            data.extend(self.get_epg_by_time(now + datetime.timedelta(minutes=(rounds *
                                                                              self.max_duration)), remainder))

        return data

    def get_epg_from_past_by_duration(self, duration: int) -> Dict[epg_item, epg_item]:
        rounds = math.floor(duration / self.max_duration)
        past = datetime.datetime.now(self.tz) - datetime.timedelta(minutes=duration)
        data = []

        for i in range(0, rounds):
            data.extend(self.get_epg_by_time(
                past + datetime.timedelta(minutes=(i*self.max_duration)), self.max_duration))

        remainder = duration - (rounds * self.max_duration)
        if remainder > 0:
            data.extend(self.get_epg_by_time(past + datetime.timedelta(minutes=(rounds *
                                                                              self.max_duration)), remainder))

        return data

    def __download__(self, start_time: datetime.datetime, end_time: datetime.datetime,
                     rangetype: str = "begin") -> Dict[epg_item, epg_item]:
        try:
            print(f"[*] Dowloading from {start_time.isoformat()} until {end_time.isoformat()}")
            data = []
            skip = 0
            while True:
                response = self.sess.get("https://tv.api.teleboy.ch/epg/broadcasts?begin="
                                         f"{start_time.astimezone(self.tz).strftime('%Y-%m-%dT%H:%M:%S')}"
                                         f"&end={end_time.astimezone(self.tz).strftime('%Y-%m-%dT%H:%M:%S')}"
                                         f"&rangetype={rangetype}&sort=time&expand=station,logos,flags,primary_image"
                                         f"&limit={self.page_limit}&skip={skip}")
                raw_data = response.json()
                if not raw_data.get("success", False):
                    raise Exception(f"API error {raw_data.get('error_code')}: {raw_data.get('error_message')}")

                page = raw_data.get("data", {}).get("items", [])
                total = raw_data.get("data", {}).get("total", len(page))

                for item in page:
                    item_epg = {
                        "subtitle": item.get("subtitle") or "",
                        "image": (
                            f"{item['primary_image']['base_path']}raw/{item['primary_image']['hash']}.jpg"
                            if item.get("primary_image") else ""
                        ),
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

                skip += self.page_limit
                if len(data) >= total or len(page) < self.page_limit:
                    break
            if(len(data) == 0):
                print("[!] No data returned. Still continuing...")
            return data
        except Exception as e:
            print("[!] Download failed with err")
            print(e)
        return []
