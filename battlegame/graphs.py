from re import TEMPLATE
from rest_framework.views import View
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import render
from plotly import graph_objects


def get_sample_graph():
    data = graph_objects.Figure(
        [graph_objects.Bar(y=[1, 2, 3])],
        layout_title_text="Sample Graph using plotly"
    )
    return data.to_html()


def get_usage_stats_graph():
    return None


TEMPLATE_NAME = 'graphs.html'
GRAPHS = {'sample': get_sample_graph,
          'usage': get_usage_stats_graph}


class GetGraphView(View):
    def get(self, request, name=None):
        graph = GRAPHS[name]() if name in GRAPHS else None
        context = {'graph_title': 'Defense Placement Statistics', 'graph_contents': graph}
        return render(request, TEMPLATE_NAME, context)
