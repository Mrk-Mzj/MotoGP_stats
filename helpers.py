from io import StringIO
import requests
from bs4 import BeautifulSoup
import matplotlib.pyplot as plt
import numpy as np
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
        df_tables = pd.read_html(StringIO(str(soup)), attrs={"class": "wikitable"})

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
    def teams(self) -> pd.DataFrame:
        ...

    # scrapping constructors standings #TODO
    def constructors(self) -> pd.DataFrame:
        ...


# class Weather: #TODO
#     ...


class Cleaning:
    def __new__(cls, df: pd.DataFrame) -> pd.DataFrame:
        # removing columns
        df.drop(columns=["Pos.", "Bike", "Team", "Pts"], inplace=True)

        # removing last two rows
        df.drop(df.tail(2).index, inplace=True)

        # converting status strings to 0
        df.replace(["Ret", "DNS", "NC", "WD", "DNQ"], 0, inplace=True)

        # converting NaN (empty cells) to 0:
        df.fillna(0, inplace=True)

        # setting index to rider name
        df.set_index("Rider", inplace=True)

        # converting columns from object to numeric:
        df[df.columns] = df[df.columns].apply(pd.to_numeric)

        return df


class Plotting:
    def __new__(cls, df: pd.DataFrame, limit_drivers=0, limit_races=0) -> None:
        cls.df = df

        # limit to n drivers
        if limit_drivers:
            df.drop(index=df.index[limit_drivers:], inplace=True)

        # limit to n races
        if limit_races:
            df.drop(columns=df.columns[limit_races:], inplace=True)

        print(df, "\n")

        # setting plot size in pixels / dpi
        plt.figure(figsize=(900 / 72, 400 / 72))

        # plot drivers with Matplotlib:
        for rider in df.index:
            plt.plot(df.columns, df.loc[rider], marker="o", label=rider)

        # plot drivers - other method:
        # for index, row in df.iterrows():
        #     plt.plot(row, marker="o", label=index)

        plt.title("Riders' standings")
        plt.legend()
        plt.xlabel("Races")
        plt.xticks(rotation=45)
        plt.ylabel("Place")

        # show plot
        plt.show()  # TODO: (1)flip plot upside down, (2)convert 0 to 30 / break


def main():
    results = ScrappingReasultsFrom(2023).riders()
    Cleaning(results)

    print()
    # print(results.to_json()) # TODO: saving to cache
    Plotting(results, limit_drivers=5)


if __name__ == "__main__":
    main()
