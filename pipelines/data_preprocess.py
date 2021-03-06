# coding=utf-8

"""
Created by jayvee on 17/3/3.
https://github.com/JayveeHe
"""
import csv
import gzip
import os
import sys

import cPickle
import numpy as np
from sklearn import preprocessing
from sklearn.preprocessing import Imputer
import pandas as pd

import json

PROJECT_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
print 'Related File:%s\t----------project_path=%s' % (__file__, PROJECT_PATH)
sys.path.append(PROJECT_PATH)

import multiprocessing

from utils.logger_utils import data_process_logger
from pipelines.train_models import DATA_ROOT


def load_csv_data(csv_path, normalize=True, is_combine=False):
    """

    Args:
        csv_path:
        normalize: 是否进行标准化
        is_combine: 是否进行norm特征和的拼接

    Returns:

    """
    from sklearn import preprocessing
    with open(csv_path, 'rb') as fin:
        data_process_logger.info('loading file: %s' % csv_path)
        datas = []
        temp_list = []
        score_list = []
        date_list = []
        id_list = []
        vec_list = []
        for line in fin:
            line = line.strip()
            tmp = line.split(',')
            stock_id = tmp[0]
            trade_date = tmp[1]
            score = eval(tmp[2])
            score_list.append(score)
            vec_value = [eval(a) for a in tmp[3:]]
            vec_list.append(vec_value)
            date_list.append(trade_date)
            id_list.append(stock_id)
            temp_list.append((stock_id, trade_date, score, vec_value))
        # all not normalize
        if not normalize:
            avg = np.mean(score_list)
            std = np.std(score_list)
            for item in temp_list:
                normalize_score = (item[2] - avg) / std
                datas.append((item[0], item[1], normalize_score, item[3]))
            return datas
        else:
            score_scale = preprocessing.scale(score_list)
            score_scale_list = list(score_scale)
            vec_scale = preprocessing.scale(vec_list)
            vec_scale_list = vec_scale
            for i in range(len(id_list)):
                if is_combine:
                    datas.append((id_list[i], date_list[i], score_scale_list[i], list(vec_scale_list[i]) + vec_list[i]))
                else:
                    datas.append((id_list[i], date_list[i], score_scale_list[i], list(vec_scale_list[i])))
            # avg = np.mean(score_list)
            #            std = np.std(score_list)
            #            for item in temp_list:
            #                normalize_score = (item[2] - avg) / std
            #                datas.append((item[0], item[1], normalize_score, item[3]))
            return datas


def normalize_data(input_data):
    """
    author:zxj
    func:normalize
    input:origin input data
    return:tuple of (normalize_score,fea_vec,id,date)
    """
    output_data = []
    from itertools import groupby
    import numpy as np
    score_list = [(input_data[i][1], (input_data[i][2], input_data[i][3], input_data[i][0])) \
                  for i in range(len(input_data))]
    score_group_list = groupby(score_list, lambda p: p[0])
    # for key,group in score_group_list:
    #	print list(group)[0][1]
    for key, group in score_group_list:
        temp_list = list(group)
        score_list = [a[1][0] for a in temp_list]
        score_list = np.array(score_list).astype(np.float)
        print "the score list is %s" % (''.join(str(v) for v in score_list))
        vec_list = [a[1][1] for a in temp_list]
        id_list = [a[1][2] for a in temp_list]
        avg = np.mean(score_list)
        std = np.std(score_list)
        for i in range(len(score_list)):
            # normalize
            normalize_score = (score_list[i] - avg) / std
            output_data.append((normalize_score, vec_list[i], id_list[i], key))
    return output_data


