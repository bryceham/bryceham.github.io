import csv, json, os.path, math
from pollingregions import polling_regions
from datetime import datetime, date

parties = ["conservative", "labour", "libdems",	"ukip", "green", "snp",
            "plaidcymru", "other", "sdlp", "sinnfein", "alliance", "dup", "uu"]

regions = ["northernireland", "scotland", "yorkshireandthehumber", "wales", "northeastengland", "northwestengland",
            "southeastengland", "southwestengland", "london", "eastofengland", "eastmidlands", "westmidlands"]

# get regional party totals from 2015
old_data = {}
previous_regional_totals = {}
current_dir = os.path.dirname(__file__)
parent_dir = os.path.split(current_dir)[0]
file_path = os.path.join(parent_dir, "2015election.json")

with open(file_path) as data_file:
    data = json.load(data_file)
    for seat in data:
        old_data[seat] = data[seat]
    data_file.close()

def get_old_totals(region):
    turnout = 0
    party_votes = {}

    for party in parties:

        party_total = 0

        for seat in old_data:
            if old_data[seat]["seatInfo"]["region"] == region:
                if party in old_data[seat]["partyInfo"]:
                    turnout += old_data[seat]["partyInfo"][party]["total"]
                    party_total += old_data[seat]["partyInfo"][party]["total"]
                if party == "other":
                    if "others" in old_data[seat]["partyInfo"]:
                        party_total += old_data[seat]["partyInfo"]["others"]["total"]
                        turnout += old_data[seat]["partyInfo"]["others"]["total"]

        party_votes[party] = party_total

    party_votes["turnout"] = turnout
    previous_regional_totals[region] = party_votes

for region in regions:
    get_old_totals(region)

#get polls from csv
polls = {}
with open("polls.csv", "rb") as polls_file:
    poll_data = csv.DictReader(polls_file, delimiter = "\t")
    for row in poll_data:
        code = row["code"]
        if code not in polls:
            polls[code] = {
                "company" : row["company"],
                "date" : datetime(int(row["year"]), int(row["month"]), int(row["day"])),
                "regions" : {}
            }


        region_to_add = {}
        for party in parties:
            if row[party] != "":
                region_to_add[party] = int(row[party])
            else:
                region_to_add[party] = 0
            region_to_add["total"] = int(row["total"])

        polls[code]["regions"][row["region"]] = region_to_add


    polls_file.close()

#manipulate specific polls based on company

def poll_maths(poll):
    company = poll["company"]

    if company == "icm":
        for region, numbers in poll["regions"].iteritems():
            if region == "North":
                for party in numbers:
                    numbers[party] -= int(poll["regions"]["Scotland"][party])

            if region == "Midlands":
                for party in numbers:
                    numbers[party] -= int(poll["regions"]["Wales"][party])

    if company == "mori":
        for party in poll["regions"]["Wales"]:
            poll["regions"]["Wales"][party] = - (poll["regions"]["England"][party]
                                                - poll["regions"]["South"][party]
                                                - poll["regions"]["Midlands"][party]
                                                - poll["regions"]["North"][party])

            poll["regions"]["Midlands"][party] -= poll["regions"]["Wales"][party]

            poll["regions"]["South"][party] -= poll["regions"]["London"][party]

        del poll["regions"]["England"]

        #convert to decimal percentaegs
    raw_num_comps = ["general", "me", "icm", "icm2", "opinium",
                    "mori", "comres", "comresdm", "survation",
                    "bmg", "icmmissing", "opiniummissing", "ashcroft"]

    if company in raw_num_comps:
        for region, numbers in poll["regions"].iteritems():
            for party in numbers:
                if party != "total":
                    numbers[party] /= float(numbers["total"])

    #coinvert percentages to decimal
    if company in ["yougov"]:
        for region, numbers in poll["regions"].iteritems():
            for party in numbers:
                if party != "total":
                    numbers[party] /= float(100)


    # delete total from polls
    for region, numbers in poll["regions"].iteritems():
        del numbers["total"]

