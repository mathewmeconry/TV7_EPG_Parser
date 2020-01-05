import datetime
import dateutil
import math
import requests
import json
from typing import Dict
import cfscrape


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
    # short duration because of response size (max from teleboy is 323.6 KB)
    max_duration = 30

    def get_epg_by_time(start_time: datetime.datetime = None, duration: int = None) -> Dict[epg_item, epg_item]:
        if not start_time:
            start_time = datetime.datetime.now()

        if not duration:
            duration = teleboy.max_duration

        if duration > teleboy.max_duration:
            print("Duration too long max is " + max_duration + " min")
            return

        return teleboy.__download__(start_time, start_time + datetime.timedelta(minutes=duration))

    def get_epg_by_duration(duration: int) -> Dict[epg_item, epg_item]:
        rounds = math.floor(duration / teleboy.max_duration)
        now = datetime.datetime.now()
        data = []

        for i in range(0, rounds):
            data.extend(teleboy.get_epg_by_time(
                now + datetime.timedelta(minutes=(i*teleboy.max_duration)), teleboy.max_duration))

        data.extend(teleboy.get_epg_by_time(now + datetime.timedelta(minutes=(rounds *
                                                                              teleboy.max_duration)), duration - (rounds * teleboy.max_duration)))

        return data

    def __download__(start_time: datetime.datetime, end_time: datetime.datetime) -> Dict[epg_item, epg_item]:
        print("[*] Dowloading from " + start_time.isoformat() +
              " until " + end_time.isoformat())
        scraper = cfscrape.create_scraper()
        response = scraper.get("https://tv.api.teleboy.ch/epg/broadcasts?begin="+start_time.isoformat(
        )+"&end="+end_time.isoformat()+"&expand=station,logos,flags,primary_image&limit=0",
            headers={"x-teleboy-apikey": "db9501d64632a944f1b984d7acaf0b983c5bfcaa723a8dfcf24dd951354d1878"})
        raw_data = json.loads(response.text)

        data = []
        if "data" in raw_data and "items" in raw_data["data"]:
            for item in raw_data["data"]["items"]:
                item_epg = {
                    "subtitle": item["subtitle"],
                    "image": item["primary_image"]["base_path"] + "raw/" + item["primary_image"]["hash"] + ".jpg",
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
        return data
