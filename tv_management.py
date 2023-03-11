"""
=========================================================================================================================
Module: config.py
Description: This module provides functions for interacting with the TV show media.
Author: Steve Wilde
Email: wildfotoz@gmail.com
Date: 2023-03-07
Version: 1.0.0
Status: RC1
=========================================================================================================================
"""

# Standard library imports
import os
import datetime
import pandas as pd
# from videoprops import get_video_properties #pip install -U get-video-properties
# from moviepy.editor import VideoFileClip
import re
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
import requests
import re
from pymediainfo import MediaInfo
from datetime import timedelta 
from datetime import datetime 
from termcolor import colored       # Needed so the color of the text in the consol can have different colors.

#Third-pary imports
import config
import database         as db

#Populate parameters
params, db_conn = config.get_shared_parameters()
                    # if files.endswith(('.mkv', '.mp4', '.avi')):
                    # unformatted_episodes = len([f for f in files if not re.match(r"^"+media_folder+"+\s\d+x\d{2}\.(mkv|mp4|avi)$", f) and f != 'tvshow.nfo'])

                    # for f in files:
                    #     if not re.match(r"^"+media_folder+"+\s\d+x\d{2}\.(mkv|mp4|avi)$", f):# and f != 'tvshow.nfo':
                    #         print(f)
                    #total_episodes += total_episodes
                    #total_episodes += len([f for f in files if f.endswith('.mkv') or f.endswith('.mp4') or f.endswith('.avi')]) #+ unformatted_episodes#  + unformatted_episodes


def inventory_directories(root_folders):
    directory = []
    sub_folders = []
    additional_sub_folders = {}

    for root_folder in root_folders:
        for subdir, dirs, files in os.walk(root_folder):
            drive_letter, path = os.path.splitdrive(subdir)
            if len(subdir.split('\\')) > 5:
                parent_folder = subdir.split('\\')[2]
                tvshow = subdir.split('\\')[3]
                combination_key = (root_folder, parent_folder, tvshow)
                if combination_key in additional_sub_folders:
                    additional_sub_folders[combination_key] += 1
                else:
                    additional_sub_folders[combination_key] = 1

                for i, sf in enumerate(sub_folders):
                    if sf['RootFolder'] == root_folder and sf['ParentFolder'] == parent_folder and sf['TVShow'] == tvshow:
                        sub_folders[i]['AdditionalSubFolders'] = additional_sub_folders[combination_key]
                        break
                else:
                    sub_folders.append({
                        'DriveLetter': drive_letter,
                        'RootFolder': root_folder,
                        'ParentFolder': parent_folder,
                        'TVShow': tvshow,
                        'KeyFolder': subdir,
                        'AdditionalSubFolders': additional_sub_folders[combination_key]
                    })
            if len(subdir.split('\\')) == 4 and "TV Shows" in subdir:
                parent_folder = subdir.split('\\')[2]
                tvshow = subdir.split('\\')[3]
                if tvshow.lower() == 'specials':
                    continue
                tvshow_nfo = 1 if 'tvshow.nfo' in files else 0
                max_season = max([int(re.findall(r"\d+", x)[0]) for x in dirs if 'season' in x.lower()] or [0])
                specials = 1 if 'Specials' in dirs else 0
                other_folders = 1 if any([True for x in dirs if x.lower() not in ['specials'] and not x.lower().startswith('season')]) else 0

                directory.append({
                    'DriveLetter': drive_letter,
                    'RootFolder': root_folder,
                    'ParentFolder': parent_folder,
                    'TVShow': tvshow,
                    'KeyFolder': subdir,
                    'NFOFile': tvshow_nfo,
                    'MaxSeason': max_season,
                    'Specials': specials,
                    'OtherFolders': other_folders,
                })
    directory_df = pd.DataFrame(directory)
    sub_folders_df = pd.DataFrame(sub_folders)
    if len(sub_folders_df) > 0:
        dirInfo = pd.merge(directory_df, sub_folders_df, on=['DriveLetter', 'RootFolder', 'ParentFolder', 'TVShow', 'KeyFolder'], how='left')
    else:
        dirInfo = directory_df

    return dirInfo

