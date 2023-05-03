from bs4 import BeautifulSoup

def get_float_sector_info(ticker):
    floatchecker_url = 'https://www.floatchecker.com/stock?float='
    floatchecker_url = floatchecker_url + ticker
    html = requests.get(floatchecker_url).text
    soup = BeautifulSoup(html, 'html.parser')
    regex_list = [re.compile('Morningstar.'), re.compile('FinViz'), re.compile('Yahoo Finance'),
                  re.compile('Wall Street Journal')]
    info_dict = {}
    l = [None] * 5
    grab_sector = True
    # while the float is unavailable, search in the next regex
    i = 0
    while l[2] is None and i < len(regex_list):
        j = 0
        num = [None] * 3  # list for float, short interest, and outstanding shares
        for link in soup.find_all('a'):
            title = link.get('title')
            if re.match(regex_list[i], str(title)):
                # only grab sector once
                if grab_sector:
                    sector, industry = get_sector_info(link.get('href'))
                    l[0] = sector
                    l[1] = industry
                    grab_sector = False

                num[j] = re.findall('\d*\.?\d+', link.getText())
                # If the float is available for the regex column then we will try to grab short interest and oustanding shares too.
                # If not, then we will move to the next regex
                if not num[0]:
                    j = 0
                    break

                if num[j]:
                    l[j + 2] = num[j][0]
                j = j + 1
        i = i + 1

    info_dict['sector'] = 'N/A'
    info_dict['industry'] = 'N/A'
    info_dict['float'] = 'N/A'
    info_dict['short interest'] = 'N/A'
    info_dict['shares outstanding'] = 'N/A'

    info_dict['sector'] = l[0]
    info_dict['industry'] = l[1]
    if l[2] is not None:
        info_dict['float'] = float(l[2]) * 1000000
    else:
        info_dict['float'] = 'N/A'
    if l[3] is not None:
        info_dict['short interest'] = float(l[3]) / 100
    else:
        info_dict['short interest'] = 'N/A'
    if l[4] is not None:
        info_dict['shares outstanding'] = float(l[4]) * 1000000
    else:
        info_dict['short interest'] = 'N/A'

    return info_dict