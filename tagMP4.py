#!/usr/local/bin/python

import os
import sys
import subprocess
import pipes
import urllib
import StringIO
import re
import time
from pkg_resources import require

require('python-itunes')
require('VideoConverter')
require('tvdb_api')
require('python-dateutil')

import itunes
from converter import Converter
from tvdb_api import (Tvdb, tvdb_error)
import dateutil.parser

import patterns



class Episode_Tags:
    def __init__(self, tvdb_id, season_num, episode_num, file):
        self.file = file
        self.tvdb_id = tvdb_id
        self.season_num = season_num
        self.episode_num = episode_num
        self.artwork_path = None
        self.airdate = None
        self.tvdb_show = None
        self.tvdb_episode = None
        self.itunes_season = None
        self.itunes_episode = None

    def _fetch_tvdb(self):
        print ' - Getting TheTVDB metadata'

        tvdb_instance = Tvdb(cache=True, banners=True, actors=True)
        
        try:
            self.tvdb_show = tvdb_instance[self.tvdb_id]
            self.tvdb_episode = self.tvdb_show[self.season_num][self.episode_num]
        except tvdb_error, errormsg:
            print ' - Warning - Could not fetch TheTVDB metadata - %s' % errormsg
            self.tvdb_show = None
            self.tvdb_episode = None
            return


    def _fetch_itunes(self):
        if self.tvdb_show is not None and self.tvdb_episode is not None:
            print ' - Getting iTunes metadata from TheTVDB metadata'

            seriesname = re.sub("(.*?) \(\d\d\d\d\)", "\\1", self.tvdb_show['seriesname'])
            itunes_episodes = itunes.search_episode(seriesname + ' ' + self.tvdb_episode['episodename'])

            if len(itunes_episodes) > 0:
                self.itunes_episode = itunes_episodes[0]
                self.itunes_season = self.itunes_episode.get_album()
            else:
                print ' - No iTunes metadata found from TheTVDB metadata'

        if self.itunes_episode is None or self.itunes_season is None:
            print ' - Getting iTunes metadata from filename'

            fp = Filename_Parser(self.file)
            seriesname = re.sub("(.*?) \(\d\d\d\d\)", "\\1", fp.parse())

            self.itunes_season = itunes.search_season(seriesname + ', Season ' + str(self.season_num))
            itunes_episodes = self.itunes_season.get_tracks()

            for ep in itunes_episodes:
                if ep.number == int(self.episode_num):
                    self.itunes_episode = ep
                    break

            if self.itunes_episode is None:
                print ' - No iTunes metadata found from filename'
                self.itunes_season = None


    def _get_metadata(self):
        self._fetch_tvdb()
        self._fetch_itunes()

        print ' - Get metadata from discovered source'

        tags = []

        tags.append({'TVSeasonNum': str(self.season_num)})
        tags.append({'TVEpisodeNum': str(self.episode_num)})
        tags.append({'disk': '1/1'})
        tags.append({'stik': 'TV Show'})
        tags.append({'artwork': self._get_artwork()})

        # Options only TheTVDB has
        if self.tvdb_show is not None and self.tvdb_episode is not None:
            tags.append({'TVNetwork': self.tvdb_show['network']})
            tags.append({'TVEpisode': self.tvdb_episode['productioncode']})

        # Options only iTunes has
        if self.itunes_season is not None and self.itunes_episode is not None:
            tags.append({'copyright': self.itunes_season.get_copyright()})
            tags.append({'advisory': ('clean' if self.itunes_episode.get_explicitness() == 'notExplicit' else 'explicit')})
            tags.append({'contentRating': self.itunes_episode.get_content_rating()})
        
        # Can be set from either iTunes or TheTVDB
        if self.itunes_season is not None and self.itunes_episode is not None:
            tags.append({'TVShowName': self.itunes_episode.get_artist().get_name()})
            tags.append({'artist': self.itunes_episode.get_artist().get_name()})
            tags.append({'title': self.itunes_episode.get_name()})
            tags.append({'album': self.itunes_season.get_name()})
            tags.append({'genre': self.itunes_episode.get_genre()})
            tags.append({'tracknum': str(self.episode_num) + '/' + str(self.itunes_season.get_track_count())})
            tags.append({'year': self.itunes_episode.get_release_date_raw()})
            tags.append({'cnID': str(self.itunes_episode.get_id())})
            tags.append({'description': self.itunes_episode.get_long_description()[:254] + (self.itunes_episode.get_long_description()[254:] and '\u2026')})
            tags.append({'longdesc': self.itunes_episode.get_long_description()})
            tags.append({'comment': 'Tagged with iTunes metadata'})
            self.airdate = self.itunes_episode.get_release_date_raw()
        elif self.tvdb_show is not None and self.tvdb_episode is not None:
            tags.append({'TVShowName': self.tvdb_show['seriesname']})
            tags.append({'artist': self.tvdb_show['seriesname']})
            tags.append({'title': self.tvdb_episode['episodename']})
            tags.append({'album': self.tvdb_show['seriesname'] + ', Season ' + str(self.season_num)})
            tags.append({'genre': self.tvdb_show['genre'].strip('|').split('|')[0]})
            tags.append({'tracknum': str(self.episode_num) + '/' + str(len(self.tvdb_show[self.season_num]))})
            tags.append({'year': self.tvdb_episode['firstaired']})
            tags.append({'cnID': self.tvdb_episode['id']})
            tags.append({'description': self.tvdb_episode['overview'][:254] + (self.tvdb_episode['overview'][254:] and '\u2026')})
            tags.append({'longdesc': self.tvdb_episode['overview']})
            tags.append({'comment': 'Tagged with TheTVDB metadata'})
            self.airdate = self.tvdb_episode['firstaired']
        else:
            fp = Filename_Parser(self.file)
            seriesname = fp.parse()
            tags.append({'TVShowName': seriesname})
            tags.append({'artist': seriesname})
            tags.append({'title': os.path.splitext(os.path.split(self.file)[1])[0]})
            tags.append({'album': seriesname + ', Season ' + str(self.season_num)})
            tags.append({'tracknum': str(self.episode_num)})

        # Check file for HDness
        print ' - Scanning video to check HDness'

        c = Converter(config.get('paths', 'ffmpeg'), config.get('paths', 'ffprobe'))
        info = c.probe(self.file)
        tags.append({'hdvideo': '1' if (info.video.video_height >= 700 or info.video.video_width >= 1260) else '0'})

        return tags


    def _gen_XML(self):
        header = '<?xml version="1.0" encoding="UTF-8"?>\n<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">\n<plist version="1.0">\n<dict>'
        castheader = '\n  <key>cast</key>\n  <array>'
        directorheader = '\n  <key>directors</key>\n  <array>'
        producerheader = '\n  <key>producers</key>\n  <array>'
        writerheader = '\n  <key>screenwriters</key>\n  <array>'
        subfooter = '\n  </array>'
        nameheader = '\n    <dict>\n      <key>name</key>\n      <string>'
        namefooter = '</string>\n    </dict>'
        footer = '\n</dict>\n</plist>\n'
        
        output = StringIO.StringIO()
        output.write(header)

        directors = self.tvdb_episode['director']
        if directors is not None:
            output.write(directorheader)
            for director in directors.strip('|').split('|'):
                if director != '':
                    output.write(nameheader)
                    output.write(director)
                    output.write(namefooter)
            output.write(subfooter)

        writers = self.tvdb_episode['writer']
        if writers is not None:
            output.write(writerheader)
            for writer in writers.strip('|').split('|'):
                if writer != '':
                    output.write(nameheader)
                    output.write(writer)
                    output.write(namefooter)
            output.write(subfooter)

        actors = self.tvdb_show['_actors']
        if actors is not None:
            output.write(castheader)
            for actor in actors:
                if actor != '':
                    output.write(nameheader)
                    output.write(actor['name'])
                    output.write(namefooter)
            output.write(subfooter)
        
        output.write(footer)
        output.flush()

        xml = output.getvalue()
        output.close()
        return xml


    def _get_artwork(self):
        artwork = os.path.join(os.path.dirname(self.file), config.get('tagMP4', 'artwork_filename'))
        artwork_path = None

        for ext in ['.png', '.jpg', '.jpeg']:
            if os.path.exists(artwork + ext):
                print ' - Local artwork found'
                artwork_path = artwork + ext

        if artwork_path is None and self.itunes_season is not None:
            artwork100 = self.itunes_season.get_artwork()['100']
            artwork600 = artwork100.replace('100x100', '600x600')
            print ' - iTunes artwork found'
            artwork_path = urllib.urlretrieve(artwork600)[0]

        if artwork_path is None and self.tvdb_show is not None:
            banners = self.tvdb_show['_banners']['season']['season']
            banners = [banners[banner] for banner in banners if (banners[banner]['season'] == str(self.season_num) and banners[banner]['language'] == 'en')]
            banners = sorted(banners, key = self._sort_banners_by_rating, reverse = True)
            artwork_path = urllib.urlretrieve(banners[0]['_bannerpath'])[0]

        return artwork_path


    def _sort_banners_by_rating(self, k):
        if 'rating' in k:
            return float(k['rating'])
        else:
            return 0


    def get_airdate(self):
        return self.airdate


    def get_commands(self):
        commands = []

        for tag in self._get_metadata():
            if tag.values()[0] is not None:
                commands.append('--' + tag.keys()[0])
                commands.append(tag.values()[0])

        if config.get('tagMP4', 'add_people') == 'True' and self.tvdb_show is not None:
            commands.append('--rDNSatom')
            commands.append(self._gen_XML())
            commands.append('name=iTunMOVI')
            commands.append('domain=com.apple.iTunes')

        return commands



