# This Python 3 environment comes with many helpful analytics libraries installed
# It is defined by the kaggle/python docker image: https://github.com/kaggle/docker-python
# For example, here's several helpful packages to load in

import numpy as np  # linear algebra
import pandas as pd  # data processing, CSV file I/O (e.g. pd.read_csv)
from functools import reduce
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import MinMaxScaler
# Input data files are available in the "../input/" directory.
# For example, running this (by clicking run or pressing Shift+Enter) will list all files under the input directory

train = pd.read_csv('Data/train.csv')
test = pd.read_csv('Data/test.csv')
train_labels = pd.read_csv('Data/train_labels.csv')

train_ids = train[['installation_id', 'game_session']].drop_duplicates()
test_ids = test[['installation_id', 'game_session']].drop_duplicates()
# train = pd.read_csv('/kaggle/input/data-science-bowl-2019/train.csv')
# test = pd.read_csv('/kaggle/input/data-science-bowl-2019/test.csv')
# train_labels = pd.read_csv('/kaggle/input/data-science-bowl-2019/train_labels.csv')
# Any results you write to the current directory are saved as output.

def convert_datetime(df):
    import pandas as pd
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df['date'] = df['timestamp'].dt.date
    df['month'] = df['timestamp'].dt.month
    df['hour'] = df['timestamp'].dt.hour
    df['year'] = df['timestamp'].dt.year
    df['dayofweek'] = df['timestamp'].dt.dayofweek
    return df



def get_previous_ac_metrics(data):
    import  pandas as pd
    Assess = data.sort_values(['installation_id', 'timestamp', 'game_session','Assessments_played_Counter'], ascending=[True, True, True, True]).copy()
    Assess = Assess[Assess.type == 'Assessment']
    Assess['Attempts'] = Assess.groupby(['installation_id', 'game_session'])['Attempt'].transform(np.sum)
    Assess['Success'] = Assess.groupby(['installation_id', 'game_session'])['IsAttemptSuccessful'].transform(np.sum)
    Assess = Assess[['installation_id', 'game_session', 'Assessments_played_Counter' ,'Attempts', 'Success']].drop_duplicates()
    ratio = Assess['Success'] / Assess['Attempts']
    conditions = [
        (ratio == 1),
        (ratio == 0.5),
        (ratio < 0.5) & (ratio > 0),
        (ratio == 0)]
    choices = [3, 2, 1, 0]
    Assess['accuracy_group'] = np.select(conditions, choices)
    Assess['Past_Assessment_ag'] = round(Assess.groupby('installation_id')['accuracy_group'].shift(1, fill_value=0))
    Assess['Past_Assessment_att'] = round(Assess.groupby('installation_id')['Attempts'].shift(1, fill_value=0))
    Assess['Past_Assessment_succ'] = round(Assess.groupby('installation_id')['Success'].shift(1, fill_value=0))
    Assess['cummean_ag'] = Assess.groupby('installation_id')['Past_Assessment_ag'].transform(
        lambda x: x.expanding().mean())
    Assess['cummean_att'] = Assess.groupby('installation_id')['Past_Assessment_att'].transform(
        lambda x: x.expanding().mean())
    Assess['cummean_succ'] = Assess.groupby('installation_id')['Past_Assessment_succ'].transform(
        lambda x: x.expanding().mean())
    Assess['cumstd_ag'] = Assess.groupby('installation_id')['Past_Assessment_ag'].transform(
        lambda x: x.expanding().std())
    Assess['cumstd_att'] = Assess.groupby('installation_id')['Past_Assessment_att'].transform(
        lambda x: x.expanding().std())
    Assess['cumstd_succ'] = Assess.groupby('installation_id')['Past_Assessment_succ'].transform(
        lambda x: x.expanding().std())
    Assess['cumstd_ag'].fillna(0, inplace=True)
    Assess['cumstd_att'].fillna(0, inplace=True)
    Assess['cumstd_succ'].fillna(0, inplace=True)

    pastAG = Assess[['installation_id', 'game_session', 'Assessments_played_Counter', 'Past_Assessment_ag']]
    Assess2 = pd.pivot_table(pastAG,
                             index=['installation_id', 'game_session','Assessments_played_Counter'],
                             columns='Past_Assessment_ag',
                             values= 'Past_Assessment_ag',
                             aggfunc='nunique').reset_index()
    Assess2 = Assess2.rename(columns={0: "zeros", 1: "ones", 2: "twos", 3:'threes'})
    Assess2 = Assess2.sort_values(['installation_id','Assessments_played_Counter'])
    Assess2.loc[:,[ "zeros", 'ones',"twos" , 'threes']] = Assess2.groupby('installation_id')[ "zeros", 'ones',"twos" , 'threes'].apply(np.cumsum)
    Assess2.loc[:, ["zeros", 'ones', "twos", 'threes']] = Assess2.groupby('installation_id')[ "zeros", 'ones',"twos" , 'threes'].fillna(method='ffill')
    Assess2.loc[:, ["zeros", 'ones', "twos", 'threes']] = Assess2.loc[:, ["zeros", 'ones', "twos", 'threes']].fillna(0)
    Assess = Assess[
        ['installation_id', 'game_session',
         'Past_Assessment_ag',
         'Past_Assessment_att',
         'Past_Assessment_succ',
         'cummean_ag',
         'cummean_att',
         'cummean_succ',
         'cumstd_ag',
         'cumstd_att',
         'cumstd_succ'
         ]]
    AssessFinal = pd.merge(Assess,Assess2, on = ['installation_id', 'game_session'], how= 'inner')
    return AssessFinal


