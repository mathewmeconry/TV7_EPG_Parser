import xml.etree.ElementTree as ET
import json
import datetime
import dateutil.parser
import requests
import math
import queue
import threading
from typing import Dict


class epg_item:
    assetId: int
    sourceId: int
    availabilityStartTime: datetime.datetime
    availabilityEndTime: datetime.datetime
    originalStartTime: datetime.datetime
    originalTitle: str
    title: str
    channelShort: str
    channelLong: str
    image: str
    imageLarge: str
    sourceLogoUrl: str
    category: str
    durationSeconds: int
    productionCountry: str
    productionYearFirst: int
    synopsis: str
    persons: dict
    episode: int
    season: int
    subtitle: str


class tele:
    __base = "https://www.tele.ch"
    __api__ = "https://www.tele.ch/epg-api/"
    max_duration = 239

    def get_epg_by_time(start_time: datetime.datetime = None, duration: int = None) -> dict:
        if not start_time:
            start_time = datetime.datetime.now()

        if not duration:
            duration = tele.max_duration

        if duration > tele.max_duration:
            print("Duration too long max is 239 min")
            return

        raw = tele.__download_base__(
            start_time, start_time + datetime.timedelta(minutes=duration))
        parsed = tele.__parse__(raw)
        return tele.__enrich_shows__(parsed)

    def get_epg_by_duration(duration: int) -> Dict[epg_item, epg_item]:
        rounds = math.floor(duration / tele.max_duration)
        now = datetime.datetime.now()
        data = []
        for i in range(0, rounds):
            data.extend(tele.get_epg_by_time(
                now + datetime.timedelta(minutes=(i*tele.max_duration)), tele.max_duration))

        data.extend(tele.get_epg_by_time(now + datetime.timedelta(minutes=(rounds *
                                                                           tele.max_duration)), duration - (rounds * tele.max_duration)))

        return data

    def __parse__(raw: dict) -> Dict[epg_item, epg_item]:
        parsed = []
        for el in raw:
            el_parsed = {}
            for attrib in el:
                if attrib in ["availabilityStartTime", "availabilityEndTime", "originalStartTime"]:
                    el_parsed[attrib] = dateutil.parser.parse(el[attrib])
                else:
                    el_parsed[attrib] = el[attrib]

            parsed.append(el_parsed)

        return parsed

    def __download_base__(start_time: datetime.datetime, end_time: datetime.datetime):
        print("[*] Downloading from " + start_time.isoformat() +
              " until " + end_time.isoformat())
        teleEPG = requests.get(
            tele.__api__ + "/shows/"+start_time.isoformat()+"+"+end_time.isoformat()+"/all").text
        teleEPG = json.loads(teleEPG)
        return teleEPG

    def __enrich_shows__(base_data: Dict[epg_item, epg_item])->Dict[epg_item, epg_item]:
        enriched_data = []
        # print("[*] Enriching " + str(len(base_data)) + " shows")

        queueLock = threading.Lock()
        workQueue = queue.Queue(0)

        # Fill the queue
        queueLock.acquire()
        for item in base_data:
            workQueue.put(item)

        queueLock.release()

        threads = []

        # Create new threads
        for threadNum in range(0, 40):
            thread = teleThread(threadNum, "Thread-"+str(threadNum),
                                workQueue, queueLock, enriched_data)
            thread.start()
            threads.append(thread)

        # Wait for queue to empty
        while not workQueue.empty():
            pass

        # Wait for all threads to complete
        for t in threads:
            t.join()

        return enriched_data

    def __enrich_show__(item)->epg_item:
        # print("[*] Enriching show " + item["title"] + " (" + item["assetId"] + ")")
        enrichment_data_parsed = json.loads(requests.get(
            tele.__api__+"/show/"+item["assetId"]).text)

        if len(enrichment_data_parsed) == 1:
            enrichment_data = enrichment_data_parsed[0]
            for attrib in enrichment_data:
                if attrib == "persons":
                    item["persons"] = {}
                    for person in enrichment_data["persons"]:
                        if person == "cast":
                            item["persons"]["cast"] = []
                            for cast in enrichment_data["persons"]["cast"]:
                                item["persons"]["cast"].append(cast["actor"])
                        else:
                            item["persons"][person] = enrichment_data["persons"][person]
                elif attrib in ["availabilityStartTime", "availabilityEndTime", "originalStartTime"]:
                    item[attrib] = dateutil.parser.parse(
                        enrichment_data[attrib])
                else:
                    item[attrib] = enrichment_data[attrib]
        else:
            print('[x] something failed...')
            print(enrichment_data_parsed)
        return item


class teleThread (threading.Thread):
    def __init__(self, threadID, name, q, queueLock, enriched_data):
        threading.Thread.__init__(self)
        self.threadID = threadID
        self.name = name
        self.q = q
        self.queueLock = queueLock
        self.exitFlag = 0
        self.enriched_data = enriched_data

    def run(self):
        #print("[*] Starting " + self.name)
        self.process_data(self.name, self.q)
        #print("[*] Exiting " + self.name)

    def process_data(self, threadName, q):
        while not self.exitFlag:
            self.queueLock.acquire()
            if not q.empty():
                data = q.get()
                self.queueLock.release()
                self.enriched_data.append(tele.__enrich_show__(data))
            else:
                self.queueLock.release()
                self.exitFlag = 1
