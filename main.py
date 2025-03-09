from bs4 import BeautifulSoup
from duckduckgo_search import DDGS
import requests
import time
import json
import os
import re

URL = "https://darksouls3.wiki.fextralife.com/Bosses"
BASE_URL = "https://darksouls3.wiki.fextralife.com/"
BOSS_PAGE_REL_PATH = "bosses/"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
}
RATE_LIMIT_SLEEP = 5 # in seconds

# Define the special characters we need to escape in Markdown
ESCAPE_MAP = {
    '\\': r'\\',  # Backslash must be first!
    '|': r'\|',
    '*': r'\*', 
    '_': r'\_',  
    '#': r'\#', 
    '+': r'\+',  
    '-': r'\-',  
    '<': r'\<', 
    '>': r'\>',  
    '[': r'\[',  
    ']': r'\]',  
    '!': r'\!',  
    "'": r"\'",  
    '"': r'\"', 
    '~': r'\~', 
    '(': r'\(', 
    ')': r'\)',  
}

def escape_markdown(text):
    for char, escape in ESCAPE_MAP.items():
        # Replace the character in the text with its escaped version
        text = text.replace(char, escape)
    return text


def scrape_boss_table():
    response = requests.get(URL, headers=HEADERS)
    soup = BeautifulSoup(response.text, "html.parser")

    # Find the boss table, it's the first one
    table = soup.find("table", class_="wiki_table")
    rows = table.find_all("tr")

    info_dicts = []

    # Scrape the whole boss table
    # Skip the first row, it's the head of the table
    for row in rows[1:]:
        # We can get the image and the subpage url from the first cell
        first_cell = row.find("td")
        img_url = BASE_URL + first_cell.find("img")["src"]
        subpage_url = BASE_URL + first_cell.find("a")["href"]

        cells = row.find_all("td")

        # solve issues with spacing
        for cell in cells:
            for p in cell.find_all("p"):
                p.replace_with(p.get_text() + " ")
            for br in cell.find_all("br"):
                br.replace_with(br.get_text() + " ")

        # We trust that nothing crazy is in this text...
        values = [cell.text.strip() for cell in cells]

        # Indices are hard-coded
        info_dict = {
            "img_url": img_url,
            "subpage_url": subpage_url,
            "boss_name": values[0],
            "location": values[1],
            "weakness": values[3],
            "resistance": values[4],
            "immunity": values[5],
        }
        info_dicts.append(info_dict)
    return info_dicts

def scrape_boss_description(subpage_url: str):
    response = requests.get(subpage_url, headers=HEADERS)
    soup = BeautifulSoup(response.text, "html.parser")

    # Find the bounding box
    block = soup.find("div", id="wiki-content-block")
    # This infobox is first and sometimes causes problems, remove it
    block.find("div", id="infobox").decompose()

    # Finds the first text section, it contains an intro to the boss
    stop_tag = block.find("p", string="\xa0")  # "\xa0" stands for &nbsp;
    paragraphs = stop_tag.find_previous_siblings("p")
    paragraphs.reverse()

    info = str()
    for p in paragraphs:
        info += escape_markdown(p.text.strip()) + "\n<br>\n\n"
    return info

def get_additional_info_DDGS(boss_name: str):
    results = dict()

    # Check if the file exists
    cache_filepath = "ddgs_cache/" + boss_name.replace(" ", "-") + ".json"
    if os.path.exists(cache_filepath):
        # If the file exists, read its content
        with open(cache_filepath, "r") as file:
            print(f"Reading {boss_name} additional info from cache: {cache_filepath}")
            results = json.load(file)
        return results
    
    print(f"No cache found for {boss_name}. Generating...")
  
     # Find the info about difficulty and strategies online with DuckDuckGo
    results["difficulty"] = DDGS().text(
        keywords=f"Dark Souls 3 +{boss_name} +difficulty", max_results=3
    )
    for idx, result in enumerate(results["difficulty"]):
        results["difficulty"][idx]["title"] = escape_markdown(result["title"])
    
    time.sleep(RATE_LIMIT_SLEEP)  # Prevent rate limiting

    results["strategy"] = DDGS().text(
        keywords=f"Dark Souls 3 +{boss_name} +strategy", max_results=3
    )
    for idx, result in enumerate(results["strategy"]):
        results["strategy"][idx]["title"] = escape_markdown(result["title"])

     # Save the generated content to the file
    with open(cache_filepath, "w") as file:
        json.dump(results, file)
    print("Generated and saved in cache.")
    
    return results


def generate_subpage_markdown(boss_info: dict, filepath: str):
    boss_name = boss_info["boss_name"]
    subpage_url = boss_info["subpage_url"]

    print(f"Generating subpage for {boss_name}...")

    description = scrape_boss_description(subpage_url)

    results = get_additional_info_DDGS(boss_name)

    with open(filepath, "w", encoding="utf-8") as md_file:
        img_markdown = f'<img src="{boss_info["img_url"]}" width="150" height="150" />'
        # Write the header for Jekyll
        md_file.write("---\nlayout: default\n---\n")

        md_file.write(f"# *{boss_name}*\n")
        md_file.write(f"{img_markdown}\n")
        md_file.write("\n## Basic information:\n")
        md_file.write(description)
        md_file.write(f"\n[[More information on this site...]]({subpage_url})\n")

        md_file.write(f"\n## Search results - Dark Souls 3 {boss_name} difficulty:\n")
        for result in results["difficulty"]:
            md_file.write(f"- {result['title']} [(link)]({result['href']})\n")

        md_file.write(f"\n## Search results - Dark Souls 3 {boss_name} strategy:\n")
        for result in results["strategy"]:
            md_file.write(f"- {result['title']} [(link)]({result['href']})\n")


def generate_main_md():
    info_dicts = scrape_boss_table()
    # Write the data in a markdown file
    with open("boss_list.markdown", "w", encoding="utf-8") as md_file:
        # Write the header for Jekyll
        md_file.write("---\nlayout: default\ntitle: List\n---\n")
        md_file.write("# Dark Souls III Boss List\n\n")

        print("Generating boss list page...")
        for info in info_dicts:
            subpage_path = BOSS_PAGE_REL_PATH + info["boss_name"].replace(" ", "-")
            subpage_filepath = subpage_path + ".markdown"
            generate_subpage_markdown(info, subpage_filepath)

            # As HTML because we need to ensure proper size
            img_markdown = f'<img src="{info["img_url"]}" width="150" height="150" />'
            md_file.write("---\n")
            md_file.write(f"## *{info['boss_name']}* ")
            md_file.write(f"[[more info]]({{{{ site.baseurl }}}}/{subpage_path})\n")
            md_file.write(f"{img_markdown}\n")
            md_file.write(f"- **Location**: {info['location']}\n")
            md_file.write(f"- **Weakness**: {info['weakness']}\n")
            md_file.write(f"- **Resistance**: {info['resistance']}\n")
            md_file.write(f"- **Immunity**: {info['immunity']}\n")
            md_file.write("\n<br>\n\n")

        print("List generation complete!")


def main():
    generate_main_md()


if __name__ == "__main__":
    main()
