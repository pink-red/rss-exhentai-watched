from typing import List

from dataclasses import dataclass
from datetime import datetime
import json
from functools import partial

from bs4 import BeautifulSoup
from flask import Flask, make_response
from lxml import etree
from lxml.builder import E
import requests
from tzlocal import get_localzone


@dataclass
class Gallery:
    title: str
    thumbnail_url: str
    pub_date: datetime
    link: str


def parse_compact(soup: BeautifulSoup) -> List[Gallery]:
    # Adopted from https://github.com/DIYgod/RSSHub/blob/8c2039902e769f140c25729a2dc6b28b9852c950/lib/routes/ehentai/ehapi.js#L26

    galleries_table = soup.select_one("table.itg")
    galleries_rows = galleries_table.select("tr")[1:]  # skip table header

    galleries = []
    for row in galleries_rows:
        a = row.select_one("td.glname a")
        title = a.select_one("div.glink").text
        link = a["href"]

        img = row.select_one("td div.glthumb div img")
        thumbnail_url = img["data-src"] if img.has_attr("data-src") else img["src"]

        pub_date = row.select_one('div[id^="posted_"]').text
        pub_date = datetime.strptime(pub_date, "%Y-%m-%d %H:%M")
        pub_date = pub_date.replace(tzinfo=get_localzone())

        galleries.append(
            Gallery(
                title=title,
                thumbnail_url=thumbnail_url,
                pub_date=pub_date,
                link=link,
            )
        )

    return galleries


def parse_thumbnail(soup: BeautifulSoup) -> List[Gallery]:
    galleries_grid = soup.select_one("div.itg")
    galleries_divs = galleries_grid.select(".gl1t")

    galleries = []
    for div in galleries_divs:
        title_link = div.select_one("a")
        title = title_link.text
        link = title_link["href"]

        thumbnail_url = div.select_one("img")["src"]

        pub_date = div.select_one('div[id^="posted_"]').text
        pub_date = datetime.strptime(pub_date, "%Y-%m-%d %H:%M")
        pub_date = pub_date.replace(tzinfo=get_localzone())

        galleries.append(
            Gallery(
                title=title,
                thumbnail_url=thumbnail_url,
                pub_date=pub_date,
                link=link,
            )
        )

    return galleries


def parse_extended(soup: BeautifulSoup) -> List[Gallery]:
    galleries_table = soup.select_one("table.itg")
    galleries_rows = galleries_table.find_all("tr", recursive=False)

    galleries = []
    for row in galleries_rows:
        link = row.select_one(".gl1e a")["href"]
        title = row.select_one(".glink").text

        thumbnail_url = row.select_one(".gl1e img")["src"]

        pub_date = row.select_one('div[id^="posted_"]').text
        pub_date = datetime.strptime(pub_date, "%Y-%m-%d %H:%M")
        pub_date = pub_date.replace(tzinfo=get_localzone())

        galleries.append(
            Gallery(
                title=title,
                thumbnail_url=thumbnail_url,
                pub_date=pub_date,
                link=link,
            )
        )

    return galleries


def parse(html: str) -> List[Gallery]:
    soup = BeautifulSoup(html, "lxml")

    # ExHentai seems to store the display mode on the server, for each account.
    # This means that if one changes the display mode for their account in the
    # browser, it will affect this script as well.
    #
    # Changing the mode from the script would interfere with normal browsing.
    #
    # So, the best option I see is to implement parsing for each mode.
    display_mode = soup.select_one("#dms option:checked").text.strip()
    parsers_by_mode = {
        "Compact": parse_compact,
        "Minimal": parse_compact,
        "Minimal+": parse_compact,
        "Extended": parse_extended,
        "Thumbnail": parse_thumbnail,
    }
    parser = parsers_by_mode[display_mode]

    return parser(soup)


def make_rss(galleries: List[Gallery]) -> str:
    entries = [
        E(
            "entry",
            E("title", g.title),
            E("link", {"href": g.link}),
            E("updated", g.pub_date.isoformat()),
            E("id", g.link),
            E(
                "content",
                {
                    "type": "html",
                    "src": g.link,
                },
                etree.CDATA(
                    etree.tostring(
                        E("img", {"src": g.thumbnail_url, "alt": "thumbnail"}),
                    ),
                ),
            ),
        )
        for g in galleries
    ]

    res = etree.tostring(
        E(
            "feed",
            {
                "xmlns": "http://www.w3.org/2005/Atom",
            },
            E("title", "ExHentai Watched"),
            E("link", {"href": "https://exhentai.org/watched"}),
            E("id", "https://exhentai.org/watched"),
            E("author", E("name", "ExHentai RSS Generator")),
            *entries,
        ),
        pretty_print=True,
        xml_declaration=True,
        encoding="UTF-8",
    ).decode()

    return res


app = Flask(__name__)


@app.route("/")
def route_root():
    with open("config.json") as f:
        config = json.load(f)

    r = requests.get(
        "https://exhentai.org/watched",
        headers={
            "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:98.0) Gecko/20100101 Firefox/98.0",
        },
        cookies=config["cookies"],
    )
    html = r.text
    galleries = parse(html)

    rss = make_rss(galleries)
    response = make_response(rss)
    response.headers["Content-Type"] = "application/xml; charset=utf-8"
    return response
