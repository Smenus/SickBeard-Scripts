import os
import re
import difflib
import requests
import datetime

import patterns


class Metadata_Source:
    def __init__(self, config):
        self.config = config

    def get_metadata(self, tvdb_id, filename):
        metadata = dict()

        # Start filename parsing
        fp = Filename_Parser()
        seriesname, seasonnumber, episodenumber, episodenumberend = fp.parse(filename)

        metadata['seriesname'] = seriesname
        metadata['seasonnumber'] = str(seasonnumber)
        metadata['episodenumber'] = str(episodenumber)
        metadata['episodename'] = filename
        # End filename parsing

        # Start Trakt.tv fetching
        # Get episodes data
        req = requests.get('http://api.trakt.tv/show/season.json/%s/%s/%d' % (self.config.get('general', 'traktapi'), tvdb_id, seasonnumber))
        if req.status_code == 200:
            j = req.json()
            metadata['episodecount'] = str(len(j))
            if episodenumber <= len(j):
                ep = j[episodenumber - 1]
                if 'title' in ep:
                    #metadata['episodename'] = self._clean_for_itunes(ep['title'])
                    metadata['episodename'] = ep['title']
                if 'first_aired' in ep:
                    airdate = datetime.datetime.utcfromtimestamp(long(ep['first_aired']))
                    metadata['airdate'] = airdate.strftime('%Y-%m-%dT%H:%M:%SZ')
                if 'tvdb_id' in ep:
                    metadata['id'] = str(ep['tvdb_id'])
                if 'overview' in ep:
                    metadata['description'] = ep['overview']

                for ep_num in range(episodenumber + 1, episodenumberend + 1):
                    if ep_num <= len(j):
                        ep = j[ep_num - 1]
                        if 'title' in ep:
                            #metadata['episodename'] = metadata['episodename'] + ' / ' + self._clean_for_itunes(ep['title'])
                            metadata['episodename'] = metadata['episodename'] + ' / ' + ep['title']
                        if 'overview' in ep:
                            metadata['description'] = metadata['description'] + '\n' + ep['overview']

        # Get show data
        req = requests.get('http://api.trakt.tv/show/summary.json/%s/%s' % (self.config.get('general', 'traktapi'), tvdb_id))
        if req.status_code == 200:
            j = req.json()
            if 'people' in j:
                if 'actors' in j['people']:
                    actors = []
                    for actor in j['people']['actors']:
                        if actor['name'] is not None and actor['name'] not in actors:
                            actors.append(actor['name'])
                    metadata['actors'] = actors
            if 'title' in j:
                metadata['seriesname'] = self._clean_for_itunes(j['title'])
            if 'genres' in j:
                metadata['genre'] = j['genres'][0]
            if 'network' in j:
                metadata['network'] = j['network']
            if 'certification' in j:
                metadata['certificate'] = j['certification']
            if 'images' in j:
                if 'poster' in j['images']:
                    metadata['poster'] = j['images']['poster']
        # End Trakt.tv fetching

        # Actually, the data from Trakt.tv is pretty good, so we don't need to go to iTunes
        # Start iTunes fetching
        # Search for the season
        #for season in itunes.search_season(metadata['seriesname'] + ', Season ' + metadata['seasonnumber']):
        #    if self._is_similar(season.get_artist().get_name(), self._clean_for_itunes(metadata['seriesname'])):
        #        for episode in season.get_tracks():
        #            if self._is_similar(episode.get_name(), self._clean_for_itunes(metadata['episodename'])):
        #                return metadata

        # Search for the volume
        #for vol in itunes.search_season(metadata['seriesname'] + ', Vol. ' + metadata['seasonnumber']):
        #    if self._is_similar(vol.get_artist().get_name(), self._clean_for_itunes(metadata['seriesname'])):
        #        for episode in vol.get_tracks():
        #            if self._is_similar(episode.get_name(), self._clean_for_itunes(metadata['episodename'])):
        #                return metadata

        # Search for the episode
        #for episode in itunes.search_episode(metadata['seriesname'] + ' ' + metadata['episodename']):
        #    if (self._is_similar(episode.get_artist().get_name(), self._clean_for_itunes(metadata['seriesname'])) and
        #            self._is_similar(episode.get_name(), self._clean_for_itunes(metadata['episodename']))):
        #        return metadata
        # End iTunes fetching

        return metadata

    def _clean_for_itunes(self, seriesname):
        return re.sub("(.*?) \(\d*?\)$", "\\1", seriesname)

    def _is_similar(self, one, two):
        return difflib.SequenceMatcher(None, one.lower(), two.lower()).ratio() >= float(self.config.get('tagMP4', 'itunes_match'))


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
                    seriesname = self._clean_match(match.group('seriesname'))
                else:
                    raise NameError("Regex must contain seriesname. Pattern was:\n" + cmatcher.pattern)

                if 'seasonnumber' in namedgroups:
                    seasonnumber = int(self._clean_match(match.group('seasonnumber')))
                else:
                    seasonnumber = 1

                if 'episodenumber' in namedgroups:
                    episodenumber = int(self._clean_match(match.group('episodenumber')))
                else:
                    if 'episodenumberstart' in namedgroups:
                        episodenumber = int(self._clean_match(match.group('episodenumberstart')))
                    else:
                        raise NameError("Regex must contain either episodenumber or episodenumberstart. Pattern was:\n" + cmatcher.pattern)

                if 'episodenumberend' in namedgroups:
                    episodenumberend = int(self._clean_match(match.group('episodenumberend')))
                else:
                    episodenumberend = episodenumber

                return (seriesname, seasonnumber, episodenumber, episodenumberend)
        else:
            raise LookupError("Couldn't match filename against any of the regexs")

    def _clean_match(self, match):
        """Cleans up regex match by removing any . and _
        characters, along with any trailing and leading hyphens.

        Is basically equivalent to replacing all _ and . with a
        space, but handles decimal numbers in string, for example:

        >>> cleanRegexedmatch("an.example.1.0.test")
        'an example 1.0 test'
        >>> cleanRegexedmatch("an_example_1.0_test")
        'an example 1.0 test'
        """
        match = re.sub("(\D)[.](\D)", "\\1 \\2", match)
        match = re.sub("(\D)[.]", "\\1 ", match)
        match = re.sub("[.](\D)", " \\1", match)
        match = match.replace("_", " ")
        match = re.sub("-$", "", match)
        match = re.sub("^-", "", match)
        match = re.sub("(.*?) \(\d\d\d\d\)", "\\1", match)
        return match.strip()

    def _compile_regexs(self):
        """Takes filename_patterns from patterns, compiles them all
        into compiled_regexs
        """
        compiled_regexs = []

        for cpattern in patterns.filename_patterns:
            try:
                cregex = re.compile(cpattern, re.VERBOSE)
            except re.error, errormsg:
                raise RuntimeWarning("Invalid episode_pattern (error: %s)\nPattern:\n%s" % (errormsg, cpattern))
            else:
                compiled_regexs.append(cregex)

        return compiled_regexs