def get_past_attemps_and_successes(data):
    slice2 = data.loc[(data.game_time == data.Total_Game_Session_Time) &
                      (data.event_count == data.Total_Game_Session_Events),
                      ['installation_id', 'game_session', 'type',
                       'Cumulative_Attempts', 'Cumulative_Successes','Cumulative_Fails',
                       'Assessments_played_Counter']].copy().drop_duplicates()
    slice2['Game_Session_Order'] = slice2.groupby('installation_id')['game_session'].cumcount() + 1
    slice2 = slice2.sort_values(['installation_id', 'Game_Session_Order'])
    slice2 = slice2[slice2.type == 'Assessment']
    slice2['Past_Total_Attempts'] = round(
        slice2.groupby('installation_id')['Cumulative_Attempts'].shift(1, fill_value=0)).astype('int')
    slice2['Past_Total_Successes'] = round(
        slice2.groupby('installation_id')['Cumulative_Successes'].shift(1, fill_value=0)).astype('int')
    slice2['Past_Total_Fails'] = round(
        slice2.groupby('installation_id')['Cumulative_Fails'].shift(1, fill_value=0)).astype('int')
    slice2['Past_Assessments_Played'] = round(
        slice2.groupby('installation_id')['Assessments_played_Counter'].shift(1, fill_value=0)).astype('int')
    slice2 = slice2.loc[:, ['installation_id', 'game_session', 'Past_Total_Attempts',
                            'Past_Total_Successes', 'Past_Total_Fails','Past_Assessments_Played']]
    return slice2


def get_past_assessment_time_events_and_metrics(data):
    slice3 = data.loc[data.type == 'Assessment', ['installation_id',
                                                  'game_session',
                                                  'Assessment_Session_Time',
                                                  'Assessment_NumberOfEvents']].drop_duplicates()
    slice3['Past_Assessment_Session_Time'] = slice3.groupby('installation_id')['Assessment_Session_Time']. \
        shift(1, fill_value=0)
    slice3['Past_Assessment_NumberOfEvents'] = slice3.groupby('installation_id')['Assessment_NumberOfEvents']. \
        shift(1, fill_value=0)
    # slice3 = slice3.assign(
    #     cumAverageTime=slice3.groupby('installation_id', sort=False)['Past_Assessment_Session_Time']. \
    #                        transform(lambda x: x.expanding().mean()))
    # slice3 = slice3.assign(
    #     cumAverageEvents=slice3.groupby('installation_id', sort=False)['Past_Assessment_NumberOfEvents']. \
    #         transform(lambda x: x.expanding().mean()))
    # slice3 = slice3.assign(cumsdTime=slice3.groupby('installation_id', sort=False)['Past_Assessment_Session_Time']. \
    #                        transform(lambda x: x.expanding().std()))
    # slice3['cumsdTime'].fillna(0, inplace=True)
    # slice3 = slice3.assign(cumsdEvents=slice3.groupby('installation_id', sort=False)['Past_Assessment_NumberOfEvents']. \
    #                        transform(lambda x: x.expanding().std()))
    # slice3['cumsdEvents'].fillna(0, inplace=True)
    slice3 = slice3[
        ['installation_id', 'game_session',
         'Past_Assessment_Session_Time',
         'Past_Assessment_NumberOfEvents'
         #    ,
         # 'cumAverageTime',
         # 'cumAverageEvents',
         # 'cumsdTime',
         # 'cumsdEvents'
         ]]
    return (slice3)


