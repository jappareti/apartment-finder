from scraper import do_scrape
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

        # Print countdown timer
        for t in range(settings.SLEEP_INTERVAL,-1,-1):
            minutes = t / 60
            seconds = t % 60
            print("Sleeping for %d:%02d" % (minutes,seconds), end='\r')
            time.sleep(1.0)
        #print("Sleeping for {} mins".format(settings.SLEEP_INTERVAL / 60))
        time.sleep(settings.SLEEP_INTERVAL)
