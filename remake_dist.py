# Imports basics

import numpy as np
import pandas as pd
import h5py
import json
import uproot
import os,sys

# Defines important variables

particle_num = 50
fill_factor = 1.0
max_files_sig = 125
max_files_bkg = 1000
sigindex = 0
bkgindex = 0
pt_range = [200., 500.]
mass_range = [20., 80.]

# Opens json files for signal and background

with open("pf.json") as jsonfile:
    payload = json.load(jsonfile)
    weight = payload['weight']
    features_track = payload['features_track']
    conversion_track = payload['conversion_track']
    features_tower = payload['features_tower']
    conversion_tower = payload['conversion_tower']
    ss = payload['ss_vars']

# Creates the column names of the final data frame

part_features = []
for iVar in features_track:
    for i0 in range(particle_num):
        part_features.append(iVar + str(i0))

columns = ss + weight + part_features + ['label']

# Unnests a pandas dataframe


def unnest(df, explode):
    """unnest(DataFrame,List)"""
    idx = df.index.repeat(df[explode[0]].str.len())
    df1 = pd.concat([
        pd.DataFrame({x: np.concatenate(df[x].values)}) for x in explode], axis=1)
    df1.index = idx

    return df1.join(df.drop(explode, 1), how='left')


# Makes a data set where the distribution of the background across mass and pT is similar to that of the signal

