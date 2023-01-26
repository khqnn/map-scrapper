
#!/usr/bin/env python
# coding: utf-8


from selenium import webdriver
import time
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
import time
import re

import pandas as pd
import json
import os

settings_file = open('settings.json')
settings = json.load(settings_file)

time_wait_business_detail_page = settings['time_wait_business_detail_page']
time_load_maps_list = settings['time_load_maps_list']
time_interval_scroll_down = settings['time_interval_scroll_down']
time_wait_to_open_sublink = settings['time_wait_to_open_sublink']
time_wait_for_home_page = settings['time_wait_for_home_page']
fetch_emails = settings['fetch_emails']


non_searchable_domains = settings['non_searchable_domains']


EMAIL_REGEX = r"""(?:[a-z0-9!#$%&'*+=?^_`{|}~-]+(?:\.[a-z0-9!#$%&'*+=?^_`{|}~-]+)*|"(?:[\x01-\x08\x0b\x0c\x0e-\x1f\x21\x23-\x5b\x5d-\x7f]|\\[\x01-\x09\x0b\x0c\x0e-\x7f])*")@(?:(?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\.)+[a-z0-9](?:[a-z0-9-]*[a-z0-9])?|\[(?:(?:(2(5[0-5]|[0-4][0-9])|1[0-9][0-9]|[1-9]?[0-9]))\.){3}(?:(2(5[0-5]|[0-4][0-9])|1[0-9][0-9]|[1-9]?[0-9])|[a-z0-9-]*[a-z0-9]:(?:[\x01-\x08\x0b\x0c\x0e-\x1f\x21-\x5a\x53-\x7f]|\\[\x01-\x09\x0b\x0c\x0e-\x7f])+)\])"""


def check_for_domain_filteration(domain, filtered_domains):
    if not domain or str(domain) == 'nan':
        return True
    for item in filtered_domains:
        if item in domain:
            return True
    return False


def fetch_business_details(url, driver):
    print(url)
    driver.get(url)
    source = driver.page_source
    soup = BeautifulSoup(source)
    time.sleep(time_wait_business_detail_page)
    business_name, business_type, business_reviews, business_phone, business_address, business_website, business_url = None, None, None, None, None, None, None

    try:
        business_name = str(driver.find_element(
            By.XPATH, "//h1[@class='DUwDvf fontHeadlineLarge']//span[1]").text).strip()

    except:
        print('error in fetching business name...')

    try:
        business_type = str(driver.find_element(
            By.XPATH, "//button[contains(@class, 'DkEaL')]").text).strip()
    except:
        print('error in fetching business type...')

    try:
        business_reviews = str(driver.find_element(
            By.XPATH, "//div[@class='F7nice mmu3tf']//span[1]//span[1]//span[1]").text).strip()

    except:
        print('error in fetching business review...')

    try:
        business_url = str(soup.find_all(
            'a', {'data-tooltip': 'Open website'})[0].get('href'))

    except:
        print('error in fetching business url...')

    try:
        buttons = driver.find_elements(By.XPATH, "//button[@class='CsEnBe']")
        business_phone, business_address, business_website = None, None, None
        for element in buttons:
            aria_label = str(element.get_attribute('aria-label'))
            if "Phone:" in aria_label:
                business_phone = aria_label.strip().replace('Phone:', '').strip()
            elif "Address:" in aria_label:
                business_address = aria_label.strip().replace('Address:', '').strip()

    except:
        print('error in fetching business phonr/address...')

    try:
        hrefs = driver.find_elements(By.XPATH, "//a[@class='CsEnBe']")
        for href in hrefs:
            aria_label = str(href.get_attribute('aria-label'))
            if "Website:" in aria_label:
                business_website = aria_label.strip().replace('Website:', '').strip()

    except:
        print('error in fetching business website...')

    return {
        'business_name': business_name,
        'business_type': business_type,
        'business_reviews': business_reviews,
        'business_phone': business_phone,
        'business_address': business_address,
        'business_website': business_website,
        'business_url': business_url
    }


def fetch_links(url):
    options = webdriver.ChromeOptions()
    options.add_argument('headless')
    driver = webdriver.Chrome("chromedriver", options=options)

    links = []
    driver.get(url)
    time.sleep(time_load_maps_list)

    while True:
        time.sleep(time_interval_scroll_down)
        driver.find_element(
            By.XPATH, "//div[@role='feed']").send_keys(Keys.PAGE_DOWN)
        try:
            check = driver.find_element(By.XPATH, "//span[@class='HlvSq']")
            if str(check.text).strip() == "You've reached the end of the list.":
                break
        except:
            pass

    all_links = driver.find_elements(By.XPATH, "//a[@class='hfpxzc']")
    for link in all_links:
        links.append(link.get_attribute('href'))

    driver.close()
    driver.quit()
    return links


