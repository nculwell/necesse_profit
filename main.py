#!/usr/bin/env python3
# vim: et ts=8 sts=4 sw=4

import re
import json
import sys, os, itertools
import requests
from bs4 import BeautifulSoup
from dataclasses import dataclass, field, asdict
from typing import Optional

NECESSE_BASE_URL = "https://necessewiki.com"
NECESSE_CONSUMABLES_PAGE = NECESSE_BASE_URL + "/Consumables"

FOOD_SECTIONS = ["Raw_Food", "Common_Fish", "Fine_Food", "Gourmet_Food"]

class NotFoundError(Exception):
    pass

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
    if response.status_code == 404:
        raise NotFoundError("Page not found: " + url)
    elif response.status_code != 200:
        raise Exception(f"Unable to fetch page ({response.status_code}): {url}")
    with open(path, "w", encoding="utf8") as f:
        f.write(response.text)
    return response.text

@dataclass
class FoodItem:
    name: str
    category: str
    broker_value: Optional[int]
    result_count: Optional[int]
    ingredients: list  # [(ingredient_name, count), ...]

def parse_itemplate(span):
    a = span.find('a')
    if not a:
        return None, None
    name = a.get_text(strip=True)
    m = re.search(r'\((\d+)\)', span.get_text())
    count = int(m.group(1)) if m else 1
    return name, count

def parse_food_page(html):
    soup = BeautifulSoup(html, "html.parser")

    broker_value = None
    for td in soup.find_all('td', class_='infobox-section'):
        if 'Broker value' in td.get_text():
            detail = td.find_next_sibling('td', class_='infobox-detail')
            if detail:
                m = re.match(r'(\d+)', detail.get_text(strip=True))
                if m:
                    broker_value = int(m.group(1))
            break

    result_count = None
    ingredients = []
    for table in soup.find_all('table', class_='wikitable'):
        for row in table.find_all('tr')[1:]:
            cells = row.find_all('td')
            if len(cells) < 2:
                continue
            # mw-selflink in the Result cell means this item is what's being crafted
            if not cells[0].find(class_='mw-selflink'):
                continue
            result_span = cells[0].find('span', class_='itemplate')
            if result_span:
                _, result_count = parse_itemplate(result_span)
            for ing_span in cells[1].find_all('span', class_='itemplate'):
                name, count = parse_itemplate(ing_span)
                if name:
                    ingredients.append({"name": name, "count": count})
            break

    return broker_value, result_count, ingredients

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

KNOWN_BROKER_VALUES = {
    "Any Common Fish": 12,  # all 7 common fish share this value
}

def analyze_profitability(items):
    broker = {item.name: item.broker_value for item in items if item.broker_value is not None}
    broker.update(KNOWN_BROKER_VALUES)

    recipes = [item for item in items if item.ingredients]

    out = []

    def row(label, count, per_unit, total):
        count_s  = str(count)  if count  is not None else "?"
        per_s    = str(per_unit) if per_unit is not None else "?"
        total_s  = str(total)  if total  is not None else "?"
        return f"  {label:<26}  {count_s:>5}  {per_s:>9}  {total_s:>8}"

    summary = []  # (name, category, cost, result_value, profit, pct) — None cost/profit if incomplete

    for item in recipes:
        out.append(f"\n{'─' * 60}")
        out.append(f"{item.name}  [{item.category}]  →  broker value: {item.broker_value}")
        out.append(row("Ingredient", "Count", "Broker/ea", "Total"))
        out.append("  " + "─" * 56)

        total_cost = 0
        complete = True
        for ing in item.ingredients:
            name, count = ing["name"], ing["count"]
            per_unit = broker.get(name)
            if per_unit is None:
                complete = False
                total = None
            else:
                total = per_unit * count
                total_cost += total
            out.append(row(name, count, per_unit, total))

        out.append("  " + "─" * 56)
        if complete:
            profit = item.broker_value - total_cost
            pct = profit / total_cost * 100 if total_cost else float("inf")
            out.append(row("Ingredients cost", "", "", total_cost))
            out.append(row("Result value", "", "", item.broker_value))
            out.append(row(f"Profit  ({pct:+.0f}%)", "", "", f"{profit:+d}"))
            summary.append((item.name, item.category, total_cost, item.broker_value, profit, pct))
        else:
            out.append(row("Ingredients cost", "", "", "? (incomplete)"))
            summary.append((item.name, item.category, None, item.broker_value, None, None))

    out.append(f"\n{'═' * 60}")
    out.append("SUMMARY  (sorted by profit margin, highest first)")
    out.append(f"{'═' * 60}")
    out.append(f"  {'Name':<26}  {'Category':<15}  {'Cost':>6}  {'Value':>6}  {'Profit':>7}  {'Margin':>7}")
    out.append("  " + "─" * 74)

    complete_rows = [(n, c, co, v, p, pct) for n, c, co, v, p, pct in summary if p is not None]
    incomplete_rows = [(n, c, co, v, p, pct) for n, c, co, v, p, pct in summary if p is None]

    for name, cat, cost, value, profit, pct in sorted(complete_rows, key=lambda r: r[5], reverse=True):
        out.append(f"  {name:<26}  {cat:<15}  {cost:>6}  {value:>6}  {profit:>+7}  {pct:>+6.0f}%")
    for name, cat, cost, value, profit, pct in incomplete_rows:
        out.append(f"  {name:<26}  {cat:<15}  {'?':>6}  {value:>6}  {'?':>7}  {'?':>7}")

    return "\n".join(out)

def main():
    consumables_page = get(NECESSE_CONSUMABLES_PAGE)
    food_links = parse_food_links(consumables_page)
    items = []
    for section, links in food_links.items():
        for link in links:
            name = parse_page_name(link).replace('_', ' ')
            html = get(link)
            broker_value, result_count, ingredients = parse_food_page(html)
            items.append(FoodItem(
                name=name,
                category=section,
                broker_value=broker_value,
                result_count=result_count,
                ingredients=ingredients,
            ))
    with open("output/foods.json", "w", encoding="utf8") as f:
        json.dump([asdict(item) for item in items], f, indent=2)
    print(f"Wrote {len(items)} items to output/foods.json")

    report = analyze_profitability(items)
    with open("output/profitability.txt", "w", encoding="utf8") as f:
        f.write(report + "\n")
    print("Wrote output/profitability.txt")

if __name__ == "__main__":
    main()