def remake(iFiles_sig, iFiles_bkg, iFile_out):
    """remake(list[array(nxm),...], list[array(nxs),...], str)"""

    # Creates the signal data frame

    df_sig_to_concat = []
    for sig in iFiles_sig:
        file_list = os.listdir(payload['samples'][sig])
        for i in range(sigindex*max_files_sig,min(len(file_list),(sigindex+1)*max_files_sig)):
            if i%10==0: print('%i/%i'%(i,len(file_list)))
            data_set = payload['samples'][sig]+file_list[i]
            arr_sig_to_concat_temp = []
            file1 = uproot.open(data_set)
            tree = file1['tree']
            branches = tree.arrays()
            event_num = len(branches['jet_pt'])
            df_sig_tower = pd.DataFrame({column: list(branches[conversion_tower[column]]) for column in features_tower})
            df_sig_tower = unnest(df_sig_tower, features_tower)
            df_sig_track = pd.DataFrame({column: list(branches[conversion_track[column]]) for column in features_track})
            df_sig_track = unnest(df_sig_track, features_track)
            for event in range(event_num):
                df_sig_temp = pd.concat([df_sig_track.loc[event], df_sig_tower.loc[event]], sort=False).fillna(0)
                df_sig_temp = df_sig_temp.sort_values("pt", ascending=False).head(particle_num)
                arr_sig_temp = df_sig_temp.values.flatten('F')
                arr_sig_to_concat_temp.append(arr_sig_temp)
            arr_sig_temp = np.vstack(arr_sig_to_concat_temp)
            df_sig_temp = pd.DataFrame(arr_sig_temp, columns=part_features)
            for column in ss + weight:
                df_sig_temp[column] = branches[column].reshape(-1, 1)
            df_sig_temp['label'] = 1
            df_sig_temp = df_sig_temp[columns]
            pt_col = df_sig_temp[weight[0]].values.reshape(-1, 1)
            mass_col = df_sig_temp[weight[1]].values.reshape(-1, 1)
            df_sig_temp = df_sig_temp[np.logical_and(np.logical_and(np.greater(pt_col, pt_range[0]), np.less(pt_col, pt_range[1])), np.logical_and(np.greater(mass_col, mass_range[0]), np.less(mass_col, mass_range[1])))]
            df_sig_to_concat.append(df_sig_temp[columns].astype('float32'))
    df_sig = pd.concat(df_sig_to_concat)

    # Calculates the distribution of the signal

    sig_hist, _x, _y = np.histogram2d(df_sig[weight[0]], df_sig[weight[1]], bins=20,
                                      range=np.array([pt_range, mass_range]))
    print(sig_hist)
    print(np.sum(sig_hist))

    # Creates output file
    #df_sig = df_sig[columns].astype('float32')
    #df_sig = df_sig[~(np.sum(np.isinf(df_sig.values), axis=1) > 0)] 
    print(list(df_sig.columns))

    # Open HDF5 file and write dataset

    h5_file = h5py.File(iFile_out+"_sig.z", 'w')
    h5_file.create_dataset('taggerInputs', data=df_sig.values, compression='lzf')
    h5_file.close()
    del h5_file
    del df_sig

    # Creates the background data frame

    df_remade_bkg = pd.DataFrame(columns=columns)
    for bkg in iFiles_bkg:
        df_bkg_to_concat = []
        file_list = os.listdir(payload['samples'][bkg])
        for i in range(bkgindex*max_files_bkg,min(len(file_list),(bkgindex+1)*max_files_bkg)):
            if i%10==0: print('%i/%i'%(i,len(file_list)))
            data_set = payload['samples'][bkg]+file_list[i]
            arr_bkg_to_concat_temp = []
            file1 = uproot.open(data_set)
            tree = file1['tree']
            branches = tree.arrays()
            event_num = len(branches['jet_pt'])
            df_bkg_tower = pd.DataFrame({column: list(branches[conversion_tower[column]]) for column in features_tower})
            df_bkg_tower = unnest(df_bkg_tower, features_tower)
            df_bkg_track = pd.DataFrame({column: list(branches[conversion_track[column]]) for column in features_track})
            df_bkg_track = unnest(df_bkg_track, features_track)
            for event in range(event_num):
                df_bkg_temp = pd.concat([df_bkg_track.loc[event], df_bkg_tower.loc[event]], sort=False).fillna(0)
                df_bkg_temp = df_bkg_temp.sort_values("pt", ascending=False).head(particle_num)
                arr_bkg_temp = df_bkg_temp.values.flatten('F')
                arr_bkg_to_concat_temp.append(arr_bkg_temp)
            arr_bkg_temp = np.vstack(arr_bkg_to_concat_temp)
            df_bkg_temp = pd.DataFrame(arr_bkg_temp, columns=part_features)
            for column in ss + weight:
                df_bkg_temp[column] = branches[column].reshape(-1, 1)
            df_bkg_temp['label'] = 0
            df_bkg_temp = df_bkg_temp[columns]
            df_bkg_to_concat.append(df_bkg_temp[columns].astype('float32'))
        df_bkg = pd.concat(df_bkg_to_concat)

        # Adds background based on signal distribution until fill factor is reached

        for ix in range(len(_x) - 1):
            print(len(_x))
            for iy in range(len(_y) - 1):
                df_remade_bkg = pd.concat([df_remade_bkg, df_bkg[(
                            (df_bkg[weight[0]] >= _x[ix]) & (df_bkg[weight[0]] < _x[ix + 1]) & (
                                df_bkg[weight[1]] >= _y[iy]) & (df_bkg[weight[1]] < _y[iy + 1]))].head(
                    int(int(sig_hist[ix, iy]) * fill_factor))], ignore_index=True)

    # Shows fill factor per bin

    bkg_hist, _, _ = np.histogram2d(df_remade_bkg[weight[0]], df_remade_bkg[weight[1]], bins=20,
                                    range=np.array([pt_range, mass_range]))
    print(np.nan_to_num(np.divide(bkg_hist, sig_hist)))

    # Creates output file

    #df_remade_bkg = df_remade_bkg[columns].astype('float32')
    #df_remade_bkg = df_remade_bkg[~(np.sum(np.isinf(df_remade_bkg.values), axis=1) > 0)]
    print(list(df_remade_bkg.columns))
    # Open HDF5 file and write dataset

    h5_file = h5py.File(iFile_out+"_bkg.z", 'w')
    h5_file.create_dataset('taggerInputs', data=df_remade_bkg.values, compression='lzf')
    h5_file.close()
    del h5_file
    del df_bkg
    del df_remade_bkg


# Remakes data sets
signal_list = ['ZPrimeToQQ_M50_nom']
background_list = ['QCD_HT500to700_nom','QCD_HT700to1000_nom']
output_name = "test%i_nom"%sigindex
remake(signal_list, background_list, output_name)

signal_list = ['ZPrimeToQQ_M50_down']
background_list = ['QCD_HT500to700_down','QCD_HT700to1000_down']
output_name = "test%i_down"%sigindex
remake(signal_list, background_list, output_name)