def get_prev_events_and_time_till_attempt(data):
    Cols = ['installation_id', 'game_session', 'type', 'event_count', 'event_code', 'Attempt', 'game_time']
    Event_and_Attempts = data[Cols].copy()
    Event_and_Attempts = Event_and_Attempts[Event_and_Attempts['type'] == 'Assessment']
    Event_and_Attempts['Num_Of_Events_Till_Attempt'] = Event_and_Attempts.loc[Event_and_Attempts.Attempt == 1,
                                                                              'event_count']
    Event_and_Attempts['Num_Of_Events_Till_Attempt'] = Event_and_Attempts['Num_Of_Events_Till_Attempt']. \
        replace(np.nan, 0)
    Event_and_Attempts['Time_past_Till_Attempt'] = Event_and_Attempts.loc[Event_and_Attempts.Attempt == 1,
                                                                          'game_time']
    Event_and_Attempts['Time_past_Till_Attempt'] = Event_and_Attempts['Time_past_Till_Attempt'].replace(np.nan, 0)
    Event_and_Attempts = Event_and_Attempts.groupby(['installation_id', 'game_session'])['Num_Of_Events_Till_Attempt',
                                                                                         'Time_past_Till_Attempt'].max()
    Event_and_Attempts = Event_and_Attempts.reset_index()
    Event_and_Attempts['Prev_Assessment_Time_past_Till_Attempt'] = Event_and_Attempts['Time_past_Till_Attempt']. \
        shift(1, fill_value=0)
    Event_and_Attempts['Prev_Assessment_Num_Of_Events_Till_Attempt'] = Event_and_Attempts['Num_Of_Events_Till_Attempt']. \
        shift(1, fill_value=0)

    Event_and_Attempts = Event_and_Attempts.assign(
        cummean_Assessment_Time_past_Till_Attempt=
        Event_and_Attempts.groupby('installation_id', sort=False)['Prev_Assessment_Time_past_Till_Attempt']. \
            transform(lambda x: x.expanding().mean()))
    Event_and_Attempts = Event_and_Attempts.assign(
        cummean_Assessment_Num_Of_Events_Till_Attempt=
        Event_and_Attempts.groupby('installation_id', sort=False)['Prev_Assessment_Num_Of_Events_Till_Attempt']. \
            transform(lambda x: x.expanding().mean()))

    Event_and_Attempts = Event_and_Attempts.assign(
        cumsd_Assessment_Time_past_Till_Attempt=
        Event_and_Attempts.groupby('installation_id', sort=False)['Prev_Assessment_Time_past_Till_Attempt']. \
            transform(lambda x: x.expanding().std()))
    Event_and_Attempts['cumsd_Assessment_Time_past_Till_Attempt'].fillna(0, inplace=True)

    Event_and_Attempts = Event_and_Attempts.assign(
        cumsd_Assessment_Num_Of_Events_Till_Attempt=
        Event_and_Attempts.groupby('installation_id', sort=False)['Prev_Assessment_Num_Of_Events_Till_Attempt']. \
            transform(lambda x: x.expanding().std()))
    Event_and_Attempts['cumsd_Assessment_Num_Of_Events_Till_Attempt'].fillna(0, inplace=True)

    Event_and_Attempts = Event_and_Attempts[['installation_id',
                                             'game_session',
                                             'Prev_Assessment_Time_past_Till_Attempt',
                                             'Prev_Assessment_Num_Of_Events_Till_Attempt',
                                             'cummean_Assessment_Num_Of_Events_Till_Attempt',
                                             'cummean_Assessment_Time_past_Till_Attempt',
                                             'cumsd_Assessment_Time_past_Till_Attempt',
                                             'cumsd_Assessment_Num_Of_Events_Till_Attempt']]
    return Event_and_Attempts


def get_frequency_per_type(data):
    import pandas as pd
    slice1 = data.loc[(data.game_time == data.Total_Game_Session_Time) &
                      (data.event_count == data.Total_Game_Session_Events),
                      ['installation_id', 'game_session', 'type', 'title', 'world', 'Total_Game_Session_Time',
                       'Total_Game_Session_Events']].drop_duplicates().copy()
    slice1['Game_Session_Order'] = slice1.groupby('installation_id')['game_session'].cumcount() + 1
    slice1['Cumulative_Time_Spent'] = slice1.groupby(['installation_id'])['Total_Game_Session_Time'].cumsum()
    type_slice = pd.pivot_table(slice1[['installation_id', 'game_session', 'type', 'Game_Session_Order']],
                                index=['installation_id', 'game_session','type', 'Game_Session_Order'],
                                columns='type',
                                aggfunc=len,
                                fill_value=0).reset_index().sort_values(['installation_id', 'Game_Session_Order'])
    type_slice['Activities_played'] = type_slice.groupby('installation_id')['Activity'].transform(np.cumsum)
    type_slice['Games_played'] = type_slice.groupby('installation_id')['Game'].transform(np.cumsum)
    type_slice['Clips__played'] = type_slice.groupby('installation_id')['Clip'].transform(np.cumsum)
    type_slice['Assessments_played'] = type_slice.groupby('installation_id')['Assessment'].transform(np.cumsum)
    type_slice_assessments = type_slice[type_slice.Assessment == 1]
    type_slice_assessments = type_slice_assessments.rename(columns={'Game_Session_Order': 'Total_Games_played'})
    type_slice_assessments = type_slice_assessments.drop(['Game', 'Clip', 'Assessment', 'Activity'], axis=1)
    type_slice_assessments = type_slice_assessments.loc[:,
                             ['installation_id', 'game_session', 'Total_Games_played', 'Clips__played',
                              'Games_played', 'Assessments_played', 'Activities_played']].drop_duplicates()
    return type_slice_assessments


