# coding=utf-8

"""
Created by jayvee on 17/2/23.
https://github.com/JayveeHe
"""
import os
import sys
import pickle

import cPickle

from sklearn import grid_search
from sklearn.cross_validation import cross_val_score
from sklearn.ensemble import GradientBoostingRegressor
import numpy as np

project_path = os.path.dirname(os.path.abspath(__file__))
print 'Related File:%s\t----------project_path=%s' % (__file__, project_path)
sys.path.append(project_path)

from logger_utils import data_process_logger


def load_csv_data(csv_path):
    with open(csv_path, 'rb') as fin:
        datas = []
        for line in fin:
            line = line.strip()
            tmp = line.split(',')
            stock_id = tmp[0]
            trade_date = tmp[1]
            score = eval(tmp[2])
            vec_value = [eval(a) for a in tmp[3:]]
            datas.append((stock_id, trade_date, score, vec_value))
        return datas


def train_model(input_datas, output_path='./datas/gbrt_model.mod'):
    label_set = []
    vec_set = []
    for i in range(len(input_datas)):
        label_set.append(input_datas[i][2])
        vec_set.append(input_datas[i][3])
    gbrt_model = GradientBoostingRegressor(n_estimators=301, loss='lad')
    print 'training'
    gbrt_model.fit(vec_set[:], label_set[:])
    print 'saving'
    with open(output_path, 'wb') as fout:
        pickle.dump(gbrt_model, fout)
    return gbrt_model


def train_regression_age_model(input_xlist, input_ylist, model_label):
    """
    train age regression model
    :param input_xlist:
    :param input_ylist:
    :param model_label:
    :return:
    """
    from sklearn import svm
    from sklearn.ensemble import GradientBoostingRegressor
    data_process_logger.info('loading model')
    input_xlist = np.float64(input_xlist)
    # SVR
    data_process_logger.info('training svr')
    clf = svm.SVR()
    parameters = {'C': [1e3, 5e3, 1e4, 5e4, 1e5, 1e2, 1e1, 1e-1], 'kernel': ['rbf', 'sigmoid'],
                  'gamma': [0.0001, 0.0005, 0.001, 0.005, 0.01, 0.1, 0.05]}
    svr_mod = grid_search.GridSearchCV(clf, parameters, n_jobs=10, scoring='mean_absolute_error')
    svr_mod.fit(input_xlist, input_ylist)
    print svr_mod.best_estimator_
    fout = open('%s/models/svr_%s.model' % (project_path, model_label), 'wb')
    cPickle.dump(svr_mod, fout)
    for item in svr_mod.grid_scores_:
        print item
    # GBRT
    data_process_logger.info('training gbrt')
    gbrt_mod = GradientBoostingRegressor()
    gbrt_parameters = {'n_estimators': [100, 200, 300, 350], 'max_depth': [2, 3, 4],
                       'max_leaf_nodes': [10, 20, 30], 'loss': ['huber', 'ls', 'lad']}
    gbrt_mod = grid_search.GridSearchCV(gbrt_mod, gbrt_parameters, n_jobs=10, scoring='mean_absolute_error')
    gbrt_mod.fit(input_xlist, input_ylist)
    gbrt_out = open('%s/models/gbrt_%s.model' % (project_path, model_label), 'wb')
    cPickle.dump(gbrt_mod, gbrt_out)
    print gbrt_mod.best_estimator_
    for item in gbrt_mod.grid_scores_:
        print item
        # clf.fit(reduced_xlist, input_ylist)


def cross_valid(input_x_datas, input_y_datas, cv_model):
    cv = cross_val_score(cv_model, X=input_x_datas, y=input_y_datas, cv=5, scoring='mean_squared_error')
    print cv


def test_datas(input_datas, model):
    input_ranked_list = sorted(input_datas, cmp=lambda x, y: 1 if x[2] - y[2] > 0 else -1)
    xlist = [a[3] for a in input_ranked_list]
    ylist = model.predict(xlist)
    index_ylist = [(i, ylist[i], xlist[i][2]) for i in range(len(ylist))]
    ranked_index_ylist = sorted(index_ylist, cmp=lambda x, y: 1 if x[1] - y[1] > 0 else -1)
    for i in range(len(ranked_index_ylist)):
        print 'pre: %s\t origin: %s\t delta: %s' % (i, ranked_index_ylist[i][0], i - ranked_index_ylist[i][0])




if __name__ == '__main__':
    train_datas = []
    for i in range(310, 311):
        datas = load_csv_data('./datas/%s.csv' % i)
        train_datas += datas
    label_set = []
    vec_set = []
    for i in range(len(train_datas)):
        label_set.append(train_datas[i][2])
        vec_set.append(train_datas[i][3])
    # gbrt_mod = train_model(train_datas)
    model_tag = 'single'
    # train_regression_age_model(input_xlist=vec_set, input_ylist=label_set, model_label=model_tag)
    # xlist = [a[3] for a in datas[100:200]]
    # ylist = [a[2] for a in datas[100:200]]
    # cross_valid(xlist, ylist, gbrt_mod)
    print '--------GBRT:----------'
    gbrt_mod = cPickle.load(open('%s/models/gbrt_%s.model' % (project_path, model_tag), 'rb'))
    datas = load_csv_data('./datas/310.csv')
    data_process_logger.info('testing')
    test_datas(datas, gbrt_mod)
    print '==============='
    datas = load_csv_data('./datas/4.csv')
    test_datas(datas, gbrt_mod)
    print '--------SVR:----------'
    svr_mod = cPickle.load(open('%s/models/svr_%s.model' % (project_path, model_tag), 'rb'))
    datas = load_csv_data('./datas/310.csv')
    data_process_logger.info('testing')
    test_datas(datas, svr_mod)
    print '==============='
    datas = load_csv_data('./datas/4.csv')
    test_datas(datas, svr_mod)
