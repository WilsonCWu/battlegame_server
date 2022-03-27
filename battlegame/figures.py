from datetime import datetime, timezone, timedelta
from math import ceil
import numpy as numpy
import pandas as pd
from plotly import graph_objects as go
from dataclasses import dataclass

from playerdata import constants, formulas
from playerdata.models import BaseCharacterUsage, DungeonProgress, DungeonStats, UserStats

pd.options.plotting.backend = "plotly"


def get_sample_graph():
    data = go.Figure(
        [go.Bar(y=[1, 2, 3])],
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
        bucket_name = f'{index*constants.USAGE_BUCKET_ELO_SIZE} - {(index+1)*constants.USAGE_BUCKET_ELO_SIZE-1}'
        df_offense[bucket_name] = 100 * df[f'games bucket {index}'] / (games_bucket_sum/5)
        df_defense[bucket_name] = 100 * df[f'defense games bucket {index}'] / (def_games_bucket_sum/5)
        if games_bucket_sum + def_games_bucket_sum != 0:
            context['other_data'].append(f'Bucket {index} ({bucket_name}) offense games: {games_bucket_sum}, defense games: {def_games_bucket_sum}')

    # Drop all buckets that have no data (nan or zeros):
    df_offense = df_offense.loc[:, (df_offense**2).sum() != 0]
    df_defense = df_defense.loc[:, (df_defense**2).sum() != 0]

    graphs = []  # This needs to be a list of graph.to_html

    # Take each row of the dataframe and plot it (facet_row = "variable" makes it 2 bar graphs together)
    for index in range(len(names)):
        offense_data = df_offense.loc[index, :]
        defense_data = df_defense.loc[index, :]
        if offense_data.sum() == 0 and defense_data.sum() == 0:  # Don't display empty graphs (like for PVE enemies)
            continue
        graph_df = pd.DataFrame(dict(offense=offense_data, defense=defense_data))
        fig = graph_df.plot.bar(facet_row="variable", title=names[index], width=800,
                                color_discrete_sequence=['#EF553B', '#636EFA'],  # plotly default color orange, blue
                                labels=dict(index="bucket", value="usage rate", variable="game type"))
        fig.update_yaxes(range=[0, 100])
        graphs.append(fig.to_html)
    context['graph_title'] = 'Usage Rate Graphs'
    context['graph_contents'] = graphs
    return context


def get_dungeon_winrate_graph():
    df = get_dungeon_stats_dataframe(DungeonStats.objects.all())

    context = {}
    context['graph_contents'] = []
    context['other_data'] = []

    # Handle each dungeon type separately.
    for dungeon_type in constants.DungeonType:
        df_dungeon = df.loc[df['dungeon_type'] == dungeon_type.value]
        df_dungeon['winrate'] = 100 * df_dungeon['wins'] / df_dungeon['games']
        context['other_data'].append(f"Total games for {dungeon_type}: {df_dungeon['games'].sum()}")
        fig = df_dungeon.plot.bar(y='winrate', x='stage', title=f'{dungeon_type} Win Rates:')
        fig.update_yaxes(range=[0, 100])
        fig.update_traces(width=1)
        context['graph_contents'].append(fig.to_html())
    return context


def get_dungeon_progress_graph():
    # Setup

    context = {}
    context['graph_contents'] = []
    context['other_data'] = []

    # Pull data from user stats
    stats = UserStats.objects.all().select_related('user__userinfo').select_related('user__dungeonprogress')
    active_players = [x for x in stats if x.user.userinfo.elo > 0]
    dungeon_prog = [x.user.dungeonprogress.campaign_stage for x in active_players]
    best_dd = [x.user.userinfo.best_daily_dungeon_stage for x in active_players]

    # Hardcode number of stages to check
    DUNGEON_STAGE_COUNT = constants.MAX_DUNGEON_STAGE[constants.DungeonType.CAMPAIGN.value] + 2  # max stage +1 (+1 for 1-indexed)
    DAILY_DUNGEON_STAGE_COUNT = 80 + 2  # max stage +1 (+1 for 1-indexed)

    # Collect 'total players who peaked here' data for dungeon and dailydungeon
    highest_dungeon_stage_is_index = [0] * DUNGEON_STAGE_COUNT
    highest_dd_stage_is_index = [0] * DAILY_DUNGEON_STAGE_COUNT
    for stage in dungeon_prog:
        highest_dungeon_stage_is_index[stage] += 1
    for stage in best_dd:
        highest_dd_stage_is_index[stage] += 1

    # Graph dungeon
    df_dungeon = pd.DataFrame()
    df_dungeon['stage'] = [index for index in range(DUNGEON_STAGE_COUNT)]
    df_dungeon['players'] = highest_dungeon_stage_is_index
    df_dungeon = df_dungeon[df_dungeon.players != 0]  # Drop rows with no columns
    df_dungeon = df_dungeon[df_dungeon.stage != 1]  # Drop stage 1
    fig_dungeon = df_dungeon.plot.bar(y='players', x='stage', title=f'Dungeon Max Stage Reached Count')
    fig_dungeon.update_traces(width=1)
    fig_dungeon.update_xaxes(range=[0, DUNGEON_STAGE_COUNT])

    # Graph tunnels
    df_daily = pd.DataFrame()
    df_daily['stage'] = [index for index in range(DAILY_DUNGEON_STAGE_COUNT)]
    df_daily['players'] = highest_dd_stage_is_index
    df_daily = df_daily[df_daily.players != 0]  # Drop rows with no columns
    df_daily = df_daily[df_daily.stage != 0]  # Drop stage 0
    fig_daily = df_daily.plot.bar(y='players', x='stage', title=f'Daily Dungeon Max Stage Reached Count')
    fig_daily.update_traces(width=1)
    fig_daily.update_xaxes(range=[0, DAILY_DUNGEON_STAGE_COUNT])

    # Prepare context
    context['other_data'].append(f"Total players in Dungeon progress graph: {df_dungeon['players'].sum()}")
    context['other_data'].append(f"Total players in Daily Dungeon progress graph: {df_daily['players'].sum()}")
    context['graph_contents'].append(fig_dungeon.to_html())
    context['graph_contents'].append(fig_daily.to_html())
    return context


# Combines graph_contents for the two dungeon graphs, drops everything else from the context
def get_combined_dungeon_graphs():
    context = {'graph_contents': [], 'other_data': []}
    context_list = [get_dungeon_progress_graph(), get_dungeon_winrate_graph()]
    for single_context in context_list:
        if 'graph_contents' in single_context:
            for graph in single_context['graph_contents']:
                context['graph_contents'].append(graph)
        if 'other_data' in single_context:
            for line in single_context['other_data']:
                context['other_data'].append(line)
    context['graph_title'] = "Dungeon Stats"
    return context


def get_level_graphs():
    context = {}
    context['graph_contents'] = []
    context['other_data'] = []

    # We take the column(list[list[int]]) and the corresponding days (list[int]), and turn it into the graph.
    def prepare_figure(data_col, days_col, graph_title):
        df = pd.DataFrame(data_col.tolist(), index=days_col)
        df.reset_index()
        boxes = []
        # Form a list of go.Box
        for index, row in df.iterrows():
            flat_list = [sublist[0] for sublist in row.tolist()]  # Iterrows gives us a list[list[int]] where each sublist was length 1, flatten it to list[int]
            boxes.append(go.Box(y=flat_list, boxpoints=False, orientation='v', name=f'{index} Days'))
        fig = go.Figure(data=boxes, layout_title_text=graph_title)
        return fig

    df_days = get_level_and_progress_dataframe(DungeonProgress.objects.all(), 1, 14)
    df_weeks = get_level_and_progress_dataframe(DungeonProgress.objects.all(), 7, 8)
    df_months = get_level_and_progress_dataframe(DungeonProgress.objects.all(), 30)

    fig_lvl_days = prepare_figure(df_days['level'], df_days['days played'], 'Average level grouped by account age: First 14 days')
    fig_lvl_weeks = prepare_figure(df_weeks['level'], df_weeks['days played'], 'Average level grouped by account age: First 8 weeks')
    fig_lvl_months = prepare_figure(df_months['level'], df_months['days played'], 'Average level grouped by account age: All data, grouped in months played')

    fig_campaign_days = prepare_figure(df_days['campaign progress'], df_days['days played'], 'Average campaign progress grouped by account age: First 14 days')
    fig_campaign_weeks = prepare_figure(df_weeks['campaign progress'], df_weeks['days played'], 'Average campaign progress grouped by account age: First 8 weeks')
    fig_campaign_months = prepare_figure(df_months['campaign progress'], df_months['days played'], 'Average campaign progress grouped by account age: All data, grouped in months played')

    fig_tower_days = prepare_figure(df_days['tower progress'], df_days['days played'], 'Average tower progress grouped by account age: First 14 days')
    fig_tower_weeks = prepare_figure(df_weeks['tower progress'], df_weeks['days played'], 'Average tower progress grouped by account age: First 8 weeks')
    fig_tower_months = prepare_figure(df_months['tower progress'], df_months['days played'], 'Average tower progress grouped by account age: All data, grouped in months played')

    context['graph_contents'].append(fig_lvl_days.to_html())
    context['graph_contents'].append(fig_lvl_weeks.to_html())
    context['graph_contents'].append(fig_lvl_months.to_html())
    context['graph_contents'].append(fig_campaign_days.to_html())
    context['graph_contents'].append(fig_campaign_weeks.to_html())
    context['graph_contents'].append(fig_campaign_months.to_html())
    context['graph_contents'].append(fig_tower_days.to_html())
    context['graph_contents'].append(fig_tower_weeks.to_html())
    context['graph_contents'].append(fig_tower_months.to_html())
    return context


# Each entry should be a list of functions
# Each function should return a dictionary with graph_contents being the graph or a list of graphs.
# dictionary can also have an 'other_data' field.
GRAPHS = {'sample': get_sample_graph,  # Single graph example
          'samples': get_sample_graphs,  # Multiple graphs example
          'usage': get_usage_stats_graph,
          'dungeon': get_combined_dungeon_graphs,
          'level': get_level_graphs,
          }


# Gives context for rendering a graph or list of graphs with the graphs.html template
def get_graph_context(name):
    start = datetime.utcnow()
    context = {}
    if name in GRAPHS:
        context = GRAPHS[name]()
    end = datetime.utcnow()
    elapsed = end - start
    if 'graph_title' not in context:
        context['graph_title'] = 'Graph'
    if 'other_data' not in context:
        context['other_data'] = [f'Function runtime: {elapsed}']
    else:
        context['other_data'].append(f'Function runtime: {elapsed}')
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


# Queryset should be DungeonStats objects
def get_dungeon_stats_dataframe(queryset):
    @dataclass
    class DungeonStatsRow:
        stage: int
        dungeon_type: int
        wins: int
        games: int

        def to_dict(self):
            return dict(stage=self.stage,
                        dungeon_type=self.dungeon_type,
                        wins=self.wins,
                        games=self.games)

    stage_stats_rows = []

    for stage_stats in queryset:
        stage_stats_rows.append(DungeonStatsRow(
            stage=stage_stats.stage,
            dungeon_type=stage_stats.dungeon_type,
            wins=stage_stats.wins,
            games=stage_stats.games))
    return pd.DataFrame([stats_row.to_dict() for stats_row in stage_stats_rows])


# Queryset should be HackerAlert objects
def get_hacker_alert_dataframe(queryset):

    @dataclass
    class HackerStatsRow:
        user_id: int
        user_name: str
        reports: int
        reports_processed: int
        flagged_sims: int

        def to_dict(self):
            return dict(user_id=self.user_id,
                        user_name=self.user_name,
                        reports=self.reports,
                        reports_processed=self.reports_processed,
                        flagged_sims=self.flagged_sims)

    hacker_stats_dict = {}

    queryset = queryset.select_related('user').select_related('user__userinfo')

    # We want the table to be stats per user, so compile each hacker alert into a dict instead of list
    for report in queryset:
        id = report.user.id
        if id not in hacker_stats_dict:
            hacker_stats_dict[id] = HackerStatsRow(
                user_id=id,
                user_name=report.user.userinfo.name,
                reports=0,
                reports_processed=0,
                flagged_sims=0)

        # Increment the stats based on the hacker alert.
        hacker_stats_dict[id].reports += 1
        if report.match_simulated:
            hacker_stats_dict[id].reports_processed += 1
            if report.match_simulated_alert:
                hacker_stats_dict[id].flagged_sims += 1

    return pd.DataFrame([hacker_stats_dict[key].to_dict() for key in hacker_stats_dict])


# Queryset should be DungeonProgress objects
def get_level_and_progress_dataframe(queryset, group_size, bucket_count=-1):

    PERCENTILES_COLLECTED = [1, 25, 50, 75, 99]

    # We don't have static intervals for the days_played, so we can get more granularity for new players
    @dataclass
    class ProgressByLevelGroupRow:
        days_played_group: int  # This'll correspond to "minimum days played", and we can place a player's data into the highest group that applies.
        level_percentiles: list  # Follows same order as PERCENTILES_COLLECTED
        campaign_percentiles: list
        tower_percentiles: list
        entries: int

        def to_dict(self):
            dict = {'days played': self.days_played_group,  # Same number repeated n times because plotly likes the data like that.
                    'level': self.level_percentiles,
                    'campaign progress': self.campaign_percentiles,
                    'tower progress': self.tower_percentiles,
                    'entries': self.entries, }
            return dict

    now = datetime.now(timezone.utc)
    queryset = queryset.select_related('user__userstats').select_related('user__userinfo') \
        .order_by('-user__userstats__time_started')

    # Establish brackets:
    date_brackets = []  # List of list [][0] = int:days played, [][1] = datetime:corresponding date
    date_brackets.append([0, now])
    days_played_tracker = 0

    EARLIEST_DATE = datetime(2021, 3, 1, tzinfo=timezone.utc)

    # By default, we take buckets of the specified size until march 2021.
    number_of_buckets = ceil((now - EARLIEST_DATE).days / group_size)
    if bucket_count != -1:
        number_of_buckets = min(bucket_count, number_of_buckets) + 1  # Cap number of buckets if we specify it (+1 catches anything too old).

    # Calculate all of the dates by bracket before iterating through all the DungeonProgress objects.
    for i in range(number_of_buckets):
        days_played_tracker += group_size
        date_brackets.append([days_played_tracker, now - timedelta(days=days_played_tracker)])

    # Declare empty rows corresponding to each bracket
    row_list = []
    for bracket_start in date_brackets:
        row_list.append(ProgressByLevelGroupRow(
            days_played_group=bracket_start[0],
            level_percentiles=[],
            campaign_percentiles=[],
            tower_percentiles=[],
            entries=0
            ))
    index = 0

    # Used for calculating percentiles.
    level_list = []
    campaign_list = []
    tower_list = []

    # Fill in the rows by iterating over every DungeonProgress
    for dungeon_prog in queryset:
        if dungeon_prog.user.userstats.num_games == 0:
            continue

        # Queryset and date brackets are sorted, so we can increment the index instead of searching every time
        time_started = dungeon_prog.user.userstats.time_started
        while index+1 < len(date_brackets) and time_started < date_brackets[index+1][1]:
            # Calculate the percentiles
            for p in PERCENTILES_COLLECTED:
                row_list[index].level_percentiles.append([numpy.percentile(level_list, p) if len(level_list) > 0 else 0])
                row_list[index].campaign_percentiles.append([numpy.percentile(campaign_list, p) if len(campaign_list) > 0 else 0])
                row_list[index].tower_percentiles.append([numpy.percentile(tower_list, p) if len(tower_list) > 0 else 0])

            # Clear the data
            level_list = []
            campaign_list = []
            tower_list = []
            index += 1

        level_list.append(formulas.exp_to_level(dungeon_prog.user.userinfo.player_exp))
        campaign_list.append(dungeon_prog.campaign_stage)
        tower_list.append(dungeon_prog.tower_stage)

        row_list[index].entries += 1

    # Do it again for the last index.
    for p in PERCENTILES_COLLECTED:
        row_list[index].level_percentiles.append([numpy.percentile(level_list, p) if len(level_list) > 0 else 0])
        row_list[index].campaign_percentiles.append([numpy.percentile(campaign_list, p) if len(campaign_list) > 0 else 0])
        row_list[index].tower_percentiles.append([numpy.percentile(tower_list, p) if len(tower_list) > 0 else 0])

    df = pd.DataFrame([prog_row.to_dict() for prog_row in row_list])
    # If we specified the number of buckets, then that means anything "too old" will be grouped in an extra bucket at the end.
    if bucket_count != -1:
        df.drop(df.tail(1).index, inplace=True)
    return df
