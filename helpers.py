from io import StringIO
import requests
from bs4 import BeautifulSoup
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
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

        # converting status strings to 22
        df.replace(["Ret", "DNS", "NC", "WD", "DNQ"], "-1", inplace=True)

        # converting NaN (empty cells) to 22:
        df.fillna("-1", inplace=True)

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

        # print clipped dataframe to console
        print(df, "\n")

        # setting plot size in pixels / dpi
        plt.figure(figsize=(900 / 72, 400 / 72))

        # expand margins for drivers names
        plt.margins(x=0.12)

        # plot drivers standings with matplotlib
        for rider in df.index:
            # plot race results for each driver
            plt.plot(
                df.columns,
                df.loc[rider],
                marker=".",
                ms=17,
                label=rider,
                alpha=0.8,
            )

            # add small tag on each marker
            for x, y in zip(df.columns, df.loc[rider]):
                if int(y) == -1:
                    tag = "X"  # crash / failure / etc.
                else:
                    tag = str(y)

                plt.text(
                    x,
                    y,
                    tag,
                    size=6,
                    # weight="bold",
                    color="white",
                    horizontalalignment="center",
                    verticalalignment="center",
                )

            # add small drivers names
            plt.text(
                *np.array((-0.2, df.loc[rider].iloc[0])),  # position x,y
                str(rider).split()[-1],  # last name
                size=7,
                stretch="extra-condensed",
                horizontalalignment="right",
            )

        # line cutting off the crashed drivers
        line_length = len(df.columns)
        plt.plot([0, line_length], [-0.3, -0.3], color="white", alpha=0.7, linewidth=30)

        plt.title("Riders' standings", fontsize=15, pad=10)
        plt.legend(fontsize=9)
        plt.xlabel("Races")
        plt.xticks(rotation=30, fontsize=9)
        plt.ylabel("Place")
        plt.yticks(fontsize=9)
        plt.grid(alpha=0.2)

        # set Y axis to integer values
        ax = plt.gca()
        ax.yaxis.set_major_locator(ticker.MaxNLocator(integer=True))

        # set range, to show values in increments of 1
        ax.set_yticks(range(0, 20))

        ax.invert_yaxis()
        plt.show()


def main():
    results = ScrappingReasultsFrom(2023).riders()
    Cleaning(results)

    print()
    # print(results.to_json()) # TODO: saving to cache
    Plotting(results, limit_drivers=4)


if __name__ == "__main__":
    main()
