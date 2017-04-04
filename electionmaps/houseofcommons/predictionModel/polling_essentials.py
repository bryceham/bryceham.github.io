from datetime import datetime, date
import math

parties = ["conservative", "labour", "libdems",	"ukip", "green", "snp",
            "plaidcymru", "other", "sdlp", "sinnfein", "alliance", "dup", "uu"]

regions = ["northernireland", "scotland", "yorkshireandthehumber", "wales", "northeastengland", "northwestengland",
            "southeastengland", "southwestengland", "london", "eastofengland", "eastmidlands", "westmidlands"]

party_map = {
     'conservative': "Conservative",
     'labour': "Labour",
     'libdems': "Lib Dems",
     'ukip': "UKIP",
     'snp': "SNP",
     'plaidcymru': "Plaid Cymru",
     'green': "Green",
     'uu': "UUP",
     'sdlp': "SDLP",
     'dup': "DUP",
     'sinnfein': "Sinn Fein",
     'alliance': "Alliance",
     'other' : "Others"
}

class Seat(object):

    def __init__(self, data):
        self.data = data
        self.region = data["seatInfo"]["region"]
        self.electorate = data["seatInfo"]["electorate"]
        self.current = data["seatInfo"]["current"]
        self.majority = 0
        self.old_partyInfo = data["partyInfo"]
        self.new_partyInfo = {}
        self.output = None

        other_total = 0
        for party in self.old_partyInfo:
            if party == "others" or party == "other":
                other_total += self.old_partyInfo[party]["total"]

        self.old_partyInfo["other"] = {"total" : other_total, "name" : "Others"}
        if "others" in self.old_partyInfo:
            del data["partyInfo"]["others"]


    def get_new_data(self, regional):
        turnout = 0
        for party in  self.old_partyInfo:
            turnout += self.old_partyInfo[party]["total"]

        # for getting current, majority
        max = 0
        current_max = ""

        new_percentages = {}

        for party in self.old_partyInfo:
            percentage_vote = self.old_partyInfo[party]["total"] / float(turnout)

            #old method
            #seat_relative = percentage_vote / regional[party]
            #new = 0
            #
            # if seat_relative != 0:
            #     distribute = regional[party] - 1
            #     seat_change = 1 + distribute / math.pow(seat_relative, 0.5)
            #
            #     if seat_change < 0.15:
            #         seat_change = 0.15
            #
            #     new = seat_change * self.old_partyInfo[party]["total"] / float(turnout)
            #
            #     incumbencies = {"libdems" : 0.04, "ukip" : 0.03, "conservative" : 0.02, "labour" : 0.02, "green" : 0.03, "snp": 0.04, "plaidcymru" : 0.04}
            #
            #     if party == self.current:
            #         if party in incumbencies:
            #             new += incumbencies[party]
            #
            #     if new > max:
            #         max = new
            #         current_max = party

            new = regional[party] + percentage_vote

            if new > max:
                max = new
                current_max = party

            if new < 0.1 * percentage_vote:

                new = 0.1 * percentage_vote

            if percentage_vote == 0:
                new = 0

            new_percentages[party] = new

        sum = 0
        for party, total in new_percentages.iteritems():
            sum += total

        votes_array = []
        normaliser = 1 / sum
    
        for party, total in new_percentages.iteritems():
            new_percentages[party] *= normaliser
            votes = int(round(new_percentages[party] * turnout))
            votes_array.append(votes)
            self.new_partyInfo[party] = {"name" : party_map[party], "total" : votes}

        self.current = current_max
        self.majority =  sorted(votes_array)[-1] - sorted(votes_array)[-2]

        self.new_partyInfo["others"] = self.new_partyInfo["other"]
        del self.new_partyInfo["other"]

    def generate_output(self):
        self.output = {
            "seatInfo" : {"current" : self.current, "region" : self.region, "electorate" : self.electorate, "majority" : self.majority},
            "partyInfo" : self.new_partyInfo
        }


