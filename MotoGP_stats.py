from io import StringIO
import json
import requests
from requests.exceptions import ConnectionError, HTTPError
from urllib.request import urlopen
from urllib.error import URLError
from bs4 import BeautifulSoup
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np
import pandas as pd


class Cleaning:
    def __new__(cls, df: pd.DataFrame) -> pd.DataFrame:
        # removing columns
        df.drop(columns=["Pos.", "Bike", "Team", "Pts"], inplace=True)

        # removing last two rows
        df.drop(df.tail(2).index, inplace=True)

        # marking unfinished races as NaN.
        # side effect: this converts df to float.
        df.replace(["Ret", "DNS", "NC", "WD", "DNQ"], np.nan, inplace=True)

        # setting index to rider name
        df.set_index("Rider", inplace=True)

        # converting columns from object to numeric:
        df[df.columns] = df[df.columns].apply(pd.to_numeric)

        return df


class GatheringReasultsFrom:
    def __init__(self, YEAR: int):
        self.YEAR = YEAR
        self.CACHE_PATH = "cache/"
        self.WIKI_URL = (
            f"https://en.wikipedia.org/wiki/{self.YEAR}_MotoGP_World_Championship"
        )

    # gathering riders standings
    def riders(self) -> pd.DataFrame:
        #
        # gathering from cache
        try:
            df_riders = pd.read_pickle(
                f"{self.CACHE_PATH}{self.YEAR}-MotoGP-riders.pkl"
            )
            print("\n Gathering riders data from cache")
            return df_riders
        except FileNotFoundError:
            pass

        # gathering through scrapping
        print("\n Gathering riders data through scrapping...")
        # checking URL and connection:
        try:
            response = requests.get(self.WIKI_URL)
            if response.status_code != 200:
                raise HTTPError(
                    f"\n Error connecting to {self.WIKI_URL} \n code: {response.status_code}"
                )
        except HTTPError as e:
            raise HTTPError(f"\n HTTP error occurred: {e}")
        except URLError as e:
            raise URLError(f"\n URL error for {self.WIKI_URL}: {e}")
        except ConnectionError:
            raise ConnectionError("\n Internet connection Error!")

        # creating Soup object
        soup = BeautifulSoup(response.content, "html.parser")

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
            print(f"\n No riders standings found!\n")
            raise ValueError

        # saving file to cache
        df_riders.to_pickle(f"{self.CACHE_PATH}{self.YEAR}-MotoGP-riders.pkl")
        return df_riders

    # gathering weather data
    def weather(self) -> dict:
        #
        # gathering from cache
        try:
            with open(f"{self.CACHE_PATH}{self.YEAR}-MotoGP-weather.json", "r") as file:
                races_weather = json.load(file)
                print("\n Gathering weather data from cache")
                return races_weather
        except FileNotFoundError or json.JSONDecodeError:
            pass

        # gathering from API
        # API info: https://github.com/micheleberardi/racingmike_motogp_import
        def fetch_api_data(url):
            try:
                with urlopen(url) as response:
                    data = json.loads(response.read())

                    return data

            except HTTPError as e:
                raise HTTPError(
                    f"\n Error connecting to {url} \n code: {response.status_code}"
                )
            except URLError as e:
                raise URLError(f"\n URL error for {url}: {e}")

            except ConnectionError:
                raise ConnectionError("\n Internet connection Error!")

            except json.JSONDecodeError:
                raise ValueError(f"\n Invalid JSON response from url {url}")

        print("\n Gathering weather data through API. It may take a while...")

        # list of dictionaries - to store race names and weather
        races_weather = {}

        # 1. find Season (year) id
        url = "https://api.motogp.pulselive.com/motogp/v1/results/seasons"
        all_seasons = fetch_api_data(url)

        for item in all_seasons:
            if item["year"] == self.YEAR:
                season_id = item["id"]

        # 2. find right Category (MotoGP) id for a given Season (year)
        url = f"https://api.motogp.pulselive.com/motogp/v1/results/categories?seasonUuid={season_id}"
        all_categories = fetch_api_data(url)

        for item in all_categories:
            if item["name"] == "MotoGP™":
                category_id = item["id"]

        # 3. find Event (race week) id for a given Season (year)
        url = f"https://api.motogp.pulselive.com/motogp/v1/results/events?seasonUuid={season_id}&isFinished=true"
        all_events = fetch_api_data(url)

        for event in all_events:
            # if race week (not alphanum test week)
            if event["short_name"].isalpha():
                event_id = event["id"]
                short_name = event["short_name"]

                url = f"https://api.motogp.pulselive.com/motogp/v1/results/sessions?eventUuid={event_id}&categoryUuid={category_id}"
                all_sessions = fetch_api_data(url)

                # 4. find weather
                for session in all_sessions:
                    if session["type"] == "RAC":  # looking for a race session
                        races_weather.update(
                            {
                                short_name: {
                                    "track_wet": session["condition"]["track"],
                                    "air_temp": session["condition"]["air"],
                                    "humidity": session["condition"]["humidity"],
                                    "ground_temp": session["condition"]["ground"],
                                    "clouds": session["condition"]["weather"],
                                }
                            }
                        )

        # saving file to cache
        with open(f"{self.CACHE_PATH}{self.YEAR}-MotoGP-weather.json", "w") as file:
            json.dump(races_weather, file)

        return races_weather


