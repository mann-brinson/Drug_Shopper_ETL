import requests
import time
import json
from lxml import html
import re
import os
import random
import caffeine

#GOAL: Query GoodRx for each drug_name>zip_code combination, to get stores that sell the drug. 
# For each drug_name>zip_code>store, get a list of price_types (ex: coupon, cash, member). 
# For each price_type, provide a link to purchase the drug from said store.

def get_drugNames(**kwargs):
    '''Get the wikidata query for essential medicine, and select a desired number of drugNames.
    n_drugNames - specifies the desired length of drug sample <optional>'''
    path_parent = os.path.dirname(os.getcwd())
    # drug_data = f'{path_parent}/wikidata_queries/drug.csv' #essential medicines N = 434
    drug_data = f'{path_parent}/wikidata_queries/drug2.csv' #all medicines N =1640
    fd = open(drug_data, 'r') 
    lines = fd.readlines()
    #Get all the drugLabels from this wikidata query
    #drugName_list = list()
    drugName_set = set()
    for idx, line in enumerate(lines):
        if idx != 0:
            drugName = line.strip().split(',')[2] #Pharm_Product
            #if drugName != '': drugName_list.append(drugName)
            if drugName != '': drugName_set.add(drugName)
    #drugName_set = set(drugName_list)
    drugName_set_list = list(drugName_set)
    
    #Sample drugs - optional
    if kwargs != {}: 
        n = kwargs['n_drugNames']
        drugName_samp = drugName_set_list[:n] #Sample N drugs
    else:
        drugName_samp = drugName_set_list
    return drugName_samp

class DrugPriceScraper():
    '''For a given drug list, attempt to query GoodRx with the drug, and scrape the drug features if available.'''
    def __init__(self, drug_list, zip_codes_file, url_base, url_base_api, headers): #STEP 1
        '''
        drug_list - seed drug list from wikidata
        zip_codes_file - opendata_zipcodes.csv
        url_base - https://www.goodrx.com/
        url_base_api - https://www.goodrx.com/api/v4/drugs/
        headers - headers of your browser
        '''
        self.drug_list = drug_list
        self.city_zip_index = self.construct(zip_codes_file)
        
        self.url_base = url_base
        self.url_base_api = url_base_api
        self.headers = headers
        
        self.grx_drug_map = dict() #will have key = drug_name, val = grx_drug_id
        self.drug_zip_store_price = dict() #Stores the scraped data
        
    def construct(self, zip_codes_file): # called by __init__
        '''Build an index of key = city, values = zip_codes.
        zip_codes_file - should be opendata_zipcodes.csv '''
        fd = open(zip_codes_file, 'r') 
        lines = fd.readlines() 
        headers = lines[0].strip().split(';')
        city_zip_index = dict()
        for line in lines[1:]:
            line_list = line.strip().split(';')
            city = line_list[1]
            zipcode = int(line_list[0])
            latitude = float(line_list[3])
            longitude = float(line_list[4])
            if city not in city_zip_index:
                city_zip_index[city] = {zipcode: f'{round(latitude, 4)},{round(longitude, 4)}'}
                city_zip_index[city] = {zipcode: f'{"%.4f"%latitude},{"%.4f"%longitude}'}
            else:
                city_zip_index[city][zipcode] = f'{"%.4f"%latitude},{"%.4f"%longitude}'
        return city_zip_index

    def scrape(self): #STEP 2
        '''Takes the given drug list, and attempts to scrape drug prices from GoodRx.'''
        for drug in self.drug_list:
            #print(drug)
            self.drug_zip_store_price[drug] = dict() #Add empty drug record
            drug_token = drug.split(' ')[0].lower()
            url = f'{self.url_base}{drug_token}' #Construct URL
            print(url)
            response = requests.get(url, headers=self.headers) #Make request - TEST SMALL AT FIRST !!! 
            #print('resp: ', response)
            tree = html.fromstring(response.content)

            #Check for valid page before attempting a scrape
            check1 = tree.xpath('//div[@class="span12"]/h2/@title="HTTP Error 404"') #Does the drug's page exist?
            if check1 != True:
                # print(f'check1 passed {drug_token}')
                                        
                check2 = tree.xpath('//div[@class="title-S8gEl"]/text()') #Does the drug's page potentially have prices?
                if check2 == []:
                    # print(f'check2 passed {drug_token}')
                                        
                    check3 = tree.xpath('//div[@class="title-fSLC7"]/text()') #Is the drug's page not for a drug administered by provider?
                    if check3 == []:
                        # print(f'check3 passed {drug_token}')
