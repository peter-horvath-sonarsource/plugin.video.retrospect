#===============================================================================
# LICENSE Retrospect-Framework - CC BY-NC-ND
#===============================================================================
# This work is licenced under the Creative Commons
# Attribution-Non-Commercial-No Derivative Works 3.0 Unported License. To view a
# copy of this licence, visit http://creativecommons.org/licenses/by-nc-nd/3.0/
# or send a letter to Creative Commons, 171 Second Street, Suite 300,
# San Francisco, California 94105, USA.
#===============================================================================

import os
from xbmcwrapper import XbmcWrapper
from helpers.jsonhelper import JsonHelper

__all__ = ["local", "remote", "cached", "TextureHandler"]

Local = "local"
Remote = "remote"
Cached = "cached"


class TextureHandler:
    __TextureHandler = None

    def __init__(self, logger):
        """ Initialize the texture base

        @param logger:      A logger to log stuff.

        """

        self._logger = logger               # : a logger
        self._addonId = None                # : the addon ID

        # some dictionaries for caching
        self.__cdnPaths = {}
        self.__addonIds = {}

    @staticmethod
    def instance():
        return TextureHandler.__TextureHandler

    @staticmethod
    def set_texture_handler(config, logger, uri_handler=None):
        """ Fetches a TextureManager for specific mode and channel.

        @param config:              The Retrospect Config object
        @param logger:              An Logger
        @param uri_handler:          The UriHandler

        @return: A TextureHandler object for the requested mode

        """

        mode = config.TextureMode.lower()
        if logger is not None:
            logger.trace("Creating '%s' Texture Mananger", mode)

        if mode == Local:
            import local
            TextureHandler.__TextureHandler = local.Local(logger)
        elif mode == Remote:
            import remote
            TextureHandler.__TextureHandler = remote.Remote(config.TextureUrl, logger)
        elif mode == Cached:
            import cached
            TextureHandler.__TextureHandler = cached.Cached(config.TextureUrl,
                                                            config.profileDir, config.profileUri,
                                                            logger, uri_handler)
        else:
            raise Exception("Invalide mode: %s" % (mode,))

        return TextureHandler.__TextureHandler

    def get_texture_uri(self, channel, file_name):
        """ Gets the full URI for the image file. Depending on the type of textures handling, it might also cache
        the texture and return that path.

        @param file_name: the file name
        @param channel:  the channel

        """

        # Should be implemented
        pass

    def number_of_missing_textures(self):
        """ Indication whether or not textures need to be retrieved.

        @return: a boolean value
        """

        # Could be implemented
        return 0

    def fetch_textures(self, dialog_call_back=None):
        """ Fetches all the needed textures

        @param dialog_call_back:  Callback method with signature
                                  Function(self, retrievedSize, totalSize, perc, completed, status)

        @return: the number of bytes fetched

        """

        # Could be implemented
        return 0

    def purge_texture_cache(self, channel):
        """ Removes those entries from the textures cache that are no longer required.

        @param channel:  the channel

        """

        # Should be implemented
        pass

    def _get_addon_id(self, channel):
        """ Determines the add-on ID from the add-on to which the channel belongs,
        e.g.: net.rieter.xot.channel.be

        @param channel: the channel to determine the CDN folder for.

        Remark: we cache some stuff for performance improvements

        """

        if channel.path in self.__addonIds:
            return self.__addonIds[channel.path]

        parts = channel.path.rsplit(os.sep, 2)[-2:]
        addon_id = parts[0]
        self.__addonIds[channel.path] = addon_id
        return addon_id

    def _get_cdn_sub_folder(self, channel):
        """ Determines the CDN folder, e.g.: net.rieter.xot.channel.be.canvas

        @param channel: the channel to determine the CDN folder for.

        Remark: we cache some stuff for performance improvements

        """

        if channel.path in self.__cdnPaths:
            return self.__cdnPaths[channel.path]

        parts = channel.path.rsplit(os.sep, 2)[-2:]
        cdn = ".".join(parts)
        self.__cdnPaths[channel.path] = cdn
        return cdn

    def _purge_kodi_cache(self, channel_texture_path):
        """ Class the JSON RPC within Kodi that removes all changed items which paths contain the
        value given in channelTexturePath

        @param channel_texture_path: string - The

        """

        json_cmd = '{' \
                   '"jsonrpc": "2.0", ' \
                   '"method": "Textures.GetTextures", ' \
                   '"params": {' \
                   '"filter": {"operator": "contains", "field": "url", "value": "%s"}, ' \
                   '"properties": ["url"]' \
                   '}, ' \
                   '"id": "libTextures"' \
                   '}' % (channel_texture_path,)
        json_results = XbmcWrapper.ExecuteJsonRpc(json_cmd, self._logger)

        results = JsonHelper(json_results, logger=self._logger)
        if "error" in results.json or "result" not in results.json:
            self._logger.error("Error retreiving textures:\nCmd   : %s\nResult: %s", json_cmd, results.json)
            return

        results = results.get_value("result", "textures", fallback=[])
        for result in results:
            texture_id = result["textureid"]
            texture_url = result["url"]
            self._logger.debug("Going to remove texture: %d - %s", texture_id, texture_url)
            json_cmd = '{' \
                       '"jsonrpc": "2.0", ' \
                       '"method": "Textures.RemoveTexture", ' \
                       '"params": {' \
                       '"textureid": %s' \
                       '}' \
                       '}' % (texture_id,)
            XbmcWrapper.ExecuteJsonRpc(json_cmd, self._logger)
        return