class Plotting:
    def __new__(cls, df: pd.DataFrame, limit_riders=0, limit_races=0) -> None:
        cls.df = df

        # limit to n riders
        if limit_riders:
            df.drop(index=df.index[limit_riders:], inplace=True)

        # limit to n races
        if limit_races:
            df.drop(columns=df.columns[limit_races:], inplace=True)

        # print clipped dataframe to console
        print(df, "\n")

        # setting plot size in pixels / dpi
        plt.figure(figsize=(900 / 72, 400 / 72))

        # expand margins for riders names
        plt.margins(x=0.12)

        # plot riders standings with matplotlib
        for rider in df.index:
            # plot race results for each driver
            plt.plot(
                df.columns,
                df.loc[rider],
                marker="o",
                ms=11,
                label=rider,
            )

            # add small numbers on each marker
            for x, y in zip(df.columns, df.loc[rider]):
                # skip number when NaN (unfinished race)
                if np.isnan(y):
                    continue

                plt.text(
                    x,
                    y,
                    str(round(y)),
                    size=7,
                    color="white",
                    horizontalalignment="center",
                    verticalalignment="center",
                )

            # add small riders names
            # only when driver finished his first race (if not NaN)
            if not np.isnan(df.loc[rider].iloc[0]):
                plt.text(
                    *np.array((-0.3, df.loc[rider].iloc[0])),  # position x,y
                    str(rider).split()[-1],  # last name
                    size=7,
                    stretch="extra-condensed",
                    horizontalalignment="right",
                )

        plt.title("Riders' standings", fontsize=15, pad=10)
        plt.legend(fontsize=9)
        plt.xlabel("Races")
        plt.xticks(rotation=30, fontsize=9)
        plt.ylabel("Place")
        plt.yticks(fontsize=9)
        plt.grid(axis="x", alpha=0.3)

        # set Y axis to integer values
        ax = plt.gca()
        ax.yaxis.set_major_locator(ticker.MaxNLocator(integer=True))

        # set range, to show values in increments of 1
        ax.set_yticks(range(0, 20))

        ax.invert_yaxis()
        plt.show()


def main():
    YEAR = 2023

    # weather data
    weather = GatheringReasultsFrom(YEAR).weather()
    print("\n", json.dumps(weather))

    # riders standings
    results = GatheringReasultsFrom(YEAR).riders()
    Cleaning(results)
    print()
    Plotting(results, limit_riders=4)


if __name__ == "__main__":
    main()