def get_cumulative_time_spent_on_types(data):
    import pandas as pd
    slice1 = data.loc[(data.game_time == data.Total_Game_Session_Time) &
                      (data.event_count == data.Total_Game_Session_Events),
                      ['installation_id', 'game_session', 'type', 'title', 'world', 'Total_Game_Session_Time',
                       'Total_Game_Session_Events']].drop_duplicates().copy()
    slice1['Game_Session_Order'] = slice1.groupby('installation_id')['game_session'].cumcount() + 1
    slice1['Cumulative_Time_Spent'] = slice1.groupby(['installation_id'])['Total_Game_Session_Time'].cumsum()
    type_slice2 = pd.pivot_table(
        slice1[['installation_id', 'game_session', 'type', 'Game_Session_Order', 'Total_Game_Session_Time']],
        index=['installation_id', 'game_session', 'Game_Session_Order','type'],
        columns='type',
        values='Total_Game_Session_Time',
        aggfunc=sum,
        fill_value=0).reset_index().sort_values(['installation_id', 'Game_Session_Order'])
    type_slice2['Time_spent_on_Activities'] = type_slice2.groupby('installation_id')['Activity'].transform(np.cumsum)
    type_slice2['Time_spent_on_Games'] = type_slice2.groupby('installation_id')['Game'].transform(np.cumsum)
    type_slice2['Time_spent_on_Assessments'] = type_slice2.groupby('installation_id')['Assessment'].transform(np.cumsum)

    type_slice2['Average_Time_spent_on_Activities'] = \
        type_slice2[type_slice2.type == 'Activity'].groupby('installation_id')['Activity'].transform(
            lambda x: x.expanding().mean())
    type_slice2['Average_Time_spent_on_Activities'] = type_slice2.groupby('installation_id')[
                'Average_Time_spent_on_Activities'].fillna(method='ffill')
    type_slice2['Average_Time_spent_on_Activities'] = type_slice2['Average_Time_spent_on_Activities'].fillna(0)
    type_slice2['Average_Time_spent_on_Activities'] = type_slice2.groupby('installation_id')[
        'Average_Time_spent_on_Activities'].shift(1, fill_value=0)

    type_slice2['Average_Time_spent_on_Games'] = \
    type_slice2[type_slice2.type == 'Game'].groupby('installation_id')['Game'].transform(
            lambda x: x.expanding().mean())
    type_slice2['Average_Time_spent_on_Games'] = type_slice2.groupby('installation_id')[
                'Average_Time_spent_on_Games'].fillna(method='ffill')
    type_slice2['Average_Time_spent_on_Games'] = type_slice2['Average_Time_spent_on_Games'].fillna(0)
    type_slice2['Average_Time_spent_on_Games'] = type_slice2.groupby('installation_id')[
        'Average_Time_spent_on_Games'].shift(1, fill_value=0)


    type_slice2['Average_Time_spent_on_Assessments'] = \
    type_slice2[type_slice2.type == 'Assessment'].groupby('installation_id')['Assessment'].transform(
            lambda x: x.expanding().mean())
    type_slice2['Average_Time_spent_on_Assessments'] = type_slice2.groupby('installation_id')[
                'Average_Time_spent_on_Assessments'].fillna(method='ffill')
    type_slice2['Average_Time_spent_on_Assessments'] = type_slice2['Average_Time_spent_on_Assessments'].fillna(0)
    type_slice2['Average_Time_spent_on_Assessments'] = type_slice2.groupby('installation_id')[
        'Average_Time_spent_on_Assessments'].shift(1, fill_value=0)


    type_slice2_assessments = type_slice2[type_slice2.type == 'Assessment'].copy()
    type_slice2_assessments.loc[:, 'Total_Time_spent'] = type_slice2_assessments[
    ['Time_spent_on_Activities', 'Time_spent_on_Games','Time_spent_on_Assessments']].sum(axis=1)

    type_slice2_assessments['Average_Time_spent_on_games'] = \
    type_slice2_assessments.groupby('installation_id')['Total_Time_spent'].transform(lambda x: x.expanding().mean())

    type_slice2_assessments['Std_Time_spent_on_games'] = \
    type_slice2_assessments.groupby('installation_id')['Total_Time_spent'].transform(lambda x: x.expanding().std())
    type_slice2_assessments = type_slice2_assessments.reset_index()
    type_slice2_assessments = type_slice2_assessments.loc[:,
    ['installation_id', 'game_session',
    'Total_Time_spent',
    'Time_spent_on_Activities',
    'Time_spent_on_Games',
    'Time_spent_on_Assessments',
    'Average_Time_spent_on_Activities',
    'Average_Time_spent_on_Games',
    'Average_Time_spent_on_Assessments',
    'Average_Time_spent_on_games'
    ]].drop_duplicates()
    return type_slice2_assessments


