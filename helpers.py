import requests
import pandas as pd
from bs4 import BeautifulSoup


class ScrappingYear:
    def __init__(self, year: int):
        self.year = year
        self.url = f"https://en.wikipedia.org/wiki/{year}_MotoGP_World_Championship"

    def riders(self) -> pd.DataFrame:
        df_tables = pd.read_html(self.url, attrs={"class": "wikitable"}, flavor="bs4")

        for _ in df_tables:
            if "Bike" in _.columns:
                df_riders = _
                break

        return df_riders

    # def constructors(self):
    #     ...


def main():
    standings = ScrappingYear(2024)
    print(standings.riders())


if __name__ == "__main__":
    main()
