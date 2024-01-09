import requests
from bs4 import BeautifulSoup
import matplotlib.pyplot as plt
import pandas as pd


class ScrappingReasultsFrom:
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
        soup = BeautifulSoup(requests.get(self.url).content, "html.parser")

        # remove all <sup> tags, that could be added to the numbers
        for sup in soup.select("sup"):
            sup.extract()

        # create list of all tables (dataframes):
        df_tables = pd.read_html(str(soup), attrs={"class": "wikitable"})

        # extract riders standings table:
        df_riders = pd.DataFrame()
        for _ in df_tables:
            if "Bike" in _.columns:
                df_riders = _
                break

        # make sure riders standings table was found:
        if df_riders.empty:
            print(f"\nNo riders standings found!\n")
            raise ValueError

        return df_riders

    # scrapping teams standings #TODO
    def teams(self):
        ...

    # scrapping constructors standings #TODO
    # def constructors(self):
    #     ...


# class Weather: #TODO
#     ...


class Cleaning:
    def __new__(cls, df: pd.DataFrame) -> pd.DataFrame:
        # removing columns:
        df.drop(columns=["Bike", "Team", "Pts"], inplace=True)

        # removing last two rows:
        df.drop(df.tail(2).index, inplace=True)

        # converting status strings to 0:
        df.replace(["Ret", "DNS", "NC", "WD", "DNQ"], 0, inplace=True)

        # converting NaN (empty cells) to 0:
        df.fillna(0, inplace=True)

        return df


class Plotting:
    def __init__(self, df: pd.DataFrame):
        self.df = df
        # df.plot()
        # plt.show()


def main():
    results = ScrappingReasultsFrom(2023).riders()
    Cleaning(results)

    print()
    print(results)  # results.to_string() to show all

    # Plotting(results.riders()) #TODO


if __name__ == "__main__":
    main()
