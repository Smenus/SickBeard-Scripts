#!/usr/bin/env python

import os
import subprocess
import urllib
import StringIO
import time
#from pkg_resources import require

#require('python-dateutil')
#require('pymediainfo')

from pymediainfo import MediaInfo
import dateutil.parser

from utils import Metadata_Source


class Episode_Tags:
    def __init__(self, config, tvdb_id, filename):
        self.config = config
        self.filename = filename
        self.tvdb_id = tvdb_id

    def _get_metadata(self):
        source = Metadata_Source(self.config)
        metadata = source.get_metadata(self.tvdb_id, self.filename)

        print ' - Setting options'

        tags = dict()

        # Metadata that's always present
        tags['TVSeasonNum'] = metadata['seasonnumber']
        tags['TVEpisodeNum'] = metadata['episodenumber']
        tags['TVShowName'] = tags['artist'] = metadata['seriesname']
        tags['title'] = metadata['episodename']
        tags['album'] = metadata['seriesname'] + ', Season ' + metadata['seasonnumber']
        tags['disk'] = '1/1'
        tags['stik'] = 'TV Show'

        # Metadata that may not be present
        if 'poster' in metadata:
            tags['artwork'] = self._get_artwork(metadata['poster'])
        else:
            tags['artwork'] = self._get_artwork(None)
        if 'network' in metadata:
            tags['TVNetwork'] = metadata['network']
        if 'airdate' in metadata:
            tags['year'] = metadata['airdate']
            self.airdate = metadata['airdate']
        if 'certificate' in metadata:
            tags['contentRating'] = metadata['certificate']
        if 'genre' in metadata:
            tags['genre'] = metadata['genre']
        if 'episodecount' in metadata:
            tags['tracknum'] = metadata['episodenumber'] + '/' + metadata['episodecount']
        if 'id' in metadata:
            tags['cnID'] = metadata['id']
        if 'description' in metadata:
            tags['description'] = metadata['description']
        if 'description' in metadata:
            tags['longdesc'] = metadata['description']

        # Check file for HDness
        print ' - Scanning video to check HDness'

        mi = MediaInfo.parse(self.filename)
        video_hd = False
        for track in mi.tracks:
            if track.track_type == 'Video':
                video_hd = True if (track.height >= 700 or track.width >= 1260) else False
        tags['hdvideo'] = '1' if video_hd else '0'

        xml = None
        if self.config.get('tagMP4', 'add_people') == 'True' and 'actors' in metadata:
            xml = self._gen_XML(metadata['actors'])

        return tags, xml

    def _gen_XML(self, actors):
        header = '<?xml version="1.0" encoding="UTF-8"?>\n<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">\n<plist version="1.0">\n<dict>'
        castheader = '\n  <key>cast</key>\n  <array>'
        #directorheader = '\n  <key>directors</key>\n  <array>'
        #producerheader = '\n  <key>producers</key>\n  <array>'
        #writerheader = '\n  <key>screenwriters</key>\n  <array>'
        subfooter = '\n  </array>'
        nameheader = '\n    <dict>\n      <key>name</key>\n      <string>'
        namefooter = '</string>\n    </dict>'
        footer = '\n</dict>\n</plist>\n'

        output = StringIO.StringIO()
        output.write(header)

        #directors = tvdb_episode['director']
        #if directors is not None:
        #    output.write(directorheader)
        #    for director in directors.strip('|').split('|'):
        #        if director != '':
        #            output.write(nameheader)
        #            output.write(director)
        #            output.write(namefooter)
        #    output.write(subfooter)

        #writers = tvdb_episode['writer']
        #if writers is not None:
        #    output.write(writerheader)
        #    for writer in writers.strip('|').split('|'):
        #        if writer != '':
        #            output.write(nameheader)
        #            output.write(writer)
        #            output.write(namefooter)
        #    output.write(subfooter)

        if actors is not None:
            output.write(castheader)
            for actor in actors:
                if actor != '':
                    output.write(nameheader)
                    output.write(actor)
                    output.write(namefooter)
            output.write(subfooter)

        output.write(footer)
        output.flush()

        xml = output.getvalue()
        output.close()
        return xml

    def _get_artwork(self, poster):
        artwork = os.path.join(os.path.dirname(self.filename), self.config.get('tagMP4', 'artwork_filename'))

        for ext in ['.png', '.jpg', '.jpeg']:
            if os.path.exists(artwork + ext):
                print ' - Local artwork found'
                return artwork + ext

        if poster is not None:
            try:
                print ' - Poster artwork found - won\'t be square'
                return urllib.urlretrieve(poster)[0]
            except IOError:
                print ' - Could not retrieve poster artwork'

        return None

    def get_airdate(self):
        if hasattr(self, 'airdate'):
            return self.airdate
        else:
            return None

    def get_commands(self):
        commands = []

        tags, xml = self._get_metadata()

        for key, value in tags.items():
            commands.append('--' + key)
            commands.append(value)

        if xml is not None:
            commands.append('--rDNSatom')
            commands.append(xml)
            commands.append('name=iTunMOVI')
            commands.append('domain=com.apple.iTunes')

        return commands


class MP4_Tagger:
    def __init__(self, config, filename, tags):
        self.config = config
        self.filename = filename
        self.tags = tags

    def write_tags(self):
        environment = os.environ.copy()
        environment['PIC_OPTIONS'] = 'SquareUp:removeTempPix'

        command = [self.config.get('paths', 'atomicparsley'), self.filename, '--overWrite', '--metaEnema', '--artwork', 'REMOVE_ALL']
        command.extend(self.tags.get_commands())

        print ' - Writing tags to file'

        if self.config.get('general', 'debug') == 'True':
            print command

        subprocess.check_output(command, env=environment)

    def update_times(self):
        print ' - Updating file creation and modification times'

        airdate = self.tags.get_airdate()

        if airdate is not None:
            airdate = dateutil.parser.parse(airdate)
            file_date = time.mktime(airdate.timetuple())
            os.utime(self.filename, (file_date, file_date))


class TagMP4:
    def __init__(self, config, filename, tvdb_id):
        self.config = config
        self.filename = filename
        self.tvdb_id = tvdb_id

    def tag(self):
        print ''
        print 'Tagging MP4 - ' + self.filename

        tags = Episode_Tags(self.config, self.tvdb_id, self.filename)
        tagger = MP4_Tagger(self.config, self.filename, tags)

        tagger.write_tags()
        tagger.update_times()

        print ' * Done tagging MP4'


if __name__ == '__main__':
    raise SystemExit('This file shouldn\'t be run directly')
