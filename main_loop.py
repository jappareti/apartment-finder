from scraper import do_scrape
from random import randint
import settings
import time
import sys
import traceback

if __name__ == "__main__":
    while True:
        print("{}: Starting scrape cycle".format(time.ctime()))
        try:
            do_scrape()
        except KeyboardInterrupt:
            print("Exiting....")
            sys.exit(1)
        except Exception as exc:
            print("Error with the scraping:", sys.exc_info()[0])
            traceback.print_exc()
        else:
            print("{}: Successfully finished scraping".format(time.ctime()))
        # Randomize sleep time between re-scrape to avoid blockage from CL
        # 900-1500 seconds = 15-25 mins
        s = randint(900,1500)
        print("Sleeping for " + str(s / 60) + " mins...")
        time.sleep(s)