class RegionalTotals(object):

    def __init__(self, region):
        self.region = region
        self.old_totals = {}
        self.old_percentages = {}
        self.new_totals = {}
        self.relative = {}
        self.numerical = {}

    #numerical totals per region, combine other and others
    def get_regional_totals(self, data_set):
        party_votes = {}
        turnout = 0

        for party in parties:
            party_total = 0

            for seat in data_set:

                if data_set[seat].region == self.region:
                    if party in data_set[seat].old_partyInfo:
                        turnout += data_set[seat].old_partyInfo[party]["total"]
                        party_total += data_set[seat].old_partyInfo[party]["total"]
                    if party == "other":
                        if "others" in data_set[seat].old_partyInfo:
                            party_total += data_set[seat].old_partyInfo["others"]["total"]
                            turnout += data_set[seat].old_partyInfo["others"]["total"]

            party_votes[party] = party_total

        party_votes["turnout"] = turnout
        return party_votes

    def normalise(self):
        # sometimes parties dip below 0
        for party in self.new_totals:
            if self.new_totals[party] < 0:
                self.new_totals[party] = 0

        sum = 0
        for party in self.new_totals:
            sum += self.new_totals[party]

        normaliser = 1 / sum

        for party in self.new_totals:
            self.new_totals[party] *= normaliser

    def get_old_percentages(self):
        for party in self.old_totals:
            if party != "turnout":
                self.old_percentages[party] = self.old_totals[party] / float(self.old_totals["turnout"])

    def get_relative_change(self):
        for party in self.old_percentages:
            if self.old_percentages[party] != 0:
                self.relative[party] = self.new_totals[party] / self.old_percentages[party]


    def get_numerical_change(self):
            for party in self.old_percentages:
                if self.old_percentages[party] != 0:
                    self.numerical[party] = self.new_totals[party] - self.old_percentages[party]


class Poll(object):

    def __init__(self, code, company, day, month, year):
        self.code = code
        self.company = company
        self.date = datetime(int(year), int(month), int(day))
        self.regions = {}
        self.weight = 1


    def add_row(self, row):
        to_add = {}
        for party in parties:
            if row[party] == "":
                to_add[party] = 0
            else:
                to_add[party] = int(row[party])

        to_add["total"] = int(row["total"])
        self.regions[row["region"]] = to_add

    def poll_maths(self):

        #sort out certain companies/regions
        if self.company == "icm":
            for region, numbers in self.regions.iteritems():
                if region == "North":
                    for party in numbers:
                        numbers[party] -= int(self.regions["Scotland"][party])

                if region == "Midlands":
                    for party in numbers:
                        numbers[party] -= int(self.regions["Wales"][party])

        if self.company == "mori":
            for party in self.regions["Wales"]:
                self.regions["Wales"][party] = - (self.regions["England"][party]
                                                    - self.regions["South"][party]
                                                    - self.regions["Midlands"][party]
                                                    - self.regions["North"][party])

                self.regions["Midlands"][party] -= self.regions["Wales"][party]

                self.regions["South"][party] -= self.regions["London"][party]

            del self.regions["England"]

        #convert to decimal percentaegs
        raw_num_comps = ["general", "me", "icm", "icm2", "opinium",
                        "mori", "comres", "comresdm", "survation",
                        "bmg", "icmmissing", "opiniummissing", "ashcroft", "gfk"]

        if self.company in raw_num_comps:
            for region, numbers in self.regions.iteritems():
                for party in numbers:
                    if party != "total":
                        numbers[party] /= float(numbers["total"])

        #convert percentages to decimal
        if self.company in ["yougov"]:
            for region, numbers in self.regions.iteritems():
                for party in numbers:
                    if party != "total":
                        numbers[party] /= float(100)


        # delete total from polls
        for region, numbers in self.regions.iteritems():
            del numbers["total"]

    def weight_poll(self):
        today = datetime.today()
        days_past = (today - self.date).days

        weight = 1

        # alter closer to election  when more polls
        degrade_factor = 0.98 #per day
        weight *= math.pow(degrade_factor, days_past)

        #testing
        if self.company == "me":
            self.weight = 10000000

        return weight

    def scatterplot(self):
        to_add = {
            "dateobj" : self.date,
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

        to_add["date"].append(self.date.day)
        to_add["date"].append(self.date.month)
        to_add["date"].append(self.date.year)

        companies = ["yougov", "icm", "mori", "opinium", "comres", "icm2",
                    "comresdm", "icmmissing", "opiniummissing"]

        if self.company in companies:
            to_add["company"] = self.company
        else:
            to_add["company"] = "others"

        total = 0
        for region, numbers in self.regions.iteritems():
            if (self.company != "mori" or region != "England") and (self.company != "icm" or region not in ["Wales", "Scotland"]):
                for party, votes in numbers.iteritems():
                    if party != "total":
                        if self.company == "yougov":
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

        return to_add