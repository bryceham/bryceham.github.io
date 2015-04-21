import time
import datetime
import subprocess
import os
import json
import moment

seat_dict = open("seat_map.json").read()
seat_map = json.loads(seat_dict)

old = open("old_data.json").read()
old_data = json.loads(old)

live_data = {}
new_data = {}

parties = ["conservative", "labour", "libdems", "ukip", "snp", "plaidcymru", "green", "uu", "sdlp", "dup", "sinnfein", "alliance", "other", "others"]

seat_list = []

def get_data(file):

    jsondata = open(path + file).read()
    data = json.loads(jsondata)

    seat_name = file[0:-5]

    turnout = data["seat_info"]["turnout"]
    electorate = data["seat_info"]["electorate"]
    percentage_turnout = data["seat_info"]["percentage_turnout"]
    declared_at = data["seat_info"]["declared_at"]
    declared_at_simple = data["seat_info"]["declared_at_simple"]

    by_party = {}

    max_party = ["" , 0]

    for party in parties:
        if party in data["party_info"].keys():
            info = data["party_info"][party]
            name = info["name"]
            vote_total = info["vote_total"]
            if vote_total > max_party[1]:
                max_party[0] = party
                max_party[1] = vote_total

            vote_percentage = 100 * vote_total / float(turnout)

            if old_data[seat_name][party] == None:
                old_votes = 0
            else:
                old_votes = old_data[seat_name][party]

            old_percentage = 100 * old_votes / float(old_data[seat_name]["turnout"])

            change_in_percentage = vote_percentage - old_percentage


            by_party[party] = {"name" : name,
                                "vote_total" : vote_total,
                                "vote_percentage" : vote_percentage,
                                "change_in_percentage": change_in_percentage}


    by_seat = {}
    by_seat["area"] = old_data[seat_name]["area"]
    by_seat["winning_party"] = max_party[0]
    by_seat["incumbent"] = old_data[seat_name]["incumbent"]

    if max_party[0] != old_data[seat_name]["incumbent"]:
        change = "gain"
    else:
        change = "hold"

    by_seat["change"] = change
    by_seat["electorate"] = electorate
    by_seat["turnout"] = turnout
    by_seat["percentage_turnout"] = percentage_turnout

    all_the_votes = []
    for candidate in by_party:
        all_the_votes.append(by_party[candidate]["vote_total"])


    all_the_votes.remove(max(all_the_votes))
    majority_total = max_party[1] - max(all_the_votes)
    majority_percentage = 100 * majority_total / turnout
    by_seat["majority_total"] = majority_total
    by_seat["majority_percentage"] = majority_percentage

    by_seat["declared_at"] = declared_at
    by_seat["declared_at_simple"] = declared_at_simple


    live_data[seat_name] = {"seat_info" : by_seat, "party_info" : by_party}

    if seat_name not in seat_list:
        seat_list.append(seat_name)

    now = time.time()
    if now - declared_at < 360:
        new_data[seat_name] = {"seat_info" : by_seat, "party_info" : by_party}




seats_declared = 0

while(True):

    print "********************"
    current_time = datetime.datetime.now()
    current_time = str(current_time)[0:16]
    print current_time

    delay = 30

    print "Refresh Rate: ", delay, "seconds"
    print "\n"

    path = "data/seats/"
    files = os.listdir(path)

    live_data = {}
    new_data = {}

    total_seats = 0
    for file in files:
        if file[0:-5] not in seat_list:
            print file[0:-5]
        total_seats +=1
        get_data(file)

    print "\n"

    print "seats declared so far", total_seats

    print "********************"
    if seats_declared == total_seats:
        print "no change"

    else:
        print "change"
        print "dumping to json"
        with open("info.json", "w") as output:
            json.dump(live_data, output)
        with open("new_info.json", "w") as out:
            json.dump(new_data, out)
        print "updating git"
        subprocess.call("autorun.sh", shell = True)

    print "\n" * 3
    seats_declared = total_seats

    for i in range(delay):
        if (delay - i) % 10 == 0:
            print "time to next update", delay - i, "seconds"
        time.sleep(1)
