import os
import io
import json
import xbmc


def migrate_profile(new_profile, add_on_id, kodi_add_on_dir):
    """ Migrates the old user profile.

    :param str|unicode new_profile:     The new profile folder
    :param str|unicode add_on_id:       The new add-on id
    :param str|unicode kodi_add_on_dir: The Kodi add-on dir

    """

    old_add_on_id = "net.rieter.xot"

    # If the profile already existed, just stop here.
    if os.path.isdir(new_profile):
        return

    import shutil

    old_add_on_path = os.path.abspath(os.path.join(kodi_add_on_dir, "..", old_add_on_id))

    # If an old add-on with the old ID was found, disable and rename it.
    if os.path.isdir(old_add_on_path):
        xbmc.log("Retrospect: Disabling add-on from {}".format(old_add_on_path), 1)

        # Disable it.
        data = {
            "jsonrpc": "2.0",
            "method": "Addons.SetAddonEnabled",
            "params": {
                "addonid": old_add_on_id,
                "enabled": False},
            "id": 1
        }
        result = xbmc.executeJSONRPC(json.dumps(data))
        xbmc.log(result, xbmc.LOGINFO)
        result = json.loads(result)
        if not result or "error" in result:
            xbmc.log("Retrospect: Error disabling {}".format(old_add_on_id), xbmc.LOGERROR)

        # Rename it.
        old_add_on_xml = os.path.join(old_add_on_path, "addon.xml")
        if os.path.exists(old_add_on_xml):
            with io.open(old_add_on_xml, mode="r", encoding='utf-8') as fp:
                content = fp.read()

            content = content.replace('name="Retrospect"', 'name="Retrospect OLD ID"')
            with io.open(old_add_on_xml, mode='w+', encoding='utf-8') as fp:
                fp.write(content)

    # If there was an old profile, migrate it.
    old_profile = os.path.join(new_profile, "..", old_add_on_id)
    if not os.path.exists(old_profile):
        return

    xbmc.log("Retrospect: Cloning {} addon_data to {}".format(old_add_on_id, add_on_id), 1)
    shutil.copytree(old_profile, new_profile, ignore=shutil.ignore_patterns("textures"))

    # If there were local setttings, we need to migrate those too so the channel ID's are updated.
    local_settings_file = os.path.join(new_profile, "settings.json")
    if not os.path.exists(local_settings_file):
        return

    xbmc.log("Retrospect: Migrating {}".format(local_settings_file), 1)
    with io.open(local_settings_file, mode="rb") as fp:
        content = fp.read()
        settings = json.loads(content, encoding='utf-8')

    channel_ids = settings.get("channels", {})
    channel_settings = {}
    for channel_id in channel_ids:
        new_channel_id = channel_id.replace(old_add_on_id, add_on_id)
        xbmc.log("Retrospect: Renaming {} -> {}".format(channel_id, new_channel_id), 1)
        channel_settings[new_channel_id] = settings["channels"][channel_id]

    settings["channels"] = channel_settings
    with io.open(local_settings_file, mode='w+b') as fp:
        content = json.dumps(settings, indent=4, encoding='utf-8')
        fp.write(content)

    # fix the favourites
    favourites_path = os.path.join(new_profile, "favourites")
    if os.path.isdir(favourites_path):
        xbmc.log("Updating favourites at {}".format(favourites_path), xbmc.LOGINFO)
        for fav in os.listdir(favourites_path):
            # plugin://net.rieter.xot/
            fav_path = os.path.join(favourites_path, fav)
            xbmc.log("Updating favourite: {}".format(fav), xbmc.LOGINFO)
            with io.open(fav_path, mode='r', encoding='utf-8') as fp:
                content = fp.read()

            content = content.replace("plugin://net.rieter.xot/",
                                      "plugin://plugin.video.retrospect/")
            with io.open(fav_path, mode='w+', encoding='utf-8') as fp:
                fp.write(content)

    return
