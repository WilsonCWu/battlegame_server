from rest_framework.views import APIView
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
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
GRAPHS = {'sample': [get_sample_graph],  # Single graph example
          'samples': [get_sample_graph, get_sample_graph, get_sample_graph],  # Multiple graphs example
          'usage': [get_usage_stats_graph]}  # Doesn't exist


# Import this to get graphs from admin panel
def get_graph_http_response(request, name):
    graph_list = []
    if name in GRAPHS:
        for graph_function in GRAPHS[name]:
            graph_list.append(graph_function())
    context = {'graph_title': 'Graph',
               'graph_contents': graph_list,
               'other_graph_links': GRAPHS.keys()}
    return render(request, TEMPLATE_NAME, context)


# Gives context to render a dataframe with the table.html template.
def get_table_context(df):
    columns = [{'field': f, 'title': str(f).capitalize(), 'sortable': 'true'} for f in list(df.columns)]
    json_df = df.to_json(orient='records')
    context = {'data': json_df, 'columns': columns}
    return context


@login_required(login_url='/admin/')
def get_graph_view(request, name=None):
    return get_graph_http_response(request, name)
