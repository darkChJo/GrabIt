import praw
from handlers.ImgurDownloader import saveImage
import  resources.handlers.common
from resources.handlers.imgur import Imgur
from resources.handlers.common import Common
from handlers.dbHandler import createTable, dbWrite
from save import Save
import requests
import re
import sys
import os
import time
import urllib.request,json
from creds import *
import argparse
import youtube_dl
import json

class color:
   RED = '\033[91m'
   BOLD = '\033[1m'
   END = '\033[0m'

with open('./resources/config.json') as f:
        config = json.load(f)

def grabber(subR, base_dir, posts, sort):
    if 'u/' in subR or '/u/' in subR:
        if '/u/' in subR: subR = subR[3:]
        elif 'u/'in subR: subR = subR[2:]
        if sort == 'hot': submissions = reddit.redditor(subR).submissions.hot(limit = int(posts))
        elif sort == 'new': submissions = reddit.redditor(subR).submissions.new(limit = int(posts))
        elif sort =='top': submissions = reddit.redditor(subR).submissions.top(limit = int(posts))
    else:
        if sort == 'hot': submissions = reddit.subreddit(subR).hot(limit = int(posts))
        elif sort == 'new': submissions = reddit.subreddit(subR).new(limit = int(posts))
        elif sort == 'top': submissions = reddit.subreddit(subR).top(limit = int(posts))

    for submission in submissions:
        title = submission.title
        link = submission.url
        if(dbWrite(submission.permalink, title, submission.created, submission.author, link) and not(submission.author in config["blacklist"])):
        #if(1):
            print_title = title.encode('utf-8')[:25] if len(title) > 25 else title.encode('utf-8')
            print('{}Post:{} {}... {}From:{} {} {}By:{} {}'.format(color.BOLD, color.END, print_title, color.BOLD, color.END, str(subR), color.BOLD, color.END, str(submission.author)))
            title = formatName(title)
            
            # Selftext post
            if submission.is_self:
                with open(os.path.join(save.get_dir(str(submission.author), str(submission.subreddit)), title + '.txt'), 'a+') as f:
                    f.write(str(submission.selftext.encode('utf-8')))

            # Link to a jpg, png, gifv, gif, jpeg
            elif any(ext in link for ext in ['.jpg', '.png', '.gif', 'gifv', 'jpeg']) or 'i.reddituploads.com' in link:
                Common(link, title, save.get_dir(str(submission.author), str(submission.subreddit)))

            # Imgur
            elif 'imgur.com/' in link:
                 Imgur(link, title, save.get_dir(str(submission.author), str(submission.subreddit)))

            # Giphy
            elif 'giphy.com/gifs' in link:
                link = 'https://media.giphy.com/media/' + link.split('-', 2)[-1] + '/giphy.gif'
                saveImage(link, title, '.gif', save.get_dir(str(submission.author), str(submission.subreddit)))

            # Flickr
            elif 'flickr.com/' in link:
                print("No Flickr support")
                with open(os.path.join(base_dir, 'error.txt'), 'a+') as logFile:
                        logFile.write('Needs support: ' + link + '\n')

            # Reddit submission
            elif 'reddit.com/r/' in link:
                with open(os.path.join(base_dir, 'error.txt'), 'a+') as logFile:
                    logFile.write('Link to reddit' + link + ' by ' + str(submission.author) + ' \n')
                    logFile.close()
            
            # All others are caught by youtube-dl, if still no match it's written to the log file
            else:
                folder = save.get_dir(str(submission.author), str(submission.subreddit))
                ydl_opts = {
                    'format': 'best',
                    'outtmpl': os.path.join(folder, '%(title)s-%(id)s.%(ext)s'),
                    'quiet': 'quiet'
                }
                try:
                    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
                        ydl.download([link])
                except youtube_dl.utils.DownloadError:
                    with open(os.path.join(base_dir, 'error.txt'), 'a+') as logFile:
                        logFile.write('No matches: ' + link + '\n')

'''
Removes special characters and shortens long
filenames
'''
def formatName(title):
    title = re.sub('[?/|\\\:<>*"]', '', title)
    if len(title) > 211: title = title[:210]
    return title

def main(subR, posts, base_dir, sort):
    with open('./resources/config.json') as f:
        config = json.load(f)
    print(color.BOLD, "****", subR, "****", color.END)
    grabber(subR, base_dir, posts, sort)

if __name__ == '__main__':
    '''
    Parser input
    '''
    parser = argparse.ArgumentParser(description = "Downloads images, GIFS and text from YouTube")
    parser.add_argument("Subreddit", help = "Enter a subreddit to backup or text file")
    parser.add_argument("-w", "--wait", help = "Change wait time between subreddits in seconds")
    parser.add_argument("-p", "--posts", help = "Number of posts to grab on each cycle")
    parser.add_argument("-o", "--output", help = "Set base directory to start download")
    parser.add_argument("--by_author", help = "Sort downloads by author, default by subreddit", action = "store_true")
    parser.add_argument("--sort", help = "Sort submissions by 'hot', 'new' or 'top'")
    parser.add_argument("--blacklist", help = "Avoid downloading a user, without /u/")

    args = parser.parse_args()

    subR = None
    filepath = None
    verb = False
    
    # Subreddit
    if '.txt' in args.Subreddit: filepath = args.Subreddit
    else: subR = args.Subreddit

    # wait
    if args.wait:
        try:
            wait = int(args.wait)
        except ValueError:
            print("Please enter an integer in seconds to wait")
            sys.exit()
    else:
        wait = 600

    # posts
    if args.posts:
        try:
            posts = int(args.posts)
        except ValueError:
            print("Please enter an integer for the number of posts")
            sys.exit()
    else:
        posts = 50
    
    # output
    if args.output:
        base_dir = os.path.abspath(args.output)
        if not os.path.exists(base_dir): os.makedirs(base_dir)
    else:
        base_dir = os.getcwd()

    # sort
    sort = 'hot'
    if args.sort and (args.sort.lower() == 'hot' or args.sort.lower() == 'new' or args.sort.lower() == 'top'):
        sort = args.sort
    elif args.sort:
        print("Please enter hot, new or top for sort")
        sys.exit()
    
    # blacklist
    if args.blacklist:
        config["blacklist"].append(args.blacklist)
        with open('./resources/config.json', 'w') as f:
            json.dump(config, f)

    # by_author
    save = Save(base_dir, args.by_author)
    # print(save.get_dir('author', 'sub'))
    # sys.exit()
    createTable()

    '''
    Initialise Reddit
    '''
    reddit = praw.Reddit(client_id = Re_client_id,
                        client_secret= Re_client_secret,
                        user_agent= Re_user_agent)

    '''
    Feed subreddits to main
    '''
    while(True):
        if filepath is not None:
            with open(filepath) as f:
                line = f.readline()
                while line:
                    subR = "{}".format(line.strip())
                    main(subR, posts, base_dir, sort)
                    line = f.readline()
        else:
            main(subR, posts, base_dir, sort)
        print(color.BOLD, "Waiting", wait, "seconds.", color.END)
        time.sleep(wait)
