#!/usr/bin/python3
# TODO 
# Add compatibility with new schmeckle notation:
# "SHM XX.XX"

from logging import lastResort
import privateinfo
import praw
import json
from collections import namedtuple
import pdb
import re
import time
import os
import urllib3
import sys
import datetime
import rate_updater

if len(sys.argv) > 1:
	argv = ""
	for arg in sys.argv:
		argv += arg + ' '
	#print(argv)
	if re.search("(?i) --help", argv):
		print ("\nUSAGE: python3 schmeckmichbot.py [-c] [-s] [-ls] [-i N] [-k] [-r/subreddit] [-x r/sub1 [[r/sub2] [r/subX...]]\n")
		print ("Options:\n      -c   scrape Comments\n      -s   scrape Submissions\n     -ls   Log Subreddits\n  -r/sub   specifies subreddit for scraping\n    -i N   override exchange rate refresh Interval in seconds (default is 3600)\n      -k   sKip existing posts\n-x r/sub   specifies subreddits to eXclude\n")
		exit()


#reddit = praw.reddit(client_id, client_secret, user_agent, username, password)
reddit = praw.Reddit(client_id=privateinfo.Client_id, client_secret=privateinfo.Client_secret, user_agent=privateinfo.User_agent, username=privateinfo.Username, password=privateinfo.Password)

if not os.path.isfile("posts_replied_to.txt"):
	posts_replied_to = []
else:
	with open("posts_replied_to.txt", "r") as f:
		posts_replied_to = f.read()
		posts_replied_to = posts_replied_to.split("\n")
		posts_replied_to = list(filter(None, posts_replied_to))

cache = ""
# rate_EUR = rate_EUR = rate_GPB = rate_CAD = rate_CNY= rate_SHMACK = 1.0

def getRates ():
    os.system('python3 rate_updater.py &')
    print("Checking currency exchange rates...\n")
    rate_data=None
    with open(rate_updater.datafile) as f:
        rate_data = f.read()
    global rates
    rates = json.loads(rate_data, object_hook=lambda d: namedtuple('Rates', d.keys())(*d.values()))
    global lastRateRefreshTime
    lastRateRefreshTime = rate_updater.getTimestamp(rate_data) # keep time of last refresh in a buffer, to keep rates up to date
    print("Done.\n")
    global rate_EUR
    rate_EUR = float(rates.rates.EUR)
    global rate_GBP 
    rate_GBP = float(rates.rates.GBP)
    global rate_CAD
    rate_CAD = float(rates.rates.CAD)
    global rate_RUB
    rate_RUB = float(rates.rates.RUB)
    global rate_CNY
    rate_CNY = float(rates.rates.CNY)
    global rate_SHMACK
    rate_SHMACK = (1 / 101)