def infer_missing_datas(fin_csv_path, fout_pickle_path, is_norm=False, is_norm_score=True):
    """
    处理NaN数据,并将处理后的数据分别存储为csv与pickle文件
    Args:
        is_norm: 是否进行标准化
        is_norm_score: 是否对score进行标准化
        fin_csv_path:
        fout_pickle_path:

    Returns:

    """
    with open(fin_csv_path, 'rb') as fin_csv, \
            open(fout_pickle_path, 'wb') as fout_pickle:
        origin_datas = []
        reader = csv.reader(fin_csv)
        # writer = csv.writer(fout_csv)
        count = 1
        n_feature = 4563
        data_process_logger.info('start reading %s' % fin_csv_path)
        for line in reader:
            if len(line) == n_feature:
                single_vec_value = [float(i) if i != 'NaN' else np.nan for i in line]
                # process the 453th col, remove future feature.
                single_vec_value = single_vec_value[:453] + single_vec_value[454:]
                origin_datas.append(single_vec_value)
                # data_process_logger.info('handled line %s' % count)

            else:
                data_process_logger.info(
                    'casting line: %s in file %s, it has %s features while the first line has %s' % (
                        count, fin_csv_path, len(line), n_feature))
            count += 1
        # inferring missing data
        imp = Imputer(missing_values='NaN', strategy='mean', axis=0)
        imp.fit(origin_datas)
        transformed_datas = imp.transform(origin_datas)
        if is_norm:
            # standardising datas
            stock_ids = transformed_datas[:, 0]
            stock_scores = transformed_datas[:, 1]
            vec_values = transformed_datas[:, 2:]
            scaled_vec_values = preprocessing.scale(vec_values)
            if is_norm_score:
                stock_scores = preprocessing.scale(stock_scores)
            transformed_datas = (stock_ids.tolist(), stock_scores.tolist(), scaled_vec_values.tolist())  # 存为tuple
        # writting transformed datas
        # data_process_logger.info('start writting %s' % fout_csv_path)
        data_process_logger.info('start dumping %s' % fout_pickle_path)
        # transformed_datas = transformed_datas.tolist()  # 转为list进行存储
        cPickle.dump(transformed_datas, fout_pickle, protocol=2)
        data_process_logger.info('%s done' % fin_csv_path)
        return transformed_datas


def infer_missing_datas_to_gzip(fin_csv_path, fout_gzip_path, is_norm=True, is_norm_score=True):
    """
    处理NaN数据,并将处理后的数据分别存储为csv与pickle文件
    Args:
        is_norm: 是否进行标准化
        is_norm_score: 是否对score进行标准化
        fin_csv_path:
        fout_gzip_path:

    Returns:

    """
    with open(fin_csv_path, 'rb') as fin_csv, \
            gzip.open(fout_gzip_path, 'wb') as fout_gzip:
        origin_datas = []
        reader = csv.reader(fin_csv)
        # writer = csv.writer(fout_csv)
        count = 1
        n_feature = 4563
        data_process_logger.info('start reading %s' % fin_csv_path)
        for line in reader:
            if len(line) == n_feature:
                single_vec_value = [float(i) if i != 'NaN' else np.nan for i in line]
                # process the 453th col, remove future feature.
                # single_vec_value = single_vec_value[:453] + single_vec_value[454:]
                origin_datas.append(single_vec_value)
                # data_process_logger.info('handled line %s' % count)

            else:
                data_process_logger.info(
                    'casting line: %s in file %s, it has %s features while the first line has %s' % (
                        count, fin_csv_path, len(line), n_feature))
            count += 1
        # inferring missing data
        imp = Imputer(missing_values='NaN', strategy='mean', axis=0)
        imp.fit(origin_datas)
        transformed_datas = imp.transform(origin_datas)
        stock_ids = []
        stock_scores = []
        scaled_vec_values = []
        stock_ids = transformed_datas[:, 0]
        stock_scores = transformed_datas[:, 1]
        scaled_vec_values = transformed_datas[:, 2:]
        if is_norm:
            # standardising datas
            scaled_vec_values = preprocessing.scale(scaled_vec_values)
            if is_norm_score:
                stock_scores = preprocessing.scale(stock_scores)
        # transformed_datas = (stock_ids.tolist(), stock_scores.tolist(), scaled_vec_values.tolist())  # 存为tuple
        # writting transformed datas
        # data_process_logger.info('start writting %s' % fout_csv_path)
        data_process_logger.info('start saving %s' % fout_gzip_path)
        # transformed_datas = transformed_datas.tolist()  # 转为list进行存储
        # cPickle.dump(transformed_datas, fout_gzip, protocol=2)
        for line_index in xrange(len(stock_ids)):
            stock_id = stock_ids[line_index]
            stock_score = stock_scores[line_index]
            scaled_vec_value = scaled_vec_values[line_index]
            tmp_vec = [int(stock_id)] + [float(stock_score)] + scaled_vec_value.tolist()
            tmp_vec_str = [str(a) for a in tmp_vec]
            try:
                # tmp_list_vec = tmp_vec.tolist()
                tmp_line = ','.join(tmp_vec_str)
                fout_gzip.write(tmp_line + '\n')
                if line_index % 100 == 0:
                    print 'line %s join success' % line_index
            except Exception, e:
                print 'line %s join failed, details=%s' % (line_index, e)
        data_process_logger.info('%s done' % fin_csv_path)
        return transformed_datas