def parse_nfo(root_folders):
    Show = []

    for root_folder in root_folders:
        for subdir, dirs, files in os.walk(root_folder):
            drive_letter, path = os.path.splitdrive(subdir)
            if len(subdir.split('\\')) == 4 and os.path.isfile(subdir+'\\tvshow.nfo'):
                parent_folder = subdir.split('\\')[2]
                tvshow = subdir.split('\\')[3]
                try:
                    #print(subdir)
                    tree = ET.parse(subdir+'\\tvshow.nfo')

                    tvdb_id = (tree.find('id').text.replace('\n', '') if (tree.find('id').text is not None and '\n' in tree.find('id').text) else tree.find('id').text)
                    plot = (tree.find('plot').text.replace('\n', '') if (tree.find('plot').text is not None and '\n' in tree.find('plot').text) else tree.find('plot').text)
                    imdbid = (tree.find('imdbid').text.replace('\n', '') if (tree.find('imdbid').text is not None and '\n' in tree.find('imdbid').text) else tree.find('imdbid').text)
                    year = (tree.find('year').text.replace('\n', '') if (tree.find('year').text is not None and '\n' in tree.find('year').text) else tree.find('year').text)
                    premiered = (tree.find('premiered').text.replace('\n', '') if (tree.find('premiered').text is not None and '\n' in tree.find('premiered').text) else tree.find('premiered').text)
                    studio = (tree.find('studio').text.replace('\n', '') if (tree.find('studio').text is not None and '\n' in tree.find('studio').text) else tree.find('studio').text)
                    mpaa = (tree.find('mpaa').text.replace('\n', '') if (tree.find('mpaa').text is not None and '\n' in tree.find('mpaa').text) else tree.find('mpaa').text)
                    status = (tree.find('status').text.replace('\n', '') if (tree.find('status').text is not None and '\n' in tree.find('status').text) else tree.find('status').text)

                    genre = []
                    root = tree.getroot()
                    for child in root:
                        if child.tag == 'genre':
                            genre.append(child.text)

                    url = []
                    episodeguide = tree.find('episodeguide')
                    for sub in episodeguide:
                        if sub.tag == 'url':
                            url.append(sub.text)

                    thetvdbURL = url[0]
                    genreList = ','.join(map(str, genre))
                except:
                    print('parse_nfo error: ',subdir)
                    tvdb_id = ""
                    plot = ""
                    imdbid = ""
                    year = ""
                    premiered = ""
                    studio = ""
                    thetvdbURL = ""
                    genreList = ""
                    mpaa = ""
                    status = ""
                Show.append({
                    'DriveLetter'  : drive_letter,
                    'RootFolder'   : root_folder,
                    'ParentFolder' : parent_folder,
                    'TVShow'       : tvshow,
                    'KeyFolder'    : subdir,
                    'TVDBID'       : tvdb_id,
                    'plot'         : plot,
                    'IMDBID'       : imdbid,
                    'StartingYear' : year,
                    'Premiered'    : premiered,
                    'Studio'       : studio,
                    'EpisodeGuide' : thetvdbURL,
                    'Genre'        : genreList,
                    'MPAA'         : mpaa,
                    'ShowStatus'   : status

                })

    return pd.DataFrame(Show)

