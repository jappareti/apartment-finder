from craigslist import CraigslistHousing
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, DateTime, Float, Boolean
from sqlalchemy.orm import sessionmaker
from dateutil.parser import parse
from util import post_listing_to_slack, find_points_of_interest
from slackclient import SlackClient
from airtable import airtable
from motionless import DecoratedMap, AddressMarker
from bs4 import BeautifulSoup
from random import randint
import requests
import time
import settings
import pytz

engine = create_engine('sqlite:///listings.db', echo=False)

Base = declarative_base()

class Listing(Base):
    """
    A table to store data on craigslist listings.
    """

    __tablename__ = 'listings'

    id = Column(Integer, primary_key=True)
    link = Column(String, unique=True)
    created = Column(DateTime)
    geotag = Column(String)
    lat = Column(Float)
    lon = Column(Float)
    name = Column(String)
    price = Column(Float)
    location = Column(String)
    cl_id = Column(Integer, unique=True)
    area = Column(String)
    bart_stop = Column(String)

Base.metadata.create_all(engine)

Session = sessionmaker(bind=engine)
session = Session()

def scrape_area(area):
    """
    Scrapes craigslist for a certain geographic area, and finds the latest listings.
    :param area:
    :return: A list of results.
    """
    cl_h = CraigslistHousing(site=settings.CRAIGSLIST_SITE, area=area, category=settings.CRAIGSLIST_HOUSING_SECTION,
                             filters={'max_price': settings.MAX_PRICE, "min_price": settings.MIN_PRICE, "zip_code": settings.ZIP_CODE, "search_distance": settings.SEARCH_DISTANCE})

    results = []
    gen = cl_h.get_results(sort_by='newest', geotagged=True, limit=20)
    while True:
        try:
            
            result = next(gen)
            # Random integer between 5 and 20 seconds
            s = randint(5,20)
            print("Getting next result in " + str(s) + " seconds...")
            # Pause before getting another result to help avoid blockage from CL
            time.sleep(s)
        except StopIteration:
            break
        except Exception:
            continue
        listing = session.query(Listing).filter_by(cl_id=result["id"]).first()

        # Don't store the listing if it already exists.
        if listing is None:
            if result["where"] is None:
                # If there is no string identifying which neighborhood the result is from, skip it.
                continue

            lat = 0
            lon = 0
            if result["geotag"] is not None:
                # Assign the coordinates.
                lat = result["geotag"][0]
                lon = result["geotag"][1]

                # Annotate the result with information about the area it's in and points of interest near it.
                geo_data = find_points_of_interest(result["geotag"], result["where"])
                result.update(geo_data)

            else:
                result["area"] = ""
                result["bart"] = ""
                result["bart_station"] = ""
                result["near_bart"] = False
                result["photo"] = ""

            # Try parsing the price.
            price = 0
            try:
                price = float(result["price"].replace("$", ""))
                result['price'] = price
            except Exception:
                pass

            # Create the listing object.
            listing = Listing(
                link=result["url"],
                created=parse(result["datetime"]),
                lat=lat,
                lon=lon,
                name=result["name"],
                price=result['price'],
                location=result["where"],
                cl_id=result["id"],
                area=result["area"],
                bart_stop=result["bart_station"]
            )

            # Save the listing so we don't grab it again.
            session.add(listing)
            session.commit()

            # Get photo from listing
            if result['has_image']:
                r = requests.get(result['url'])
                data = r.text
                soup = BeautifulSoup(data, 'html5lib')
                result['photo'] = soup.find('img').get('src')

            # Return the result if it's near a bart station, or if it is in an area we defined.
            if result["near_bart"]:
                print("It's near a bart station!")
                # Generate static map image
                dmap = DecoratedMap(key=settings.GMAPS_API_KEY, zoom=14)
                dmap.add_marker(AddressMarker(str(result['geotag'][0]) + ", " + str(result['geotag'][1])))
                result['map_image_url'] = dmap.generate_url()

                results.append(result)

    return results

def do_scrape():
    """
    Runs the craigslist scraper, and posts data to slack.
    """

    # Create Airtable 
    at = airtable.Airtable(settings.AIRTABLE_BASE_ID, settings.AIRTABLE_API_KEY)

    # Set timezone
    tz = pytz.timezone("US/Pacific")

    # Get all the results from craigslist.
    all_results = []
    for area in settings.AREAS:
        all_results += scrape_area(area)

    print("{}: Got {} results".format(time.ctime(), len(all_results)))

    # Post each result to Airtable.
    for result in all_results:
        print(result)

        date_localized = tz.localize(parse(result['datetime']))

        at_listing = {
            "Name": result['name'],
            "Link": result['url'],
            "Price": result['price'],
            "Location": result['where'],
            "Closest Bart Station": result['bart_station'],
            "Bart Walking Time": result['bart_walking_dist'],
            "Map": [{"url":result['map_image_url']}],
            "Photos": [{"url":result['photo']}],
            "Added to CL": date_localized.isoformat()
        }
        at.create('All Results', at_listing)

