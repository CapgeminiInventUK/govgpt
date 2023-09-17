from datetime import datetime

import requests
import xmltodict as xmltodict

# Get the XML data from file
res = requests.get('https://www.gov.uk/sitemap.xml')
data = xmltodict.parse(res.text)

sitemaps = data['sitemapindex']['sitemap']
for sitemap in sitemaps:
    print('Starting sitemap: ' + sitemap['loc'] + ' @ ' + str(datetime.now()))
    file = open('to_do_sitemaps/' + sitemap['loc'].split('/')[-1], "w+")

    file.write(requests.get(sitemap['loc']).text)
