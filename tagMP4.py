#!/usr/local/bin/python

import os
import subprocess
import urllib
import StringIO
import re
import time
from pkg_resources import require

require('VideoConverter')
require('python-dateutil')

from converter import Converter
import dateutil.parser

from utils import (Metadata_Source, Filename_Parser)



class Episode_Tags:
    def __init__(self, tvdb_id, season_num, episode_num, file):
        self.file = file
        self.tvdb_id = tvdb_id
        self.season_num = season_num
        self.episode_num = episode_num


    def _get_metadata(self):
        source = Metadata_Source()
        tvdb_show, tvdb_episode = source.get_tvdb(self.tvdb_id, self.season_num, self.episode_num)
        itunes_season, itunes_episode = source.get_itunes(tvdb_show, tvdb_episode, self.season_num, self.episode_num, self.file)

        print ' - Getting metadata'

        tags = []

        tags.append({'TVSeasonNum': str(self.season_num)})
        tags.append({'TVEpisodeNum': str(self.episode_num)})
        tags.append({'disk': '1/1'})
        tags.append({'stik': 'TV Show'})
        tags.append({'artwork': self._get_artwork(tvdb_show, itunes_season)})

        # Options only TheTVDB has
        if tvdb_show is not None and tvdb_episode is not None:
            tags.append({'TVNetwork': tvdb_show['network']})
            tags.append({'TVEpisode': tvdb_episode['productioncode']})

        # Options only iTunes has
        if itunes_season is not None and itunes_episode is not None:
            tags.append({'copyright': itunes_season.get_copyright()})
            tags.append({'contentRating': itunes_episode.get_content_rating()})
        
        # Can be set from either iTunes or TheTVDB
        if itunes_season is not None and itunes_episode is not None:
            tags.append({'TVShowName': itunes_episode.get_artist().get_name()})
            tags.append({'artist': itunes_episode.get_artist().get_name()})
            tags.append({'title': itunes_episode.get_name()})
            tags.append({'album': itunes_season.get_name()})
            tags.append({'genre': itunes_episode.get_genre()})
            tags.append({'tracknum': str(self.episode_num) + '/' + str(itunes_season.get_track_count())})
            tags.append({'year': itunes_episode.get_release_date_raw()})
            tags.append({'cnID': str(itunes_episode.get_id())})
            tags.append({'description': itunes_episode.get_long_description()})
            tags.append({'longdesc': itunes_episode.get_long_description()})
            tags.append({'comment': 'Tagged with iTunes metadata'})
            self.airdate = itunes_episode.get_release_date_raw()
        elif tvdb_show is not None and tvdb_episode is not None:
            seriesname = re.sub("(.*?) \(\d\d\d\d\)", "\\1", tvdb_show['seriesname'])
            tags.append({'TVShowName': seriesname})
            tags.append({'artist': seriesname})
            tags.append({'title': tvdb_episode['episodename']})
            tags.append({'album': seriesname + ', Season ' + str(self.season_num)})
            tags.append({'genre': tvdb_show['genre'].strip('|').split('|')[0]})
            tags.append({'tracknum': str(self.episode_num) + '/' + str(len(tvdb_show[self.season_num]))})
            tags.append({'year': tvdb_episode['firstaired']})
            tags.append({'cnID': tvdb_episode['id']})
            tags.append({'description': tvdb_episode['overview']})
            tags.append({'longdesc': tvdb_episode['overview']})
            tags.append({'comment': 'Tagged with TheTVDB metadata'})
            self.airdate = tvdb_episode['firstaired']
        else:
            fp = Filename_Parser()
            seriesname = fp.parse(self.file)
            tags.append({'TVShowName': seriesname})
            tags.append({'artist': seriesname})
            tags.append({'title': os.path.splitext(os.path.split(self.file)[1])[0]})
            tags.append({'album': seriesname + ', Season ' + str(self.season_num)})
            tags.append({'tracknum': str(self.episode_num)})
            tags.append({'comment': 'No metadata found'})

        # Check file for HDness
        print ' - Scanning video to check HDness'

        c = Converter(config.get('paths', 'ffmpeg'), config.get('paths', 'ffprobe'))
        info = c.probe(self.file)
        tags.append({'hdvideo': '1' if (info.video.video_height >= 700 or info.video.video_width >= 1260) else '0'})

        xml = None
        if config.get('tagMP4', 'add_people') == 'True' and tvdb_show is not None:
            xml = self._gen_XML(tvdb_show, tvdb_episode)

        return tags, xml


    def _gen_XML(self, tvdb_show, tvdb_episode):
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
            for director in directors.strip('|').split('|'):
                if director != '':
                    output.write(nameheader)
                    output.write(director)
                    output.write(namefooter)
            output.write(subfooter)

        writers = tvdb_episode['writer']
        if writers is not None:
            output.write(writerheader)
            for writer in writers.strip('|').split('|'):
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


    def _get_artwork(self, tvdb_show, itunes_season):
        artwork = os.path.join(os.path.dirname(self.file), config.get('tagMP4', 'artwork_filename'))
        artwork_path = None

        for ext in ['.png', '.jpg', '.jpeg']:
            if os.path.exists(artwork + ext):
                print ' - Local artwork found'
                artwork_path = artwork + ext

        if artwork_path is None and itunes_season is not None:
            artwork100 = itunes_season.get_artwork()['100']
            artwork600 = artwork100.replace('100x100', '600x600')
            try:
                artwork_path = urllib.urlretrieve(artwork600)[0]
                print ' - iTunes artwork found'
            except IOError:
                print ' - Could not retrieve TheTVDB artwork'

        if artwork_path is None and tvdb_show is not None:
            banners = tvdb_show['_banners']['season']['season']
            banners = [banners[banner] for banner in banners if (banners[banner]['season'] == str(self.season_num) and banners[banner]['language'] == 'en')]
            banners = sorted(banners, key = self._sort_banners_by_rating, reverse = True)
            try:
                artwork_path = urllib.urlretrieve(banners[0]['_bannerpath'])[0]
                print ' - TheTVDB artwork found - won\'t be square'
            except IOError:
                print ' - Could not retrieve TheTVDB artwork'

        return artwork_path


    def _sort_banners_by_rating(self, k):
        if 'rating' in k:
            return float(k['rating'])
        else:
            return 0


    def get_airdate(self):
        if hasattr(self, 'airdate'):
            return self.airdate
        else:
            return None


    def get_commands(self):
        commands = []

        tags, xml = self._get_metadata()

        for tag in tags:
            if tag.values()[0] is not None:
                commands.append('--' + tag.keys()[0])
                commands.append(tag.values()[0])

        if xml is not None:
            commands.append('--rDNSatom')
            commands.append(xml)
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
        environment['PIC_OPTIONS'] = 'SquareUp:removeTempPix'

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
