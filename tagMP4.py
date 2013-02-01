#!/usr/local/bin/python

import os
import sys
import subprocess
import pipes
import urllib
import StringIO
import re
from pkg_resources import require

require('python-itunes')
require('VideoConverter')
require('tvdb_api')

import itunes
from converter import Converter
from tvdb_api import (Tvdb, tvdb_error)

import patterns



class Episode_Tags:
    def __init__(self, tvdb_id, season_num, episode_num, file):
        self.tags = []
        self.file = file

        print ' - Fetching information'

        tvdb_instance = Tvdb(cache=True, banners=True, actors=True)
        try:
            tvdb_show = tvdb_instance[tvdb_id]
            tvdb_episode = tvdb_show[season_num][episode_num]

            itunes_episodes = itunes.search_episode(tvdb_show['seriesname'] + ' ' + tvdb_episode['episodename'])
            if len(itunes_episodes) > 0:
                itunes_episode = itunes_episodes[0]
                itunes_season = itunes_episode.get_album()
                print ' - iTunes episode information found'
            else:
                itunes_episode = None
                itunes_season = itunes.search_season(tvdb_show['seriesname'] + ', Season ' + str(season_num))
                print ' - No iTunes episode information found'
                if len(itunes_season) == 0:
                    itunes_season = None
                    print ' - No iTunes season information found'
                else:
                    itunes_season = itunes_season[0]
                    print ' - iTunes season information found'
        except tvdb_error, errormsg:
            print ' @ Error: Could not fetch episode information - %s' % errormsg
            itunes_episode = None
            tvdb_show = None

        self.tags.append({'TVSeasonNum': str(season_num)})
        self.tags.append({'TVEpisodeNum': str(episode_num)})
        self.tags.append({'disk': '1/1'})
        self.tags.append({'stik': 'TV Show'})

        if itunes_episode is not None:
            self.tags.append({'TVShowName': itunes_episode.get_artist().get_name()})
            self.tags.append({'artist': itunes_episode.get_artist().get_name()})
            self.tags.append({'title': itunes_episode.get_name()})
            self.tags.append({'album': itunes_season.get_name()})
            self.tags.append({'genre': itunes_episode.get_genre()})
            self.tags.append({'tracknum': str(episode_num) + '/' + str(itunes_season.get_track_count())})
            self.tags.append({'year': itunes_episode.get_release_date_raw()})
            self.tags.append({'copyright': itunes_season.get_copyright()})
            self.tags.append({'advisory': ('clean' if itunes_episode.get_explicitness() == 'notExplicit' else 'explicit')})
            self.tags.append({'cnID': str(itunes_episode.get_id())})
            self.tags.append({'contentRating': itunes_episode.get_content_rating()})
            self.get_itunes_artwork(itunes_season)
            self.tags.append({'description': itunes_episode.get_long_description()[:252] + (itunes_episode.get_long_description()[252:] and '...')})
            self.tags.append({'longdesc': itunes_episode.get_long_description()})
        elif tvdb_show is not None:
            self.tags.append({'TVShowName': tvdb_show['seriesname']})
            self.tags.append({'artist': tvdb_show['seriesname']})
            self.tags.append({'title': tvdb_episode['episodename']})
            self.tags.append({'album': tvdb_show['seriesname'] + ', Season ' + str(season_num)})
            self.tags.append({'genre': tvdb_show['genre']})
            self.tags.append({'tracknum': str(episode_num) + '/' + str(len(tvdb_show[season_num]))})
            self.tags.append({'year': tvdb_episode['firstaired']})
            self.tags.append({'cnID': tvdb_episode['id']})
            if itunes_season is None:
                self.get_tvdb_artwork(tvdb_show, season_num)
            else:
                self.get_itunes_artwork(itunes_season)
            self.tags.append({'TVNetwork': tvdb_show['network']})
            self.tags.append({'TVEpisode': tvdb_episode['productioncode']})
            self.tags.append({'description': tvdb_episode['overview'][:252] + (tvdb_episode['overview'][252:] and '...')})
            self.tags.append({'longdesc': tvdb_episode['overview']})
        else:
            fp = Filename_Parser(file)
            seriesname = fp.parse()
            self.tags.append({'TVShowName': seriesname})
            self.tags.append({'artist': seriesname})
            self.tags.append({'title': os.path.splitext(os.path.split(file)[1])[0]})
            self.tags.append({'album': seriesname + ', Season ' + str(season_num)})
            self.tags.append({'tracknum': str(episode_num)})

        self.get_local_artwork()

        if config.get('tagMP4', 'add_people') == 'True' and tvdb_show is not None:
            print ' - Adding cast and crew information'
            self.xml = self.gen_XML(tvdb_show, tvdb_episode)


    def gen_XML(self, tvdb_show, tvdb_episode):
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

        directors = tvdb_episode['director']
        if directors is not None:
            output.write(directorheader)
            for director in directors.split('|'):
                if director != '':
                    output.write(nameheader)
                    output.write(director)
                    output.write(namefooter)
            output.write(subfooter)

        writers = tvdb_episode['writer']
        if writers is not None:
            output.write(writerheader)
            for writer in writers.split('|'):
                if writer != '':
                    output.write(nameheader)
                    output.write(writer)
                    output.write(namefooter)
            output.write(subfooter)

        actors = tvdb_show['_actors']
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


    def get_local_artwork(self):
        artwork = os.path.join(os.path.dirname(self.file), config.get('tagMP4', 'artwork_filename'))

        for ext in ['.png', '.jpg', '.jpeg']:
            if os.path.exists(artwork + ext):
                print ' - Local artwork found - ' + artwork + ext
                self.artwork_path = artwork + ext


    def get_itunes_artwork(self, itunes_season):
        artwork100 = itunes_season.get_artwork()['100']
        artwork600 = artwork100.replace('100x100', '600x600')
        self.retrieve_artwork(artwork600)


    def get_tvdb_artwork(self, tvdb_show, season_num):
        banners = tvdb_show['_banners']['season']['season']
        banners = [banners[banner] for banner in banners if (banners[banner]['season'] == str(season_num) and banners[banner]['language'] == 'en')]
        banners = sorted(banners, key = self.sort_banners_by_rating, reverse = True)
        self.retrieve_artwork(banners[0]['_bannerpath'])


    def retrieve_artwork(self, url):
        self.artwork_path = urllib.urlretrieve(url)[0]


    def sort_banners_by_rating(self, k):
        if 'rating' in k:
            return float(k['rating'])
        else:
            return 0


    def set_hd(self, hd):
        self.tags.append({'hdvideo': hd})


    def get_tags(self):
        command = []
        for tag in self.tags:
            if tag.values()[0] is not None:
                command.append('--' + tag.keys()[0])
                command.append(tag.values()[0])
        if hasattr(self, 'artwork_path'):
            command.append('--artwork')
            command.append(self.artwork_path)
        if config.get('tagMP4', 'add_people') == 'True' and hasattr(self, 'xml'):
            command.append('--rDNSatom')
            command.append(self.xml)
            command.append('name=iTunMOVI')
            command.append('domain=com.apple.iTunes')
        return command



class MP4_Tagger:
    def __init__(self, file, tags):
        self.file = file
        self.tags = tags

        print ' - Scanning video to check HDness'
        c = Converter(config.get('paths', 'ffmpeg'), config.get('paths', 'ffprobe'))
        info = c.probe(self.file)
        self.tags.set_hd('1' if (info.video.video_height >= 700 or info.video.video_width >= 1260) else '0')


    def write(self):
        print ' - Writing tags to file'
        environment = os.environ.copy()
        environment['PIC_OPTIONS'] = 'removeTempPix'
        command = [config.get('paths', 'atomicparsley'), self.file, '--overWrite', '--metaEnema', '--artwork', 'REMOVE_ALL']
        command.extend(self.tags.get_tags())
        if config.get('general', 'debug') == 'True':
            print command
        subprocess.check_output(command, env = environment)



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

        print ' * Done tagging MP4'



if __name__ == '__main__':
    raise SystemExit('This file shouldn\'t be run directly')
