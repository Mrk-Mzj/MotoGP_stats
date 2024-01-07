import requests
import pandas as pd
from bs4 import BeautifulSoup


class ScrappingYear:
    def __init__(self, year: int):
        self.year = year
        self.url = f"https://en.wikipedia.org/wiki/{year}_MotoGP_World_Championship"

        # check URL:
        try:
            response = requests.head(self.url)
            if response.status_code != 200:
                print(f"\nError connecting to: \n{self.url}\n")
                raise ConnectionError

        # check internet connection:
        except requests.exceptions.ConnectionError:
            print("Internet Connection Error!")

    # scrapping riders standings
    def riders(self) -> pd.DataFrame:
        # get list of tables from url:
        df_tables = pd.read_html(self.url, attrs={"class": "wikitable"}, flavor="bs4")

        # look for riders standings table:
        df_riders = pd.DataFrame()
        for _ in df_tables:
            if "Bike" in _.columns:
                df_riders = _
                break

        # check if riders standings table was found:
        if df_riders.empty:
            print(f"\nNo riders standings found!\n")
            raise ValueError

        return df_riders

    # scrapping constructors standings
    # def constructors(self):
    #     ...


def main():
    standings = ScrappingYear(2023)
    print(standings.riders())


if __name__ == "__main__":
    main()
