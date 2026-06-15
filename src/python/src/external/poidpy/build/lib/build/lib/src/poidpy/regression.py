import pandas as pd
from sklearn.model_selection import train_test_split
import statsmodels.formula.api as smf
from sklearn import metrics
import numpy as np

# This file is part of the Demand Generation Tool, Poidpy, developed at KU Leuven.
# Contributors: Lotte Notelaers, Jeroen Verstraete
# License: GNU GENERAL PUBLIC LICENSE Version 3, 29 June 2007, see license.txt
# More information at: https://gitlab.kuleuven.be/ITSCreaLab or contact: ITScrealab@kuleuven.be


def _regression(data, response_variable, variables):
    x = data[variables]
    y = data[response_variable]
    df_regression = pd.concat([x, y], axis=1)
    tmp_var = []
    for ind, var in enumerate(variables):
        tmp_var.append(var)
    model = smf.ols(formula=f'{response_variable} ~ {"+".join(tmp_var)} - 1', data=df_regression)
    result = model.fit()
    coeff = result.params
    print(result.summary2())
    return coeff, result


def regression(data, test_size=0, seed=0, columns_atr=None, columns_prod=None):
    data_test = None
    data_train = data
    if test_size > 0:
        data_train, data_test = train_test_split(data, test_size=test_size, random_state=seed)
    if columns_atr is None:
        columns_atr = ['School', 'Health', 'Leisure',
                       'Shops', 'Services', 'Industry', 'Catering_industry', 'Tourism',
                       'Others', 'Leisure_area']
    if columns_prod is None:
        columns_prod = ['large_residential', 'small_residential']
    if len(columns_atr) > 0:
        betas_atr, result_atr = _regression(data_train, 'attraction', columns_atr)
    else:
        betas_atr, result_atr = None, None
    if len(columns_prod) > 0:
        betas_prod, result_prod = _regression(data_train, 'production', columns_prod)
    else:
        betas_prod, result_prod = None, None

    if test_size > 0:
        if len(columns_atr) > 0:
            y_pred_atr = result_atr.predict(data_test)
            y_real_atr = data_test['attraction']
            # df = pd.DataFrame({'Actual': y_real_atr, 'Predicted': y_pred_atr})
            print('Attraction')
            print('Mean Absolute Error:', metrics.mean_absolute_error(y_real_atr, y_pred_atr))
            print('Mean Squared Error:', metrics.mean_squared_error(y_real_atr, y_pred_atr))
            print('Root Mean Squared Error:', np.sqrt(metrics.mean_squared_error(y_real_atr, y_pred_atr)))
            print('R2 score:', metrics.r2_score(y_real_atr, y_pred_atr))
            print('(uncentered) R2 score:', 1 - sum((y_real_atr - y_pred_atr) ** 2) / sum(y_real_atr ** 2))
        if len(columns_prod) > 0:
            y_pred_prod = result_prod.predict(data_test)
            y_real_prod = data_test['production']
            # df = pd.DataFrame({'Actual': y_real_atr, 'Predicted': y_pred_atr})
            print('Production')
            print('Mean Absolute Error:', metrics.mean_absolute_error(y_real_prod, y_pred_prod))
            print('Mean Squared Error:', metrics.mean_squared_error(y_real_prod, y_pred_prod))
            print('Root Mean Squared Error:', np.sqrt(metrics.mean_squared_error(y_real_prod, y_pred_prod)))
            print('R2 score:', metrics.r2_score(y_real_prod, y_pred_prod))
            print('(uncentered) R2 score:', 1 - sum((y_real_prod - y_pred_prod) ** 2) / sum(y_real_prod ** 2))
    return betas_atr, betas_prod, result_atr, result_prod
