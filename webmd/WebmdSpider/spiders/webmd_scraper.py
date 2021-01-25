import scrapy
import string
from lxml import html
import caffeine

class WebMdSpider(scrapy.Spider):
    name = 'webmd'
    start_urls = [f'https://www.webmd.com/drugs/2/conditions/{char}' for char in string.ascii_lowercase[:26]]
    # start_urls = ['https://www.webmd.com/drugs/2/conditions/a']


    def parse(self, response):
        #INNER LOOP - for each item on each page
        # print('made this far')
        url_base = 'https://www.webmd.com'
        cond_pages_raw = response.xpath('//ul[@class="drug-list"]/li/a/@href').getall()
        cond_pages = list()
        # # cond_pages = dict()
        #print('type: ', type(cond_pages_raw))
        for idx, page in enumerate(cond_pages_raw):
            #if idx in [0,1,2]: #TODO: Remove later
            #print('page: ', page)
            cond = page.split('/')[-1]
            #print('cond: ', condition)
        
            page_link = page.split(' ')
            base_plus = [url_base + page_link[0]]
            base_plus.extend(page_link[1:])
            cond_page = '%20'.join(base_plus)
            # print('cond_page: ', cond_page)
        
    # #     # cond_pages[cond] = {'webmd_url': cond_page}
            cond_pages.append(cond_page)
        yield from response.follow_all(cond_pages, self.parse_cond_lvl_one, meta={'url_base': 'https://www.webmd.com'})    
        #print('made this far')

    def parse_cond_lvl_one(self, response):
        # print('reached level one')
        # print('meta: ', response.meta['url_base'])
        cond_pad = response.request.url.split('%20')
        cond_list = [cond_pad[0].split('/')[-1]]
        cond_list.extend(cond_pad[1:])
        cond = ' '.join(cond_list)

        # print('cond_pad: ', cond_pad)
        # print('cond_one: ', cond_one)
        # print('cond_list: ', cond_list)
        # print('cond: ', cond)
        #cond
        #print('cond: ', cond)
        start = 0
        window = 2
        k = 50
            
        tbody = response.xpath('//table[@class="drugs-treatments-table"]/tbody')[0]

        indication_type = tbody.xpath('//tr/td/text()').getall()
        name_nreviews = tbody.xpath('//tr/td/a/text()').getall()
        drug_reviews_links = tbody.xpath('//tr/td/a/@href').getall()
        
        if k > (int(len(indication_type) / window)): n_iters = int(len(indication_type) / window)
        else: n_iters = k

        for i in range(n_iters):
            start = i * window
            end = start + window

            i = indication_type[start:end]
            n = name_nreviews[start:end]
            r = drug_reviews_links[start:end]
            drug = i + n + r
            webmd_url = response.meta['url_base'] + drug[4]
            #print(webmd_url)

            # cond_drugs[cond]['treatments'][drug[2]] = {'indication': drug[0],
            #                              'type': drug[1],
            #                              'n_reviews': drug[3],
            #                              'webMd_link': webmd_url}

            yield {
                'condition': cond,
                'treatment': drug[2],
                'condition_url': response.request.url,
                'treatment_url': webmd_url,
                'indication': drug[0],
                'type': drug[1],
                'n_reviews': drug[3],
            }
