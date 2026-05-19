#!/usr/bin/env python3
# vim: et ts=8 sts=4 sw=4

import sys, os, itertools
import requests

NECESSE_CONSUMABLES_PAGE = "https://necessewiki.com/Consumables"

def get(url):
    print("Fetching URL:", url)
    return requests.get(NECESSE_CONSUMABLES_PAGE)

def main():
    consumables_page = get(NECESSE_CONSUMABLES_PAGE)
    print(consumables_page)

if __name__ == "__main__":
    main()