#                         print(f'drug is scrapable: {drug_token}') 
                        
                        check4 = tree.xpath('//h1[@class="classTitle-3_hOt"]/text()')
                        if check4 == []:
                            # print(f'check4 passed {drug_token}')
                                                        
                            #proceed to scrape
                            self.scrape_tree(tree, drug, drug_token)

    def scrape_tree(self, tree, drug, drug_token): #called by scrape()
        '''For a given xpath tree, scrape the desired drug price attributes.
        tree - html tree
        drug - drug from wikidata
        drug_token - the first token from drug'''
        scripts = tree.xpath('//script/text()')
        print('drug candidate: ', drug_token)

        #Desired node looks like window.__state__=dict()
        for s in scripts:
            s_list = s.split('=')
            if s_list[0] == 'window.__state__':
                drug_node = ''.join(s_list[1:])
                break
        
        #Extract the drug_id
        drug_node_d = drug_node[:1500] #Assumes the drug_id is within first 1500 chars... 
        pattern = r"currentChoice([^,]+)"
        res = re.search(pattern, drug_node_d)
        if res:
            drug_id_raw = res.group()
            drug_id = drug_id_raw.split(':')[-1]
            self.grx_drug_map[drug] = drug_id
        time.sleep(random.randint(1, 10) / 10)                          

        #INNER LOOP : For each drug_id>zip_code, get stores and their prices
        for z in [90026]: #TODO: Fixed at 1 zipcode to start
            self.drug_zip_store_price[drug][z] = dict() #ADD ZIP

            #Get latitude and longitude
            zip_lat_lng = self.city_zip_index['Los Angeles'][z] #TODO: Fixed at Los Angeles
            quantity = tree.xpath('//span[@class="labelText-34ve5"]/text()')
            if quantity == []: quantity = 30
            else: quantity = quantity[0].split(' ')[0]
            url_full = f'{self.url_base_api}{drug_id}/prices?backend_drive_thru_flag_desktop_override=show_flag&location={zip_lat_lng}&location_type=LAT_LNG&quantity={quantity}'
            response = requests.get(url_full, headers=headers)
            drug_zip_resp = response.json()

            #Select the stores for this drug>zip
            drug_zip_stores = drug_zip_resp['results']

            for store in drug_zip_stores:
                store_name = store['pharmacy']['name']
                store_type = store['pharmacy']['type']
                self.drug_zip_store_price[drug][z][store_name] = dict() #ADD STORE

                #Get prices for the store
                store_prices = store['prices']
                for p in store_prices:
                    price_type = p['type']
                    price = p['price']

                    #Construct link depending on if its coupon or not
                    if price_type == 'COUPON':
                        coup_url = p['url']
                        shop_link = f'https://www.goodrx.com{coup_url}&price_tab=coupons&'
                    else: shop_link = p['url']

                    #Add features to drug_store_prices
                    self.drug_zip_store_price[drug][z][store_name][price_type] = {'price': price, 'link': shop_link}
            time.sleep(random.randint(1, 10) / 10)

    def output_result(self): #STEP 3
        '''Write the result of scraper to json file'''
        # output_file = 'grx_drug_zip_store_price.json'
        output_file = 'grx_drug_zip_store_price2.json'
        data = json.dumps(self.drug_zip_store_price, indent=1)
        fd = open(output_file, "w")
        fd.write(data)
        fd.close() 

#PARAMETERS
headers = {
    'authority': 'www.goodrx.com',
    'grx-api-version': '2017-11-17',
    'accept': 'application/json, text/plain, */*',
    'goodrx-profile-id': '87e94989-bf5c-43ec-b00a-e070527a2d62',
    'goodrx-user-id': '4c752527dc854963a021a0a105ab2818',
    'grx-api-client-id': '8f9b4435-0377-46d7-a898-e1b656649408',
    'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/85.0.4183.121 Safari/537.36',
    'x-grx-internal-user': 'true',
    'sec-fetch-site': 'same-origin',
    'sec-fetch-mode': 'cors',
    'sec-fetch-dest': 'empty',
    'referer': 'https://www.goodrx.com/',
    'accept-language': 'en-US,en;q=0.9,la;q=0.8',
}
url_base = 'https://www.goodrx.com/'
url_base_api = 'https://www.goodrx.com/api/v4/drugs/'
zip_codes_file = 'opendata_zipcodes.csv'

#DRIVER
# drugName_samp = get_drugNames(n_drugNames=5) #Sample
drugName_samp = get_drugNames() #No sample
# drugName_samp = ['Forane', 'Carnexiv', 'amoxicillin']
# drugName_samp = ['insulin']
scraper = DrugPriceScraper(drugName_samp, zip_codes_file, url_base, url_base_api, headers) #STEP 1
scraper.scrape() #STEP 2
scraper.output_result() #STEP 3