class MP4_Tagger:
    def __init__(self, file, tags):
        self.file = file
        self.tags = tags


    def write(self):
        print ' - Writing tags to file'

        environment = os.environ.copy()
        environment['PIC_OPTIONS'] = 'removeTempPix'

        command = [config.get('paths', 'atomicparsley'), self.file, '--overWrite', '--metaEnema', '--artwork', 'REMOVE_ALL']
        command.extend(self.tags.get_commands())

        if config.get('general', 'debug') == 'True':
            print command
        
        subprocess.check_output(command, env = environment)


    def update_times(self):
        print ' - Updating file creation and modification times'

        airdate = self.tags.get_airdate()
        
        if airdate is not None:
            airdate = dateutil.parser.parse(airdate)
            file_date = time.mktime(airdate.timetuple())
            os.utime(self.file, (file_date, file_date))



class Filename_Parser:
    def __init__(self, file):
        self.file = file
        self.compiled_regexs = []
        self._compile_regexs()


    def parse(self):
        """Runs path via configured regex, extracting data from groups.
        Returns an EpisodeInfo instance containing extracted data.
        """
        _, filename = os.path.split(self.file)

        for cmatcher in self.compiled_regexs:
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
        return seriesname.strip()


    def _compile_regexs(self):
        """Takes episode_patterns from config, compiles them all
        into self.compiled_regexs
        """
        for cpattern in patterns.filename_patterns:
            try:
                cregex = re.compile(cpattern, re.VERBOSE)
            except re.error, errormsg:
                warn("WARNING: Invalid episode_pattern (error: %s)\nPattern:\n%s" % (
                    errormsg, cpattern))
            else:
                self.compiled_regexs.append(cregex)



class TagMP4:
    def __init__(self, cfg, file, tvdb_id, season_num, episode_num):
        global config
        config = cfg
        self.file = file
        self.tvdb_id = tvdb_id
        self.season_num = season_num
        self.episode_num = episode_num


    def tag(self):
        print ''
        print 'Tagging MP4 - ' + self.file

        tags = Episode_Tags(self.tvdb_id, self.season_num, self.episode_num, self.file)
        tagger = MP4_Tagger(self.file, tags)

        tagger.write()
        tagger.update_times()

        print ' * Done tagging MP4'



if __name__ == '__main__':
    raise SystemExit('This file shouldn\'t be run directly')
