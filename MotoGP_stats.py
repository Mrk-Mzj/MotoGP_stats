from io import StringIO
import json
import sys
from bs4 import BeautifulSoup
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np
import pandas as pd
import requests
from requests.exceptions import ConnectionError, HTTPError, RequestException


class Cleaning:
    def __new__(cls, df: pd.DataFrame) -> pd.DataFrame:
        #
        # removing columns
        columns_to_remove = ["Bike", "CRT", "Open", "Pos.", "Pos", "Pts", "Team"]
        for column in columns_to_remove:
            if column in df.columns:
                df.drop(columns=column, inplace=True)

        # removing last two rows
        df.drop(df.tail(2).index, inplace=True)

        # marking unfinished races as NaN.
        # side effect: this converts df to float.
        df.replace(
            [
                "C",
                "DNA",
                "DNP",
                "DNPQ",
                "DNQ",
                "DNS",
                "DSQ",
                "EX",
                "NC",
                "Ret",
                "Ret†",
                "WD",
            ],
            np.nan,
            inplace=True,
        )

        # setting index to rider name
        df.set_index("Rider", inplace=True)

        # converting columns from object to numeric:
        df[df.columns] = df[df.columns].apply(pd.to_numeric)

        return df


class GatheringReasultsFrom:
    def __init__(self, YEAR: int):
        self.YEAR = YEAR
        self.CACHE_PATH = "cache/"

        if self.YEAR < 2012:
            self.WIKI_URL = f"https://en.wikipedia.org/wiki/{self.YEAR}_Grand_Prix_motorcycle_racing_season"
        else:
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
            response.raise_for_status()  # will rise HTTPError if != 200

        except ConnectionError:
            raise ConnectionError("\n Internet connection Error!")
        except HTTPError as e:
            raise HTTPError(f"\n HTTP error occurred: {e}")
        except RequestException as e:
            raise RequestException(f"\n Error during request to {self.WIKI_URL}: {e}")

        # creating Soup object
        soup = BeautifulSoup(response.content, "html.parser")

        # remove all <sup> tags, that could be added to the numbers
        for sup in soup.select("sup"):
            sup.extract()

        # create list of all tables (dataframes):
        try:
            df_tables = pd.read_html(StringIO(str(soup)), attrs={"class": "wikitable"})
        except ValueError:  # 2003 wiki table is corrupted
            sys.exit(f"\n Error reading table!")

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

    #
    # gathering weather data
    def weather(self) -> dict:
        if self.YEAR < 2005:
            print(
                "\n No weather data available before 2005.\n"
            )  # TODO: check the weather plotting if we skip all steps below

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
                response = requests.get(url)
                response.raise_for_status()  # will rise HTTPError if != 200
                data = response.json()
                return data

            except ConnectionError:
                raise ConnectionError("\n Internet connection Error!")
            except HTTPError as e:
                raise HTTPError(
                    f"\n Error connecting to {url} \n code: {response.status_code}"
                )
            except json.JSONDecodeError:
                raise ValueError(f"\n Invalid JSON response from url {url}")
            except RequestException as e:
                raise RequestException(f"\n Error during request to {url}: {e}")

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
        plt.figure(figsize=(1000 / 72, 600 / 72), layout="tight")

        # first plot:
        # riders standings on top
        plt.subplot(2, 1, 1)

        # plot riders standings
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
        # expand margins for riders names
        plt.margins(x=0.1)
        plt.title("Riders' standings", fontsize=15, pad=10)
        plt.legend(fontsize=9)
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

        # second plot:
        # weather detail on bottom

        x = np.array([1, 2, 3, 4])
        y = np.array([10, 30, 15, 40])

        plt.subplot(2, 1, 2)
        plt.plot(x, y)

        plt.margins(x=0.1)
        plt.title("Weather", fontsize=15, pad=10)
        plt.legend(fontsize=9)
        plt.xticks(rotation=30, fontsize=9)
        plt.ylabel("Temperature")
        plt.yticks(fontsize=9)
        plt.grid(axis="x", alpha=0.3)

        plt.show()


def main():
    YEAR = 2022  # MotoGP era: 2002-current

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
