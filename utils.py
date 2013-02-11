#!/usr/local/bin/python

import os
import re
import difflib
from pkg_resources import require

require('tvdb_api')
require('python-itunes')

from tvdb_api import (Tvdb, tvdb_error)
import itunes

import patterns



class Metadata_Source:
    def __init__(self, itunes_match):
        self.itunes_match = itunes_match


    def get_tvdb(self, tvdb_id, season_num, episode_num):
        print ' - Getting TheTVDB metadata'

        try:
            tvdb_instance = Tvdb(cache=False, banners=True, actors=True)
            tvdb_show = tvdb_instance[tvdb_id]
            tvdb_episode = tvdb_show[season_num][episode_num]
        except tvdb_error, errormsg:
            print ' - Warning - Could not fetch TheTVDB metadata - %s' % errormsg
            tvdb_show = None
            tvdb_episode = None

        return (tvdb_show, tvdb_episode)


    def get_itunes(self, tvdb_show, tvdb_episode, season_num, episode_num, filename):
        if tvdb_show is not None and tvdb_episode is not None:
            print ' - Getting iTunes metadata from TheTVDB metadata'

            seriesname = re.sub("(.*?) \(\d\d\d\d\)", "\\1", tvdb_show['seriesname'])

            for ep in itunes.search_episode(seriesname + ' ' + tvdb_episode['episodename']):
                if difflib.SequenceMatcher(None, tvdb_episode['episodename'].lower(), ep.get_name().lower()).ratio() >= self.itunes_match:
                    return (ep.get_album(), ep)
            
            # Couldn't find exact match for episode name, try searching for season first
            for season in itunes.search_season(seriesname + ', Season ' + str(season_num)):
                if difflib.SequenceMatcher(None, seriesname.lower(), season.get_artist().get_name().lower()).ratio() >= self.itunes_match:
                    for ep in season.get_tracks():
                        if difflib.SequenceMatcher(None, tvdb_episode['episodename'].lower(), ep.get_name().lower()).ratio() >= self.itunes_match:
                            return (season, ep)

            # Last try, without season number
            for season in itunes.search_season(seriesname):
                if difflib.SequenceMatcher(None, seriesname.lower(), season.get_artist().get_name().lower()).ratio() >= self.itunes_match:
                    for ep in season.get_tracks():
                        if difflib.SequenceMatcher(None, tvdb_episode['episodename'].lower(), ep.get_name().lower()).ratio() >= self.itunes_match:
                            return (season, ep)

        print ' - No iTunes metadata found'
        return (None, None)



class Filename_Parser:
    def parse(self, file):
        """Runs path via configured regex, extracting data from groups.
        Returns an EpisodeInfo instance containing extracted data.
        """
        _, filename = os.path.split(file)

        for cmatcher in self._compile_regexs():
            match = cmatcher.match(filename)
            if match:
                namedgroups = match.groupdict().keys()

                if 'seriesname' in namedgroups:
                    seriesname = match.group('seriesname')
                else:
                    raise ConfigValueError(
                        "Regex must contain seriesname. Pattern was:\n" + cmatcher.pattern)

                if seriesname != None:
                    seriesname = self._clean_series_name(seriesname)

                return seriesname
        else:
            return filename


    def _clean_series_name(self, seriesname):
        """Cleans up series name by removing any . and _
        characters, along with any trailing hyphens.

        Is basically equivalent to replacing all _ and . with a
        space, but handles decimal numbers in string, for example:

        >>> cleanRegexedSeriesName("an.example.1.0.test")
        'an example 1.0 test'
        >>> cleanRegexedSeriesName("an_example_1.0_test")
        'an example 1.0 test'
        """
        seriesname = re.sub("(\D)[.](\D)", "\\1 \\2", seriesname)
        seriesname = re.sub("(\D)[.]", "\\1 ", seriesname)
        seriesname = re.sub("[.](\D)", " \\1", seriesname)
        seriesname = seriesname.replace("_", " ")
        seriesname = re.sub("-$", "", seriesname)
        seriesname = re.sub("(.*?) \(\d\d\d\d\)", "\\1", seriesname)
        return seriesname.strip()


    def _compile_regexs(self):
        """Takes filename_patterns from patterns, compiles them all
        into compiled_regexs
        """
        compiled_regexs = []

        for cpattern in patterns.filename_patterns:
            try:
                cregex = re.compile(cpattern, re.VERBOSE)
            except re.error, errormsg:
                warn("WARNING: Invalid episode_pattern (error: %s)\nPattern:\n%s" % (
                    errormsg, cpattern))
            else:
                compiled_regexs.append(cregex)

        return compiled_regexs
