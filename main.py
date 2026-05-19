#!/usr/bin/env python3
# vim: et ts=8 sts=4 sw=4

import sys, os, itertools
import requests
from bs4 import BeautifulSoup

NECESSE_BASE_URL = "https://necessewiki.com"
NECESSE_CONSUMABLES_PAGE = NECESSE_BASE_URL + "/Consumables"

FOOD_SECTIONS = ["Raw_Food", "Common_Fish", "Fine_Food", "Gourmet_Food"]

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
        raise Exception(f"Unable to fetch page ({response.status_code}): {url}")
    with open(path, "w", encoding="utf8") as f:
        f.write(response.text)
    return response.text

def parse_food_links(html):
    soup = BeautifulSoup(html, "html.parser")
    food_links = {}
    for section_id in FOOD_SECTIONS:
        headline = soup.find("span", id=section_id)
        if not headline:
            continue
        h4 = headline.find_parent("h4")
        items_p = h4.find_next_sibling("p")
        links = [
            NECESSE_BASE_URL + a["href"]
            for a in items_p.find_all("a")
            if a.get("href", "").startswith("/") and "action=edit" not in a.get("href", "")
        ]
        food_links[section_id] = links
    return food_links

def main():
    consumables_page = get(NECESSE_CONSUMABLES_PAGE)
    food_links = parse_food_links(consumables_page)
    for section, links in food_links.items():
        print(f"\n{section} ({len(links)} items):")
        for link in links:
            item = parse_page_name(link)
            print(item)
            html = get(link)

if __name__ == "__main__":
    main()

