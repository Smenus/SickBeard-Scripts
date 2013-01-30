#!/usr/local/bin/python

import os
import sys
import subprocess
import pipes
import urllib
import StringIO
import itunes
import converter
import tvdb_api



class Episode_Tags:
    def __init__(self, tvdb_id, season_num, episode_num):
        self.tags = []

        tvdb_instance = tvdb_api.Tvdb(cache=True, banners=True, actors=True)
        tvdb_show = tvdb_instance[tvdb_id]
        tvdb_episode = tvdb_show[season_num][episode_num]

        itunes_episodes = itunes.search_episode(tvdb_show['seriesname'] + ' ' + tvdb_episode['episodename'])
        if len(itunes_episodes) > 0:
            itunes_episode = itunes_episodes[0]
            itunes_season = itunes_episode.get_album()
        else:
            itunes_episode = None

        self.tags.append({'TVSeasonNum': str(season_num)})
        self.tags.append({'TVEpisodeNum': str(episode_num)})
        self.tags.append({'disk': '1/1'})
        self.tags.append({'TVNetwork': tvdb_show['network']})
        self.tags.append({'TVEpisode': tvdb_episode['productioncode']})
        self.tags.append({'stik': 'TV Show'})
        self.tags.append({'artwork': 'REMOVE_ALL'})

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
            self.tags.append({'description': itunes_episode.get_short_description()})
            self.tags.append({'longdesc': itunes_episode.get_long_description()})
        else:
            self.tags.append({'TVShowName': tvdb_show['seriesname']})
            self.tags.append({'artist': tvdb_show['seriesname']})
            self.tags.append({'title': tvdb_episode['episodename']})
            self.tags.append({'album': tvdb_show['seriesname'] + ', Season ' + str(season_num)})
            self.tags.append({'genre': tvdb_show['genre']})
            self.tags.append({'tracknum': str(episode_num) + '/' + len(tvdb_show[season_num])})
            self.tags.append({'year': tvdb_episode['firstaired']})
            self.tags.append({'cnID': tvdb_episode['id']})
            self.get_tvdb_artwork(tvdb_show, season_num)
            self.tags.append({'description': tvdb_episode['overview'][:252] + (data[252:] and '...')})
            self.tags.append({'longdesc': tvdb_episode['overview']})

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


    def sort_banners_by_rating(k):
        if 'rating' in k:
            return float(k['rating'])
        else:
            return 0


    def set_hd(self, hd):
        self.tags.append({'hdvideo': hd})


    def set_artwork(self, artwork_path):
        self.artwork_path = artwork_path


    def get_tags(self):
        line = []
        for tag in self.tags:
            if tag.values()[0] is not None:
                line.append('--' + tag.keys()[0])
                line.append(tag.values()[0])
        line.append('--artwork')
        line.append(self.artwork_path)
        line.append('--rDNSatom')
        line.append(self.xml)
        line.append('name=iTunMOVI')
        line.append('domain=com.apple.iTunes')
        return line



class MP4_Tagger:
    def __init__(self, file, tags):
        self.file = file
        self.tags = tags

        c = converter.Converter('/usr/local/bin/ffmpeg', '/usr/local/bin/ffprobe')
        video = c.probe(file).video
        self.tags.set_hd('1' if (video.video_height >= 700 or video.video_width >= 1260) else '0')
        path = os.path.dirname(file)
        if os.path.exists(path + os.sep + 'artwork.png'):
            self.tags.set_artwork(path + os.sep + 'artwork.png')
        elif os.path.exists(path + os.sep + 'artwork.jpg'):
            self.tags.set_artwork(path + os.sep + 'artwork.jpg')
        elif os.path.exists(path + os.sep + 'artwork.jpeg'):
            self.tags.set_artwork(path + os.sep + 'artwork.jpeg')


    def write(self):
        environment = os.environ.copy()
        environment['PIC_OPTIONS'] = 'removeTempPix'
        command = ['/usr/local/bin/AtomicParsley', self.file, '--overWrite']
        command.extend(self.tags.get_tags())
        subprocess.call(command, env = environment)



def main():
    if len(sys.argv) != 7:
        print 'Not enough arguments, this script should be called by Sick Beard'
        sys.exit(1)

    path = os.path.splitext(sys.argv[1])[0] + '.m4v'
    tvdb_id = int(sys.argv[3])
    season_num = int(sys.argv[4])
    episode_num = int(sys.argv[5])

    if not os.path.exists(path):
        print 'Path doesn\'t exist'
        sys.exit(1)

    c = converter.Converter('/usr/local/bin/ffmpeg', '/usr/local/bin/ffprobe')
    file = c.probe(path)

    if file.format.format.find('mp4') == -1:
        print 'File isn\'t MP4 compatible, we can\'t tag it!'
        sys.exit(1)

    tags = Episode_Tags(tvdb_id, season_num, episode_num)
    tagger = MP4_Tagger(path, tags)

    tagger.write()



if __name__ == '__main__':
    main()
