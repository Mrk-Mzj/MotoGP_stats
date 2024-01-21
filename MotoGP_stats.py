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

        # grouping duplicated indexes into one; duplicates occur
        # when rider changes team mid season:

        def choose_one(series):
            # return number, if possible, or NaN
            if not series.dropna().empty:
                return series.dropna().iloc[0]
            else:
                return np.nan


        # variables to temporarily store processed rows and indexes (names). Rows will be converted into dataframe, and names will become indexes.
        riders_list = []
        merged_rows_list = []

        # for unique drivers names (skipping copies)
        for rider in df.index.unique():
            #
            # select row (or rows) of data for a current rider
            current_rows = df.loc[rider]

            # merge those into a single new merged row
            if isinstance(current_rows, pd.DataFrame):
                merged_row = current_rows.apply(choose_one)
            else:
                merged_row = current_rows

            # add this row to list of merged rows
            merged_rows_list.append(merged_row)

            # add rider name to list of riders
            riders_list.append(rider)

        # convert list of merged rows into dataframe; transpose columns to rows
        df_cleaned = pd.concat(merged_rows_list, axis=1).transpose()

        # set indexies to riders names
        df_cleaned.index = riders_list

        # set columns names to original ones
        df_cleaned.columns = df.columns

        return df_cleaned


class GatheringReasultsFrom:
    def __init__(self, year: int):
        self.year = year
        self.CACHE_PATH = "cache/"

        if self.year < 2012:
            self.WIKI_URL = f"https://en.wikipedia.org/wiki/{self.year}_Grand_Prix_motorcycle_racing_season"
        else:
            self.WIKI_URL = (
                f"https://en.wikipedia.org/wiki/{self.year}_MotoGP_World_Championship"
            )

    #
    # gathering historical average of 3 previous seasons
    def history(self, results: pd.DataFrame) -> pd.DataFrame:
        results_hist_A = Cleaning(GatheringReasultsFrom(self.year - 3).riders())
        results_hist_B = Cleaning(GatheringReasultsFrom(self.year - 2).riders())
        results_hist_C = Cleaning(GatheringReasultsFrom(self.year - 1).riders())

        # creating dataframe equivalent to 'results' but full of NaN.
        # To be filled with average results from 3 prev years, where possible
        results_hist_avrg = results.map(lambda x: np.nan)

        # Filling with average results
        for rider in results_hist_avrg.index:
            for track in results_hist_avrg.columns:
                try:
                    # Trying to check if rider was on this track in all 3 previous years
                    extracted_A = results_hist_A.at[rider, track]
                    extracted_B = results_hist_B.at[rider, track]
                    extracted_C = results_hist_C.at[rider, track]

                    # if not NaN found, calculate average result
                    if (
                        pd.notna(extracted_A)
                        and pd.notna(extracted_B)
                        and pd.notna(extracted_C)
                    ):
                        average = np.mean([extracted_A, extracted_B, extracted_C])
                        results_hist_avrg.at[rider, track] = average

                except KeyError:
                    # If a rider or track doesn't exist in one of the previous years (KeyError), just skip it.
                    continue

        return results_hist_avrg

    #
    # gathering riders standings
    def riders(self) -> pd.DataFrame:
        #
        # gathering from cache
        try:
            df_riders = pd.read_pickle(
                f"{self.CACHE_PATH}{self.year}-MotoGP-riders.pkl"
            )
            print(f"Gathering {self.year} riders data from cache")
            return df_riders
        except FileNotFoundError:
            pass

        # gathering through scrapping
        print(f"Gathering {self.year} riders data through scrapping...")

        # checking URL and connection:
        try:
            response = requests.get(self.WIKI_URL)
            response.raise_for_status()  # will rise HTTPError if != 200

        except ConnectionError:
            raise ConnectionError("\nInternet connection Error!")
        except HTTPError as e:
            raise HTTPError(f"\nHTTP error occurred: {e}")
        except RequestException as e:
            raise RequestException(f"\nError during request to {self.WIKI_URL}: {e}")

        # creating Soup object
        soup = BeautifulSoup(response.content, "html.parser")

        # remove all <sup> tags, that could be added to the numbers
        for sup in soup.select("sup"):
            sup.extract()

        # create list of all tables (dataframes):
        try:
            df_tables = pd.read_html(StringIO(str(soup)), attrs={"class": "wikitable"})
        except ValueError:  # 2003 wiki table is corrupted
            sys.exit(f"\nError reading table!")

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

        # saving file to cache
        df_riders.to_pickle(f"{self.CACHE_PATH}{self.year}-MotoGP-riders.pkl")
        return df_riders

    #
    # gathering weather data
    def weather(self) -> dict:
        if self.year < 2005:
            print("\nNo weather data available before 2005.")

        # gathering from cache
        try:
            with open(f"{self.CACHE_PATH}{self.year}-MotoGP-weather.json", "r") as file:
                races_weather = json.load(file)
                print(f"\nGathering {self.year} weather data from cache")
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
                raise ConnectionError("\nInternet connection Error!")
            except HTTPError as e:
                raise HTTPError(
                    f"\nError connecting to {url} \ncode: {response.status_code}"
                )
            except json.JSONDecodeError:
                raise ValueError(f"\nInvalid JSON response from url {url}")
            except RequestException as e:
                raise RequestException(f"\nError during request to {url}: {e}")

        print(
            f"\nGathering  {self.year} weather data through API. It may take a while..."
        )

        # list of dictionaries - to store race names and weather
        races_weather = {}

        # 1. find Season (year) id
        url = "https://api.motogp.pulselive.com/motogp/v1/results/seasons"
        all_seasons = fetch_api_data(url)

        for item in all_seasons:
            if item["year"] == self.year:
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
        with open(f"{self.CACHE_PATH}{self.year}-MotoGP-weather.json", "w") as file:
            json.dump(races_weather, file)

        return races_weather