def get_media_details(root_folders, extensions, include_cols=None):
    all_tracks = []
    bit_rate_issues = []
    df_episodes = db.sql_to_df(db_conn,"SELECT CompleteName, FileLastModificationDateLocal FROM Fact.Episodes WHERE FileLastModificationDateLocal IS NOT NULL")
    print(df_episodes)
    for root_folder in root_folders:
        print('Processing: ',colored(root_folder,'blue'))
        for subdir, dirs, files in os.walk(root_folder):
            drive_letter, path = os.path.splitdrive(subdir)
            print(subdir)
            for file in files:
                _, extension = os.path.splitext(file)
                if extension in extensions and "TV Shows" in subdir:
                    check_file_name = os.path.join(subdir, file)
                    check_date_modified = pd.Timestamp(os.path.getmtime(check_file_name), unit='s')
                    process_file = ((df_episodes['CompleteName'] == check_file_name) & (df_episodes['FileLastModificationDateLocal'] < check_date_modified)).any()
                    if process_file:
                        print('Skipped Processing: ', check_file_name)
                    if not process_file:
                        parent_folder = subdir.split('\\')[2]
                        tvshow = subdir.split('\\')[3]
                        media_info = MediaInfo.parse(os.path.join(subdir, file))
                        episode_number = None #Episodes that are not in the 1x01 format, will have a null value which can be reported on as an invalid file format.
                        match = re.search(r'\d+x(\d+)', file)
                        if match:
                            episode_number = match.group(1)
                        # Define columns for the dataframe based on track type
                        columns = set()
                        for track in media_info.tracks:
                            columns.update(track.__dict__.keys())
                        columns = list(columns)

                        # Use include_cols if provided, otherwise use all columns
                        if include_cols:
                            columns = include_cols

                        # Create a master dictionary with all possible keys for all tracks
                        master_dict = {col: [] for col in columns}

                        # Append each track's data as a separate row
                        for track in media_info.tracks:
                            # Create a dictionary for the current track
                            row_data = {col: getattr(track, col) for col in columns if hasattr(track, col)}
                            # Fill in missing keys with None
                            for col in columns:
                                if col not in row_data:
                                    row_data[col] = None
                            # Apply selective formatting to specific columns based on include_cols
                            # matching_rows = df_episodes[df_episodes['CompleteName'] == track.complete_name]
                            if track.encoded_date:
                                date_format = "UTC %Y-%m-%d %H:%M:%S"
                                try:
                                    date_obj = datetime.strptime(track.encoded_date, date_format)
                                except:
                                    print(colored(subdir, "yellow"), "track.encoded_date: ", track.encoded_date)
                                row_data['encoded_date'] = date_obj
                            if subdir[-2:].strip(' ').isdigit():
                                row_data['season_number'] = int(subdir[-2:].strip(' '))
                            else:
                                row_data['season_number'] = int(0)
                            row_data['episode_number'] = episode_number
                            row_data['drive_letter'] = drive_letter
                            row_data['root_folder'] = root_folder
                            row_data['parent_folder'] = parent_folder
                            row_data['tvshow'] = tvshow
                            if track.track_type == 'General':
                                file = track.file_name
                                extension = track.file_extension
                                complete_name = track.complete_name

                            row_data['complete_name'] = complete_name
                            row_data['file_name'] = file #Add to all rows
                            row_data['file_extension'] = extension #Add to all rows
                            if 'duration' in columns and track.track_type == 'General':
                                try:
                                    milliseconds = track.duration if track.duration is not None else 0
                                    delta = timedelta(milliseconds=milliseconds)
                                    duration = (datetime.min + delta).time().strftime('%H:%M:%S')
                                    row_data['duration'] = duration
                                    row_data['duration_minutes'] = track.duration / 60000
                                except:
                                    print('Duration Issue: ', check_file_name, ' : ', track.duration)
                            else:
                                row_data['duration'] = None

                            if 'bit_rate' in columns and track.track_type == 'Video':
                                try:
                                    row_data['bit_rate'] = row_data['bit_rate'] / 1000
                                except:
                                    full_filename = file+'.'+extension #there's probably a better way to do this
                                    bit_rate_issues.append(os.path.join(subdir, full_filename))
                                    #Add the file to the issues database table - re-encoding in MKVToolNix GUI fixes the issue.
                            else:
                                row_data['bit_rate'] = track.bit_rate

                            if track.track_type == 'General':
                                row_data['file_size_converted'] = (f"{track.file_size} bytes" if track.file_size < 1024 else
                                                                f"{track.file_size / 1024:.2f} KB" if track.file_size < (1024 ** 2) else
                                                                f"{track.file_size / (1024 ** 2):.2f} MB" if track.file_size < (1024 ** 3) else
                                                                f"{track.file_size / (1024 ** 3):.2f} GB")
                            if track.track_type == 'Text' and track.language not in('en','und'):
                                row_data['language'] = 'fn'
                                row_data['title'] = 'foreign'
                                row_data['track_id'] = 99
                            if track.track_type == 'Video':
                                row_data['other_display_aspect_ratio'] = str(track.other_display_aspect_ratio).replace('[','').replace(']','').replace('\'','')
                            for col in columns:
                                master_dict[col].append(row_data[col])
                            all_tracks.append(row_data)
                    # print(all_tracks)
    media_df = pd.DataFrame(all_tracks).drop_duplicates()
    #media_df = pd.DataFrame(master_dict).applymap(lambda x: tuple(x) if isinstance(x, list) else x).drop_duplicates() #This code will convert any lists in the DataFrame to tuples before calling drop_duplicates()
    issues_df = pd.DataFrame({'FileName': bit_rate_issues})
    if not issues_df.empty:
        sql_results = db.df_to_sql(db_conn,issues_df,'Stage','BitRateIssues')
        print(sql_results[0])

    return media_df

