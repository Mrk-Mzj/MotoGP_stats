from datetime import datetime

from django import forms
from django.shortcuts import render
from django.conf import settings
from charts_app.utils.MotoGP_utils import plot_chart

CURRENT_YEAR = datetime.now().year
MIN_YEAR = 2004  # earlier data are corrupted


class ParametersForm(forms.Form):

    # year
    years_list = [tuple([x, x]) for x in range(MIN_YEAR, CURRENT_YEAR + 1)]

    year_chosen = forms.IntegerField(
        label="Select year", widget=forms.Select(choices=years_list), initial=CURRENT_YEAR
    )

    # checkbox
    hist_results = forms.BooleanField(
        label="Show average prev. 3 years results",
        widget=forms.CheckboxInput(attrs={"id": "checkbox"}),
        required=False,
    )

    # riders to show
    places_from = forms.IntegerField(
        label="Show places from",
        min_value=1,
        max_value=20,
        widget=forms.NumberInput(attrs={"id": "show-from"}),
        required=True,
        initial=1,
    )

    places_to = forms.IntegerField(
        label="– to place number",
        min_value=1,
        max_value=20,
        widget=forms.NumberInput(attrs={"id": "show-to"}),
        required=True,
        initial=5,
    )


# Create your views here.
def index(request):

    # show plot (POST)
    if request.method == "POST":

        year = int(request.POST["year_chosen"])

        # if checkbox is "on", set True, otherwise False
        show_average_hist_results = request.POST.get("hist_results", False)


        # checking if user really filled the form
        if request.POST.get("places_from"):
            places_from = int(request.POST.get("places_from"))
        else:
            places_from = 1

        if request.POST.get("places_to"):
            places_to = int(request.POST.get("places_to"))
        else:
            places_to = 1


        # checking if user didn't mix the values
        if places_from <= places_to:
            show_riders_pos = [places_from, places_to]
        else:
            show_riders_pos = [places_to, places_from]


        if year in range(MIN_YEAR, CURRENT_YEAR + 1):
            plot_chart(year, show_average_hist_results, show_riders_pos)

            # render and fill form with entered data
            return render(
                request,
                "charts_app/index.html",
                {
                    "MEDIA_URL": settings.MEDIA_URL,
                    "form": ParametersForm(request.POST),
                },
            )

    # input form data (GET)
    if request.method == "GET":
        return render(
            request,
            "charts_app/index.html",
            {"MEDIA_URL": settings.MEDIA_URL, "form": ParametersForm()},
        )