def get_time_spent_on_diffrent_worlds(data):
    import pandas as pd
    slice1 = data.loc[(data.game_time == data.Total_Game_Session_Time) &
                      (data.event_count == data.Total_Game_Session_Events),
                      ['installation_id', 'game_session', 'type', 'title', 'world', 'Total_Game_Session_Time',
                       'Total_Game_Session_Events']].drop_duplicates().copy()
    slice1['Game_Session_Order'] = slice1.groupby('installation_id')['game_session'].cumcount() + 1
    slice1['Cumulative_Time_Spent'] = slice1.groupby(['installation_id'])['Total_Game_Session_Time'].cumsum()
    world_slice3 =  pd.pivot_table(
        slice1[['installation_id', 'game_session', 'world', 'Game_Session_Order', 'type', 'Total_Game_Session_Time']],
        index=['installation_id', 'game_session', 'type', 'Game_Session_Order'],
        columns='world',
        values='Total_Game_Session_Time',
        aggfunc=sum,
        fill_value=0).reset_index().sort_values(['installation_id', 'Game_Session_Order'])
    world_slice3['Time_spent_in_CRYSTALCAVES'] = world_slice3.groupby('installation_id')['CRYSTALCAVES'].transform(
    np.cumsum)
    world_slice3['Time_spent_in_MAGMAPEAK'] = world_slice3.groupby('installation_id')[
        'MAGMAPEAK'].transform(np.cumsum)
    world_slice3['Time_spent_in_TREETOPCITY'] = world_slice3.groupby('installation_id')['TREETOPCITY'].transform(
    np.cumsum)
    world_slice3 = world_slice3[world_slice3.type == 'Assessment']
    world_slice3 = world_slice3[['installation_id', 'game_session', 'Time_spent_in_CRYSTALCAVES',
    'Time_spent_in_MAGMAPEAK', 'Time_spent_in_TREETOPCITY']]
    return world_slice3


def substract_level(data):
    import pandas as pd
    slice1 = data.loc[(data.game_time == data.Total_Game_Session_Time) &
                      (data.event_count == data.Total_Game_Session_Events),
                      ['installation_id', 'game_session', 'type', 'title', 'world', 'Total_Game_Session_Time',
                       'Total_Game_Session_Events']].drop_duplicates().copy()
    slice1['Game_Session_Order'] = slice1.groupby('installation_id')['game_session'].cumcount() + 1
    slice1['Cumulative_Time_Spent'] = slice1.groupby(['installation_id'])['Total_Game_Session_Time'].cumsum()
    Level_slice4 = slice1.copy()
    Level_slice4['Level'] = np.where(Level_slice4['title'].str.contains("Level"),
        Level_slice4['title'].str.strip().str[-1], 0)
    Level_slice4['Level'] = pd.to_numeric(Level_slice4['Level'])
    Level_slice4 = pd.pivot_table(
        Level_slice4[['installation_id', 'game_session', 'type', 'world', 'Level', 'Game_Session_Order']],
        index=['installation_id', 'game_session', 'type', 'Game_Session_Order'],
        columns='world',
        values='Level',
        aggfunc=max,
        fill_value=0).reset_index().sort_values(['installation_id', 'Game_Session_Order'])
    Level_slice4['Level_reached_in_CRYSTALCAVES'] = Level_slice4.groupby('installation_id')['CRYSTALCAVES'].transform(
    'cummax')
    Level_slice4['Level_reached_in_MAGMAPEAK'] = Level_slice4.groupby('installation_id')['MAGMAPEAK'].transform(
    'cummax')
    Level_slice4['Level_reached_in_TREETOPCITY'] = Level_slice4.groupby('installation_id')['TREETOPCITY'].transform(
    'cummax')
    Level_slice4 = Level_slice4[Level_slice4.type == 'Assessment']
    Level_slice4['Total_Level'] = Level_slice4['Level_reached_in_CRYSTALCAVES'] + \
                                  Level_slice4['Level_reached_in_MAGMAPEAK'] + \
                                  Level_slice4['Level_reached_in_TREETOPCITY']
    Level_slice4 = Level_slice4[['installation_id', 'game_session',
                                 'Level_reached_in_CRYSTALCAVES',
                                 'Level_reached_in_MAGMAPEAK',
                                 'Level_reached_in_TREETOPCITY',
                                 'Total_Level']]
    return Level_slice4





def create_world_time_assesstitle_Dummies(data):
    def dummyfy(df, colname):
        df[colname] = pd.Categorical(df[colname])
        dummies = pd.get_dummies(df[colname])
        dummies.columns = [str(i) + '_' + colname for i in dummies.columns]
        df = pd.concat([df,dummies], axis=1)
        del df[colname]
        return df

    import pandas as pd
    Assessments = data[data.type == 'Assessment'].copy()
    Assessments['timestamp'] = pd.to_datetime(Assessments['timestamp'], format="%Y-%m-%d %H:%M")
    Assessments = Assessments.sort_values('timestamp', ascending=True)
    Assessments = Assessments.drop_duplicates()
    Assessments = convert_datetime(Assessments)
    del Assessments['timestamp']
    Assessments['title'] = Assessments['title'].str.rstrip(' (Assessment)')
    Assessments = Assessments.set_index(['installation_id', 'game_session'])
    Assessments = Assessments[['title', 'world', 'hour',  'dayofweek']]
    Assessments = dummyfy(df=Assessments, colname='title')
    Assessments = dummyfy(df=Assessments, colname='world')
    Assessments = dummyfy(df=Assessments, colname='hour')
    Assessments = dummyfy(df=Assessments, colname='dayofweek')
    Assessments = Assessments.reset_index()
    Assessments = Assessments.drop_duplicates()
    return Assessments


