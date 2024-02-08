from datetime import datetime

from django import forms
from django.shortcuts import render
from django.conf import settings
from charts_app.utils.MotoGP_utils import plot_chart

CURRENT_YEAR = datetime.now().year
MIN_YEAR = 2004  # earlier data are corrupted


class parameters_form(forms.Form):
    years_list = [tuple([x, x]) for x in range(MIN_YEAR, CURRENT_YEAR + 1)]

    year_chosen = forms.IntegerField(
        label="Select year", widget=forms.Select(choices=years_list)
    )

    hist_results = forms.BooleanField(
        label="Show average prev. 3 years results",
        widget=forms.CheckboxInput(attrs={"id": "checkbox"}),
        required=False,
    )


# Create your views here.
def index(request):

    # show plot (POST)
    if request.method == "POST":

        year = int(request.POST["year_chosen"])

        # if checkbox is "on", set True, otherwise False
        show_average_hist_results = request.POST.get("hist_results", False)

        if year in range(MIN_YEAR, CURRENT_YEAR + 1):
            plot_chart(year, show_average_hist_results)

            # render and fill form with entered data
            return render(
                request,
                "charts_app/index.html",
                {
                    "MEDIA_URL": settings.MEDIA_URL,
                    "form": parameters_form(request.POST),
                },
            )

    # input form data (GET)
    if request.method == "GET":
        return render(
            request,
            "charts_app/index.html",
            {"MEDIA_URL": settings.MEDIA_URL, "form": parameters_form()},
        )
