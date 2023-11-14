from polygon import RESTClient
from configparser import ConfigParser
from csv import writer, reader

config = ConfigParser()
config.read('config/config.ini')
polygon_key = config.get('main', 'POLYGON_API_KEY')

# RESTClient can be used as a context manager to facilitate closing the underlying http session
# https://requests.readthedocs.io/en/master/user/advanced/#session-objects
def get_holidays_from_polygon():
    holidays = []
    polygon_client = RESTClient(polygon_key)
    resp = polygon_client.get_market_holidays()

    for date in resp:
        holidays.append(date.date)

    with open('holidays.csv', 'a+', newline='') as f_object:
        # Pass the CSV  file object to the writer() function
        writer_object = writer(f_object)
        # Result - a writer object
        # Pass the data in the list as an argument into the writerow() function
        writer_object.writerow(holidays)
        # Close the file object
        f_object.close()

def grab_holidays_from_csv():
    file = open("holidays.csv", "r")
    csv_reader = reader(file)

    lists_from_csv = []
    #for row in csv_reader:
    #    lists_from_csv.append(row)
    holidays = list(csv_reader)
    return holidays[0]

#    print(lists_from_csv)

#get_holidays_from_polygon()
#grab_holidays_from_csv()