def get_last_assessment(data):
    Assess = data[data.type == 'Assessment'].copy()
    Assess = Assess[['installation_id', 'game_session']]
    Assess["To_Predict"] = 0
    Assess['order'] = Assess.groupby('installation_id')[
        'game_session'].transform(lambda x: np.round(pd.factorize(x)[0] + 1))
    Assess['LastGame'] = Assess.groupby('installation_id')['order'].transform('max')
    Assess.loc[Assess.order == Assess.LastGame, "To_Predict"] = 1
    Assess = Assess.drop_duplicates()
    Assess = Assess.loc[Assess.To_Predict == 1, ['installation_id', 'game_session']]
    return Assess


def get_all_but_last_assessment(data):
    Assess = data[data.type == 'Assessment'].copy()
    Assess['Attempt'] = 0
    AssessmentTitles = Assess['title'].unique()
    AssessmentTitles1 = [item for item in AssessmentTitles if item not in ['Bird Measurer (Assessment)']]
    Assess.loc[Assess['event_code'].isin([4100]) & Assess.title.isin(AssessmentTitles1), 'Attempt'] = 1
    Assess.loc[
    Assess['event_code'].isin([4110]) & Assess.title.isin(['Bird Measurer (Assessment)']), 'Attempt'] = 1
    Assess.loc[
    Assess['event_data'].str.contains('false') & Assess['Attempt'] == 1, 'IsAttemptSuccessful'] = 0
    Assess.loc[
    Assess['event_data'].str.contains('true') & Assess['Attempt'] == 1, 'IsAttemptSuccessful'] = 1
    Assess['timestamp'] = pd.to_datetime(Assess['timestamp'], format="%Y-%m-%d %H:%M")
    Assess['Attempts'] = Assess.groupby(['installation_id', 'game_session'])['Attempt'].transform(np.sum)
    Assess['Success'] = Assess.groupby(['installation_id', 'game_session'])['IsAttemptSuccessful'].transform(np.sum)
    Assess = Assess.set_index(['installation_id', 'game_session'])
    Assess = Assess[['Attempts', 'Success', 'timestamp']]
    ratio = Assess['Success'] / Assess['Attempts']
    conditions = [
    (ratio == 1),
    (ratio == 0.5),
    (ratio < 0.5) & (ratio > 0),
    (ratio == 0)]
    choices = [3, 2, 1, 0]
    Assess['accuracy_group'] = np.select(conditions, choices)
    Assess['accuracy'] = ratio
    Assess = Assess.reset_index()
    Assess = Assess.sort_values(['installation_id', 'timestamp'])
    Assess = Assess[[ 'accuracy', 'accuracy_group', 'installation_id', 'game_session']]
    Assess["To_Predict"] = 0
    Assess['order'] = Assess.groupby('installation_id')['game_session'].transform(lambda x: np.round(pd.factorize(x)[0] + 1))
    Assess['LastGame'] = Assess.groupby('installation_id')['order'].transform('max')
    Assess.loc[Assess.order == Assess.LastGame - 1, "To_Predict"] = 1
    Assess = Assess.drop('accuracy', axis=1)
    Assess = Assess.drop_duplicates()
    Assess = Assess.loc[Assess.To_Predict != 1, :]
    return Assess[['installation_id', 'game_session', 'accuracy_group']]



def get_event_code_history(data):
    his = data[['installation_id', 'timestamp','game_session','type', 'event_code']].copy()
    his = his.sort_values(['installation_id', 'timestamp'])
    his['order'] = his.groupby('installation_id')['game_session'].transform(lambda x: np.round(pd.factorize(x)[0] + 1))
    Events = pd.pivot_table(his,
        index=['installation_id', 'game_session', 'order','type'],
        columns='event_code',
        values='event_code',
        aggfunc='nunique',
        fill_value=0).reset_index().sort_values(['installation_id', 'order'])

    eventList = Events.columns[~Events.columns.isin(['installation_id', 'game_session', 'order','type'])]
    Events.loc[:,eventList] =  Events.groupby('installation_id')[eventList].cumsum()
    Events = Events[Events.type == 'Assessment']
    event_code_history = Events.drop(['order','type'], axis=1)
    return event_code_history

# def get_success_rate_by_world:
#     import pandas as pd
#     df = data[data.type == 'Assessment'].copy()
#     df['Success_Rate'] = df.groupby(['installation_id', 'game_session', 'world'])['Attempt', 'IsAttemptSuccessful'].\
#         apply(lambda x,y: sum(y)/sum(x))
#     return bla