def get_imdb(imdb_id,max_seasons):
    stats = list()
    for sn in range(1,max_seasons):
        # Request from the server the content of the web page by using get(), and store the server’s response in the variable response
        response = requests.get('https://www.imdb.com/title/' + imdb_id + '/episodes?season=' + str(sn))

        # Parse the content of the request with BeautifulSoup
        page_html = BeautifulSoup(response.text, 'html.parser')

        # Select all the episode containers from the season's page
        episode_containers = page_html.find_all('div', class_ = 'info')

        # For each episode in each season
        for episodes in episode_containers:
                # Get the info of each episode on the page
                season = sn
                episode_number = episodes.meta['content']
                title = episodes.a['title']
                airdate = pd.to_datetime(episodes.find('div', class_='airdate').text.strip())
                rating = episodes.find('span', class_='ipl-rating-star__rating').text
                total_votes = format_ratings(episodes.find('span', class_='ipl-rating-star__total-votes').text)
                desc = episodes.find('div', class_='item_description').text.strip()
                # Compiling the episode info
                episode_data = [season, title, episode_number, airdate, rating, total_votes, desc]

                # Append the episode info to the complete dataset
                stats.append(episode_data)

    # url = 'https://www.imdb.com/title/'+imdb_id+'/episodes?season='+str(season)
    # response = requests.get(url)
    # html_soup = BeautifulSoup(response.text, 'html.parser')
    # episode_containers = html_soup.find_all('div', class_='info')
    # for x in episode_containers:
    #     print(x.sourceline)
    #     title = episode_containers[0].a['title']
    #     episodeNumber = episode_containers[0].meta['content']
    #     airdate = pd.to_datetime(episode_containers[0].find('div', class_='airdate').text.strip())
    #     episodeDescription = episode_containers[0].find('div', class_='item_description').text.strip()
    #     totalVotes = episode_containers[0].find('span', class_='ipl-rating-star__total-votes').text
    #     try:
    #             rating = episode_containers[0].find('div', class_='ipl-rating-star__rating').text
    #     except:
    #             try:
    #                     rating = episode_containers[0].find('span', class_='ipl-rating-star__rating').text
    #             except:
    #                     rating = ''
    #     stats.append((season,title,episode_number,airdate,rating,desc,total_votes))
    episodeStats = pd.DataFrame(stats, columns=['Season','EpisodeTitle','EpisodeNumber','EpisodeAirDate','EpisodeRating','EpisodeDescription','EpisodeTotalVotes'])
    return episodeStats

def format_ratings(votes):
    for r in ((',',''), ('(',''),(')','')):
        votes = votes.replace(*r)

    return votes
