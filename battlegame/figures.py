import pandas as pd
from plotly import graph_objects
from dataclasses import dataclass

from playerdata import constants
from playerdata.models import BaseCharacterUsage


def get_sample_graph():
    data = graph_objects.Figure(
        [graph_objects.Bar(y=[1, 2, 3])],
        layout_title_text="Sample Graph using plotly"
    )
    context = {'graph_contents': [data.to_html()]}
    return context


def get_sample_graphs():
    context_list = [get_sample_graph(), get_sample_graph(), get_sample_graph()]
    graph_contents = [context['graph_contents'][0] for context in context_list]
    return {'graph_contents': graph_contents}


def get_usage_stats_graph():
    df = get_base_character_usage_dataframe(BaseCharacterUsage.objects.all())
    pd.options.plotting.backend = "plotly"

    context = {'other_data': []}  # What we'll be returning
    names = df['name']
    df = df.loc[:, df.columns.str.contains('bucket')]  # We only need bucket data

    df_offense = pd.DataFrame()
    df_defense = pd.DataFrame()

    # Make another column for each bucket.
    bucket_count = constants.NUMBER_OF_USAGE_BUCKETS
    for index in range(bucket_count):
        games_bucket_sum = df[f'games bucket {index}'].sum()
        def_games_bucket_sum = df[f'defense games bucket {index}'].sum()
        # Divide total games by 5 (even though not all teams have 5 heroes, almost all of them should)
        bucket_name = f'{index*500} - {(index+1)*500-1}'
        df_offense[bucket_name] = 100 * df[f'games bucket {index}'] / (games_bucket_sum/5)
        df_defense[bucket_name] = 100 * df[f'defense games bucket {index}'] / (def_games_bucket_sum/5)
        if games_bucket_sum + def_games_bucket_sum != 0:
            context['other_data'].append(f'Bucket {index} games: {games_bucket_sum}, defense games: {games_bucket_sum}')

    # Drop all buckets that have no data (nan or zeros):
    df_offense = df_offense.loc[:, (df_offense**2).sum() != 0]
    df_defense = df_defense.loc[:, (df_defense**2).sum() != 0]

    graphs = []  # This needs to be a list of graph.to_html

    # Take each row of the dataframe and plot it (facet_row = "variable" makes it 2 bar graphs together)
    for index in range(len(names)):
        offense_data = df_offense.loc[index, :]
        defense_data = df_defense.loc[index, :]
        graph_df = pd.DataFrame(dict(offense=offense_data, defense=defense_data))
        fig = graph_df.plot.bar(facet_row="variable", title=names[index], width=800,
                                color_discrete_sequence=['#EF553B', '#636EFA'],  # plotly default color orange, blue
                                labels=dict(index="bucket", value="usage rate", variable="game type"))
        fig.update_yaxes(range=[0, 100])
        graphs.append(fig.to_html)
    context['graph_title'] = 'Usage Rate Graphs'
    context['graph_contents'] = graphs
    return context


# Each entry should be a list of functions
# Each function should return a dictionary with graph_contents being the graph or a list of graphs.
# dictionary can also have an 'other_data' field.
GRAPHS = {'sample': get_sample_graph,  # Single graph example
          'samples': get_sample_graphs,  # Multiple graphs example
          'usage': get_usage_stats_graph}


# Gives context for rendering a graph or list of graphs with the graphs.html template
def get_graph_context(name):
    context = {}
    if name in GRAPHS:
        context = GRAPHS[name]()
    if 'graph_title' not in context:
        context['graph_title'] = 'Graph'
    context['other_graph_links'] = GRAPHS.keys()
    return context


# Gives context to render a dataframe with the table.html template.
def get_table_context(df):
    columns = [{'field': f, 'title': str(f).capitalize(), 'sortable': 'true'} for f in list(df.columns)]  # All the header options go here
    json_df = df.to_json(orient='records')  # Format as list of tuples
    context = {'data': json_df, 'columns': columns}
    return context


# Queryset should be some set of BaseCharacterUsage objects.
def get_base_character_usage_dataframe(queryset):
    @dataclass
    class CharacterUsageRow:
        name: str
        rarity: int
        wins_buckets: list
        games_buckets: list
        defense_wins_buckets: list
        defense_games_buckets: list

        def to_dict(self):
            dict = {'name': self.name, 'rarity': self.rarity}
            dict.update({f'wins bucket {f}': self.wins_buckets[f] for f in range(len(self.wins_buckets))})
            dict.update({f'games bucket {f}': self.games_buckets[f] for f in range(len(self.games_buckets))})
            dict.update({f'defense wins bucket {f}': self.defense_wins_buckets[f] for f in range(len(self.defense_wins_buckets))})
            dict.update({f'defense games bucket {f}': self.defense_games_buckets[f] for f in range(len(self.defense_games_buckets))})
            return dict

    queryset = queryset.select_related('char_type')
    char_data = []

    # pull usage statistics from the selected characters
    for base_char_usage in queryset:
        char_data.append(CharacterUsageRow(
                         name=base_char_usage.char_type.name,
                         rarity=base_char_usage.char_type.rarity,
                         games_buckets=base_char_usage.num_games_buckets,
                         wins_buckets=base_char_usage.num_wins_buckets,
                         defense_games_buckets=base_char_usage.num_defense_games_buckets,
                         defense_wins_buckets=base_char_usage.num_defense_wins_buckets))
    df = pd.DataFrame([character.to_dict() for character in char_data])
    return df