def reply_to_stream (subreddit, scrape_submissions=False, log_subs=False, Skip_existing=False, exclude=""):

	replies_sent = 0
	global cache
	global refresh_interval
	global lastRateRefreshTime
	try:

		if scrape_submissions == True: # opted to reply to submissions, not comments

			#raise
			for submission in reddit.subreddit(subreddit).stream.submissions(skip_existing=Skip_existing):
				amounts_seen = ""
				if str(submission.subreddit) not in exclude: # subreddit not on exclude list
					if time.time() - lastRateRefreshTime > refresh_interval:
						print('this dood is refreshing already!!')
						getRates()
					replySent = False
					print("\n")
					try:
						author = submission.author
						time_created = submission.created
						
						print("in r/%s" % submission.subreddit)
						print("by u/%-22s on %s" % (author.name, datetime.datetime.fromtimestamp(time_created)))
						print('"%s"' % submission.title)
						has_selftext = True
						print("submission selftext:\n%s" % submission.selftext)
						if submission.selftext == "[deleted]":
							has_selftext = False

					except AttributeError:
						print("AttributeError")
						has_selftext = False
					
					if has_selftext:
						if submission.id not in posts_replied_to and not re.search("(?i)SchmeckMichBot", author.name):
							Match_title = re.findall(r"(?i)([0-9,]*\.?[0-9]+)\s*([kmbt]|hundred|thousand|(m|b|tr)illion)? +(sc?hm[ae](ck|ch|c|k))((le|el)?)", submission.title)
							Match_selftext = re.findall("pattern", "none") # by default
							bad_numbers = re.search("[0-9]{60}[0-9]*", submission.selftext)
							if not bad_numbers: # do not let processor do useless work
								Match_selftext = re.findall(r"(?i)([0-9,]*\.?[0-9]+)\s*([kmbt]|hundred|thousand|(m|b|tr)illion)? +(sc?hm[ae](ck|ch|c|k))((le|el)?)", submission.selftext)
							Match_all = Match_title + Match_selftext
							
							if (Match_title or Match_selftext) and submission.id not in cache:
								reply_contents=''
								for amount in Match_all:
									remark = ""
									amount_no_commas = amount[0].replace(',', '')
									
									if amount[6] == '': # if amount given is in shmacks and not schmeckles
										amount_PFE = float(amount_no_commas) * 101
										base_unit = "shmacks"
									else:
										amount_PFE = float(amount_no_commas)
										base_unit = "schmeckles"

									# applying multipliers
									if re.search("(?i)hundred", amount[1]):
										multiplier = 100
									elif re.search("(?i)k|thousand", amount[1]):
										multiplier = 1000
									elif re.search("(?i)m|million", amount[1]):
										multiplier = 1000000
									elif re.search("(?i)b|billion", amount[1]):
										multiplier = 1000000000
									elif re.search("(?i)t|trillion", amount[1]):
										multiplier = 1000000000000
									else:
										multiplier = 1
									amount_PFE *= multiplier
									
									#calculating conversion results
									amount_USD = amount_PFE * 1.266
									amount_EUR = amount_USD * rate_EUR
									amount_SHMACK = amount_PFE * rate_SHMACK
									amount_GBP = amount_USD * rate_GBP
									amount_CAD = amount_USD * rate_CAD
									amount_RUB = amount_USD * rate_RUB
									amount_CNY = amount_USD * rate_CNY
									
									# determine what unit to display in
									if amount[6] == '': # if amount given is in shmacks and not schmeckles
										base_amount = amount_SHMACK
										other_amount = amount_PFE
										base_abbrev = "SHM"
										other_abbrev = "SCH"
									else:
										base_amount = amount_PFE
										other_amount = amount_SHMACK
										base_abbrev = "SCH"
										other_abbrev = "SHM"
										
									if base_amount == 420.00:
										remark = "blaze it. "
									elif base_amount == 69.00:
										remark = "Nice. "
									elif base_amount == 420.69:
										remark = "**NICE.** "
									if str(base_amount) + base_abbrev not in amounts_seen:
										reply_contents += "%s%.2f %s is:\n\nUSD|%s|EUR|GBP|CAD|RUB|CNY  \n---|------|---|---|---|---|---  \n%.2f|%.2f|%.2f|%.2f|%.2f|%.2f|%.2f\n\n" % (remark, base_amount, base_unit, other_abbrev, amount_USD, other_amount, amount_EUR, amount_GBP, amount_CAD, amount_RUB, amount_CNY)
										amounts_seen += str(base_amount) + base_abbrev
								
								reply_contents += "***\n^(created by [u/Nissingmo](http://reddit.com/u/nissingmo))" 
								submission.reply(reply_contents)
								cache += submission.id
								posts_replied_to.append(submission.id)
								replySent = True
								replies_sent += 1
								print("reply sent: table")
								with open("posts_replied_to.txt", "a") as f:
									f.write(submission.id + '\n')

							if not replySent:
								print("no reply sent: no amount recognized")
						else:
							print("no reply sent: already replied and/or submission by self")
					else:
						print("no reply sent: submission deleted or no selftext")
					
							# f.write(post_id + "\n")
					print("%02d replies sent          as of %s" % (replies_sent, datetime.datetime.fromtimestamp(time.mktime(time.gmtime()))))

		else: #scrape comments instead
			for comment in reddit.subreddit(subreddit).stream.comments(skip_existing=Skip_existing):
				amounts_seen = ""
				if str(comment.subreddit) not in exclude: # subreddit not on exclude list
					if time.time() - lastRateRefreshTime > refresh_interval:
						print ('%s - %s' % (time.time(), lastRateRefreshTime))
						print('this dood is refreshing already!!')
						getRates()
					replySent = False
					print("\n")

					comment_still_exists = True
					if comment.body == "[deleted]" or comment.author == None:
						comment_still_exists = False
					
					if comment_still_exists:
						try:
							author = comment.author
							time_created = comment.created
							
							print("in r/%s" % comment.subreddit)
							print("by u/%-22s on %s" % (author.name, datetime.datetime.fromtimestamp(time_created)))
							print("comment body:\n%s" % comment.body)

						except AttributeError:
							no_body = True

						#print (comment.permalink)
						if comment.id not in posts_replied_to and not re.search("(?i)SchmeckMichBot", author.name):
							# VERY IMPORTANT
							bad_numbers = re.search("[0-9]{60}[0-9]*", comment.body) # too long numbers to process, also beyond python accuracy
                                                        
							Match = False # by default
							if not bad_numbers:    
								Match = re.findall(r"(?i)([0-9,]*\.?[0-9]+)\s*([kmbt]|hundred|thousand|(m|b|tr)illion)? +(sc?hm[ae](ck|ch|c|k))((le|el)?)", comment.body)
							
							if Match and comment.id not in cache:
								reply_contents = ''
								for amount in Match:
									remark = ""
									amount_no_commas = amount[0].replace(',', '')
									#amount[0] = amount[0].replace(',', '')
									
									if amount[6] == '': # if amount given is in shmacks and not schmeckles
										amount_PFE = float(amount_no_commas) * 101
										base_unit = "shmacks"
									else:
										amount_PFE = float(amount_no_commas)
										base_unit = "schmeckles"

									if re.search("(?i)hundred", amount[1]):
										multiplier = 100
									elif re.search("(?i)k|thousand", amount[1]):
										multiplier = 1000
									elif re.search("(?i)m|million", amount[1]):
										multiplier = 1000000
									elif re.search("(?i)b|billion", amount[1]):
										multiplier = 1000000000
									elif re.search("(?i)t|trillion", amount[1]):
										multiplier = 1000000000000
									else:
										multiplier = 1
									amount_PFE *= multiplier

									#calculating conversion results
									amount_USD = amount_PFE * 1.266
									amount_EUR = amount_USD * rate_EUR
									amount_SHMACK = amount_PFE * rate_SHMACK
									amount_GBP = amount_USD * rate_GBP
									amount_CAD = amount_USD * rate_CAD
									amount_RUB = amount_USD * rate_RUB
									amount_CNY = amount_USD * rate_CNY
									
									# determine what unit to display in
									if amount[6] == '': # if amount given is in shmacks and not schmeckles
										base_amount = amount_SHMACK
										other_amount = amount_PFE
										base_abbrev = "SHM"
										other_abbrev = "SCH"
									else:
										base_amount = amount_PFE
										other_amount = amount_SHMACK
										base_abbrev = "SCH"
										other_abbrev = "SHM"
									
									if base_amount == 420.00:
										remark = "blaze it. "
									elif base_amount == 69.00:
										remark = "Nice. "
									elif base_amount == 420.69:
										remark = "**NICE.** "
									
									if str(base_amount) + base_abbrev not in amounts_seen:
										reply_contents += "%s%.2f %s is:\n\nUSD|%s|EUR|GBP|CAD|RUB|CNY  \n---|------|---|---|---|---|---  \n%.2f|%.2f|%.2f|%.2f|%.2f|%.2f|%.2f\n\n" % (remark, base_amount, base_unit, other_abbrev, amount_USD, other_amount, amount_EUR, amount_GBP, amount_CAD, amount_RUB, amount_CNY)
										amounts_seen += str(base_amount) + base_abbrev
								reply_contents += "***\n^([exchange rate source](http://api.ratesapi.io/%s?base=USD) | created by [u/Nissingmo](http://reddit.com/u/nissingmo))" % datetime.date.fromtimestamp(time.mktime(time.gmtime()))
								comment.reply(reply_contents)
								cache += comment.id
								posts_replied_to.append(comment.id)
								replySent = True
								replies_sent += 1
								print("reply sent: table")
								with open("posts_replied_to.txt", "a") as f:
									f.write(comment.id + '\n')

							if not replySent:
								print("no reply sent: no amount recognized")
						else:
							print("no reply sent: already replied and/or comment by self")
					else:
						print("no reply sent: comment deleted")
					
							# f.write(post_id + "\n")
					print("%02d replies sent          as of %s" % (replies_sent, datetime.datetime.fromtimestamp(time.mktime(time.gmtime()))))

	except:
		raise
		return [-1, replies_sent]

