class teleboy:
    def get_images(teleboy_raw):
        icon_links = []
        for program in teleboy_raw:
            icon = {}
            icon['name'] = program['station']
            icon['src'] = "https://www.teleboy.ch/assets/stations/" + \
                str(program['stationid']) + "/icon160_light.png"
            icon_links.append(icon)

        return icon_links