def find_emails(url, driver):
    try:
        driver.get(url)
    except:
        return []

    time.sleep(time_wait_to_open_sublink)
    response = driver.page_source
    emails_list = []
    for re_match in re.finditer(EMAIL_REGEX, response.lower()):
        emails_list.append(re_match.group())

    return emails_list


def fetch_sublinks(domain, driver):
    url = create_link(domain)

    try:
        driver.get(url)
    except:
        return []
    time.sleep(time_wait_for_home_page)
    response = driver.page_source
    soup = BeautifulSoup(response)
    hrefs = soup.find_all('a')

    website_url = re.findall('https://www.*.*', url)[0]
    sublinks = []
    for href in hrefs:

        link = href.get('href')
        if link == None:
            pass
        elif domain in link and len(link) > len(website_url) + 1:
            sublinks.append(link)
        elif len(link) > 1 and 'www' not in link and link[0] == '/':
            sublinks.append(website_url + link)

    return sublinks


def create_link(url):
    if 'https://www/' in url:
        return url
    return 'https://www.' + url


def fetch_all_emails(domain, driver):
    print(domain, check_for_domain_filteration(domain, non_searchable_domains))
    if check_for_domain_filteration(domain, non_searchable_domains):
        return set([])

    url = create_link(domain)

    sublinks = set(fetch_sublinks(domain, driver))

    emails_list = find_emails(url, driver)
    for sublink in sublinks:
        emails = []
        try:
            emails = find_emails(sublink, driver)
        except:
            print('error fetching emails: ', link)
        emails_list.extend(emails)

    return set(emails_list)


def update_state(state):
    query_file = open('query.json')
    query_data = json.load(query_file)
    query_data['state'] = state
    with open("query.json", "w") as outfile:
        outfile.write(json.dumps(query_data))


options = webdriver.ChromeOptions()
options.add_argument('headless')
driver = webdriver.Chrome("chromedriver", options=options)


query_file = open('query.json')
query_data = json.load(query_file)
url = query_data['url']
state = query_data['state']
task_name = query_data['task_name']


data_file_name = 'data.csv'

if not os.path.exists('outputs'):
    os.mkdir('outputs')

outdir = f"outputs/{task_name}"
if not os.path.exists(outdir):
    os.mkdir(outdir)

data_file_path = os.path.join(outdir, data_file_name)

if state == None:
    print('fetching links....')
    links = fetch_links(url)
    print('saving links file....')
    pd.DataFrame(links, columns=['Link']).to_csv(data_file_path, index=False)
    state = 'links_fetched'
    update_state(state)


if state == 'links_fetched':
    data_df = pd.read_csv(data_file_path)
    num_records = len(data_df)
    counter = 0
    print('here')
    for index, data in data_df.iterrows():
        link = data['Link']
        fetched_business_details = False
        fetched_business_emails = False
        try:
            details_fetched = data['fetched_business_details']
            fetched_business_details = details_fetched

            emails_fetched = data['fetched_business_emails']
            fetched_business_emails = emails_fetched
        except:
            pass

        if not fetched_business_details or str(fetched_business_details) == 'nan':
            business_details = fetch_business_details(link, driver)
            business_website = business_details['business_website']
            data_df.at[index, 'fetched_business_details'] = True
            data_df.at[index, 'business_name'] = business_details['business_name']
            data_df.at[index, 'business_type'] = business_details['business_type']
            data_df.at[index,
                       'business_reviews'] = business_details['business_reviews']
            data_df.at[index,
                       'business_phone'] = business_details['business_phone']
            data_df.at[index,
                       'business_address'] = business_details['business_address']
            data_df.at[index,
                       'business_website'] = business_details['business_website']
            data_df.at[index, 'business_url'] = business_details['business_url']
        else:
            business_website = data['business_website']

        if fetch_emails and ( not fetched_business_emails or str(fetched_business_emails) == 'nan'):
            print(business_website)
            emails_list = fetch_all_emails(business_website, driver)
            emails_string = ','.join(emails_list)
            data_df.at[index, 'fetched_business_emails'] = True
            data_df.at[index, 'emails'] = emails_string
        else:
            emails_string = data['emails']

        data_df.to_csv(data_file_path, index=False)

        counter += 1

        print(
            f'Progress:..............................................{(counter/num_records)*100}% completed')

    state = 'completed'
    update_state(state)