Skip_existing = False
total_replies = 0

got_post_type = False
got_subreddit = False
log_subs = False
refresh_interval = 3600
exclude = ""

if len(sys.argv) > 1: # interpret options
	argv = ""
	for arg in sys.argv:
		argv += arg + ' '
	exc_match = re.search("(?i) -(x|-exclude) ((r\/([a-z0-9]{1,23}) )+)", argv)
	if exc_match:
		exclude = exc_match.group(2)

	skip_match = re.search("(?i) -(k|-skip_existing)", argv)
	if skip_match:
		Skip_existing = True

	interval_match = re.search("(?i) -(i|-interval) ([0-9]+)", argv)
	if interval_match:		
		refresh_interval = int(interval_match.group(2))
		
	if re.search("(?i) -(ls|-logsubs)", argv):
		log_subs = True
	else:
		log_subs = False
		
	if re.search("(?i) -(c|-comments)", argv):
		scrape_submissions = False
		got_post_type = True
	elif re.search("(?i) -(s|-submissions)", argv):
		scrape_submissions = True
		got_post_type = True
	else:
		got_input = False
		
	subreddit_match = re.search("(?i) -r\/([a-z0-9]{1,23})", argv)
	if subreddit_match:
		sub_name = subreddit_match.group(1)
		got_subreddit = True

if True:
	if not got_subreddit:
		sub_name = input("\n*Enter subreddit name:*\nr/")
	while not got_post_type:
		scrape_submissions = input("Scrape submissions? (Y for submissions, N for comments):").upper()
		got_post_type = re.search("^[YN]$", scrape_submissions)
		if got_post_type:
			scrape_submissions = bool(scrape_submissions == 'Y')
			break
print("\n\n")

getRates()

while True:
	try:
		reply_finished = reply_to_stream(sub_name, scrape_submissions, log_subs, Skip_existing, exclude)
		total_replies += reply_finished[1]
		if reply_finished[0] == -1:
			break
			raise
	except:
		raise
		print("\n\nreplies sent: %d" % total_replies)
		break
print("\n\n")