def calculate_accuracy_group(data):
        dt = data.copy()
        dt['Attempts'] = dt.groupby(['installation_id', 'game_session'])['Attempt'].transform(np.sum)
        dt['Success'] = dt.groupby(['installation_id', 'game_session'])['IsAttemptSuccessful'].transform(np.sum)
        dt = dt.set_index(['installation_id', 'game_session'])
        dt = dt[['Attempts', 'Success', 'timestamp']]
        ratio = dt['Success'] / dt['Attempts']
        conditions = [
            (ratio == 1),
            (ratio == 0.5),
            (ratio < 0.5) & (ratio > 0),
            (ratio == 0)]
        choices = [3, 2, 1, 0]
        dt['accuracy_group'] = np.select(conditions, choices)
        dt = dt.reset_index()
        dt = dt[['installation_id', 'game_session','accuracy_group']].drop_duplicates()
        return dt



def create_features(data):
    data['timestamp'] = pd.to_datetime(data['timestamp'], format="%Y-%m-%d %H:%M")
    data = data.sort_values(['installation_id', 'timestamp', 'game_session'], ascending=[True, True, True])
    Inst_Group = data.groupby('installation_id')
    Inst_Game_Group = data.groupby(['installation_id', 'game_session'])
    # initial measures
    data['Total_Game_Session_Time'] = Inst_Game_Group['game_time'].transform(np.max)
    data['Total_Game_Session_Events'] = Inst_Game_Group['event_count'].transform(np.max)
    data['Assessments_played_Counter'] = data[data.type == 'Assessment'].groupby('installation_id')[
        'game_session'].transform(lambda x: np.round(pd.factorize(x)[0] + 1))

    trainTitles = data['title'].unique()
    trainTitles_sub = [item for item in trainTitles if item not in ['Bird Measurer (Assessment)']]
    AttemptIndicator = (data.type == 'Assessment') & \
                       ((data.event_code.isin([4100]) & data.title.isin(trainTitles_sub)) |
                        (data.event_code.isin([4110]) & data.title.isin(['Bird Measurer (Assessment)'])))
    data['Attempt'] = 0
    data.loc[AttemptIndicator, 'Attempt'] = 1
    SuccessfulAttemptIndicator = data['event_data'].str.contains('true') & AttemptIndicator
    data['IsAttemptSuccessful'] = 0
    data.loc[SuccessfulAttemptIndicator, 'IsAttemptSuccessful'] = 1
    ag = calculate_accuracy_group(data)
    data['Cumulative_Attempts'] = Inst_Group['Attempt'].transform(np.cumsum)
    data['Cumulative_Successes'] = Inst_Group['IsAttemptSuccessful'].transform(np.nancumsum)
    data['Cumulative_Fails'] = data['Cumulative_Attempts'] - data['Cumulative_Successes']
    data['Assessment_Session_Time'] = data[data.type == 'Assessment'].groupby(['installation_id', 'game_session'])[
        'game_time'].transform(np.max)
    data['Assessment_NumberOfEvents'] = data[data.type == 'Assessment'].groupby(['installation_id', 'game_session'])[
        'event_count'].transform(np.max)
    # Previous Accuracy
    previous_accuracy_metrics = get_previous_ac_metrics(data)
    print('previous_accuracy_metrics')
    # Slice 2
    Number_of_attemps_and_successes = get_past_attemps_and_successes(data)
    print('Number_of_attemps_and_successes')
    # Slice 3
    past_assessment_time_events_and_metrics = get_past_assessment_time_events_and_metrics(data)
    print('past_assessment_time_events_and_metrics')
    # Event_and_Attempts
    print('pre_time_till_attempt_metrics')
    Number_of_games_played_per_type = get_frequency_per_type(data)
    print('Number_of_games_played_per_type')
    Time_spent_on_games_metrics = get_cumulative_time_spent_on_types(data)
    print('Time_spent_on_games_metrics')
    print('time_spent_on_diffrent_worlds')
    Level_reached = substract_level(data)
    print('Level_reached')
    world_time_gametitles_dummies = create_world_time_assesstitle_Dummies(data)
    print('world_time_gametitles_dummies')

    words_time_spent = get_time_spent_on_diffrent_worlds(data)
    print('words_time_spent')
    events_and_teme_before_attampt = get_prev_events_and_time_till_attempt(data)

    Sets = [Number_of_games_played_per_type,
            Time_spent_on_games_metrics,
            world_time_gametitles_dummies,
            Number_of_attemps_and_successes,
            past_assessment_time_events_and_metrics,
            Level_reached,
            previous_accuracy_metrics,
            events_and_teme_before_attampt,
            words_time_spent,

            ag]
    FinalData = reduce(lambda left, right: pd.merge(left, right, how='inner', on=['installation_id', 'game_session']),
                       Sets)
    return FinalData