def parallel_inferring(file_number_list, process_count=12, is_norm=True, is_norm_score=True, data_root_path=None):
    """
    并行化进行数据清理
    Returns:

    """
    data_process_logger.info('Start parallel inferring, process count = %s' % process_count)
    proc_pool = multiprocessing.Pool(process_count)
    # multi_results = []
    for i in file_number_list:
        # data_process_logger.info('loading %s file' % i)
        # csv_path = '%s/datas/%s.csv' % (PROJECT_PATH, i)
        if not data_root_path:
            data_root_path = '%s/datas/Quant-Datas-2.0' % (DATA_ROOT)
        fin_csv_path = '%s/%s.csv' % (data_root_path, i)
        if is_norm:
            # fout_csv_path = '%s/transformed_datas/%s_trans_norm.csv' % (data_root_path, i)
            # fout_pickle_path = '%s/pickle_datas/%s_trans_norm.pickle' % (data_root_path, i)
            fout_gzip_path = '%s/gzip_datas_norm/%s_trans_norm.gz' % (data_root_path, i)
        else:
            # fout_csv_path = '%s/transformed_datas/%s_trans.csv' % (data_root_path, i)
            # fout_pickle_path = '%s/pickle_datas/%s_trans.pickle' % (data_root_path, i)
            fout_gzip_path = '%s/gzip_datas/%s_trans.gz' % (data_root_path, i)
        # data_res = proc_pool.apply_async(infer_missing_datas_to_gzip,
        #                                  args=(fin_csv_path, fout_gzip_path, is_norm, is_norm_score))
        data_res = proc_pool.apply_async(infer_data_pandas,
                                         args=(fin_csv_path, fout_gzip_path))
        # multi_results.append(data_res)
        # datas = load_csv_data(csv_path, normalize=True, is_combine=True)
        # train_datas += datas
    proc_pool.close()
    proc_pool.join()
    data_process_logger.info('Done with %s files' % len(file_number_list))


def prepare_pair_data(single_file_path, output_path):
    with open(single_file_path, 'r') as fin, gzip.open(output_path, 'w') as fout:
        csv_item = pd.read_csv(fin)
        csv_item.fillna(csv_item.mean())
        count = 0
        normed_data = csv_item.apply(lambda x: (x - np.min(x)) / (np.max(x) - np.min(x)))  # min/max 归一化
        for line in normed_data.iterrows():
            data = line[1].values.tolist()
            fout.write(json.dumps(data) + '\n')
            count += 1
            if count % 500 == 0:
                print '%s done in %s' % (count, single_file_path)
                # item = line.strip().split()


def infer_data_pandas(single_file_path, output_path):
    with open(single_file_path, 'r') as fin, gzip.open(output_path, 'w') as fout:
        csv_item = pd.read_csv(fin)
        csv_item.fillna(csv_item.mean())
        count = 0
        normed_data = csv_item.apply(lambda x: (x - np.min(x)) / (np.max(x) - np.min(x)))  # min/max 归一化
        normed_list = np.array(normed_data).tolist()
        for line in normed_list:
            data = line
            fout.write(json.dumps(data) + '\n')
            count += 1
            if count % 500 == 0:
                print '%s done in %s' % (count, single_file_path)


if __name__ == '__main__':
    # print len(load_csv_data('%s/datas/%s.csv' % (PROJECT_PATH, 1), is_combine=True))
    # infer_missing_datas_to_gzip(
    #     fin_csv_path='/Users/jayveehe/git_project/FundDataAnalysis/pipelines/datas/tmp_data/9.csv',
    #     fout_gzip_path='/Users/jayveehe/git_project/FundDataAnalysis/pipelines/datas/tmp_data/9_non_normvec_non_normscore.gz',
    #     is_norm=True, is_norm_score=False)
    # pickle_data = cPickle.load()
    # print len(pickle_data)
    # infer_data_pandas('/Users/jayveehe/git_project/FundDataAnalysis/pipelines/datas/999.csv',
    #                   'datas/gzip_datas/999_trans.gz')
    d_r_p = '%s/datas/Quant_Datas_v4.0' % (DATA_ROOT)
    parallel_inferring(file_number_list=range(1, 1511), process_count=20, is_norm=True, is_norm_score=True,
                       data_root_path=d_r_p)
