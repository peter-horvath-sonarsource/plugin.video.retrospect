﻿# coding:UTF-8
import datetime

import mediaitem
import chn_class
# import proxyinfo

from regexer import Regexer
from logger import Logger
from urihandler import UriHandler
from helpers.jsonhelper import JsonHelper
from helpers.languagehelper import LanguageHelper
from helpers.htmlentityhelper import HtmlEntityHelper
from helpers.datehelper import DateHelper
from helpers.subtitlehelper import SubtitleHelper
from parserdata import ParserData
from addonsettings import AddonSettings
from streams.m3u8 import M3u8


class Channel(chn_class.Channel):
    def __init__(self, channelInfo):
        """Initialisation of the class.

        Arguments:
        channelInfo: ChannelInfo - The channel info object to base this channel on.

        All class variables should be instantiated here and this method should not
        be overridden by any derived classes.

        """

        chn_class.Channel.__init__(self, channelInfo)

        # ============== Actual channel setup STARTS here and should be overwritten from derived classes ===============
        # The following data was taken from http://playapi.mtgx.tv/v3/channels
        self.channelId = None
        if self.channelCode == "se3":
            self.mainListUri = "https://www.viafree.se/program/"
            self.noImage = "tv3seimage.png"
            self.channelId = (
                1209,  # TV4
                6000,  # MTV
                6001,  # Comedy Central
                7000,  # Online Only ???
            )

        elif self.channelCode == "se6":
            self.mainListUri = "https://www.viafree.se/program/"
            self.noImage = "tv6seimage.png"
            self.channelId = (959, )

        elif self.channelCode == "se8":
            self.mainListUri = "https://www.viafree.se/program/"
            self.noImage = "tv8seimage.png"
            self.channelId = (801, )

        elif self.channelCode == "se10":
            self.mainListUri = "https://www.viafree.se/program/"
            self.noImage = "tv10seimage.png"
            self.channelId = (5462, )

        elif self.channelCode == "viafreese":
            self.mainListUri = "https://www.viafree.se/program/"
            self.noImage = "viafreeimage.png"
            self.channelId = None

        elif self.channelCode == "sesport":
            raise NotImplementedError('ViaSat sport is not in this channel anymore.')

        # Danish channels
        elif self.channelCode == "tv3dk":
            self.mainListUri = "http://www.viafree.dk/programmer"
            self.noImage = "tv3noimage.png"
            # self.channelId = (3687, 6200, 6201) -> show all for now

        # Norwegian Channels
        elif self.channelCode == "no3":
            self.mainListUri = "https://www.viafree.no/programmer"
            self.noImage = "tv3noimage.png"
            self.channelId = (1550, 6100, 6101)

        elif self.channelCode == "no4":
            self.mainListUri = "https://www.viafree.no/programmer"
            self.noImage = "viasat4noimage.png"
            self.channelId = (935,)

        elif self.channelCode == "no6":
            self.mainListUri = "https://www.viafree.no/programmer"
            self.noImage = "viasat4noimage.png"
            self.channelId = (1337,)

        self.baseUrl = self.mainListUri.rsplit("/", 1)[0]
        self.searchInfo = {
            "se": ["sok", "S&ouml;k"],
            "ee": ["otsing", "Otsi"],
            "dk": ["sog", "S&oslash;g"],
            "no": ["sok", "S&oslash;k"],
            "lt": ["paieska", "Paie&scaron;ka"],
            "lv": ["meklet", "Mekl&#275;t"]
        }

        # setup the urls
        self.swfUrl = "http://flvplayer.viastream.viasat.tv/flvplayer/play/swf/MTGXPlayer-1.8.swf"

        # New JSON page data
        self._AddDataParser(self.mainListUri, preprocessor=self.ExtractJsonData,
                            matchType=ParserData.MatchExact)
        self._AddDataParser(self.mainListUri, preprocessor=self.ExtractCategoriesAndAddSearch, json=True,
                            matchType=ParserData.MatchExact,
                            parser=("allProgramsPage", "programs"),
                            creator=self.CreateJsonEpisodeItem)

        # This is the new way, but more complex and some channels have items with missing
        # category slugs and is not compatible with the old method channels.
        self.useNewPages = False
        if self.useNewPages:
            self._AddDataParser("*", preprocessor=self.ExtractJsonData)
            self._AddDataParser("*", json=True, preprocessor=self.MergeSeasonData,
                                # parser=("context", "dispatcher", "stores", "ContentPageProgramStore", "format", "videos", "0", "program"),
                                # creator=self.CreateJsonVideoItem
                                )

            self._AddDataParser("http://playapi.mtgx.tv/", updater=self.UpdateVideoItem)
        else:
            self._AddDataParser("*", parser=('_embedded', 'videos'), json=True, preprocessor=self.AddClips,
                                creator=self.CreateVideoItem, updater=self.UpdateVideoItem)
            self.pageNavigationJson = ("_links", "next")
            self.pageNavigationJsonIndex = 0
            self._AddDataParser("*", json=True,
                                parser=self.pageNavigationJson, creator=self.CreatePageItem)

        self._AddDataParser("https://playapi.mtgx.tv/v3/search?term=", json=True,
                            parser=("_embedded", "formats"), creator=self.CreateJsonSearchItem)

        self._AddDataParser("/api/playClient;isColumn=true;query=", json=True,
                            matchType=ParserData.MatchContains,
                            parser=("data", "formats"), creator=self.CreateJsonEpisodeItem)
        self._AddDataParser("/api/playClient;isColumn=true;query=", json=True,
                            matchType=ParserData.MatchContains,
                            parser=("data", "clips"), creator=self.CreateJsonVideoItem)
        self._AddDataParser("/api/playClient;isColumn=true;query=", json=True,
                            matchType=ParserData.MatchContains,
                            parser=("data", "episodes"), creator=self.CreateJsonVideoItem)
        # ===============================================================================================================
        # non standard items
        self.episodeLabel = LanguageHelper.get_localized_string(LanguageHelper.EpisodeId)
        self.seasonLabel = LanguageHelper.get_localized_string(LanguageHelper.SeasonId)
        self.__categories = {}

        # ===============================================================================================================
        # Test Cases
        #  No GEO Lock: Extra Extra
        #  GEO Lock:
        #  Multi Bitrate: Glamourama

        # ====================================== Actual channel setup STOPS here =======================================
        return

    def ExtractCategoriesAndAddSearch(self, data):
        """ Extracts the Category information from the JSON data

        @param data: the JSON data
        @return: Unmodified JSON data
        """

        Logger.info("Extracting Category Information")
        dummyData, items = self.AddSearch(data)

        # The data was already in a JsonHelper
        categories = data.get_value("categories")
        for category in categories:
            self.__categories[category["id"]] = category

        Logger.debug("Extracting Category Information finished")
        return data, items

    def ExtractJsonData(self, data):
        """ Extracts the JSON data from the HTML page and passes it back to Retrospect.

        @param data: the HTML data
        @return: the JSON part of the HTML data
        """

        Logger.info("Performing Pre-Processing")
        items = []

        jsonData = Regexer.DoRegex('__initialState__=([^<]+);\W+window.__config__', data)[0]
        # the "RouteStore" has some weird functions, removing it.
        # start = jsonData.index('"RouteStore"')
        # the need at least the 'ApplicationStore'
        # end = jsonData.index('"ApplicationStore"')
        # returnData = jsonData[0:start] + jsonData[end:]
        returnData = jsonData
        Logger.trace("Found Json:\n%s", returnData)

        # append categorie data
        # catData = Regexer.DoRegex('"categories":(\[.*?),"allProgramsPage', data)
        # if catData:
        #     catData = catData[0]
        #     returnData = returnData[:-1] + ', "categories": ' + catData + '}'

        # file('c:\\temp\\json.txt', 'w+').write(returnData)
        return JsonHelper(returnData), items

    def CreateJsonEpisodeItem(self, resultSet):
        return self.__CreateJsonEpisodeItem(resultSet, checkChannel=True)

    def CreateJsonSearchItem(self, resultSet):
        return self.__CreateJsonEpisodeItem(resultSet, checkChannel=False)

    def MergeSeasonData(self, data):
        items = []

        jsonData = JsonHelper(data)
        seasonFolders = jsonData.get_value("context", "dispatcher", "stores",
                                          "ContentPageProgramStore", "format", "videos")
        for season in seasonFolders:
            for video in seasonFolders[season]['program']:
                items.append(self.CreateJsonVideoItem(video))

        return data, items

    def CreateJsonVideoItem(self, resultSet):
        Logger.trace(resultSet)
        url = "http://playapi.mtgx.tv/v3/videos/stream/%(id)s" % resultSet
        item = mediaitem.MediaItem(resultSet["title"], url)
        item.type = "video"
        item.thumb = self.parentItem.thumb
        item.icon = self.parentItem.icon
        item.description = resultSet.get("summary", None)

        airedAt = resultSet.get("airedAt", None)
        if airedAt is None:
            airedAt = resultSet.get("publishedAt", None)
        if airedAt is not None:
            # 2016-05-20T15:05:00+00:00
            airedAt = airedAt.split("+")[0].rstrip('Z')
            timeStamp = DateHelper.get_date_from_string(airedAt, "%Y-%m-%dT%H:%M:%S")
            item.SetDate(*timeStamp[0:6])

        item.thumb = self.__GetThumbImage(resultSet.get("image"))

        # webvttPath / samiPath
        # loginRequired
        isPremium = resultSet.get("loginRequired", False)
        if isPremium and AddonSettings.hide_premium_items():
            Logger.debug("Found premium item, hiding it.")
            return None

        srt = resultSet.get("samiPath")
        if not srt:
            srt = resultSet.get("subtitles_webvtt")
        if srt:
            Logger.debug("Storing SRT/WebVTT path: %s", srt)
            part = item.CreateNewEmptyMediaPart()
            part.Subtitle = srt
        return item

    def AddClips(self, data):
        Logger.info("Adding Clips Pre-Processing")
        items = []

        # if the main list was retrieve using json, are the current data is json, just determine
        # the clip URL
        clipUrl = None
        if data.lstrip().startswith("{"):
            if self.parentItem.url.endswith("type=program"):
                # http://playapi.mtgx.tv/v3/videos?format=6723&order=-airdate&type=program
                # http://playapi.mtgx.tv/v3/videos?format=6723&order=-updated&type=clip" % (dataId,)
                clipUrl = self.parentItem.url.replace("type=program", "type=clip")
        else:
            # now we determine the ID and load the json data
            dataId = Regexer.DoRegex('data-format-id="(\d+)"', data)[-1]
            Logger.debug("Found FormatId = %s", dataId)
            programUrl = "http://playapi.mtgx.tv/v3/videos?format=%s&order=-airdate&type=program" % (dataId,)
            data = UriHandler.Open(programUrl, proxy=self.proxy)
            clipUrl = "http://playapi.mtgx.tv/v3/videos?format=%s&order=-updated&type=clip" % (dataId,)

        if clipUrl is not None:
            clipTitle = LanguageHelper.get_localized_string(LanguageHelper.Clips)
            clipItem = mediaitem.MediaItem("\a.: %s :." % (clipTitle,), clipUrl)
            clipItem.thumb = self.noImage
            items.append(clipItem)

        Logger.debug("Pre-Processing finished")
        return data, items

    def AddSearch(self, data):
        """Performs pre-process actions for data processing/

        Arguments:
        data : string - the retrieve data that was loaded for the current item and URL.

        Returns:
        A tuple of the data and a list of MediaItems that were generated.

        Accepts an data from the ProcessFolderList method, BEFORE the items are
        processed. Allows setting of parameters (like title etc) for the channel.
        Inside this method the <data> could be changed and additional items can
        be created.

        The return values should always be instantiated in at least ("", []).

        """

        Logger.info("Performing Pre-Processing")
        items = []

        title = "\a.: %s :." % (self.searchInfo.get(self.language, self.searchInfo["se"])[1], )
        Logger.trace("Adding search item: %s", title)
        searchItem = mediaitem.MediaItem(title, "searchSite")
        searchItem.thumb = self.noImage
        searchItem.fanart = self.fanart
        searchItem.dontGroup = True
        items.append(searchItem)

        Logger.debug("Pre-Processing finished")
        return data, items

    def SearchSite(self, url=None):
        """Creates an list of items by searching the site

        Keyword Arguments:
        url : String - Url to use to search with a %s for the search parameters

        Returns:
        A list of MediaItems that should be displayed.

        This method is called when the URL of an item is "searchSite". The channel
        calling this should implement the search functionality. This could also include
        showing of an input keyboard and following actions.

        The %s the url will be replaced with an URL encoded representation of the
        text to search for.

        """

        # https://playapi.mtgx.tv/v3/search?term=nyheter&limit=20&columns=formats&with=format&device=web&include_prepublished=1&country=se&page=1

        url = "https://playapi.mtgx.tv/v3/search?term=%s&limit=50&columns=formats&with=format" \
              "&device=web&include_prepublished=1&country={0}&page=1".format(self.language)

        # # we need to do some ugly stuff to get the %s in the URL-Encoded query.
        # query = '{"term":"tttt","limit":2000,"columns":"formats,episodes,clips","with":"format"}'
        # query = HtmlEntityHelper.url_encode(query).replace("%", "%%").replace("tttt", "%s")
        # baseUrl = self.baseUrl.rsplit('/', 1)[0]
        # url = "%s/api/playClient;isColumn=true;query=%s;resource=search?returnMeta=true" % (baseUrl, query)

        Logger.debug("Using search url: %s", url)
        return chn_class.Channel.SearchSite(self, url)

    def CreatePageItem(self, resultSet):
        """Creates a MediaItem of type 'page' using the resultSet from the regex.

        Arguments:
        resultSet : tuple(string) - the resultSet of the self.pageNavigationRegex

        Returns:
        A new MediaItem of type 'page'

        This method creates a new MediaItem from the Regular Expression or Json
        results <resultSet>. The method should be implemented by derived classes
        and are specific to the channel.

        """

        Logger.debug("Starting CreatePageItem")
        Logger.trace(resultSet)

        url = resultSet["href"]
        page = url.rsplit("=", 1)[-1]

        item = mediaitem.MediaItem(page, url)
        item.type = "page"
        Logger.debug("Created '%s' for url %s", item.name, item.url)
        return item

    def CreateSearchResult(self, resultSet):
        """Creates a MediaItem of type 'video' using the resultSet from the regex.

        Arguments:
        resultSet : tuple (string) - the resultSet of the self.videoItemRegex

        Returns:
        A new MediaItem of type 'video' or 'audio' (despite the method's name)

        This method creates a new MediaItem from the Regular Expression or Json
        results <resultSet>. The method should be implemented by derived classes
        and are specific to the channel.

        If the item is completely processed an no further data needs to be fetched
        the self.complete property should be set to True. If not set to True, the
        self.UpdateVideoItem method is called if the item is focussed or selected
        for playback.

        """

        Logger.trace(resultSet)
        item = mediaitem.MediaItem(
            resultSet["title"],
            "http://playapi.mtgx.tv/v3/videos/stream/%s" % (resultSet["url"], )
        )
        item.type = "video"
        item.thumb = resultSet["thumburl"]
        item.complete = False
        # item.description = resultSet["description"]
        return item

    def CreateVideoItem(self, resultSet):
        """Creates a MediaItem of type 'video' using the resultSet from the regex.

        Arguments:
        resultSet : tuple (string) - the resultSet of the self.videoItemRegex

        Returns:
        A new MediaItem of type 'video' or 'audio' (despite the method's name)

        This method creates a new MediaItem from the Regular Expression or Json
        results <resultSet>. The method should be implemented by derived classes
        and are specific to the channel.

        If the item is completely processed an no further data needs to be fetched
        the self.complete property should be set to True. If not set to True, the
        self.UpdateVideoItem method is called if the item is focussed or selected
        for playback.

        """

        Logger.trace(resultSet)

        drmLocked = False
        geoBlocked = resultSet["is_geo_blocked"]
        # hideGeoBloced = AddonSettings().HideGeoLocked()
        # if geoBlocked and hideGeoBloced:
        #     Logger.Warning("GeoBlocked item")
        #     return None

        title = resultSet["title"]
        if ("_links" not in resultSet or
                "stream" not in resultSet["_links"] or
                "href" not in resultSet["_links"]["stream"]):
            Logger.warning("No streams found for %s", title)
            return None

        # the description
        description = resultSet["description"].strip()  # The long version
        summary = resultSet["summary"].strip()  # The short version
        # Logger.Trace("Comparing:\nDesc: %s\nSumm:%s", description, summary)
        if description.startswith(summary):
            pass
        else:
            # the descripts starts with the summary. Don't show
            description = "%s\n\n%s" % (summary, description)

        videoType = resultSet["type"]
        if not videoType == "program":
            title = "%s (%s)" % (title, videoType.title())

        elif resultSet["format_position"]["is_episodic"]:  # and resultSet["format_position"]["episode"] != "0":
            # make sure we show the episodes and seaso
            # season = int(resultSet["format_position"]["season"])
            episode = int(resultSet["format_position"]["episode"] or "0")
            # name = "s%02de%02d" % (season, episode)
            webisode = resultSet.get("webisode", False)

            # if the name had the episode in it, translate it
            if episode > 0 and not webisode:
                description = "%s\n\n%s" % (title, description)
                title = "%s - %s %s %s %s" % (resultSet["format_title"],
                                              self.seasonLabel,
                                              resultSet["format_position"]["season"],
                                              self.episodeLabel,
                                              resultSet["format_position"]["episode"])
            else:
                Logger.debug("Found episode number '0' for '%s', using name instead of episode number", title)

        url = resultSet["_links"]["stream"]["href"]
        item = mediaitem.MediaItem(title, url)

        dateInfo = None
        dateFormat = "%Y-%m-%dT%H:%M:%S"
        if "broadcasts" in resultSet and len(resultSet["broadcasts"]) > 0:
            dateInfo = resultSet["broadcasts"][0]["air_at"]
            Logger.trace("Date set from 'air_at'")

            if "playable_from" in resultSet["broadcasts"][0]:
                startDate = resultSet["broadcasts"][0]["playable_from"]
                playableFrom = DateHelper.get_date_from_string(startDate[0:-6], dateFormat)
                playableFrom = datetime.datetime(*playableFrom[0:6])
                if playableFrom > datetime.datetime.now():
                    drmLocked = True

        elif "publish_at" in resultSet:
            dateInfo = resultSet["publish_at"]
            Logger.trace("Date set from 'publish_at'")

        if dateInfo is not None:
            # publish_at=2007-09-02T21:55:00+00:00
            info = dateInfo.split("T")
            dateInfo = info[0]
            timeInfo = info[1]
            dateInfo = dateInfo.split("-")
            timeInfo = timeInfo.split(":")
            item.SetDate(dateInfo[0], dateInfo[1], dateInfo[2], timeInfo[0], timeInfo[1], 0)

        item.type = "video"
        item.complete = False
        item.icon = self.icon
        item.isGeoLocked = geoBlocked
        item.isDrmProtected = drmLocked

        thumbData = resultSet['_links'].get('image', None)
        if thumbData is not None:
            # item.thumbUrl = thumbData['href'].replace("{size}", "thumb")
            item.thumb = self.__GetThumbImage(thumbData['href'])

        item.description = description

        srt = resultSet.get("sami_path")
        if not srt:
            srt = resultSet.get("subtitles_webvtt")
        if srt:
            Logger.debug("Storing SRT/WebVTT path: %s", srt)
            part = item.CreateNewEmptyMediaPart()
            part.Subtitle = srt
        return item

    def UpdateVideoItem(self, item):
        """Updates an existing MediaItem with more data.

        Arguments:
        item : MediaItem - the MediaItem that needs to be updated

        Returns:
        The original item with more data added to it's properties.

        Used to update none complete MediaItems (self.complete = False). This
        could include opening the item's URL to fetch more data and then process that
        data or retrieve it's real media-URL.

        The method should at least:
        * set at least one MediaItemPart with a single MediaStream.
        * set self.complete = True.

        if the returned item does not have a MediaItemPart then the self.complete flag
        will automatically be set back to False.

        """

        Logger.debug('Starting UpdateVideoItem for %s (%s)', item.name, self.channelName)
        useKodiHls = AddonSettings.use_adaptive_stream_add_on()

        # User-agent (and possible other headers), should be consistent over all M3u8 requests (See #864)
        headers = {}
        if not useKodiHls:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows; U; Windows NT 6.1; en-GB; rv:1.9.2.13) Gecko/20101203 Firefox/3.6.13 (.NET CLR 3.5.30729)",
            }
        if self.localIP:
            headers.update(self.localIP)

        data = UriHandler.Open(item.url, proxy=self.proxy, additionalHeaders=headers or None)
        json = JsonHelper(data)

        # see if there was an srt already
        if item.MediaItemParts:
            part = item.MediaItemParts[0]
            if part.Subtitle and part.Subtitle.endswith(".vtt"):
                part.Subtitle = SubtitleHelper.download_subtitle(part.Subtitle, format="webvtt", proxy=self.proxy)
            else:
                part.Subtitle = SubtitleHelper.download_subtitle(part.Subtitle, format="dcsubtitle", proxy=self.proxy)
        else:
            part = item.CreateNewEmptyMediaPart()

        for q in ("high", 3500), ("hls", 2700), ("medium", 2100):
            url = json.get_value("streams", q[0])
            Logger.trace(url)
            if not url:
                continue

            if ".f4m" in url:
                # Kodi does not like the f4m streams
                continue

            if url.startswith("http") and ".m3u8" in url:
                # first see if there are streams in this file, else check the second location.
                for s, b in M3u8.get_streams_from_m3u8(url, self.proxy, headers=headers):
                    if useKodiHls:
                        strm = part.AppendMediaStream(url, 0)
                        M3u8.set_input_stream_addon_input(strm, headers=headers)
                        # Only the main M3u8 is needed
                        break
                    else:
                        part.AppendMediaStream(s, b)

                if not part.MediaStreams and "manifest.m3u8" in url:
                    Logger.warning("No streams found in %s, trying alternative with 'master.m3u8'", url)
                    url = url.replace("manifest.m3u8", "master.m3u8")
                    for s, b in M3u8.get_streams_from_m3u8(url, self.proxy, headers=headers):
                        if useKodiHls:
                            strm = part.AppendMediaStream(url, 0)
                            M3u8.set_input_stream_addon_input(strm, headers=headers)
                            # Only the main M3u8 is needed
                            break
                        else:
                            part.AppendMediaStream(s, b)

                # check for subs
                # https://mtgxse01-vh.akamaihd.net/i/201703/13/DCjOLN_1489416462884_427ff3d3_,48,260,460,900,1800,2800,.mp4.csmil/master.m3u8?__b__=300&hdnts=st=1489687185~exp=3637170832~acl=/*~hmac=d0e12e62c219d96798e5b5ef31b11fa848724516b255897efe9808c8a499308b&cc1=name=Svenska%20f%C3%B6r%20h%C3%B6rselskadade~default=no~forced=no~lang=sv~uri=https%3A%2F%2Fsubstitch.play.mtgx.tv%2Fsubtitle%2Fconvert%2Fxml%3Fsource%3Dhttps%3A%2F%2Fcdn-subtitles-mtgx-tv.akamaized.net%2Fpitcher%2F20xxxxxx%2F2039xxxx%2F203969xx%2F20396967%2F20396967-swt.xml%26output%3Dm3u8
                # https://cdn-subtitles-mtgx-tv.akamaized.net/pitcher/20xxxxxx/2039xxxx/203969xx/20396967/20396967-swt.xml&output=m3u8
                if "uri=" in url and not part.Subtitle:
                    Logger.debug("Extracting subs from M3u8")
                    subUrl = url.rsplit("uri=")[-1]
                    subUrl = HtmlEntityHelper.url_decode(subUrl)
                    subData = UriHandler.Open(subUrl, proxy=self.proxy)
                    # subUrl = None
                    subs = filter(lambda line: line.startswith("http"), subData.split("\n"))
                    if subs:
                        part.Subtitle = SubtitleHelper.download_subtitle(subs[0], format='webvtt', proxy=self.proxy)

            elif url.startswith("rtmp"):
                # rtmp://mtgfs.fplive.net/mtg/mp4:flash/sweden/tv3/Esport/Esport/swe_skillcompetition.mp4.mp4
                oldUrl = url
                if not url.endswith(".flv") and not url.endswith(".mp4"):
                    url += '.mp4'

                if "/mp4:" in url:
                    # in this case we need to specifically set the path
                    # url = url.replace('/mp4:', '//') -> don't do this, but specify the path
                    server, path = url.split("mp4:", 1)
                    url = "%s playpath=mp4:%s" % (server, path)

                if oldUrl != url:
                    Logger.debug("Updated URL from - to:\n%s\n%s", oldUrl, url)

                url = self.GetVerifiableVideoUrl(url)
                part.AppendMediaStream(url, q[1])

            elif "[empty]" in url:
                Logger.debug("Found post-live url with '[empty]' in it. Ignoring this.")
                continue
            else:
                part.AppendMediaStream(url, q[1])

        if not useKodiHls:
            part.HttpHeaders.update(headers)

        if part.MediaStreams:
            item.complete = True
        Logger.trace("Found mediaurl: %s", item)
        return item

    def __CreateJsonEpisodeItem(self, resultSet, checkChannel=True):
        Logger.trace(resultSet)
        if checkChannel and self.channelId is not None and resultSet['channel'] not in self.channelId:
            Logger.trace("Found item for wrong channel %s instead of %s", resultSet['channel'], self.channelId)
            return None

        # For now we keep using the API, otherwise we need to do more complex VideoItem parsing
        if self.useNewPages:
            categorySlug = self.__categories[resultSet["category"]]["slug"]
            url = "%s/%s/%s" % (self.baseUrl, categorySlug, resultSet['slug'])
        else:
            url = "http://playapi.mtgx.tv/v3/videos?format=%(id)s&order=-airdate&type=program" % resultSet
        item = mediaitem.MediaItem(resultSet['title'], url)
        item.icon = self.icon
        item.thumb = self.__GetThumbImage(resultSet.get("image") or self.noImage)
        # item.fanart = self.__GetThumbImage(resultSet.get("image") or self.fanart, fanartSize=True)

        item.isGeoLocked = resultSet.get('onlyAvailableInSweden', False)
        return item

    def __GetThumbImage(self, url, fanartSize=False):
        if not url:
            return url

        if fanartSize:
            return url.replace("{size}", "1280x720")
        return url.replace("{size}", "230x150")