def weight_poll(data):
    today = datetime.today()
    days_past = (today - data["date"]).days

    weight = 1

    # alter closer to election  when more polls
    degrade_factor = 0.95 #per day
    weight *= math.pow(degrade_factor, days_past)

    #testing
    if data["company"] == "me":
        weight = 10000000

    return weight

polls_for_scatterplot = {"polls" : []}

def scatterplot(data):

    to_add = {
        "dateobj" : data["date"],
        "date" : [],
        "company" : None,
        "labour" : 0,
        "conservative" : 0,
        "libdems" : 0,
        "snp" : 0,
        "ukip" : 0,
        "green" : 0,
        "others" : 0
    }

    to_add["date"].append(data["date"].day)
    to_add["date"].append(data["date"].month)
    to_add["date"].append(data["date"].year)


    companies = ["yougov", "icm", "mori", "opinium", "comres", "icm2",
                "comresdm", "icmmissing", "opiniummissing"]

    if data["company"] in companies:
        to_add["company"] = data["company"]
    else:
        to_add["company"] = "others"

    total = 0
    for region, numbers in data["regions"].iteritems():

        if (data["company"] != "mori" or region != "England") and (data["company"] != "icm" or region not in ["Wales", "Scotland"]):

            for party, votes in numbers.iteritems():
                if party != "total":

                    if data["company"] == "yougov":
                        if party in to_add:
                            to_add[party] += votes * numbers["total"] / 100
                        else:
                            to_add["others"] += votes * numbers["total"] / 100
                        total += votes * numbers["total"] / 100

                    else:


                        if party in to_add:
                            to_add[party] += votes
                        else:
                            to_add["others"] += votes

                        total += votes


    for party in to_add:
        if party != "date" and party != "company" and party !="dateobj":
            to_add[party] /= (float(total) / 100)
            to_add[party] = round(to_add[party], 1)

    if to_add["company"] == "icm2" or to_add["company"] == "icmmissing":
        to_add["company"] = "icm"
    if to_add["company"] == "comresdm":
        to_add["company"] = "comres"
    if to_add["company"] == "opiniummissing":
        to_add["company"] = "opinium"

    #print to_add["company"], "\n", to_add, "\n"
    return to_add

#alter polls per company, get weight
for poll, data in polls.iteritems():

    if data["company"] != "me":
        polls_for_scatterplot["polls"].append(scatterplot(data))

    poll_maths(data)
    data["weight"] = weight_poll(data)

#sort polls for scatterplot by date

polls_for_scatterplot["polls"].sort(key=lambda x: x["dateobj"])

for poll in polls_for_scatterplot["polls"]:
    del poll["dateobj"]

regional_averages = {} # obj to export to analysis
#set up object
for region in regions:
    regional_averages[region] = {}

#get change for each polling region relative to 2015
for poll, data in polls.iteritems():
    if poll != "1001": # my test poll nullified
        #print data["company"]
        for area, numbers in data["regions"].iteritems():
            regions_in_poll_area = polling_regions[data["company"]][area]
            for party in numbers:
                #get previous regional total per party

                previous_total = 0
                previous_turnout = 0
                #print area, party, regions_in_poll_area
                for region in regions_in_poll_area:
                    previous_turnout += previous_regional_totals[region][party]
                    previous_total += previous_regional_totals[region]["turnout"]

                previous_area_percentage = previous_turnout / float(previous_total)
                #print party, area, previous_area_percentage, numbers[party]
                #alter poll to show change
                numbers[party] -= previous_area_percentage

            for region in regions_in_poll_area:
                for party in numbers:
                    if party not in regional_averages[region]:
                        regional_averages[region][party] = 0
                    previous_region_percentage = previous_regional_totals[region][party] / float (previous_regional_totals[region]["turnout"]) #2015 region percentage
                    #print party, region, previous_region_percentage, data["weight"], numbers[party]
                    regional_averages[region][party] += (data["weight"] * (previous_region_percentage + numbers[party])) # add poll region and weight it

# normalise regional averages
#print previous_regional_totals

for region, data in regional_averages.iteritems():

    # sometimes parties dip below 0
    for party in data:
        if data[party] < 0:
            data[party] = 0

    sum = 0
    for party in data:
        sum += data[party]

    normaliser = 1 / sum

    for party in data:
        data[party] *= normaliser