from bs4 import BeautifulSoup
from duckduckgo_search import DDGS
import requests
import time

URL = "https://darksouls3.wiki.fextralife.com/Bosses"
BASE_URL = "https://darksouls3.wiki.fextralife.com/"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
}
RATE_LIMIT_SLEEP = 5 # in seconds


def scrape_bosses():
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

def scrape_boss_info(subpage_url: str):
    response = requests.get(subpage_url, headers=HEADERS)
    soup = BeautifulSoup(response.text, "html.parser")

    # Find the bounding box
    block = soup.find("div", id="wiki-content-block")
    # This infobox is first and sometimes causes problems, remove it
    block.find("div", id="infobox").decompose()

    # Finds the first text section, it contains an intro to the boss
    stop_tag = block.find("p", string="\xa0")  # "\xa0" stands for &nbsp;
    info = str()
    paragraphs = stop_tag.find_previous_siblings("p")
    paragraphs.reverse()
    for p in paragraphs:
        info += p.text.strip() + "\n\n"
    return info


def generate_subpage_md(boss_name: str, subpage_url: str):
    print(f"Generating subpage for {boss_name}...")

    info = scrape_boss_info(subpage_url)

    # Find the info about difficulty and strategies online with DuckDuckGo
    results_difficulty = DDGS().text(
        keywords=f"Dark Souls 3 +{boss_name} +difficulty", max_results=3
    )
    time.sleep(RATE_LIMIT_SLEEP)  # Prevent rate limiting
    results_strategy = DDGS().text(
        keywords=f"Dark Souls 3 +{boss_name} +strategy", max_results=3
    )

    rel_path = boss_name.replace(" ", "-")

    with open(rel_path + ".markdown", "w", encoding="utf-8") as md_file:
        # Write the header for Jekyll
        md_file.write("---\nlayout: default\n---\n")

        md_file.write(f"# {boss_name}\n")
        md_file.write("\n## Basic information:\n")
        md_file.write(info)
        md_file.write(f"\n[[More information on this site...]]({subpage_url})\n")

        md_file.write(f"\n## Search results - Dark Souls 3 {boss_name} difficulty:\n")
        for result in results_difficulty:
            md_file.write(f"- {result["title"]} [(link)]({result["href"]})\n")

        md_file.write(f"\n## Search results - Dark Souls 3 {boss_name} strategy:\n")
        for result in results_strategy:
            md_file.write(f"- {result["title"]} [(link)]({result["href"]})\n")

    return rel_path


def generate_main_md():
    info_dicts = scrape_bosses()
    # Write the data in a markdown file
    with open("boss_list.markdown", "w", encoding="utf-8") as md_file:
        # Write the header for Jekyll
        md_file.write("---\nlayout: default\ntitle: List\n---\n")
        md_file.write("# Dark Souls III Boss list\n")

        print("Generating boss list page...")
        for info in info_dicts:
            subpage_path = generate_subpage_md(info["boss_name"], info["subpage_url"])
            # As HTML because we need to ensure proper size
            img_markdown = f'<img src="{info["img_url"]}" width="150" height="150" />'
            md_file.write("\n---\n")
            md_file.write(f"## *{info["boss_name"]}* ")
            md_file.write(f"[[more info]]({{{{ site.baseurl }}}}/{subpage_path})\n")
            md_file.write(f"{img_markdown}\n")
            md_file.write(f"- **Location**: {info["location"]}\n")
            md_file.write(f"- **Weakness**: {info["weakness"]}\n")
            md_file.write(f"- **Resistance**: {info["resistance"]}\n")
            md_file.write(f"- **Immunity**: {info["immunity"]}\n")

        print("List generation complete!")


def main():
    generate_main_md()


if __name__ == "__main__":
    main()
