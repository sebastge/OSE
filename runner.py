import requests
import bs4
import re
import csv
import datetime
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import sys
import os
from matplotlib.dates import YearLocator, MonthLocator, DateFormatter
import numpy as np


class Runner:

    """

        Application to collect company-specific data from Oslo Stock Exchange (OSE).

        The three main functions are:

            1. Collect latest price-data from company and prints to console. Displays quote_date, paper, exchange, opening price,
               closing price, highest price, lowest price, closing price, volume and value.

               Example:

               > runner.py trvx current

               >
                            0      1          2      3      4      5      6       7        8
                0  quote_date  paper       exch   open   high    low  close  volume    value
                1    20181008   TRVX  Oslo Børs  11.28  11.50  11.06  11.44  114880  1299423

            2. Collect company-data from specified or unspecified dates and create a CSV-file from this. Automatically produces
               and (hopefully) opens the csv file after running. Takes either zero, one or two date arguments, depending on what
               the user wishes. Zero date arguments produces a file with all available data for the specified company. One date
               argument produces a file with all available data from the specified date up until current day. Two date arguments
               produces a file with all available data from the first argument up until the second argument.

               Examples:

               > runner.py trvx csv
               > runner.py trvx csv 20151009
               > runner.py trvx csv 20151009 20171009

            3. Collect company-data from specified or unspecified dates and create a simple plot from this (as a .png file).
               Automatically produces and (hopefully) opens the .png file after running. Takes either zero, one or two date
               arguments, depending on what the user wishes. Zero date arguments produces a plot with all available data for
               the specified company. One date argument produces a plot with all available data from the specified date up until
               current day. Two date arguments produces a plot with all available data from the first argument up until the second
               argument.

               Examples:

               > runner.py trvx plot
               > runner.py trvx plot 20151009
               > runner.py trvx plot 20151009 20171009

    """

    def __init__(self, date='unmodified', company='asc', action='csv'):

        self.csvFilename = ''
        self.plotFilename = ''
        self.errorList = []
        self.errorCheck = False
        self.current = False
        self.exchangeURL = 'https://www.netfonds.no/quotes/kurs.php?exchange=OSE'
        self.exchange = 'ose'
        self.exchangeList = self.getExchangeList(self.exchangeURL)
        self.compList = []

        for i in self.exchangeList:
            self.compList.append(i[0].lower())

        self.handleArgv(sys.argv)

        if self.errorCheck:
            raise ValueError(''.join(self.errorList))

        self.companyURL = self.getCompanyURL(self.company)
        self.dataURL = self.getDataURL(self.companyURL)
        self.historyURL = self.getHistoryURL(self.dataURL)
        self.history = self.getHistory(self.historyURL)
        self.getAction()

    def getAction(self):
        """ Method to determine action. Either csv, plot or current """

        if self.current:
            print(pd.DataFrame(self.getCurrent()))
        else:
            if self.action == 'csv':
                self.createCSV(self.history)
                os.system("open  %s" % sys.path[0] + '/' + self.csvFilename)
            elif self.action == 'plot':
                self.plotGraph(self.history)
                os.system("open  %s" % sys.path[0] + '/' + self.plotFilename)

    def handleArgv(self, argv):

        """
            Method to handle arguments given before running
            TODO: Clean up and minimize. Limit number of if/else
        """
        if argv[1].lower() in self.compList:
            self.company = argv[1]
        else:
            self.errorList.append('\nCompany not found. Try the OSE-ticker.\n')
            self.errorCheck = True
        if argv[2].lower() == 'plot':
            self.action = 'plot'
        elif argv[2].lower() == 'csv':
            self.action = 'csv'
        elif argv[2].lower() == 'current':
            self.current = True
        else:
            self.errorList.append('Action not recognized. Try csv or plot.')
            self.errorCheck = True
        if len(argv) > 3:
            if len(argv) is 4:
                try:
                    self.fromDate = pd.Timestamp(argv[3])
                    self.toDate = pd.Timestamp.today()
                except:
                    self.errorCheck = True
                    self.errorList.append(
                        'Something went wrong when converting date-string\n')
            elif len(argv) is 5:
                try:
                    self.fromDate = pd.Timestamp(argv[3])
                    self.toDate = pd.Timestamp(argv[4])
                except:
                    self.errorCheck = True
                    self.errorList.append(
                        'Something went wrong when converting date-string')
            else:
                self.errorCheck = True
                self.errorList.append(
                    'Something went wrong when converting date-string')

        else:
            self.fromDate = pd.Timestamp('20000101')
            self.toDate = pd.Timestamp.today()
            if len(argv) > 5:
                self.errorCheck = True
                self.errorList.append(
                    'Something went wrong when converting date-string')

    def getCurrent(self):
        """ Method to produce newst data from company. Returns list of strings to be printed to console. """

        outList = []
        outList.append(self.history[0].split(','))
        outList.append(self.history[1].split(','))
        return(outList)

    def getCompanyURL(self, company):
        """ Takes company name and returns URL for data from the exchangeList. """
        for i in self.exchangeList:
            if i[0].upper() == company.upper():
                return i[2]
        return None

    def getExchangeList(self, url):
        """ Takes in argument of excahnge URL (OSE) and returns info on all companies (name, ticker, url). """

        companyList = []
        linkList = []
        r = requests.get(url)
        soup = bs4.BeautifulSoup(r.text, 'lxml')

        table = soup.findAll('td', {'class': 'leftalign'})

        for i in table:
            for k in i:
                if type(k) is bs4.element.Tag:
                    companyList.append(k)
        for i in companyList:
            company = (re.search('=(.*).OSE', i.get('href')).group(1),
                       i.text, 'https://www.netfonds.no/quotes/' + i.get('href'))
            linkList.append(company)

        return linkList

    def getDataURL(self, url):
        """ Returns the URL to where the the different export-data is. """

        dataURL = ''
        r = requests.get(url)
        soup = bs4.BeautifulSoup(r.text, 'lxml')
        table = soup.findAll('option')

        for i in table:
            if (i.text == 'Dataeksport'):
                dataURL = 'https://www.netfonds.no/' + i.get('value')

        return dataURL

    def getHistoryURL(self, url):
        """ Returns the URL to where the the CSV-data is. """

        r = requests.get(url)
        soup = bs4.BeautifulSoup(r.text, 'lxml')
        table = soup.findAll('a')

        for i in table:
            try:
                if (i.get('href').startswith('paperhistory') and (i.get('href').endswith('csv'))):
                    historyURL = 'https://www.netfonds.no/quotes/' + \
                        i.get('href')
            except:
                historyURL = ''

        return historyURL

    def getHistory(self, url):
        """  Returns the company data from the csv-URL and creates a list for easier handling in other methods. """

        r = requests.get(url)
        soup = bs4.BeautifulSoup(r.text, 'lxml')
        dataList = soup.text.splitlines()

        return dataList

    def createCSV(self, list, company='one'):

        """ Creates a csv-file of data (from either all available dates or the ones given before running) and saves it as a .csv file. Should automatically open after saving """

        stringList = []
        for i in list:
            stringList.append(i.split(','))
        for i in stringList:
            i.pop(2)
            i.append(self.exchange.upper())
        for i in stringList[1:]:
            if self.toDate <= pd.to_datetime(i[0]) or self.fromDate >= pd.to_datetime(i[0]):
                stringList.remove(i)
        stringList[0][8] = 'exch'
        self.csvFilename = '%s-%s.csv' % (
            datetime.datetime.today().strftime('%Y.%m.%d'), self.company)
        with open(sys.path[0] + '/' + self.csvFilename, 'w', encoding='utf-8') as target:
            writer = csv.writer(target, delimiter=';')
            writer.writerow(stringList[0])
            stringList.pop(0)
            writer.writerows(stringList)

    def plotGraph(self, companyList):

        """ Plots a line-graph from company-data (from either all available dates or the ones given before running) and saves it as a .png file. Should automatically open after saving
        TODO: Clean up and remove redundancy.

        """

        stringList = []
        for i in companyList:
            stringList.append(i.split(','))

        plotList = []
        dateTime = []
        for i in stringList[1:]:
            if self.toDate <= pd.to_datetime(i[0]) or self.fromDate >= pd.to_datetime(i[0]):
                stringList.remove(i)
            else:
                data = (i[0], i[6])
                plotList.append(data)

        xs = [str(x[0][0:8]) for x in plotList]
        ys = [float(x[1]) for x in plotList]

        for i in xs:
            dateTime.append(pd.to_datetime(str(i)))

        if self.fromDate == pd.Timestamp('20000101'):
            self.fromDate = pd.to_datetime(stringList[len(stringList) - 1][0])
        startYear = int(self.fromDate.year)
        endYear = int(self.toDate.year)
        yearList = []
        for i in range(startYear, endYear + 1):
            yearList.append(str(i))
        self.plotFilename = '%s-%s.png' % (datetime.datetime.today().strftime('%Y.%m.%d'), self.company)
        ax = plt.subplot()
        ax.plot(dateTime, ys)
        ax.xaxis.set_ticks(yearList)
        ax.tick_params('x', labelsize=8.0)
        plt.title(self.company.upper())
        plt.xlabel('year')
        plt.ylabel('NOK')
        plt.savefig(sys.path[0] + '/' + self.plotFilename, format='png')


x = Runner()
