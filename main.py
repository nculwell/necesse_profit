#!/usr/bin/env python3
# vim: et ts=8 sts=4 sw=4

import sys, os, itertools
import requests

NECESSE_CONSUMABLES_PAGE = "https://necessewiki.com/Consumables"

def parse_page_name(url):
    u = url.split('#')[0]
    u = url.split('?')[0]
    return u.split('/')[-1]

def get(url):
    page_name = parse_page_name(url)
    path = "scraped/" + page_name
    try:
        with open(path, "r", encoding="utf8") as f:
            print("Retrieved from cache:", page_name)
            return f.read()
    except:
        pass # continue from here
    print("Fetching URL:", url)
    response = requests.get(url)
    if response.status_code != 200:
        raise Exception(f"Unable to fetch page ({reponse.status_code}): {url}")
    with open(path, "w", encoding="utf8") as f:
        f.write(response.text)
    return reponse.text

def main():
    consumables_page = get(NECESSE_CONSUMABLES_PAGE)
    print(consumables_page)

if __name__ == "__main__":
    main()