class Plotting:
    def __new__(
        cls,
        df: pd.DataFrame,
        weather: dict,
        year: int,
        show_riders_pos=[1, 5],  # default: from 1st to 5th rider
        df_hist=None,
    ) -> None:
        cls.df = df
        cls.df_hist = df_hist
        cls.weather = weather
        cls.year = year

        # limit range of riders to show
        df.drop(index=df.index[show_riders_pos[1] :], inplace=True)
        df.drop(index=df.index[: show_riders_pos[0] - 1], inplace=True)
        if not df_hist.empty:
            df_hist.drop(index=df.index[show_riders_pos[1] :], inplace=True)
            df_hist.drop(index=df.index[: show_riders_pos[0] - 1], inplace=True)

        # real position of the rider (considering shortening the list)
        selected_rider_pos = show_riders_pos[0]

        # number of riders to show
        nr_of_riders = len(df.index)
        if nr_of_riders > 20:
            print("\nPlot is most readable up to 20 riders")

        # setting colormap of the plot
        cmap = plt.colormaps["tab10"]  # colormap 10 colors long
        colors = cmap(range(nr_of_riders))

        # setting plot layout, size (in pixels / dpi) and proportions
        plt.subplots(
            2,
            1,
            figsize=(1000 / 72, 600 / 72),
            gridspec_kw={"height_ratios": [3, 1]},
            layout="tight",
        )

        # 1. first plot:
        # riders standings on the top
        plt.subplot(2, 1, 1)

        current_pass = 0  # counter

        # plot riders standings
        for rider in df.index:
            # colormap has 10 colors, so for 11-th rider we change line style and restart colors
            if current_pass < 10:
                linestyle = "-"
                color = colors[current_pass]
            elif current_pass < 20:
                linestyle = "-."
                color = colors[current_pass - 10]
            else:
                linestyle = ":"
                color = colors[current_pass - 20]

            # a) plot historical results
            if not df_hist.empty:
                plt.plot(
                    df_hist.columns,
                    df_hist.loc[rider],
                    marker="o",
                    ms=15,
                    markeredgewidth=0,
                    linewidth=4,
                    alpha=0.1,
                    color=color,
                    linestyle=linestyle,
                )
            # b) plot current season results for each rider
            plt.plot(
                df.columns,
                df.loc[rider],
                marker="o",
                ms=11,
                color=color,
                linestyle=linestyle,
                label=f"{selected_rider_pos}. {rider}",
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

            # add small riders names on the plot
            # only when driver finished his first race (if not NaN)
            if not np.isnan(df.loc[rider].iloc[0]):
                plt.text(
                    # position x,y
                    *np.array((-0.3, df.loc[rider].iloc[0])),
                    # last name
                    f"{selected_rider_pos}. {str(rider).split()[-1]}",
                    size=7,
                    stretch="extra-condensed",
                    horizontalalignment="right",
                )
            selected_rider_pos += 1
            current_pass += 1

        # expand margins for riders names
        plt.margins(x=0.1)
        plt.title(f"Riders' standings {cls.year}", fontsize=22, pad=10)
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

        # 2. second plot:
        # weather detail on the bottom
        plt.subplot(2, 1, 2)

        x = []
        y_air_temp = []
        y_ground_temp = []

        for w in weather:
            # preparing values for x axis
            air_temp = weather[w]["air_temp"]
            clouds = weather[w]["clouds"]
            ground_temp = weather[w]["ground_temp"]
            humidity = weather[w]["humidity"]
            track_wet = weather[w]["track_wet"]

            clouds = "Hv-Rain" if clouds == "Heavy-Rain" else clouds
            clouds = "Lt-Rain" if clouds == "Light-Rain" else clouds
            clouds = "Prt-Cloud" if clouds == "Partly-Cloudy" else clouds

            # adding text values to x axis
            x.append(f"{w}\n{clouds}\n{humidity}\n{track_wet}")

            # adding values to y axis of both air and ground temperatures
            try:
                y_ground_temp.append(int(ground_temp[:-1]))
            except ValueError:
                # add NaN for corrupted data
                y_ground_temp.append(np.nan)

            try:
                y_air_temp.append(int(air_temp[:-1]))
            except ValueError:
                # add NaN for corrupted data
                y_air_temp.append(np.nan)

        # plotting ground temperatures
        plt.plot(
            x,
            y_ground_temp,
            marker="o",
            ms=10,
            label="ground temp",
            color="lightslategrey",
        )

        # plotting air temperatures
        plt.plot(
            x, y_air_temp, marker="o", ms=10, label="air temp", color="deepskyblue"
        )

        # adding small numbers for ground temperature
        for a, b in zip(x, y_ground_temp):
            # skip number when NaN (corrupted data)
            if np.isnan(b):
                continue
            plt.text(
                a,
                b,
                b,
                size=6,
                color="white",
                horizontalalignment="center",
                verticalalignment="center",
            )

        # adding small numbers for air temperature
        for c, d in zip(x, y_air_temp):
            # skip number when NaN (corrupted data)
            if np.isnan(d):
                continue
            plt.text(
                c,
                d,
                d,
                size=6,
                color="white",
                horizontalalignment="center",
                verticalalignment="center",
            )

        plt.margins(x=0.1)
        plt.title("Weather", fontsize=16, pad=10)
        plt.legend(fontsize=9)
        plt.xticks(rotation=0, fontsize=8, ha="left")
        plt.ylabel("Temperature [C]")
        plt.yticks(fontsize=9)
        plt.grid(axis="x", alpha=0.3)

        plt.show()


def main():
    # config:
    show_riders_pos = [1, 50]
    show_average_hist_results = True
    MIN_YEAR = 2002  # MotoGP: 2002-current
    year = 2023

    if year < MIN_YEAR:
        raise ValueError("Year must be >= 2002")

    # gathering weather data
    weather = GatheringReasultsFrom(year).weather()

    # gathering riders standings
    results = GatheringReasultsFrom(year).riders()
    results = Cleaning(results)

    if year >= MIN_YEAR + 3 and show_average_hist_results:
        # gathering historical riders standings
        results_hist_avrg = GatheringReasultsFrom(year).history(results)
    else:
        results_hist_avrg = pd.DataFrame  # empty dataframe

    # plotting
    Plotting(
        df=results,
        weather=weather,
        year=year,
        show_riders_pos=show_riders_pos,
        df_hist=results_hist_avrg,
    )


if __name__ == "__main__":
    main()
