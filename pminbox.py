#!/usr/bin/python3
# TODO:
# Add compatibility with new schmeckle notation:
# "SHM XX.XX"

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


#reddit = praw.reddit(client_id, client_secret, user_agent, username, password)
reddit = praw.Reddit(client_id=privateinfo.Client_id, client_secret=privateinfo.Client_secret, user_agent=privateinfo.User_agent, username=privateinfo.Username, password=privateinfo.Password)


cache = ""


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

def reply_to_stream ():
    with open("messages_replied_to.txt") as f:
        messages_replied_to = f.read().split('\n')

    replies_sent = 0
    global cache
    try:
        for message in praw.models.util.stream_generator(reddit.inbox.messages):
            amounts_seen = ""

            if time.time() - lastRateRefreshTime > refresh_interval: # refresh exchange rates
                getRates()
            replySent = False
            print("\n")
            try:
                author = message.author
                time_created = message.created_utc
                	
                print("in Private Messages")
                print("from u/%-22s on %s" % (author.name, datetime.datetime.fromtimestamp(time_created)))
                print('"%s"' % message.subject)
                #has_selftext = True
                print('"%s"' % message.body)
            except AttributeError:
                print("AttributeError")
					
					
            if message.id not in messages_replied_to:
                Match_subject = re.findall(r"(?i)([0-9,]*\.?[0-9]+)\s*([kmbt]|hundred|thousand|(m|b|tr)illion)? +(sc?hm[ae](ck|ch|c|k))((le|el)?)", message.subject)
                Match_body = re.findall("pattern", "none") # by default there should be no match
                bad_numbers = re.search("[0-9]{60}[0-9]*", message.body) # first detect if the processor will get stuck doing useless work
                if not bad_numbers: # do not let processor do useless work
                    Match_body = re.findall(r"(?i)([0-9,]*\.?[0-9]+)\s*([kmbt]|hundred|thousand|(m|b|tr)illion)? +(sc?hm[ae](ck|ch|c|k))((le|el)?)", message.body)
                Match_all = Match_subject + Match_body
							
                if (Match_subject or Match_body) and message.id not in cache:
                    reply_contents = '' # initialize to blank
                    for amount in Match_all:
                        remark = ""
                        
                        amount_no_commas = amount[0].replace(',', '')
                        if amount[6] == '': # if amount given is in shmacks and not schmeckles ("le" group is blank if so)
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
									
                        # calculating conversion results
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
			
                        if str(base_amount) + base_abbrev not in amounts_seen: # if amount not already converted
                            reply_contents += "%s%.2f %s is:  \n%.2f **USD**; %.2f **%s**; %.2f **EUR**; %.2f **GBP**; %.2f **CAD**; %.2f **RUB**; %.2f **CNY**\n\n" % (remark, base_amount, base_unit, amount_USD, other_amount, other_abbrev, amount_EUR, amount_GBP, amount_CAD, amount_RUB, amount_CNY)
                            amounts_seen += str(base_amount) + base_abbrev
								
                    # reply_contents += "  \nreply with a 3-letter currency code to get your quantity converted to that code"
                    try:
                        message.reply(reply_contents)
                        replySent = True
                        replies_sent += 1
                        print("reply sent: table")
                    except:
                        print("Error sending reply")
                        replySent = False
                    cache += message.id
                    messages_replied_to.append(message.id)
                    with open("messages_replied_to.txt", "a") as f:
                        f.write(message.id + '\n')
                if not replySent:
                    print("no reply sent: no amount recognized")
            else:
                print("no reply sent: already replied")				
            print("%02d replies sent            as of %s" % (replies_sent, datetime.datetime.fromtimestamp(time.mktime(time.gmtime()))))
    except:
        raise
    return [-1, replies_sent]


total_replies = 0

refresh_interval = 1800 # 1800 second or 30 minutes by defaualt

getRates()

# TODO: fix whatever the hell this is
while True:
    try:
        reply_finished = reply_to_stream()
        total_replies += reply_finished[1]
        if reply_finished[0] == -1:
            break
            raise
    except:
        raise
        print("\n\nreplies sent: %d" % total_replies)
        break
print("\n\n")


