import httpx
import asyncio
from bs4 import BeautifulSoup
import logging
import dotenv
import datetime
import json
import urllib3
import random
from time import sleep 
from random_user_agent.user_agent import UserAgent
from random_user_agent.params import SoftwareName, HardwareType
from fp.fp import FreeProxy

logging.basicConfig(filename='Scan.log', filemode='a', format='%(asctime)s - %(name)s - %(message)s',
                    level=logging.DEBUG)

software_names = [SoftwareName.CHROME.value]
hardware_type = [HardwareType.MOBILE__PHONE]
user_agent_rotator = UserAgent(software_names=software_names, hardware_type=hardware_type)
CONFIG = dotenv.dotenv_values()

proxyObject = FreeProxy(country_id=[CONFIG['LOCATION']], rand=True)

STOCK = []
items = []
stock_q = asyncio.Queue()


def discord_webhook(product_item):
    
    #All params at https://discordapp.com/developers/docs/resources/channel#embed-object

    data = {
        "username" : "Crystal's Sweat Shop",
        "avatar_url" : "https://i.kym-cdn.com/entries/icons/facebook/000/034/065/terio.jpg"
    }
    if product_item == 'initial':
        data["embeds"] = [
            {
                "title" : "Sweat Shop Monitor Launched"
            }
        ]
    else:
        data["embeds"] = [
            {
              "title": product_item[0],
              "url":  f'https://www.scan.co.uk{product_item[3]}',
              "fields":[
              {
                "name": "In-Stock",
                "value": product_item[1],
                "inline": "true"
              },
              {
                "name": "Price",
                "value": f'£{product_item[2]}',
                "inline": "true"
              }],
              "thumbnail": {
                "url": "https://media.glassdoor.com/sqll/1582783/scan-computers-international-squarelogo-1529493867530.png"
              },
              "footer": {
                "text": "Crystal's Beta Monitors",
                "icon_url": "https://i.kym-cdn.com/entries/icons/facebook/000/034/065/terio.jpg"
              }
            }
          ]

    result = httpx.post(CONFIG['WEBHOOK'], json = data)

    try:
        result.raise_for_status()
    except requests.exceptions.HTTPError as err:
        print(err)
        logging.error(msg=err)
    else:
        print("Payload delivered successfully, code {}.".format(result.status_code))
        logging.info("Payload delivered successfully, code {}.".format(result.status_code))


def remove_duplicates(mylist):

    return [list(t) for t in set(tuple(element) for element in mylist)]


def extractor(products):

    global items
    for product in products:
        item = [product.find('span', {'class': 'description'}).text, #title
            product.find('span', {'class': 'linkNo'}).text,   #Item ID
            product.find('span',{'class': 'wishlistheart'})['data-price'],  #Price
            product.find('a')['href']]     #Link
        if not item[2] == "":
            items.append(item)
    items = remove_duplicates(items)


def checkExist(item):

    for product in STOCK:
        if product == item:
            return True
    return False


async def monitorSession(headers, proxy):

    global STOCK

    print('New monitor session launched')
    url = 'https://www.scan.co.uk/search?q=nvidia'

    while True:
        try:
            while not stock_q.empty(): 
                STOCK = await stock_q.get()
                
            async with httpx.AsyncClient(proxies=proxy, verify=False) as client:
                html = await client.get(url=url, headers=headers, timeout=15)
                soup = BeautifulSoup(html.text, 'html.parser')
                extractor(soup.find_all('li',  {'class': 'product'})) 
                print("Async Request completed") 

            for item in items:
                if not  checkExist(item):
                    discord_webhook(item)
                    await asyncio.sleep(random.uniform(0, 0.5)) 

            await stock_q.put(items)
            await asyncio.sleep(float(CONFIG['MONITOR_DELAY']))

        except Exception as e:
            print(f"Exception found '{e}' - Rotating proxy and user-agent")
            logging.error(e)
            headers = {'User-Agent': user_agent_rotator.get_random_user_agent()}
            if CONFIG['PROXY'] == "":
                proxy = {"http": proxyObject.get()}
            else:
                proxy_no = 0 if proxy_no == (len(proxy_list) - 1) else proxy_no + 1
                proxy = {"http": f"http://{proxy_list[proxy_no]}"}


def launchMonitor():

    print('STARTING MONITOR')
    logging.info(msg='Successfully started monitor')
    discord_webhook('initial')
    proxy_list = CONFIG['PROXY'].split('%')
    proxy_no = 0
    loop = asyncio.get_event_loop()

    try:
        for x in range(int(CONFIG['ASYNC_SESSIONS'])):

            proxy = {"http": proxyObject.get()} if proxy_list[0] == "" else {"http": f"http://{proxy_list[x]}"}
            headers = {'User-Agent': user_agent_rotator.get_random_user_agent()}
            loop.create_task(monitorSession(headers, proxy))

        loop.run_forever()

    except Exception as e:
        print(f"Exception found '{e}' - problem with async monitors")
        logging.error(e)
        loop.close()


if __name__ == '__main__':
    urllib3.disable_warnings()
    launchMonitor()