################################################# Create train #########################################################

Train_dataset = create_features(train)
Test_dataset = create_features(test)

Train = pd.merge(train_ids , Train_dataset, on = ['installation_id', 'game_session'], how = 'inner')
Test = pd.merge(test_ids , Test_dataset, on = ['installation_id', 'game_session'], how = 'inner')

X_train= Train.drop('accuracy_group', axis = 1).set_index(['installation_id', 'game_session'])
Y_train= np.asarray(Train['accuracy_group'])


To_predict = Test.loc[Test.Assessments_played == Test.groupby('installation_id')['Assessments_played'].transform('max'),['game_session']]
X_test = Test.loc[~Test.game_session.isin(To_predict.game_session),] # remove ~ for submission
X_test = X_test.drop('accuracy_group', axis = 1).set_index(['installation_id', 'game_session'])

Y_test= np.asarray(Test.loc[~Test.game_session.isin(To_predict.game_session),'accuracy_group'])# remove ~ for submission



################################################# Modelling  things ####################################################
from sklearn.metrics import  cohen_kappa_score
from sklearn.ensemble import RandomForestClassifier
rf = RandomForestClassifier(random_state = 42)
from pprint import pprint
# Look at parameters used by our current forest
print('Parameters currently in use:\n')
pprint(rf.get_params())


params = {'bootstrap': True,
 'class_weight': None,
 'criterion': 'gini',
 'max_depth': None,
 'max_features': 'auto',
 'max_leaf_nodes': None,
 'min_impurity_decrease': 0.0,
 'min_impurity_split': None,
 'min_samples_leaf': 1,
 'min_samples_split': 2,
 'min_weight_fraction_leaf': 0.0,
 'n_estimators': 'warn',
 'n_jobs': None,
 'oob_score': False,
 'random_state': 42,
 'verbose': 0,
 'warm_start': False}



from sklearn.model_selection import RandomizedSearchCV
# Number of trees in random forest
n_estimators = [int(x) for x in np.linspace(start = 200, stop = 2000, num = 10)]
# Number of features to consider at every split
max_features = ['auto', 'sqrt']
# Maximum number of levels in tree
max_depth = [int(x) for x in np.linspace(10, 110, num = 11)]
max_depth.append(None)
# Minimum number of samples required to split a node
min_samples_split = [2, 5, 10]
# Minimum number of samples required at each leaf node
min_samples_leaf = [1, 2, 4]
# Method of selecting samples for training each tree
bootstrap = [True, False]
# Create the random grid
random_grid = {'n_estimators': n_estimators,
               'max_features': max_features,
               'max_depth': max_depth,
               'min_samples_split': min_samples_split,
               'min_samples_leaf': min_samples_leaf,
               'bootstrap': bootstrap}
pprint(random_grid)



# Use the random grid to search for best hyperparameters
# First create the base model to tune
rf = RandomForestClassifier()
# Random search of parameters, using 3 fold cross validation,
# search across 100 different combinations, and use all available cores
rf_random = RandomizedSearchCV(estimator = rf, param_distributions = random_grid, n_iter = 100, cv = 3, verbose=2, random_state=42, n_jobs = -1)
# Fit the random search model
rf_random.fit(X_train, Y_train)
rf_random.best_params_
{'n_estimators': 1400,
 'min_samples_split': 5,
 'min_samples_leaf': 4,
 'max_features': 'sqrt',
 'max_depth': 80,
 'bootstrap': True}

def evaluate(model, test_features, test_labels):
    predictions = model.predict(test_features)
    kappa  = cohen_kappa_score(test_labels, predictions, weights='quadratic')
    print('Model Performance')
    print('kappa: {:0.4f} degrees.'.format(kappa))
    return kappa


base_model = RandomForestClassifier(n_estimators=50, random_state=42)
base_model.fit(X_train, Y_train)
base_accuracy = evaluate(base_model, X_test, Y_test)

best_random = RandomForestClassifier(n_estimators = 1400,
                            min_samples_split =  5,
                            min_samples_leaf = 4,
                            max_features = 'sqrt',
                            max_depth = 80,
                            bootstrap = True)
best_random.fit(X_train, Y_train)
random_accuracy = evaluate(best_random, X_test, Y_test)

print('Improvement of {:0.2f}%.'.format(100 * (random_accuracy - base_accuracy) / base_accuracy))









model = RandomForestClassifier(n_estimators = 1400,
                            min_samples_split =  5,
                            min_samples_leaf = 4,
                            max_features = 'sqrt',
                            max_depth = 80,
                            bootstrap = True)
model.fit(X_train, Y_train)

predictions = model.predict(X_test)

submission = pd.DataFrame({"installation_id": X_test.reset_index(1).index.values,
                           "accuracy_group": predictions})
submission = pd.DataFrame({"installation_id": X_test.reset_index(1).index.values,
                           "accuracy_group": Y_pred_test})

submission.to_csv("submission.csv", index=False)